"""Ocean profile payload schema (contracts/api/ocean-profile.schema.json)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.domain.regions import REGION_IDS


class ProfileMetadata(BaseModel):
    """Provenance metadata — never includes credentials."""

    model_version: str
    data_source: str
    preprocessing_version: str
    cached: bool
    timestamp: datetime = Field(..., description="wall-clock time of response creation")


class ProfileResponse(BaseModel):
    region: str = Field(..., pattern="|".join(REGION_IDS))
    date: str  # YYYY-MM-DD
    lat: float = Field(..., description="Grid-cell center latitude (degN).")
    lon: float = Field(..., description="Grid-cell center longitude.")
    depths: list[float] = Field(
        ..., description="Canonical depth order, meters. Exactly 15 entries."
    )
    temperatures: list[float | None] = Field(
        ...,
        description="Temperature at each depth in degC. null when unavailable "
        "(never fabricated). Exactly 15 entries.",
    )
    metadata: ProfileMetadata

    @field_validator("depths", "temperatures")
    @classmethod
    def _exactly_15(cls, v: list) -> list:
        if len(v) != 15:
            raise ValueError(f"expected exactly 15 entries, got {len(v)}")
        return v
