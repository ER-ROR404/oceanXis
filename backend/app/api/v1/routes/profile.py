"""GET /api/v1/ocean/profile — temperature at a grid cell across all 15 depths.

Status taxonomy (prediction.schema.json): ``model_prediction`` (fresh live
inference), ``cached_data`` (route TTL replay), ``fallback_demo`` (pre-built
demo cache when the model service is down), ``unavailable`` (503) when neither
path can serve. Nearest-cell semantics live ml-side (RULE 3); the backend
passes the snapped cell centers through honestly. Land cells return nulls at
every depth — zero is never fabricated (D9). Coordinates are validated against
config/regions.yaml per queried region (not the stale global openapi bounds).
"""

from __future__ import annotations

from typing import Any

from cachetools import TTLCache
from fastapi import APIRouter, Depends

from app.api.v1.envelope import (
    available_channel_status,
    build_profile_payload,
    cached_channel_status,
    mark_cached,
    prediction_envelope,
)
from app.api.v1.validation import (
    validate_coordinate,
    validate_date,
    validate_region,
)
from app.core.config import Settings
from app.core.ratelimit import rate_limit_dependency
from app.domain.regions import get_region
from app.schemas.error import (
    DataNotAvailableError,
    InferenceFailedError,
    ModelNotLoadedError,
)
from app.services.cache import DemoCache
from app.services.inference_client import InferenceClient

router = APIRouter(tags=["ocean"], dependencies=[Depends(rate_limit_dependency)])

_ENVELOPE_TTL_SECONDS = 60.0
_profile_cache: TTLCache[tuple, dict[str, Any]] = TTLCache(maxsize=256, ttl=_ENVELOPE_TTL_SECONDS)


def _try_profile_fallback(region: str, date: str, lat: float, lon: float) -> dict[str, Any] | None:
    try:
        return DemoCache().get_profile(region, date, lat, lon)
    except Exception:
        return None


@router.get("/ocean/profile")
def get_ocean_profile(
    region: str,
    date: str,
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """Temperature profile across 15 canonical depths at a single grid cell."""
    region = validate_region(region)
    date = validate_date(date)
    region_obj = get_region(region)
    lat, lon = validate_coordinate(region_obj, latitude, longitude)
    settings = Settings()

    key = (region, date, lat, lon)
    cached_payload = _profile_cache.get(key)
    if cached_payload is not None:
        return prediction_envelope(
            status="cached_data",
            payload=mark_cached(cached_payload),
            model_version=cached_payload["metadata"]["model_version"],
            channel_status=cached_channel_status(),
        )

    client = InferenceClient()
    try:
        body = client.predict_profile(region, date, lat, lon)
    except DataNotAvailableError:
        payload = _try_profile_fallback(region, date, lat, lon)
        if payload is None:
            raise
    except (ModelNotLoadedError, InferenceFailedError) as exc:
        payload = _try_profile_fallback(region, date, lat, lon)
        if payload is None:
            raise ModelNotLoadedError(
                details={
                    "region": region,
                    "date": date,
                    "fallback": "demo cache miss",
                    "cause": exc.code.lower(),
                }
            ) from exc
    else:
        payload = build_profile_payload(region, date, body, settings)
        _profile_cache[key] = payload
        return prediction_envelope(
            status="model_prediction",
            payload=payload,
            model_version=payload["metadata"]["model_version"],
            channel_status=available_channel_status(),
        )

    # fallback_demo
    _profile_cache[key] = payload
    return prediction_envelope(
        status="fallback_demo",
        payload=payload,
        model_version=payload["metadata"]["model_version"],
        channel_status=cached_channel_status(),
    )
