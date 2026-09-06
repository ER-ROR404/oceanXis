"""ARGO GDAC acquisition + harmonization for independent validation (RULE 9).

Transforms raw Argo GDAC float profiles into the harmonized JSON store
consumed by ``ml/scripts/evaluate_argo.py`` (evaluation-policy LOCKED,
ADR-012). The scientific gate agreed in the evaluation policy is enforced
here: profile dates are selected ONLY from the temporal validation window
(never the training period). Selection is the responsibility of this module,
not of the validator.

Emitted contract (flat list, matches ml/scripts/evaluate_argo.py:load_profiles):
    [{"source_id", "date", "lat", "lon", "depths_m", "temps_c"}, ...]

Documented assumptions:
- Pressure (dbar) is used as a depth proxy in meters (1 dbar ~ 1.0 m, <1%
  error); the same approximation community tools (e.g. argopy) use for
  coarse depth comparisons against gridded products in this regime.
- Profile date is rounded to the nearest day to align with the daily grid;
  the validator matches dates to grid days within 24 h.
- Where both adjusted and raw measurements exist, adjusted values with
  ADJUSTED_QC == 1 are preferred; otherwise raw values with QC == 1.
- The validation-window split MUST mirror ml/src/oceanembed/data/dataset.py
  (temporal_locked): n_samples = n_time - T + 1,
  n_val = max(1, int(n_samples * val_fraction)),
  first validation target day index = (n_samples - n_val) + T - 1.
  This module deliberately re-implements it so data-engineering never
  imports ML code (AGENTS.md environment isolation).

No network access in this module; downloading thin wrappers live in the
acquisition script.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import xarray as xr

logger = logging.getLogger(__name__)

JULD_EPOCH = date(1950, 1, 1)


@dataclass(frozen=True)
class IndexRow:
    """One row of the Argo global index (ar_index_global_prof.txt).

    ``lat``/``lon`` are None for positionless rows (GDAC index entries
    with blank coordinate fields); select_rows excludes those silently.
    """

    file: str
    date: date
    lat: float | None
    lon: float | None


# --------------------------------------------------------------------------- #
# Index parsing
# --------------------------------------------------------------------------- #


def parse_index(text: str) -> list[IndexRow]:
    """Parse the Argo global index text into IndexRow records.

    Handles the current GDAC index format 2.0 (columns: file, date
    [YYYYMMDDHHMMSS], latitude, longitude, ocean, profiler_type,
    institution, date_update; file paths relative to the GDAC ``/dac``
    root) and the legacy 9-column format with YYYYMMDD dates. Skips
    comment lines (``#``), the CSV header, and malformed lines.
    """
    rows: list[IndexRow] = []
    dropped_empty_date = 0
    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("file,"):
            continue
        parts = line.split(",")
        if len(parts) < 8:
            logger.warning("index line %d: skipping malformed row", line_no)
            continue
        try:
            file_, date_s = parts[0].strip(), parts[1].strip()
            # Empty date field: normal GDAC condition (e.g. MEDS float
            # blocks); such a row can never be selected into a validation
            # window, so drop it silently instead of warning per row.
            if not date_s:
                dropped_empty_date += 1
                continue
            row_date: date | None = None
            for fmt in ("%Y%m%d%H%M%S", "%Y%m%d"):
                try:
                    row_date = datetime.strptime(date_s, fmt).date()
                    break
                except ValueError:
                    continue
            if row_date is None:
                raise ValueError(f"unparsable date {date_s!r}")
            # Blank coordinate fields are a normal GDAC condition
            # (positionless index entries); keep the row with None so
            # select_rows can exclude it silently later.
            lat_s, lon_s = parts[2].strip(), parts[3].strip()
            lat = float(lat_s) if lat_s else None
            lon = float(lon_s) if lon_s else None
            rows.append(IndexRow(file=file_, date=row_date, lat=lat, lon=lon))
        except (ValueError, TypeError):
            logger.warning("index line %d: skipping unparsable row", line_no)
    if dropped_empty_date:
        logger.info("index: dropped %d rows with empty date field", dropped_empty_date)
    return rows


# --------------------------------------------------------------------------- #
# Selection
# --------------------------------------------------------------------------- #


def select_rows(
    rows: list[IndexRow],
    lon_min: float | None = None,
    lon_max: float | None = None,
    lat_min: float | None = None,
    lat_max: float | None = None,
    min_date: date | None = None,
    max_date: date | None = None,
) -> list[IndexRow]:
    """Filter index rows by inclusive bounding box and/or date window.

    All filters are optional; a filter with ``None`` bounds is skipped.
    """
    picked: list[IndexRow] = []
    for row in rows:
        # Positionless index rows cannot be region-matched; drop silently
        # (normal GDAC condition, not a data error).
        if row.lat is None or row.lon is None:
            continue
        if lon_min is not None and row.lon < lon_min:
            continue
        if lon_max is not None and row.lon > lon_max:
            continue
        if lat_min is not None and row.lat < lat_min:
            continue
        if lat_max is not None and row.lat > lat_max:
            continue
        if min_date is not None and row.date < min_date:
            continue
        if max_date is not None and row.date > max_date:
            continue
        picked.append(row)
    return picked


# --------------------------------------------------------------------------- #
# Validation window (MUST mirror ml/.../dataset.py temporal_locked split)
# --------------------------------------------------------------------------- #


def compute_validation_window(
    time_values: np.ndarray,
    temporal_window: int = 7,
    val_fraction: float = 0.2,
) -> tuple[date, date]:
    """Return the inclusive (start, end) ARGO validation period as dates.

    Mirrors create_dataloaders: first ``val_fraction`` of samples are held
    out as validation AFTER training samples in time. The returned range is
    the target days of those validation samples — days the model never
    trains on.

    Args:
        time_values: 1-D array of datetime64 values (the tensor-store time
            axis).
        temporal_window: Input window size (default 7), must be >= 1.
        val_fraction: Fraction held out (default 0.2), must be in (0, 1].

    Returns:
        (validation_start_date, validation_end_date) inclusive.
    """
    if temporal_window < 1:
        raise ValueError(f"temporal_window must be >= 1, got {temporal_window}")
    if not 0.0 < val_fraction <= 1.0:
        raise ValueError(f"val_fraction must be in (0, 1], got {val_fraction}")

    n_samples = int(len(time_values) - temporal_window + 1)
    n_val = max(1, int(n_samples * val_fraction))
    n_train = n_samples - n_val
    first_val_target_idx = n_train + temporal_window - 1
    start = _np_day(time_values[first_val_target_idx])
    end = _np_day(time_values[-1])
    logger.info(
        "validation window: n_samples=%d n_val=%d -> %s .. %s",
        n_samples,
        n_val,
        start,
        end,
    )
    return start, end


def _np_day(value: np.datetime64) -> date:
    """Convert a day-resolution numpy datetime to a datetime.date."""
    result = np.datetime64(value, "D").item()
    if isinstance(result, date):
        return result
    return result.date()


# --------------------------------------------------------------------------- #
# NetCDF profile parsing (QC filtering)
# --------------------------------------------------------------------------- #


def _qc_ok(qc) -> bool:
    """Argo QC flag is one character; ``"1"`` means good."""
    try:
        value = np.asarray(qc).item()
    except (ValueError, TypeError):
        return False
    if isinstance(value, bytes):
        value = value.decode("ascii", errors="replace")
    return str(value).strip() in ("1", "10", "1 ")


def _measurement_series(
    ds: xr.Dataset, base: str, adj: str, adj_qc: str, qc_flag: str
) -> tuple[np.ndarray, np.ndarray]:
    """Return (values, valid_mask) for a measurement variable.

    Adjusted values (ADJUSTED_QC == 1) are preferred per level; otherwise
    raw values with QC == 1 are used. A level is valid if its chosen value
    is finite.
    """
    values = np.asarray(ds[base].isel(N_PROF=0).values, dtype=float).copy()
    qc_values = np.asarray(ds[qc_flag].isel(N_PROF=0).values)
    raw_ok = np.array([_qc_ok(v) for v in qc_values], dtype=bool)

    if adj in ds and adj_qc in ds:
        adj_values = np.asarray(ds[adj].isel(N_PROF=0).values, dtype=float).copy()
        adj_qc_values = np.asarray(ds[adj_qc].isel(N_PROF=0).values)
        adj_ok = np.array([_qc_ok(v) for v in adj_qc_values], dtype=bool)
        use_adjusted = adj_ok & raw_ok
        values = np.where(use_adjusted, adj_values, values)
        valid = use_adjusted | raw_ok
    else:
        valid = raw_ok

    valid &= np.isfinite(values)
    return values, valid


def parse_gdac_profile(ds: xr.Dataset, source_id: str) -> dict | None:
    """Extract a harmonized profile entry from one Argo profile NetCDF.

    Args:
        ds: Opened Argo profile dataset (N_PROF=1 expected, first profile
            used).
        source_id: Identifier recorded in the store (e.g. ``4903456_001``).

    Returns:
        Entry dict {source_id, date, lat, lon, depths_m, temps_c}, or None
        if the profile is unusable (bad JULD QC, or no valid levels).
    """
    juld = float(np.asarray(ds["JULD"].isel(N_PROF=0).values).item())
    if not _qc_ok(np.asarray(ds["JULD_QC"].isel(N_PROF=0).values).item()):
        logger.warning("profile %s: JULD_QC not good, skipping", source_id)
        return None

    profile_date = (JULD_EPOCH + timedelta(days=int(round(juld)))).isoformat()
    lat = float(np.asarray(ds["LATITUDE"].isel(N_PROF=0).values).item())
    lon = float(np.asarray(ds["LONGITUDE"].isel(N_PROF=0).values).item())

    pres_values, pres_ok = _measurement_series(
        ds, "PRES", "PRES_ADJUSTED", "PRES_ADJUSTED_QC", "PRES_QC"
    )
    temp_values, temp_ok = _measurement_series(
        ds, "TEMP", "TEMP_ADJUSTED", "TEMP_ADJUSTED_QC", "TEMP_QC"
    )

    valid = pres_ok & temp_ok
    if not bool(valid.any()):
        logger.warning("profile %s: no valid levels, skipping", source_id)
        return None

    # dbar -> meters proxy (documented assumption, see module docstring).
    depths_m = pres_values[valid].tolist()
    temps_c = temp_values[valid].tolist()
    return {
        "source_id": source_id,
        "date": profile_date,
        "lat": lat,
        "lon": lon,
        "depths_m": depths_m,
        "temps_c": temps_c,
    }


# --------------------------------------------------------------------------- #
# Cache loading + JSON store
# --------------------------------------------------------------------------- #


def load_gdac_files(cache_dir: Path, rows: list[IndexRow]) -> list[dict]:
    """Load and parse Argo profile NetCDF files from a local GDAC cache.

    Files are resolved as ``cache_dir / "dac" / row.file`` (index file
    paths are relative to the GDAC ``/dac`` root, matching the FTP
    layout documented in the index header). A row whose parsed profile
    date disagrees with its index date by more than one day is skipped
    (honest provenance: never validate with a misdated profile).

    Args:
        cache_dir: Local mirror root of the GDAC (holds a ``dac/`` tree).
        rows: Index rows (typically already selected by region/window).

    Returns:
        Harmonized profile entries (empty list if nothing usable).
    """
    entries: list[dict] = []
    base = Path(cache_dir) / "dac"
    for row in rows:
        path = base / row.file
        if not path.exists():
            logger.warning("missing GDAC file %s, skipping", path)
            continue
        try:
            # Disable CF time decoding: real GDAC files declare JULD units
            # "days since 1950-01-01" which xarray would decode into
            # datetime64[ns]; converting that back via float() produced
            # "Python int too large to convert to C int" on every real
            # profile (version-fragile across xarray/netCDF4 stacks).
            # Keeping the raw days-since-1950 float matches the JULD_EPOCH
            # convention used below. mask_and_scale stays enabled so
            # _FillValue levels arrive as NaN.
            with xr.open_dataset(path, decode_times=False, decode_timedelta=False) as ds:
                entry = parse_gdac_profile(ds, source_id=path.stem)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("failed to parse %s: %s", path, exc)
            continue
        if entry is None:
            continue
        entry_date = date.fromisoformat(entry["date"])
        if abs((entry_date - row.date).days) > 1:
            logger.warning(
                "profile %s: index date %s vs file date %s disagree by >1 day, skipping",
                entry["source_id"],
                row.date,
                entry_date,
            )
            continue
        entries.append(entry)
    return entries


def write_profiles_json(profiles: list[dict], out_path: Path, provenance: dict) -> Path:
    """Write the flat profiles store consumed by the ARGO validator.

    The main file is the flat list exactly as ``evaluate_argo.py:load_profiles``
    expects; provenance is written to a sibling file so the contract stays
    untouched.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(profiles, indent=2) + "\n")
    prov_path = out_path.with_suffix(".provenance.json")
    prov_path.write_text(json.dumps(provenance, indent=2) + "\n")
    logger.info("wrote %d profiles to %s", len(profiles), out_path)
    return out_path


def load_time_index(region_dir: Path) -> np.ndarray:
    """Load the tensor-store time axis (datetime64 values) from X.zarr."""
    with xr.open_zarr(str(Path(region_dir) / "X.zarr")) as store:
        return np.asarray(store["time"].values)
