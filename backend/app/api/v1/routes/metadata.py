"""GET /api/v1/ocean/metadata — honest application/dataset metadata."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.domain.regions import REGION_IDS
from app.services import InferenceClient
from app.services.availability import available_region_ids
from app.services.cache import DemoCache

router = APIRouter(tags=["ocean"])


@router.get("/ocean/metadata")
def get_ocean_metadata(request: Request) -> dict[str, Any]:
    """Metadata for the dashboard footer: no credentials, no internal IDs (RULE 14).

    ``regions`` lists only what the current stack can actually serve today
    (verified from the live model service, then the demo-cache manifest); a
    declared-but-empty region is never advertised as available (RULE 7).
    ``regions_declared`` keeps the full declared set for full transparency.
    data_freshness mirrors trained_on — an honest statement, never a realtime claim.
    """
    settings = request.app.state.settings
    client = InferenceClient()
    demo = DemoCache()
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "regions": available_region_ids(client, demo),
        "regions_declared": list(REGION_IDS),
        "model_version": settings.model_version,
        "data_freshness": settings.data_freshness,
    }
