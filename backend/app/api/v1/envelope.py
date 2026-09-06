"""Shared helpers for prediction envelopes (plan 3.1/3.2).

prediction.schema.json requires {status, payload, metadata} with payload
oneOf ocean-map/ocean-profile. Helpers here keep the map/profile routes thin
and guarantee contract conformance: coordinates come from the ml service's
own grid arrays (never guessed — RULE 6/7), land stays None (never 0.0, D9).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.domain.depths import CANONICAL_DEPTHS

LIVE_DATA_SOURCE = "hybrid_v1 model inference (trained on GLORYS12v1 reanalysis)"

# Canonical input-channel labels for envelope.channel_status.
# Live inference: all 7 "available". Cache-served: all 7 "cached".
CHANNEL_IDS = tuple(f"channel_{i}" for i in range(7))


def available_channel_status() -> dict[str, str]:
    return {cid: "available" for cid in CHANNEL_IDS}


def cached_channel_status() -> dict[str, str]:
    return {cid: "cached" for cid in CHANNEL_IDS}


def prediction_envelope(
    *,
    status: str,
    payload: dict[str, Any],
    model_version: str,
    channel_status: dict[str, str] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a prediction.schema.json envelope around an ocean-map/profile payload."""
    metadata: dict[str, Any] = {
        "model_version": model_version,
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
    }
    if channel_status:
        metadata["channel_status"] = channel_status
    return {"status": status, "payload": payload, "metadata": metadata}


def slice_plane(flat_row: list[Any], height: int, width: int) -> list[list[Any]]:
    """Row-major (lat outer) [H*W] flat row -> 2D [lat][lon]; None stays None."""
    if len(flat_row) != height * width:
        raise ValueError("plane length != height * width")
    return [
        [None if v is None else v for v in flat_row[row * width : (row + 1) * width]]
        for row in range(height)
    ]


def build_map_payload(
    region: str,
    date: str,
    depth: int,
    predict_body: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    """ocean-map.schema.json payload from a validated ml /predict response.

    Predict body carries latitude/longitude grids (contract updated in Phase
    3.1); the slice uses those dimensions, keeping backend/ML grids in sync
    automatically.
    """
    latitude = [float(v) for v in predict_body["latitude"]]
    longitude = [float(v) for v in predict_body["longitude"]]
    depth_idx = CANONICAL_DEPTHS.index(depth)
    values = slice_plane(predict_body["mu"][depth_idx], len(latitude), len(longitude))
    return {
        "region": region,
        "date": date,
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "channel": "temperature",
        "depth": depth,
        "values": values,
        "metadata": {
            "model_version": settings.model_version,
            "data_source": LIVE_DATA_SOURCE,
            "preprocessing_version": settings.data_version,
            "cached": False,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


def mark_cached(payload: dict[str, Any]) -> dict[str, Any]:
    """Copy of a payload with metadata.cached=True (route TTL replay)."""
    out = dict(payload)
    metadata = dict(payload["metadata"])
    metadata["cached"] = True
    out["metadata"] = metadata
    return out


def build_profile_payload(
    region: str,
    date: str,
    predict_body: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    """ocean-profile.schema.json payload from a validated ml /predict_profile response.

    Profile cells carry the snapped lat/lon from the ml service; land cells
    return nulls at every depth — zero is never fabricated (D9).
    """
    return {
        "region": region,
        "date": date,
        "lat": float(predict_body["latitude"]),
        "lon": float(predict_body["longitude"]),
        "depths": list(CANONICAL_DEPTHS),
        "temperatures": predict_body["temperatures"],
        "metadata": {
            "model_version": settings.model_version,
            "data_source": LIVE_DATA_SOURCE,
            "preprocessing_version": settings.data_version,
            "cached": False,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }
