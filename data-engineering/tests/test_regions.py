"""Tests for oceanembed_data.regions — region ID to bounding box mapping."""

from __future__ import annotations

from pathlib import Path

import pytest

from oceanembed_data.regions import GridConfig, RegionBounds, RegionRegistry

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "regions.yaml"


class TestRegionBounds:
    """Tests for the RegionBounds dataclass."""

    def test_as_copernicus_bbox(self):
        bounds = RegionBounds(
            id="test",
            lon_min=80.0,
            lon_max=100.0,
            lat_min=5.0,
            lat_max=22.0,
        )
        bbox = bounds.as_copernicus_bbox()
        assert bbox["minimum_longitude"] == 80.0
        assert bbox["maximum_longitude"] == 100.0
        assert bbox["minimum_latitude"] == 5.0
        assert bbox["maximum_latitude"] == 22.0

    def test_grid_dimensions_025(self):
        bounds = RegionBounds(
            id="test",
            lon_min=80.0,
            lon_max=100.0,
            lat_min=5.0,
            lat_max=22.0,
        )
        h, w = bounds.grid_dimensions(0.25)
        # (22-5)/0.25 + 1 = 69
        # (100-80)/0.25 + 1 = 81
        assert h == 69
        assert w == 81

    def test_str_representation(self):
        bounds = RegionBounds(
            id="bay_of_bengal",
            lon_min=80.0,
            lon_max=100.0,
            lat_min=5.0,
            lat_max=22.0,
        )
        s = str(bounds)
        assert "bay_of_bengal" in s
        assert "80.0" in s
        assert "100.0" in s


class TestRegionRegistry:
    """Tests for RegionRegistry loading and lookup."""

    @pytest.fixture
    def registry(self) -> RegionRegistry:
        """Load the real config for integration-style tests."""
        return RegionRegistry.from_yaml(CONFIG_PATH)

    def test_from_yaml_loads_regions(self, registry: RegionRegistry):
        assert len(registry.regions) > 0

    def test_from_yaml_loads_bay_of_bengal(self, registry: RegionRegistry):
        assert "bay_of_bengal" in registry.regions

    def test_from_yaml_loads_arabian_sea(self, registry: RegionRegistry):
        assert "arabian_sea" in registry.regions

    def test_from_yaml_loads_official_domain(self, registry: RegionRegistry):
        assert registry.official_domain is not None
        assert registry.official_domain.id == "north_indian_ocean"

    def test_from_yaml_loads_grid_config(self, registry: RegionRegistry):
        assert registry.grid.resolution_degrees == 0.25

    def test_get_returns_correct_bounds(self, registry: RegionRegistry):
        bob = registry.get("bay_of_bengal")
        assert bob.lon_min == 80.0
        assert bob.lon_max == 100.0
        assert bob.lat_min == 5.0
        assert bob.lat_max == 22.0

    def test_get_raises_on_missing_region(self, registry: RegionRegistry):
        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")

    def test_list_regions(self, registry: RegionRegistry):
        regions = registry.list_regions()
        assert "bay_of_bengal" in regions
        assert "arabian_sea" in regions
        assert regions == sorted(regions)

    def test_official_domain_bounds(self, registry: RegionRegistry):
        domain = registry.official_domain_bounds()
        assert domain.lon_min == 45.0
        assert domain.lon_max == 105.0
        assert domain.lat_min == 5.0
        assert domain.lat_max == 30.0

    def test_from_yaml_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            RegionRegistry.from_yaml("/nonexistent/path.yaml")
