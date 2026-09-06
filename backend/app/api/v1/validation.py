"""Shared input validators for API route handlers (plan 3.1 + 3.2).

Region/date/depth validators raise contract error codes; coordinate bounds
are enforced from config/regions.yaml per queried region (never hardcoded).
"""

from __future__ import annotations

from datetime import datetime

from app.domain.depths import CANONICAL_DEPTHS_SET
from app.domain.regions import REGION_IDS, Region
from app.schemas.error import (
    InvalidCoordinateError,
    InvalidDateError,
    InvalidDepthError,
    InvalidRegionError,
)


def validate_region(region: str) -> str:
    """Validate region id; raises INVALID_REGION (400)."""
    if region not in REGION_IDS:
        raise InvalidRegionError(details={"region": region})
    return region


def validate_date(date: str) -> str:
    """Validate ISO-8601 date string; raises INVALID_DATE (400)."""
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise InvalidDateError(details={"date": date}) from None
    return date


def validate_depth(depth: int) -> int:
    """Validate canonical depth; raises INVALID_DEPTH (400)."""
    if depth not in CANONICAL_DEPTHS_SET:
        raise InvalidDepthError(details={"depth": depth})
    return depth


def validate_coordinate(region: Region, lat: float, lon: float) -> tuple[float, float]:
    """Validate coordinates fall within the queried region's bounds (inclusive).

    Bounds come from config/regions.yaml — never hardcoded.
    Raises INVALID_COORDINATE (400) when outside the region.
    """
    if not (
        region.latitude.min <= lat <= region.latitude.max
        and region.longitude.min <= lon <= region.longitude.max
    ):
        raise InvalidCoordinateError(
            details={
                "region": region.id,
                "latitude": lat,
                "longitude": lon,
                "latitude_bounds": [region.latitude.min, region.latitude.max],
                "longitude_bounds": [region.longitude.min, region.longitude.max],
            }
        )
    return lat, lon
