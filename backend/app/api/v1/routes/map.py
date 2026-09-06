"""GET /api/v1/ocean/map — gridded temperature at region/date/depth (plan 3.1).

Status taxonomy (prediction.schema.json): ``model_prediction`` (fresh live
inference), ``cached_data`` (route TTL replay), ``fallback_demo`` (pre-built
demo cache when the model service is down), ``unavailable`` (503 error
envelope, code MODEL_NOT_LOADED) when neither path can serve. Values are never
fabricated: land stays null (D9); missing channels are reported, never
zero-filled. Coordinates come from the ml service's own grid (RULE 6/7).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from cachetools import TTLCache
from fastapi import APIRouter

from app.api.v1.envelope import build_map_payload, mark_cached, prediction_envelope
from app.core.config import Settings
from app.domain.depths import CANONICAL_DEPTHS_SET
from app.domain.regions import REGION_IDS
from app.schemas.error import (
    DataNotAvailableError,
    InferenceFailedError,
    InvalidDateError,
    InvalidDepthError,
    InvalidRegionError,
    ModelNotLoadedError,
)
from app.services.cache import DemoCache
from app.services.inference_client import InferenceClient

router = APIRouter(tags=["ocean"])

# Route-level TTL cache of cooked map payloads (the client has its own raw
# cache; this one decides the cached_data status). Keyed per region/date/depth.
_ENVELOPE_TTL_SECONDS = 60.0
_map_cache: TTLCache[tuple, dict[str, Any]] = TTLCache(maxsize=256, ttl=_ENVELOPE_TTL_SECONDS)

CHANNEL_IDS = tuple(f"channel_{i}" for i in range(7))


def _available_channel_status() -> dict[str, str]:
    """Live inference: all 7 input channels were exercised successfully."""
    return {cid: "available" for cid in CHANNEL_IDS}


def _cached_channel_status() -> dict[str, str]:
    """Cache-served responses report channels as cached, never as live."""
    return {cid: "cached" for cid in CHANNEL_IDS}


def _validate_region(region: str) -> str:
    if region not in REGION_IDS:
        raise InvalidRegionError(details={"region": region})
    return region


def _validate_date(date: str) -> str:
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise InvalidDateError(details={"date": date}) from None
    return date


def _validate_depth(depth: int) -> int:
    if depth not in CANONICAL_DEPTHS_SET:
        raise InvalidDepthError(details={"depth": depth})
    return depth


def _try_fallback(region: str, date: str, depth: int) -> dict[str, Any] | None:
    """Demo-cache payload or None. Corrupt readers degrade to a cache miss
    (still honest: no fabricated data; the route then reports unavailable)."""
    try:
        return DemoCache().get_map(region, date, depth)
    except Exception:
        return None


@router.get("/ocean/map")
def get_ocean_map(region: str, date: str, depth: int = 0) -> dict[str, Any]:
    """Gridded temperature field (ocean-map.schema.json payload in envelope)."""
    region = _validate_region(region)
    date = _validate_date(date)
    depth = _validate_depth(depth)
    settings = Settings()

    key = (region, date, depth)
    cached_payload = _map_cache.get(key)
    if cached_payload is not None:
        return prediction_envelope(
            status="cached_data",
            payload=mark_cached(cached_payload),
            model_version=cached_payload["metadata"]["model_version"],
            channel_status=_cached_channel_status(),
        )

    client = InferenceClient()
    try:
        body = client.predict_map(region, date)
    except DataNotAvailableError:
        payload = _try_fallback(region, date, depth)
        if payload is None:
            raise
    except (ModelNotLoadedError, InferenceFailedError) as exc:
        payload = _try_fallback(region, date, depth)
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
        payload = build_map_payload(region, date, depth, body, settings)
        _map_cache[key] = payload
        return prediction_envelope(
            status="model_prediction",
            payload=payload,
            model_version=payload["metadata"]["model_version"],
            channel_status=_available_channel_status(),
        )

    # fallback_demo served the request.
    _map_cache[key] = payload
    return prediction_envelope(
        status="fallback_demo",
        payload=payload,
        model_version=payload["metadata"]["model_version"],
        channel_status=_cached_channel_status(),
    )
