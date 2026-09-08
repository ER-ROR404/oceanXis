"""Unit tests: demo cache readers (fallback_demo path, plan 3.1c)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from app.core.config import Settings
from app.schemas.error import DataNotAvailableError
from app.services.cache import DemoCache


def write_demo_cache(
    root,
    *,
    region: str = "bay_of_bengal",
    date: str = "2024-01-10",
    n_lat: int = 2,
    n_lon: int = 3,
    n_depths: int = 15,
    depths_m: list | None = None,
    offset: float = 0.0,
) -> None:
    """Build a minimal demo-cache dir matching the ml builder format.

    Values = base + offset so tests can distinguish depth planes:
    baseline surface plane is 20.0 + offset, deep plane is 5.0 + offset.
    """
    depths_m = depths_m or [
        0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000,
    ]
    region_dir = root / region
    region_dir.mkdir(parents=True, exist_ok=True)
    lat = [10.0 + i for i in range(n_lat)]
    lon = [88.0 + i for i in range(n_lon)]
    (region_dir / "coordinates.json").write_text(
        json.dumps(
            {
                "region": region,
                "lat": lat,
                "lon": lon,
                "depths_m": depths_m,
                "n_lat": n_lat,
                "n_lon": n_lon,
                "n_depths": n_depths,
            }
        )
    )
    mu = np.full((n_depths, n_lat, n_lon), 5.0 + offset, dtype=np.float32)
    mu[0] = 20.0 + offset  # surface plane distinct
    mu[0, 0, 1] = np.nan  # one land cell (surface)
    np.savez(region_dir / f"{date}.npz", mu=mu, log_var=np.zeros_like(mu))
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "format_version": 1,
                "region": region,
                "model_version": "hybrid_v1",
                "checkpoint": "best.pt",
                "epoch": 83,
                "val_loss": 0.3715,
                "trained_on": "2023-12-31",
                "dates": [date],
                "channel_status": {f"channel_{i}": "available" for i in range(7)},
                "generated_at": "2024-01-01T00:00:00+00:00",
            }
        )
    )


def make_cache(root) -> DemoCache:
    return DemoCache(settings=Settings(demo_cache_dir=str(root)))


class TestDemoCache:
    def test_not_accessible_without_dir(self, tmp_path) -> None:
        cache = DemoCache.__new__(DemoCache)
        cache._settings = None
        # point at a nonexistent dir directly
        cache._cache_dir = tmp_path / "does-not-exist"
        assert not cache.accessible

    def test_assert_accessible_raises(self, tmp_path) -> None:
        cache = DemoCache.__new__(DemoCache)
        cache._settings = None
        cache._cache_dir = tmp_path / "does-not-exist"
        try:
            cache.assert_accessible()
            raise AssertionError("expected DataNotAvailableError")
        except DataNotAvailableError:
            pass

    def test_get_map_returns_none_when_dir_missing(self, tmp_path) -> None:
        cache = DemoCache.__new__(DemoCache)
        cache._settings = None
        cache._cache_dir = tmp_path / "does-not-exist"
        assert cache.get_map("bay_of_bengal", "2024-01-10", 0) is None

    def test_get_map_returns_none_for_unknown_date(self, tmp_path) -> None:
        write_demo_cache(tmp_path)
        cache = make_cache(tmp_path)
        assert cache.get_map("bay_of_bengal", "1999-01-01", 0) is None

    def test_get_map_unknown_region_none(self, tmp_path) -> None:
        write_demo_cache(tmp_path)
        cache = make_cache(tmp_path)
        assert cache.get_map("atlantis", "2024-01-10", 0) is None

    def test_available_dates_reads_manifest_dates(self, tmp_path) -> None:
        write_demo_cache(tmp_path)
        cache = make_cache(tmp_path)
        assert cache.available_dates("bay_of_bengal") == ["2024-01-10"]

    def test_available_dates_empty_without_dir(self, tmp_path) -> None:
        cache = make_cache(tmp_path)
        assert cache.available_dates("bay_of_bengal") == []

    def test_available_dates_unknown_region_empty(self, tmp_path) -> None:
        write_demo_cache(tmp_path)
        cache = make_cache(tmp_path)
        assert cache.available_dates("atlantis") == []

    def test_manifest_property_exposes_loaded_manifest(self, tmp_path) -> None:
        """Public manifest accessor: availability/provenance reads the same
        manifest that feeds fallback_demo (never a second copy of the truth)."""
        write_demo_cache(tmp_path)
        cache = make_cache(tmp_path)
        manifest = cache.manifest
        assert manifest is not None
        assert manifest["region"] == "bay_of_bengal"
        assert manifest["epoch"] == 83
        assert manifest["val_loss"] == 0.3715
        assert manifest["checkpoint"] == "best.pt"

    def test_get_map_surface_plane_values(self, tmp_path) -> None:
        """2D [lat][lon] values at depth 0; land cell is null, never 0.0 (D9)."""
        write_demo_cache(tmp_path, offset=1.0)
        cache = make_cache(tmp_path)
        payload = cache.get_map("bay_of_bengal", "2024-01-10", 0)
        assert payload is not None
        assert payload["region"] == "bay_of_bengal"
        assert payload["date"] == "2024-01-10"
        assert payload["channel"] == "temperature"
        assert payload["depth"] == 0
        assert payload["coordinates"] == {"latitude": [10.0, 11.0], "longitude": [88.0, 89.0, 90.0]}
        assert payload["values"][0] == [21.0, None, 21.0]  # land stays null
        assert payload["values"][1] == [21.0, 21.0, 21.0]

    def test_get_map_deep_plane_selected_by_depth(self, tmp_path) -> None:
        write_demo_cache(tmp_path, offset=2.0)
        cache = make_cache(tmp_path)
        payload = cache.get_map("bay_of_bengal", "2024-01-10", 1000)
        assert payload is not None
        assert all(row == [7.0, 7.0, 7.0] for row in payload["values"])

    def test_get_map_metadata_honest(self, tmp_path) -> None:
        write_demo_cache(tmp_path)
        cache = make_cache(tmp_path)
        payload = cache.get_map("bay_of_bengal", "2024-01-10", 0)
        assert payload is not None
        meta = payload["metadata"]
        assert meta["cached"] is True
        assert meta["model_version"] == "hybrid_v1"
        assert meta["timestamp"] == "2024-01-01T00:00:00+00:00"
        assert "demo cache" in meta["data_source"].lower()

    def test_get_map_depth_not_in_cache_raises_valueerror(self, tmp_path) -> None:
        write_demo_cache(tmp_path, depths_m=[0, 5, 10, 20])
        cache = make_cache(tmp_path)
        with pytest.raises(ValueError):
            cache.get_map("bay_of_bengal", "2024-01-10", 1000)

    # ── profile reader (plan 3.2) ────────────────────────────────────────

    def test_get_profile_snaps_to_nearest_cell(self, tmp_path) -> None:
        """lat/lon snapped to the grid center via nearest index."""
        write_demo_cache(tmp_path, offset=1.0)  # surface 21.0, deep 6.0
        cache = make_cache(tmp_path)
        payload = cache.get_profile("bay_of_bengal", "2024-01-10", 10.3, 88.2)
        assert payload is not None
        assert payload["region"] == "bay_of_bengal"
        assert payload["date"] == "2024-01-10"
        assert payload["lat"] == 10.0  # nearest cell center (row 0)
        assert payload["lon"] == 88.0  # nearest cell center (col 0)
        assert payload["depths"][0] == 0
        assert len(payload["temperatures"]) == 15
        assert payload["temperatures"][0] == 21.0
        assert all(v == 6.0 for v in payload["temperatures"][1:])

    def test_get_profile_reports_nearest_row_for_far_query(self, tmp_path) -> None:
        write_demo_cache(tmp_path)
        cache = make_cache(tmp_path)
        payload = cache.get_profile("bay_of_bengal", "2024-01-10", 11.6, 89.9)
        assert payload is not None
        assert payload["lat"] == 11.0  # row 1
        assert payload["lon"] == 90.0  # col 2

    def test_get_profile_land_cell_all_null_never_zero(self, tmp_path) -> None:
        """All-landsdeep cell (0,1): every depth is null; zero is never fabricated."""
        write_demo_cache(tmp_path)
        region_dir = tmp_path / "bay_of_bengal"
        with np.load(region_dir / "2024-01-10.npz") as data:
            mu = data["mu"]
        mu[:, 0, 1] = np.nan  # land column across all depths
        np.savez(region_dir / "2024-01-10.npz", mu=mu, log_var=np.zeros_like(mu))
        cache = make_cache(tmp_path)
        payload = cache.get_profile("bay_of_bengal", "2024-01-10", 10.0, 89.0)
        assert payload is not None
        assert payload["lat"] == 10.0 and payload["lon"] == 89.0
        assert payload["temperatures"] == [None] * 15
        assert all(v is None for v in payload["temperatures"])

    def test_get_profile_metadata_honest(self, tmp_path) -> None:
        write_demo_cache(tmp_path)
        cache = make_cache(tmp_path)
        payload = cache.get_profile("bay_of_bengal", "2024-01-10", 10.0, 88.0)
        assert payload is not None
        meta = payload["metadata"]
        assert meta["cached"] is True
        assert meta["model_version"] == "hybrid_v1"
        assert meta["timestamp"] == "2024-01-01T00:00:00+00:00"
        assert "demo cache" in meta["data_source"].lower()

    def test_get_profile_none_when_date_missing(self, tmp_path) -> None:
        write_demo_cache(tmp_path)
        cache = make_cache(tmp_path)
        assert cache.get_profile("bay_of_bengal", "1999-01-01", 10.0, 88.0) is None

    def test_get_profile_none_when_region_missing(self, tmp_path) -> None:
        write_demo_cache(tmp_path)
        cache = make_cache(tmp_path)
        assert cache.get_profile("arabian_sea", "2024-01-10", 10.0, 88.0) is None
