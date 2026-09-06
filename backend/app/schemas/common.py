"""Shared schema primitives (region/depth enums live in config, referenced here)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CommonResponse(BaseModel):
    """Marker base shared by map/profile envelopes (concrete shape in Phase 3)."""

    region: str
    date: str


def _dump(model: BaseModel) -> dict[str, Any]:
    """JSON-safe dump that keeps None (masked cells) representable."""
    return model.model_dump(mode="json")
