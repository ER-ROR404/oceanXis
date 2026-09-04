"""Regional extraction: maps region IDs to bounding boxes.

Loads region definitions from config/regions.yaml and provides a clean
interface for data subsetting.

Usage:
    registry = RegionRegistry.from_yaml("config/regions.yaml")
    bounds = registry.get("bay_of_bengal")
    print(bounds.lon_min, bounds.lon_max, bounds.lat_min, bounds.lat_max)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegionBounds:
    """Geographic bounding box for a region.

    Attributes:
        id: Region identifier (e.g. "bay_of_bengal").
        lon_min: Western longitude bound (degrees East).
        lon_max: Eastern longitude bound (degrees East).
        lat_min: Southern latitude bound (degrees North).
        lat_max: Northern latitude bound (degrees North).
        description: Human-readable description.
    """

    id: str
    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float
    description: str = ""

    def as_copernicus_bbox(self) -> dict[str, float]:
        """Return bounding box as Copernicus Marine Toolbox expects it.

        Returns:
            Dict with keys: minimum_longitude, maximum_longitude,
            minimum_latitude, maximum_latitude.
        """
        return {
            "minimum_longitude": self.lon_min,
            "maximum_longitude": self.lon_max,
            "minimum_latitude": self.lat_min,
            "maximum_latitude": self.lat_max,
        }

    def grid_dimensions(self, resolution_deg: float = 0.25) -> tuple[int, int]:
        """Estimate grid (H, W) at the given resolution.

        Args:
            resolution_deg: Grid spacing in degrees (default 0.25).

        Returns:
            Tuple of (height_lat, width_lon) in grid cells.
        """
        height = int(round((self.lat_max - self.lat_min) / resolution_deg)) + 1
        width = int(round((self.lon_max - self.lon_min) / resolution_deg)) + 1
        return height, width

    def __str__(self) -> str:
        return (
            f"{self.id}: [{self.lat_min}°N–{self.lat_max}°N, "
            f"{self.lon_min}°E–{self.lon_max}°E]"
        )


@dataclass(frozen=True)
class GridConfig:
    """Grid configuration from config/regions.yaml."""

    resolution_degrees: float = 0.25
    temporal_frequency: str = "daily"
    grid_type: str = "regular_lat_lon"


@dataclass
class RegionRegistry:
    """Collection of region definitions loaded from config."""

    regions: dict[str, RegionBounds] = field(default_factory=dict)
    official_domain: Optional[RegionBounds] = None
    grid: GridConfig = field(default_factory=GridConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> RegionRegistry:
        """Load region registry from config/regions.yaml.

        Args:
            path: Path to the YAML config file.

        Returns:
            Populated RegionRegistry.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Region config not found: {path}")

        with open(path) as f:
            raw = yaml.safe_load(f)

        registry = cls()

        # Grid config
        grid_raw = raw.get("grid", {})
        registry.grid = GridConfig(
            resolution_degrees=grid_raw.get("spatial_resolution_degrees", 0.25),
            temporal_frequency=grid_raw.get("temporal_frequency", "daily"),
            grid_type=grid_raw.get("grid_type", "regular_lat_lon"),
        )

        # Official domain
        domain_raw = raw.get("official_domain", {})
        if domain_raw:
            lon = domain_raw.get("longitude", {})
            lat = domain_raw.get("latitude", {})
            registry.official_domain = RegionBounds(
                id=domain_raw.get("id", "north_indian_ocean"),
                lon_min=lon.get("min", 45.0),
                lon_max=lon.get("max", 105.0),
                lat_min=lat.get("min", 5.0),
                lat_max=lat.get("max", 30.0),
                description=domain_raw.get("description", ""),
            )

        # Application regions
        regions_raw = raw.get("regions", {})
        for region_id, region_raw in regions_raw.items():
            lon = region_raw.get("longitude", {})
            lat = region_raw.get("latitude", {})
            registry.regions[region_id] = RegionBounds(
                id=region_id,
                lon_min=lon.get("min", 0.0),
                lon_max=lon.get("max", 0.0),
                lat_min=lat.get("min", 0.0),
                lat_max=lat.get("max", 0.0),
                description=region_raw.get("description", ""),
            )

        logger.info(
            "Loaded %d regions: %s",
            len(registry.regions),
            ", ".join(sorted(registry.regions.keys())),
        )
        return registry

    def get(self, region_id: str) -> RegionBounds:
        """Get region bounds by ID.

        Raises:
            KeyError: If the region ID is not registered.
        """
        if region_id not in self.regions:
            available = ", ".join(sorted(self.regions.keys()))
            raise KeyError(f"Region '{region_id}' not found. Available: {available}")
        return self.regions[region_id]

    def official_domain_bounds(self) -> RegionBounds:
        """Return the official domain bounds."""
        if self.official_domain is None:
            raise ValueError("Official domain not configured")
        return self.official_domain

    def list_regions(self) -> list[str]:
        """Return sorted list of region IDs."""
        return sorted(self.regions.keys())
