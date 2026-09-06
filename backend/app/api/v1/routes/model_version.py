"""GET /api/v1/model/version — served model version (never a realtime claim)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(tags=["model"])


@router.get("/model/version")
def get_model_version(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    return {
        "model_version": settings.model_version,
        "trained_on": settings.trained_on,
        "data_version": settings.data_version,
    }
