"""Demo cache reader: fallback_demo data path when the model service is down.

Reads the cache produced by the ml builder (plan 2.3) — per-date
``<cache_dir>/<region>/<date>.npz`` (mu [15,H,W] float32, NaN land),
``coordinates.json`` (lat/lon/depths_m), root ``manifest.json`` (honest
metadata). NaN land round-trips to JSON null; zero is never fabricated (D9).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import numpy as np

from app.core.config import Settings
from app.schemas.error import DataNotAvailableError


def _nearest_index(values: list[float], target: float) -> int:
    """Index of the grid center closest to target (mirrors ml find_nearest_cell)."""
    return min(range(len(values)), key=lambda i: abs(values[i] - target))


class DemoCache:
    """Reads pre-built fallback maps/profiles from the demo cache dir."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._cache_dir = self._settings.demo_cache_dir
        self._manifest: dict[str, Any] | None = None

    @property
    def accessible(self) -> bool:
        return self._cache_dir.is_dir()

    def get_map(self, region: str, date: str, depth: int) -> dict[str, Any] | None:
        """Ocean-map payload for the pre-built cache entry, or None when absent.

        Values are a 2D [lat][lon] plane at the requested canonical depth;
        land cells are None (never 0.0). Metadata carries the manifest's honest
        provenance (checkpoint/val_loss-era/generated_at live in manifest.json).
        """
        region_dir = self._cache_dir / region
        coords_path = region_dir / "coordinates.json"
        npz_path = region_dir / f"{date}.npz"
        if not (region_dir.is_dir() and coords_path.exists() and npz_path.exists()):
            return None

        coords = json.loads(coords_path.read_text())
        depths_m = coords["depths_m"]
        if depth not in depths_m:
            raise ValueError(f"depth {depth} not present in demo cache")
        depth_idx = depths_m.index(depth)

        mu = np.asarray(np.load(npz_path)["mu"], dtype=np.float32)
        plane = mu[depth_idx]
        values = [
            [None if np.isnan(v) else float(v) for v in row]  # type: ignore[arg-type]
            for row in plane
        ]

        manifest = self._manifest or self._read_manifest()
        metadata = {
            "model_version": (manifest or {}).get("model_version", "hybrid_v1"),
            "data_source": "Pre-built demo cache (hybrid_v1 checkpoint)",
            "preprocessing_version": (
                f"demo-cache-v{(manifest or {}).get('format_version', 1)}"
            ),
            "cached": True,
            "timestamp": (manifest or {}).get("generated_at")
            or datetime.now(UTC).isoformat(),
        }
        return {
            "region": region,
            "date": date,
            "coordinates": {"latitude": coords["lat"], "longitude": coords["lon"]},
            "channel": "temperature",
            "depth": depth,
            "values": values,
            "metadata": metadata,
        }

    def get_profile(self, region: str, date: str, lat: float, lon: float) -> dict[str, Any] | None:
        """Ocean-profile payload at the nearest grid cell, or None when absent.

        Snap semantics mirror the ml service (nearest lat/lon index); snapped
        cell centers are reported honestly in the payload (never the raw query).
        All-land cells return nulls at every depth — zero is never fabricated.
        """
        region_dir = self._cache_dir / region
        coords_path = region_dir / "coordinates.json"
        npz_path = region_dir / f"{date}.npz"
        if not (region_dir.is_dir() and coords_path.exists() and npz_path.exists()):
            return None

        coords = json.loads(coords_path.read_text())
        lat_idx = _nearest_index(coords["lat"], lat)
        lon_idx = _nearest_index(coords["lon"], lon)

        mu = np.asarray(np.load(npz_path)["mu"], dtype=np.float32)
        temps = [
            None if np.isnan(v) else float(v)  # type: ignore[arg-type]
            for v in mu[:, lat_idx, lon_idx]
        ]

        manifest = self._manifest or self._read_manifest()
        metadata = {
            "model_version": (manifest or {}).get("model_version", "hybrid_v1"),
            "data_source": "Pre-built demo cache (hybrid_v1 checkpoint)",
            "preprocessing_version": (
                f"demo-cache-v{(manifest or {}).get('format_version', 1)}"
            ),
            "cached": True,
            "timestamp": (manifest or {}).get("generated_at")
            or datetime.now(UTC).isoformat(),
        }
        return {
            "region": region,
            "date": date,
            "lat": coords["lat"][lat_idx],
            "lon": coords["lon"][lon_idx],
            "depths": coords["depths_m"],
            "temperatures": temps,
            "metadata": metadata,
        }

    def _read_manifest(self) -> dict[str, Any] | None:
        manifest_path = self._cache_dir / "manifest.json"
        if not manifest_path.exists():
            return None
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        self._manifest = manifest if isinstance(manifest, dict) else None
        return self._manifest

    def assert_accessible(self) -> None:
        if not self.accessible:
            raise DataNotAvailableError(message="No demo cache available in this build.")
