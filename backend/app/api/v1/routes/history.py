"""GET /api/v1/ocean/history — available dates for a region."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.domain.regions import REGION_IDS, get_region
from app.schemas.error import InvalidRegionError
from app.services import InferenceClient
from app.services.cache import DemoCache

router = APIRouter(tags=["ocean"])


@router.get("/ocean/history")
def get_ocean_history(
    region: str = Query(..., description="Region id (bay_of_bengal, arabian_sea, north_indian_ocean)"),
) -> dict[str, Any]:
    """List available dates for a region (ordered, ISO-8601)."""
    if region not in REGION_IDS or get_region(region) is None:
        raise InvalidRegionError(details={"region": region})

    client = InferenceClient()
    try:
        dates = client.available_dates(region)
    except Exception:
        dates = []

    if not dates:
        # Model service is down (or has no coverage). Serve the same honest
        # demo-cache dates that /ocean/map serves via fallback_demo, so the
        # demo workflow stays drivable end to end. None available anywhere
        # still yields 200 + [] — never fabricated dates (Phase 1 contract).
        dates = DemoCache().available_dates(region)

    return {"region": region, "dates": sorted(dates)}
