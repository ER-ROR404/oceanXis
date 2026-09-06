"""GET /api/v1/ocean/metadata — honest application/dataset metadata."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.domain.regions import REGION_IDS

router = APIRouter(tags=["ocean"])


@router.get("/ocean/metadata")
def get_ocean_metadata(request: Request) -> dict[str, Any]:
    """Metadata for the dashboard footer: no credentials, no internal IDs (RULE 14).

    data_freshness mirrors trained_on — an honest statement, never a realtime claim.
    """
    settings = request.app.state.settings
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "regions": list(REGION_IDS),
        "model_version": settings.model_version,
        "data_freshness": settings.data_freshness,
    }
