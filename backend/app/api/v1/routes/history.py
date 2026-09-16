"""GET /api/v1/ocean/history — available dates for a region."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.domain.regions import REGION_IDS, get_region
from app.schemas.error import InvalidRegionError
from app.services import InferenceClient
from app.services.availability import available_dates
from app.services.cache import DemoCache

router = APIRouter(tags=["ocean"])


@router.get("/ocean/history")
def get_ocean_history(
    region: str = Query(..., description="Region id (bay_of_bengal, arabian_sea, north_indian_ocean)"),
) -> dict[str, Any]:
    """List available dates for a region (ordered, ISO-8601).

    Deliberately no catches here: available_dates owns the exact same
    live-service → demo-cache cascade /ocean/map uses, so the history can
    never advertise a date the payloads cannot serve (RULE 7).
    """
    if region not in REGION_IDS or get_region(region) is None:
        raise InvalidRegionError(details={"region": region})

    dates = available_dates(client=InferenceClient(), demo=DemoCache(), region=region)

    return {"region": region, "dates": dates}
