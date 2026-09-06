"""API v1 router aggregation (mounted at /api/v1)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import health, history, metadata, model_version

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(history.router)
api_router.include_router(metadata.router)
api_router.include_router(model_version.router)
