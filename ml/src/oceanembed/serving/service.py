"""InferenceService — ML-side prediction core.

CRITICAL (verified 2026-09-06 against the trainer and argon validator):
the trained model is called with ``model(x)`` and NO ``day_of_year`` /
``lat`` / ``lon``. ``trainer.py:109,138`` calls ``self.model(x_batch)``
and ``evaluation/argo.py:232`` calls ``self.model(x_win)``. The coord
encoder and ``input_proj`` exist in the architecture (config has
``use_seasonal/use_spatial: true``) but were **never trained** — feeding
coords into the untrained projection corrupts predictions and fails to run
(lat must be 2-D [H,W]). Inference MUST mirror these call sites exactly.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from oceanembed.data.dataset import OceanEmbedDataset
from oceanembed.evaluation.argo import _coord_values, find_nearest_cell

# Session window (spec v2.1 §5). Matching the value the model was trained
# with; constructing the dataset with a different window would silently
# change inputs and corrupt the prediction.
TEMPORAL_WINDOW = 7


class LoadedModel:
    """Loads a checkpoint, preferring the validated best_state_dict.

    Mirrors trainer.resume behavior: ``best_model_state`` when present,
    otherwise ``model_state_dict``. No silent fallback to a missing key.
    """

    def __init__(self, checkpoint_path: str | Path) -> None:
        self.path = Path(checkpoint_path)
        if not self.path.exists():
            raise FileNotFoundError(f"checkpoint not found: {self.path}")
        ckpt = torch.load(self.path, map_location="cpu", weights_only=True)
        state = ckpt.get("best_model_state") or ckpt.get("model_state_dict")
        if state is None:
            raise KeyError(f"checkpoint {self.path} has no model state (keys: {sorted(ckpt)})")
        self.state = state
        self.epoch: int | None = ckpt.get("epoch")
        self.val_loss: float | None = ckpt.get("val_loss")


class InferenceService:
    """Loads the model once; predicts maps and profiles for a region.

    A checkpoint is required to predict but not to list available dates
    (the tensor store alone answers that). The checkpoint is read lazily on
    the first prediction.
    """

    def __init__(
        self,
        region_dir: str | Path,
        cfg: dict,
        checkpoint_path: str | Path | None = None,
        model: torch.nn.Module | None = None,
        device: str = "cpu",
    ) -> None:
        """Args:
        region_dir: Region tensor store (X.zarr/Y.zarr/mask.zarr/stats).
        cfg: hybrid_v1 model block (in_channels, out_channels, convlstm_*,
            use_seasonal, use_spatial).
        checkpoint_path: Trained checkpoint (best.pt); optional for date-only
            usage, required for predict/predict_profile.
        model: Optional pre-built model (test injection). When None it is
            built from cfg at load time.
        device: torch device string.
        """
        self.region_dir = Path(region_dir)
        self.cfg = cfg
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        self._model = model
        self._model_loaded = model is not None
        self.device = device
        self.dataset = OceanEmbedDataset(
            self.region_dir, temporal_window=TEMPORAL_WINDOW, normalize=True
        )
        self.lats = _coord_values(self.dataset.X, ["latitude", "lat"])
        self.lons = _coord_values(self.dataset.X, ["longitude", "lon"])
        self.time_coords = self.dataset.X["time"].values
        self.mask = np.asarray(self.dataset.mask.values, dtype=float)

    @property
    def model(self) -> torch.nn.Module:
        if not self._model_loaded:
            self.load_model()
        return self._model

    def load_model(self) -> None:
        """Build the network from cfg and load the checkpoint weights."""
        if self.checkpoint_path is None:
            raise FileNotFoundError(
                "no checkpoint_path given; cannot load a model for prediction"
            )
        if self._model is None:
            from oceanembed.models.reconstruction_net import OceanEmbedNet

            b = self.cfg  # hybrid_v1 model block
            self._model = OceanEmbedNet(
                in_channels=b["in_channels"],
                out_channels=b["out_channels"],
                use_seasonal=b.get("use_seasonal", True),
                use_spatial=b.get("use_spatial", True),
                convlstm_hidden=b.get("convlstm_hidden", 128),
                convlstm_layers=b.get("convlstm_layers", 1),
            )
        self._model.load_state_dict(self.ckpt.state)
        self._model.to(self.device).eval()
        self._model_loaded = True

    # ── public API ────────────────────────────────────────────────────────
    def available_dates(self) -> list[str]:
        """ISO date strings for every day the tensor store covers."""
        return [str(np.datetime_as_string(d, unit="D")) for d in self.time_coords]

    def predict(self, date: str) -> tuple[torch.Tensor, torch.Tensor, np.ndarray]:
        """Full-field prediction for a date.

        Returns (mu, log_var, mask) with mu/log_var [15, H, W] (NaN on land,
        matching the contract's null transport). Raises ValueError for a date
        outside the tensor range / inside the window boundary.
        """
        t = self._date_to_index(date)
        if t < self.dataset.T - 1:
            raise ValueError(
                f"date {date} is inside the {TEMPORAL_WINDOW}-day window boundary "
                f"(t={t} < T-1={self.dataset.T - 1})"
            )
        x_win = self.dataset.build_window(t).unsqueeze(0).to(self.device)  # [1,T,C,H,W]
        with torch.no_grad():
            mu, log_var = self.model(x_win)  # NO coords — verified call site
        mu = mu[0].cpu()  # [D, H, W]
        log_var = log_var[0].cpu()
        # Land mask -> NaN (frontend/contract treat NaN as masked; never 0.0)
        land = torch.from_numpy(self.mask != 1.0)
        mu = mu.masked_fill(land, float("nan"))
        log_var = log_var.masked_fill(land, float("nan"))
        return mu, log_var, self.mask

    def predict_profile(self, date: str, lat: float, lon: float) -> tuple[list[float | None], list[float | None]]:
        """Nearest-cell (temperatures, log_vars) columns [15] for a date/position.

        Land cells (and out-of-domain dates) return None per depth — honestly
        "no data here", never a fabricated value. log_vars are the raw model
        uncertainty output; the backend converts to public sigma on the wire.
        """
        row, col = find_nearest_cell(lat, lon, self.lats, self.lons)
        if self.mask[row, col] != 1.0:
            return [None] * self.dataset.n_depths, [None] * self.dataset.n_depths
        mu, log_var, _ = self.predict(date)
        temps = mu[:, row, col].tolist()
        log_vars = log_var[:, row, col].tolist()
        to_ticks: list[float | None] = [float(v) if v == v else None for v in temps]
        to_logs: list[float | None] = [float(v) if v == v else None for v in log_vars]
        return to_ticks, to_logs

    # ── internals ─────────────────────────────────────────────────────────
    @property
    def ckpt(self) -> LoadedModel:
        if self.checkpoint_path is None:
            raise FileNotFoundError(
                "no checkpoint_path given; cannot load a model for prediction"
            )
        return LoadedModel(self.checkpoint_path)

    def _date_to_index(self, date: str) -> int:
        """Index of the day closest to ``date`` (within a 1-day tolerance)."""
        target = np.datetime64(date)
        idx = int(np.argmin(np.abs(self.time_coords - target)))
        gap = float(abs(self.time_coords[idx] - target) / np.timedelta64(1, "D"))
        if gap > 1.0:
            raise ValueError(f"date {date} not present in tensor store (nearest gap {gap:.1f}d)")
        return idx
