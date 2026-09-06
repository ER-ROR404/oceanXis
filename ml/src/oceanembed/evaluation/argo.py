"""ARGO independent validation (evaluation-policy LOCKED, RULE 9).

Predictions vs ARGO profiles by date/location, interpolated to the 15
canonical depths: per-depth RMSE / bias / correlation plus overall metrics.

Honesty rules (Golden Rules 4, 21):
- A profile that does not match (off-domain date, land cell, or before the
  first valid window) is reported as UNMATCHED — never fabricated or dropped.
- A canonical depth without an ARGO observation (shallower/deeper than the
  float sampled, or NaN level) is reported with n=0 and NaN metrics.
- All metrics are computed over valid (prediction AND observation) cells only.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np
import torch

# LOCKED canonical depths (contracts/ml/model-output.schema.json line 23).
CANONICAL_DEPTHS_M = np.array(
    [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000],
    dtype=float,
)
N_CANONICAL = int(CANONICAL_DEPTHS_M.size)


@dataclasses.dataclass
class ArgoProfile:
    """One ARGO float profile (single cycle at a date/location).

    Attributes:
        source_id: Traceable identifier, e.g. float WMO + cycle ("6902914_0123").
        date: Profile datetime (np.datetime64 or str parseable by it).
        lat: Float latitude (degrees north).
        lon: Float longitude (degrees east).
        depths_m: Measured pressure-converted depths, metres, irregular grid.
        temps_c: Measured temperature at each level, degC (NaN = rejected QC).
    """

    source_id: str
    date: np.datetime64
    lat: float
    lon: float
    depths_m: np.ndarray
    temps_c: np.ndarray

    def __post_init__(self) -> None:
        self.date = np.datetime64(self.date)
        self.depths_m = np.asarray(self.depths_m, dtype=float)
        self.temps_c = np.asarray(self.temps_c, dtype=float)
        if self.depths_m.shape != self.temps_c.shape:
            raise ValueError(
                f"{self.source_id}: depth/temperature level count mismatch "
                f"({self.depths_m.size} vs {self.temps_c.size})"
            )


def interp_to_canonical(
    depths_m: np.ndarray,
    temps_c: np.ndarray,
    canonical_m: np.ndarray = CANONICAL_DEPTHS_M,
) -> np.ndarray:
    """Linearly interpolate a float profile onto the canonical depths.

    NaN levels are dropped (QC-rejected data). Duplicate depths are
    averaged. Canonical depths outside the sampled range return NaN — we
    never extrapolate and never invent an observation.
    """
    depths_m = np.asarray(depths_m, dtype=float)
    temps_c = np.asarray(temps_c, dtype=float)

    finite = np.isfinite(depths_m) & np.isfinite(temps_c)
    depths_f = depths_m[finite]
    temps_f = temps_c[finite]
    if depths_f.size == 0:
        return np.full_like(canonical_m, np.nan, dtype=float)

    order = np.argsort(depths_f, kind="stable")
    depths_f = depths_f[order]
    temps_f = temps_f[order]

    # Average temperatures at duplicated depths (np.interp needs strictly
    # increasing xp).
    unique_depths, inverse = np.unique(depths_f, return_inverse=True)
    temps_u = np.zeros_like(unique_depths, dtype=float)
    counts = np.zeros_like(unique_depths, dtype=int)
    for j in range(depths_f.size):
        temps_u[inverse[j]] += temps_f[j]
        counts[inverse[j]] += 1
    temps_u /= np.maximum(counts, 1)

    if unique_depths.size < 2:
        return np.full_like(canonical_m, np.nan, dtype=float)

    values = np.interp(canonical_m, unique_depths, temps_u)
    inside = (canonical_m >= unique_depths[0]) & (canonical_m <= unique_depths[-1])
    values[~inside] = np.nan
    return values


def find_nearest_cell(lat: float, lon: float, lats: np.ndarray, lons: np.ndarray) -> tuple[int, int]:
    """Nearest grid-cell (row, col) to a float position on the 0.25° grid."""
    row = int(np.argmin(np.abs(np.asarray(lats, dtype=float) - lat)))
    col = int(np.argmin(np.abs(np.asarray(lons, dtype=float) - lon)))
    return row, col


def date_to_time_index(
    time_coords: np.ndarray,
    date: np.datetime64,
    max_gap_days: float = 1.0,
) -> int | None:
    """Map a profile date to the nearest day index in the tensor store.

    Returns None when the nearest day is further than ``max_gap_days`` —
    the profile then does not match this dataset (honest "no match")
    instead of silently clamping to a wrong day.
    """
    dates = np.asarray(time_coords)
    target = np.datetime64(date)
    idx = int(np.argmin(np.abs(dates - target)))
    gap_days = float(abs(dates[idx] - target) / np.timedelta64(1, "D"))
    return idx if gap_days <= max_gap_days else None


def score_profiles(pred_degc: np.ndarray, obs_degc: np.ndarray) -> dict[str, float]:
    """Per-depth and overall RMSE / bias / correlation over valid cells.

    Args:
        pred_degc: [n_profiles, 15] model predictions (degC), NaN = invalid.
        obs_degc: [n_profiles, 15] ARGO interpolated observations (degC).

    Returns:
        Flat dict with keys rmse/bias/corr/n_total/n_profiles plus the
        per-depth family rmse_depth_{d}/bias_depth_{d}/corr_depth_{d}/n_depth_{d}.
        NaN means "not enough valid data" — never a fabricated number.
    """
    P = np.asarray(pred_degc, dtype=float)
    obs_arr = np.asarray(obs_degc, dtype=float)
    if P.shape != obs_arr.shape:
        raise ValueError(f"pred/obs shape mismatch: {P.shape} vs {obs_arr.shape}")

    per: dict[str, float] = {}
    pooled_p: list[np.ndarray] = []
    pooled_o: list[np.ndarray] = []

    def _stats(p: np.ndarray, o: np.ndarray) -> tuple[float, float, float, int]:
        valid = np.isfinite(p) & np.isfinite(o)
        n = int(valid.sum())
        if n == 0:
            return float("nan"), float("nan"), float("nan"), 0
        rmse = float(np.sqrt(np.mean((p[valid] - o[valid]) ** 2)))
        bias = float(np.mean(p[valid] - o[valid]))
        corr = float("nan")
        sp, so = np.std(p[valid]), np.std(o[valid])
        if n >= 2 and sp > 0.0 and so > 0.0:
            corr = float(np.corrcoef(p[valid], o[valid])[0, 1])
        return rmse, bias, corr, n

    for d in range(N_CANONICAL):
        rmse, bias, corr, n = _stats(P[:, d], obs_arr[:, d])
        per[f"n_depth_{d}"] = float(n)
        per[f"rmse_depth_{d}"] = rmse
        per[f"bias_depth_{d}"] = bias
        per[f"corr_depth_{d}"] = corr
        if n:
            valid = np.isfinite(P[:, d]) & np.isfinite(obs_arr[:, d])
            pooled_p.append(P[:, d][valid])
            pooled_o.append(obs_arr[:, d][valid])

    if pooled_p:
        Pv = np.concatenate(pooled_p)
        Ov = np.concatenate(pooled_o)
    else:
        Pv = np.array([])
        Ov = np.array([])

    n_total = int(Pv.size)
    rmse, bias, corr, _ = _stats(Pv, Ov)
    report: dict[str, float] = {
        "n_profiles": float(P.shape[0]),
        "n_total": float(n_total),
        "rmse": rmse,
        "bias": bias,
        "corr": corr,
    }
    report.update(per)
    return report


class ArgoValidator:
    """Score a trained model against ARGO float profiles (RULE 9)."""

    def __init__(self, dataset, model: torch.nn.Module, device: str = "cpu") -> None:
        """Args:
            dataset: OceanEmbedDataset over the region tensor store (normalize=True).
            model: Trained OceanEmbedNet producing mu in degC (best weights).
            device: torch device string.
        """
        self.dataset = dataset
        self.model = model.to(device).eval()
        self.device = device
        self.lats = np.asarray(dataset.X["lat"].values, dtype=float)
        self.lons = np.asarray(dataset.X["lon"].values, dtype=float)
        self.time_coords = dataset.X["time"].values
        self.mask = np.asarray(dataset.mask.values, dtype=float)

    def _predict_cell(self, t: int, row: int, col: int) -> np.ndarray:
        """Model prediction [15] (degC) for the given day index and cell."""
        x_win = self.dataset.build_window(t).unsqueeze(0).to(self.device)
        with torch.no_grad():
            mu, _ = self.model(x_win)
        return mu[0, :, row, col].cpu().numpy().astype(float)

    def validate(self, profiles: list[ArgoProfile]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Score every profile; returns (report, per-profile records).

        Records give full traceability: each profile's match status (and the
        reason when unmatched) — missing data is reported, never invented.
        """
        pred_rows: list[np.ndarray] = []
        obs_rows: list[np.ndarray] = []
        records: list[dict[str, Any]] = []

        for p in profiles:
            record: dict[str, Any] = {
                "source_id": p.source_id,
                "date": str(p.date),
                "lat": p.lat,
                "lon": p.lon,
                "matched": False,
                "reason": None,
            }
            t_idx = date_to_time_index(self.time_coords, p.date)
            if t_idx is None or t_idx < self.dataset.T - 1:
                record["reason"] = "date_out_of_window"
            else:
                row, col = find_nearest_cell(p.lat, p.lon, self.lats, self.lons)
                if self.mask[row, col] != 1.0:
                    record["reason"] = "land"
                else:
                    pred = self._predict_cell(t_idx, row, col)
                    obs = interp_to_canonical(p.depths_m, p.temps_c)
                    pred_rows.append(pred)
                    obs_rows.append(obs)
                    record["matched"] = True
            records.append(record)

        if pred_rows:
            report = score_profiles(np.stack(pred_rows), np.stack(obs_rows))
        else:
            report = {
                "n_profiles": float(len(profiles)),
                "n_total": 0.0,
                "rmse": float("nan"),
                "bias": float("nan"),
                "corr": float("nan"),
            }
            for d in range(N_CANONICAL):
                report[f"n_depth_{d}"] = 0.0
                report[f"rmse_depth_{d}"] = float("nan")
                report[f"bias_depth_{d}"] = float("nan")
                report[f"corr_depth_{d}"] = float("nan")

        report["n_matched"] = float(sum(1 for r in records if r["matched"]))
        report["n_unmatched"] = float(sum(1 for r in records if not r["matched"]))
        return report, records
