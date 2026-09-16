"""Tests for the training dataset build script's file-cleanup logic.

Covers robustness against interrupted Copernicus downloads:
  - duplicate artifacts from re-runs (`name_(1).nc`) must be excluded
  - partial writes must not be consumed as data
  - clean chunks are kept
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "build_training_dataset.py"

spec = importlib.util.spec_from_file_location("build_training_dataset", _SCRIPT)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


@pytest.fixture
def processed_dir(tmp_path: Path) -> Path:
    d = tmp_path / "bay_of_bengal"
    (d / "SST").mkdir(parents=True, exist_ok=True)
    return d


class TestFindNcFiles:
    def test_excludes_copernicus_duplicates(self, processed_dir: Path) -> None:
        sst = processed_dir / "SST"
        (sst / "data_2022-01-01-2022-03-31.nc").write_bytes(b"")
        (sst / "data_2022-01-01-2022-03-31_(1).nc").write_bytes(b"")
        (sst / "data_2022-04-01-2022-06-29_(1).nc").write_bytes(b"")
        files = build.find_nc_files(processed_dir, "SST")
        assert [f.name for f in files] == ["data_2022-01-01-2022-03-31.nc"]

    def test_excludes_partial_writes(self, processed_dir: Path) -> None:
        sst = processed_dir / "SST"
        (sst / "data_2022-01-01.nc").write_bytes(b"")
        (sst / "data_2022-01-01.nc.e6j5kdgf").write_bytes(b"")  # temp suffix
        files = build.find_nc_files(processed_dir, "SST")
        assert [f.name for f in files] == ["data_2022-01-01.nc"]

    def test_keeps_all_clean_chunks_sorted(self, processed_dir: Path) -> None:
        sst = processed_dir / "SST"
        (sst / "b.nc").write_bytes(b"")
        (sst / "a.nc").write_bytes(b"")
        files = build.find_nc_files(processed_dir, "SST")
        assert [f.name for f in files] == ["a.nc", "b.nc"]

    def test_empty_dir_returns_empty(self, processed_dir: Path) -> None:
        assert build.find_nc_files(processed_dir, "SST") == []

    def test_missing_channel_dir_returns_empty(self, tmp_path: Path) -> None:
        assert build.find_nc_files(tmp_path / "bay_of_bengal", "SST") == []


class TestIsCleanNc:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("data.nc", True),
            ("data_(1).nc", False),
            ("data_(2).nc", False),
            ("data_(3).nc", False),
            ("data_2022-01-01.nc", True),
        ],
    )
    def test_flag(self, name: str, expected: bool) -> None:
        assert build._is_clean_nc(Path(name)) is expected


class TestBuildOceanMask:
    """Static land/sea mask from the input tensor.

    Regression: the mask was built with ``np.isfinite(x).any(axis=(0, 1))``,
    which marks a cell ocean if ANY channel was valid at ANY time. Real inputs
    are only NaN over land, so that rule made 94.7% of the Bay of Bengal box
    "ocean" and the temperature field rendered as a rectangle. A cell must be
    valid in EVERY channel for the majority of the record instead.
    """

    def _x(self, channel_values: list[list[float]]) -> np.ndarray:
        """Build [T, C, H=1, W] from per-channel value lists."""
        c = len(channel_values)
        t = len(channel_values[0])
        arr = np.zeros((t, c, 1, c), dtype=np.float32)
        for ci, series in enumerate(channel_values):
            arr[:, ci, 0, ci] = series
        return arr

    def test_all_channels_valid_is_ocean(self) -> None:
        x = np.ones((4, 3, 2, 2), dtype=np.float32)
        mask = build.build_ocean_mask(x)
        assert mask.shape == (2, 2)
        assert mask.dtype == bool
        assert mask.all()

    def test_cell_missing_in_any_channel_is_land(self) -> None:
        # Channel 1 is always NaN at column 1 -> that cell is land.
        x = np.ones((4, 2, 1, 2), dtype=np.float32)
        x[:, 1, :, 1] = np.nan
        mask = build.build_ocean_mask(x)
        assert mask.tolist() == [[True, False]]

    def test_transient_cloud_gap_stays_ocean(self) -> None:
        # One channel NaN on 40% of days: still ocean (majority valid).
        x = np.ones((10, 1, 1, 1), dtype=np.float32)
        x[:4, 0, 0, 0] = np.nan
        assert build.build_ocean_mask(x).all()

    def test_persistent_cloud_gap_becomes_land(self) -> None:
        # One channel NaN on 60% of days: below threshold -> land.
        x = np.ones((10, 1, 1, 1), dtype=np.float32)
        x[:6, 0, 0, 0] = np.nan
        assert not build.build_ocean_mask(x).any()

    def test_rejects_non_4d_input(self) -> None:
        with pytest.raises(ValueError):
            build.build_ocean_mask(np.ones((2, 2)))

    def test_coastline_has_interior_land_not_a_border_rectangle(self) -> None:
        """A real coastline mask leaves land strictly inside the domain.

        The original bug masked only the outer ring (land ~absent), which is the
        signature of a rectangle over the domain. A genuine land/sea mask has
        interior land cells.
        """
        n_lat, n_lon = 6, 8
        x = np.ones((5, 3, n_lat, n_lon), dtype=np.float32)  # ocean: all channels finite
        land = np.zeros((n_lat, n_lon), dtype=bool)
        land[n_lat - 1, :] = True  # northern landmass
        land[4, :4] = True
        land[2, 4] = True  # interior island
        for r in range(n_lat):
            for c in range(n_lon):
                if land[r, c]:
                    # Land is overwhelmingly missing, but a SINGLE finite value
                    # survives in one channel/day — exactly the contamination
                    # that made the old ``.any(axis=(0, 1))`` rule call land
                    # "ocean" and paint the whole domain as a rectangle.
                    x[:, :, r, c] = np.nan
                    x[0, 0, r, c] = 1.0

        # Sanity: the old any-based rule would call every cell ocean here.
        assert np.isfinite(x).any(axis=(0, 1)).all(), "fixture must reproduce the bug shape"

        mask = build.build_ocean_mask(x)
        assert mask.shape == (n_lat, n_lon)
        assert not mask[n_lat - 1].any()  # land preserved
        assert mask[0].all()  # open ocean preserved
        # NOT a rectangle: land exists strictly inside the domain.
        assert (~mask[1:-1, 1:-1]).any()
        assert mask.any() and not mask.all()


class TestComputeCommonTimes:
    """Intersection over all inputs AND the GLORYS target axis.

    Regression: inputs contained a legacy 2024-06-01 proof file (in ALL
    channels), so the input-only intersection included that day, but GLORYS
    (2022-2023 only) lacked it -> target.sel(common_times) raised KeyError.
    """

    def _arr(self, days: list[str]) -> object:
        times = np.array(days, dtype="datetime64[D]")
        return xr.DataArray(
            np.zeros(len(times)), coords={"time": times}, dims="time"
        )

    def test_intersects_inputs_and_target(self) -> None:
        arr1 = self._arr(["2022-01-01", "2022-01-02", "2022-01-03"])
        arr2 = self._arr(["2022-01-01", "2022-01-02", "2022-01-03", "2022-01-04"])
        # Target lacks 2022-01-04 (e.g. GLORYS-only gap or legacy proof file)
        target = self._arr(["2022-01-01", "2022-01-02", "2022-01-03"])
        common = build.compute_common_times({"a": arr1, "b": arr2}, target)
        assert common == [
            np.datetime64("2022-01-01"),
            np.datetime64("2022-01-02"),
            np.datetime64("2022-01-03"),
        ]

    def test_drops_days_target_lacks(self) -> None:
        # Regression: all inputs agree on a day, target does not
        arr = self._arr(["2022-01-01", "2024-06-01"])
        target = self._arr(["2022-01-01"])  # GLORYS predates 2024
        common = build.compute_common_times({"a": arr}, target)
        assert common == [np.datetime64("2022-01-01")]

    def test_sorted_ascending(self) -> None:
        arr = self._arr(["2022-01-02", "2022-01-01"])
        target = self._arr(["2022-01-01", "2022-01-02"])
        assert build.compute_common_times({"a": arr}, target) == [
            np.datetime64("2022-01-01"),
            np.datetime64("2022-01-02"),
        ]

    def test_empty_when_no_overlap(self) -> None:
        arr = self._arr(["2022-01-01"])
        target = self._arr(["2023-01-01"])
        assert build.compute_common_times({"a": arr}, target) == []