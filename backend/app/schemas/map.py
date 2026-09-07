"""Ocean map payload schema (contracts/api/ocean-map.schema.json)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.depths import CANONICAL_DEPTHS_SET
from app.domain.regions import REGION_IDS


class MapMetadata(BaseModel):
    """Provenance metadata — never includes credentials."""

    model_version: str
    data_source: str
    preprocessing_version: str
    cached: bool
    timestamp: datetime = Field(..., description="wall-clock time of response creation")


class MapCoordinateGrid(BaseModel):
    latitude: list[float]
    longitude: list[float]


class MapResponse(BaseModel):
    region: str = Field(..., pattern="|".join(REGION_IDS))
    date: str  # YYYY-MM-DD (validated by the route with the region's coverage)
    coordinates: MapCoordinateGrid
    channel: str = "temperature"
    depth: int | None = Field(
        default=None,
        description="Depth in meters; one of the 15 canonical depths for temperature.",
    )
    values: list[list[float | None]] = Field(
        ..., description="2D [lat, lon] temperature; None on masked/invalid cells."
    )
    sigma: list[list[float | None]] = Field(
        ...,
        description="2D [lat, lon] sigma = sqrt(exp(log_var)); mirrors values "
        "cell-for-cell, None on the same masked cells (raw log_var stays internal).",
    )
    metadata: MapMetadata

    def model_post_init(self, __context) -> None:
        if self.depth is not None and self.depth not in CANONICAL_DEPTHS_SET:
            raise ValueError(f"depth {self.depth} not in canonical depths")
