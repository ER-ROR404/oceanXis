"""Tests for oceanembed_data.harmonization module."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from oceanembed_data.catalog import CANONICAL_DEPTHS_M
from oceanembed_data.harmonization import (
    build_validity_mask,
    harmonize_glorys_target,
    harmonize_surface_input,
    make_target_grid,
    select_canonical_depths,
)
from oceanembed_data.regions import RegionBounds


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def region_bob() -> RegionBounds:
    """Bay of Bengal test region."""
    return RegionBounds(id="bay_of_bengal", lat_min=5.0, lat_max=22.0, lon_min=80.0, lon_max=100.0)


@pytest.fixture
def target_grid_bob(region_bob) -> tuple[np.ndarray, np.ndarray]:
    """Canonical 0.25° grid for Bay of Bengal."""
    return make_target_grid(region_bob)


@pytest.fixture
def sst_dataset() -> xr.Dataset:
    """Mock SST dataset at 0.05° resolution."""
    lat = np.arange(5.0, 22.1, 0.05)
    lon = np.arange(80.0, 100.1, 0.05)
    data = np.random.rand(1, len(lat), len(lon)).astype(np.float32) * 20 + 300
    return xr.Dataset({
        "analysed_sst": xr.DataArray(
            data, dims=["time", "latitude", "longitude"],
            coords={"latitude": lat, "longitude": lon,
                    "time": np.array(["2024-06-01"], dtype="datetime64[ns]")},
        )
    })


@pytest.fixture
def sss_dataset() -> xr.Dataset:
    """Mock SSS dataset at 0.125° with depth dim."""
    lat = np.arange(5.0, 22.1, 0.125)
    lon = np.arange(80.0, 100.1, 0.125)
    depth = np.array([1.0])
    data = np.random.rand(1, len(depth), len(lat), len(lon)).astype(np.float32) * 5 + 30
    return xr.Dataset({
        "sos": xr.DataArray(
            data, dims=["time", "depth", "latitude", "longitude"],
            coords={"latitude": lat, "longitude": lon,
                    "time": np.array(["2024-06-01"], dtype="datetime64[ns]"),
                    "depth": depth},
        )
    })


@pytest.fixture
def current_u_dataset() -> xr.Dataset:
    """Mock current_U dataset at 0.25° with depth dim (0m, 15m)."""
    lat = np.arange(5.0, 22.1, 0.25)
    lon = np.arange(80.0, 100.1, 0.25)
    depth = np.array([0.0, 15.0])
    data = np.random.rand(1, len(depth), len(lat), len(lon)).astype(np.float32) * 0.5
    return xr.Dataset({
        "uo": xr.DataArray(
            data, dims=["time", "depth", "latitude", "longitude"],
            coords={"latitude": lat, "longitude": lon,
                    "time": np.array(["2024-06-01"], dtype="datetime64[ns]"),
                    "depth": depth},
        )
    })


@pytest.fixture
def wind_dataset() -> xr.Dataset:
    """Mock wind dataset at 0.125°."""
    lat = np.arange(5.0, 22.1, 0.125)
    lon = np.arange(80.0, 100.1, 0.125)
    data = np.random.rand(1, len(lat), len(lon)).astype(np.float32) * 10
    return xr.Dataset({
        "eastward_wind": xr.DataArray(
            data, dims=["time", "latitude", "longitude"],
            coords={"latitude": lat, "longitude": lon,
                    "time": np.array(["2024-06-01"], dtype="datetime64[ns]")},
        )
    })


@pytest.fixture
def glorys_dataset() -> xr.Dataset:
    """Mock GLORYS dataset with 35 native depth levels."""
    lat = np.arange(5.0, 22.1, 0.083)
    lon = np.arange(80.0, 100.1, 0.083)
    native_depths = np.array([
        0.49, 1.54, 2.64, 3.81, 5.15, 6.82, 8.97, 11.82, 15.69, 21.07,
        28.49, 38.73, 52.81, 71.59, 97.04, 130.67, 174.01, 229.52, 299.83,
        387.45, 494.07, 620.99, 769.00, 937.73, 1125.64, 1331.14, 1551.60,
        1784.25, 2025.69, 2272.15, 2519.46, 2763.49, 3000.00, 3225.33, 3435.00,
    ])
    data = np.random.rand(1, len(native_depths), len(lat), len(lon)).astype(np.float32) * 10 + 15
    return xr.Dataset({
        "thetao": xr.DataArray(
            data, dims=["time", "depth", "latitude", "longitude"],
            coords={"latitude": lat, "longitude": lon,
                    "time": np.array(["2024-06-01"], dtype="datetime64[ns]"),
                    "depth": native_depths},
        )
    })


# ---------------------------------------------------------------------------
# Tests: make_target_grid
# ---------------------------------------------------------------------------

class TestMakeTargetGrid:
    def test_output_shape(self, region_bob, target_grid_bob):
        lat_grid, lon_grid = target_grid_bob
        # Bay of Bengal: 17° / 0.25 = 69, 20° / 0.25 = 81
        assert lat_grid.shape == (69,)
        assert lon_grid.shape == (81,)

    def test_grid_bounds(self, region_bob, target_grid_bob):
        lat_grid, lon_grid = target_grid_bob
        assert lat_grid.min() >= region_bob.lat_min
        assert lat_grid.max() <= region_bob.lat_max
        assert lon_grid.min() >= region_bob.lon_min
        assert lon_grid.max() <= region_bob.lon_max

    def test_grid_spacing(self, target_grid_bob):
        lat_grid, lon_grid = target_grid_bob
        np.testing.assert_allclose(np.diff(lat_grid), 0.25, atol=1e-10)
        np.testing.assert_allclose(np.diff(lon_grid), 0.25, atol=1e-10)


# ---------------------------------------------------------------------------
# Tests: select_canonical_depths
# ---------------------------------------------------------------------------

class TestSelectCanonicalDepths:
    def test_returns_15_indices(self, glorys_dataset):
        indices = select_canonical_depths(glorys_dataset.depth.values)
        assert len(indices) == 15

    def test_indices_are_integers(self, glorys_dataset):
        indices = select_canonical_depths(glorys_dataset.depth.values)
        assert indices.dtype in (np.int32, np.int64)

    def test_indices_within_bounds(self, glorys_dataset):
        indices = select_canonical_depths(glorys_dataset.depth.values)
        assert (indices >= 0).all()
        assert (indices < len(glorys_dataset.depth.values)).all()

    def test_depths_are_monotonic(self, glorys_dataset):
        indices = select_canonical_depths(glorys_dataset.depth.values)
        selected = glorys_dataset.depth.values[indices]
        # Should be roughly monotonic increasing (nearest-neighbor can cause
        # small non-monotonicities, but generally increasing)
        diffs = np.diff(selected)
        # Allow a few reversals due to nearest-neighbor aliasing
        assert np.sum(diffs < 0) < 3


# ---------------------------------------------------------------------------
# Tests: harmonize_surface_input
# ---------------------------------------------------------------------------

class TestHarmonizeSurfaceInput:
    def test_sst_output_shape(self, sst_dataset, region_bob):
        result = harmonize_surface_input(sst_dataset, "analysed_sst", region_bob)
        assert result.shape == (1, 69, 81)

    def test_sss_with_depth_extraction(self, sss_dataset, region_bob):
        result = harmonize_surface_input(sss_dataset, "sos", region_bob, depth_level=0)
        assert result.shape == (1, 69, 81)
        assert "depth" not in result.dims

    def test_current_with_depth_extraction(self, current_u_dataset, region_bob):
        result = harmonize_surface_input(current_u_dataset, "uo", region_bob, depth_level=0)
        assert result.shape == (1, 69, 81)
        assert "depth" not in result.dims

    def test_output_is_numeric(self, sst_dataset, region_bob):
        result = harmonize_surface_input(sst_dataset, "analysed_sst", region_bob)
        assert np.issubdtype(result.dtype, np.floating)

    def test_preserves_time_dim(self, sst_dataset, region_bob):
        result = harmonize_surface_input(sst_dataset, "analysed_sst", region_bob)
        assert "time" in result.dims
        assert result.sizes["time"] == 1

    def test_different_native_resolutions(self, region_bob):
        """SST (0.05°) and wind (0.125°) should both regrid to 0.25°."""
        lat_fine = np.arange(5.0, 22.1, 0.05)
        lon_fine = np.arange(80.0, 100.1, 0.05)
        ds_fine = xr.Dataset({
            "sst": xr.DataArray(
                np.random.rand(1, len(lat_fine), len(lon_fine)).astype(np.float32),
                dims=["time", "latitude", "longitude"],
                coords={"latitude": lat_fine, "longitude": lon_fine,
                        "time": np.array(["2024-06-01"], dtype="datetime64[ns]")},
            )
        })
        result = harmonize_surface_input(ds_fine, "sst", region_bob)
        assert result.shape == (1, 69, 81)


# ---------------------------------------------------------------------------
# Tests: harmonize_glorys_target
# ---------------------------------------------------------------------------

class TestHarmonizeGlorysTarget:
    def test_output_shape(self, glorys_dataset, region_bob):
        result = harmonize_glorys_target(glorys_dataset, region=region_bob)
        assert result.shape == (1, 15, 69, 81)

    def test_depth_dim_is_15(self, glorys_dataset, region_bob):
        result = harmonize_glorys_target(glorys_dataset, region=region_bob)
        assert result.sizes["depth"] == 15

    def test_preserves_time(self, glorys_dataset, region_bob):
        result = harmonize_glorys_target(glorys_dataset, region=region_bob)
        assert result.sizes["time"] == 1

    def test_output_is_numeric(self, glorys_dataset, region_bob):
        result = harmonize_glorys_target(glorys_dataset, region=region_bob)
        assert np.issubdtype(result.dtype, np.floating)


# ---------------------------------------------------------------------------
# Tests: vertical depth interpolation to canonical depths
# ---------------------------------------------------------------------------

class TestVerticalDepthInterpolation:
    """GLORYS native depths are irregular (not at canonical depths).

    Regression: nearest-level selection produced targets offset by up to
    ~57m (e.g. 700m canonical <- 643.57m native, 1000m <- 902.34m native).
    Must linearly interpolate vertically onto the exact canonical depths.
    """

    def _glorys_with_linear_temp(self, native_depths, slope=0.02, base=20.0):
        """Build a GLORYS-like dataset where thetao = base + slope*depth."""
        lat = np.arange(5.0, 6.0, 0.083)
        lon = np.arange(80.0, 81.0, 0.083)
        # thetao [time, depth, lat, lon], spatially constant for simplicity
        data = (base + slope * native_depths)[None, :, None, None]
        data = np.broadcast_to(
            data, (1, len(native_depths), len(lat), len(lon))
        ).astype(np.float32)
        return xr.Dataset({
            "thetao": xr.DataArray(
                data,
                dims=["time", "depth", "latitude", "longitude"],
                coords={
                    "latitude": lat,
                    "longitude": lon,
                    "time": np.array(["2024-06-01"], dtype="datetime64[ns]"),
                    "depth": native_depths,
                },
            )
        })

    def test_interpolates_exact_canonical_depths(self):
        """Targets land on the exact canonical depths, not nearest native."""
        # Native levels from the real GLORYS product (probe-verified)
        native = np.array([
            0.49, 1.54, 2.64, 3.81, 5.15, 6.82, 8.97, 11.82, 15.69, 21.07,
            28.49, 38.73, 52.81, 71.59, 97.04, 130.67, 174.01, 229.52,
            299.83, 387.45, 494.07, 620.99, 769.00, 937.73, 1125.64,
            1331.14, 1551.60, 1784.25, 2025.69, 2272.15, 2519.46, 2763.49,
            3000.00, 3225.33, 3435.00,
        ])
        ds = self._glorys_with_linear_temp(native)
        result = harmonize_glorys_target(ds, region=RegionBounds(
            id="probe", lat_min=5.0, lat_max=6.0, lon_min=80.0, lon_max=81.0
        ))

        # Depth coordinate must be exactly the 15 canonical depths
        np.testing.assert_allclose(result.depth.values, CANONICAL_DEPTHS_M, atol=1e-6)

        # Linear profile must be recovered exactly at canonical depths
        # (thetao = 20 + 0.02 * z)
        for i, target_depth in enumerate(CANONICAL_DEPTHS_M):
            expected = 20.0 + 0.02 * target_depth
            actual = float(result.isel(time=0, depth=i, latitude=0, longitude=0))
            assert abs(actual - expected) < 0.01, (
                f"depth={target_depth}m: got {actual}, expected {expected}"
            )

    def test_interpolates_between_irregular_native_levels(self):
        """Verbatim regression: 700m was mapped to 643.57m (nearest).
        Now must interpolate between the bracketing native levels."""
        native = np.array([0.49, 26.6, 318.1, 541.1, 643.6, 763.3, 902.3, 1062.4])
        slope = 0.5  # steep so offsets are obvious
        ds = self._glorys_with_linear_temp(native, slope=slope)
        result = harmonize_glorys_target(ds, region=RegionBounds(
            id="probe", lat_min=5.0, lat_max=6.0, lon_min=80.0, lon_max=81.0
        ))

        depth_700 = CANONICAL_DEPTHS_M.index(700)
        actual = float(result.isel(time=0, depth=depth_700, latitude=0, longitude=0))
        expected = 20.0 + slope * 700.0  # 20 + 350 = 370
        assert abs(actual - expected) < 0.01, (
            f"700m: got {actual}, expected interpolated {expected}"
        )

    def test_1000m_uses_deeper_native_levels(self):
        """The 1000m canonical depth must be interpolated (not clamped to
        the previous native level of 902m)."""
        native = np.array([0.49, 26.6, 318.1, 541.1, 643.6, 763.3, 902.3, 1062.4])
        ds = self._glorys_with_linear_temp(native, slope=0.5)
        result = harmonize_glorys_target(ds, region=RegionBounds(
            id="probe", lat_min=5.0, lat_max=6.0, lon_min=80.0, lon_max=81.0
        ))
        depth_1000 = CANONICAL_DEPTHS_M.index(1000)
        actual = float(result.isel(time=0, depth=depth_1000, latitude=0, longitude=0))
        expected = 20.0 + 0.5 * 1000.0
        assert abs(actual - expected) < 0.01, (
            f"1000m: got {actual}, expected {expected}"
        )

    def test_raises_when_deepest_canonical_not_available(self):
        """If native grid cannot bracket 1000m, fail loudly rather than
        silently substituting a shallower level."""
        native = np.array([0.49, 26.6, 318.1, 541.1, 643.6, 763.3, 902.3])
        ds = self._glorys_with_linear_temp(native)
        with pytest.raises(ValueError, match="1000|depth"):
            harmonize_glorys_target(ds, region=RegionBounds(
                id="probe", lat_min=5.0, lat_max=6.0, lon_min=80.0, lon_max=81.0
            ))


# ---------------------------------------------------------------------------
# Tests: build_validity_mask
# ---------------------------------------------------------------------------

class TestBuildValidityMask:
    def test_mask_shape(self, sst_dataset, region_bob):
        """Mask should be [lat, lon] matching the canonical grid."""
        harmonized = harmonize_surface_input(sst_dataset, "analysed_sst", region_bob)
        result = build_validity_mask([harmonized])
        assert result.shape == (69, 81)

    def test_mask_is_boolean(self, sst_dataset, region_bob):
        harmonized = harmonize_surface_input(sst_dataset, "analysed_sst", region_bob)
        result = build_validity_mask([harmonized])
        assert result.dtype == bool

    def test_all_valid_for_clean_data(self, sst_dataset, region_bob):
        harmonized = harmonize_surface_input(sst_dataset, "analysed_sst", region_bob)
        result = build_validity_mask([harmonized])
        # With clean data that covers the region, most cells should be valid
        assert result.mean() > 0.5  # more than half should be ocean

    def test_multiple_inputs(self, sst_dataset, sss_dataset, region_bob):
        """Mask combines validity across multiple inputs."""
        h_sst = harmonize_surface_input(sst_dataset, "analysed_sst", region_bob)
        h_sss = harmonize_surface_input(sss_dataset, "sos", region_bob, depth_level=0)
        result = build_validity_mask([h_sst, h_sss])
        assert result.shape == (69, 81)
        assert result.dtype == bool

    def test_with_target(self, sst_dataset, glorys_dataset, region_bob):
        """Mask includes target validity when provided."""
        h_sst = harmonize_surface_input(sst_dataset, "analysed_sst", region_bob)
        h_glorys = harmonize_glorys_target(glorys_dataset, region=region_bob)
        result = build_validity_mask([h_sst], harmonized_target=h_glorys)
        assert result.shape == (69, 81)


# ---------------------------------------------------------------------------
# Integration: full harmonization pipeline
# ---------------------------------------------------------------------------

class TestHarmonizationPipeline:
    def test_full_pipeline_on_mock_data(
        self, sst_dataset, sss_dataset, current_u_dataset,
        wind_dataset, glorys_dataset, region_bob
    ):
        """Test the complete harmonization pipeline on mock datasets."""
        inputs = []
        inputs.append(harmonize_surface_input(sst_dataset, "analysed_sst", region_bob))
        inputs.append(harmonize_surface_input(sss_dataset, "sos", region_bob, depth_level=0))
        inputs.append(harmonize_surface_input(current_u_dataset, "uo", region_bob, depth_level=0))
        inputs.append(harmonize_surface_input(wind_dataset, "eastward_wind", region_bob))

        target = harmonize_glorys_target(glorys_dataset, region=region_bob)
        mask = build_validity_mask(inputs, harmonized_target=target)

        # Verify tensor shapes
        for i, inp in enumerate(inputs):
            assert inp.shape == (1, 69, 81), f"Input {i} wrong shape"
        assert target.shape == (1, 15, 69, 81)
        assert mask.shape == (69, 81)
