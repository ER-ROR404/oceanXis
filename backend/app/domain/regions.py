"""Application region registry from config/regions.yaml (source of truth).

Maps region id → coordinate bounds; used for request validation and for
locating the local tensor store. Never hardcoded (RULE 7 / config first).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

_REGIONS_PATH = Path(__file__).resolve().parents[3] / "config" / "regions.yaml"

with open(_REGIONS_PATH) as _f:
    _REGIONS_CFG = yaml.safe_load(_f)


class RegionBounds(BaseModel):
    min: float
    max: float


class Region(BaseModel):
    id: str
    longitude: RegionBounds
    latitude: RegionBounds
    description: str = ""

    @property
    def label(self) -> str:
        return self.id

    @property
    def bounds(self) -> tuple[RegionBounds, RegionBounds]:
        return self.latitude, self.longitude


def _load_regions() -> dict[str, Region]:
    regions: dict[str, Region] = {}
    raw = _REGIONS_CFG.get("regions", {})
    for rid, rcfg in raw.items():
        regions[rid] = Region(
            id=rid,
            longitude=RegionBounds(**rcfg["longitude"]),
            latitude=RegionBounds(**rcfg["latitude"]),
            description=rcfg.get("description", ""),
        )
    official = _REGIONS_CFG.get("official_domain")
    if official:
        regions[official["id"]] = Region(
            id=official["id"],
            longitude=RegionBounds(**official["longitude"]),
            latitude=RegionBounds(**official["latitude"]),
            description=official.get("description", "Official full domain (LOCKED)."),
        )
    return regions


REGIONS: dict[str, Region] = _load_regions()
REGION_IDS: tuple[str, ...] = tuple(sorted(REGIONS))


def get_region(region_id: str) -> Region | None:
    """Return region by id, or None when unknown (never raise here)."""
    return REGIONS.get(region_id)
