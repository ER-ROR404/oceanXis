"""HTTP client for the ml-inference service.

Phase 1: stub with typed errors (so backend tests and health checks run
without a live model service). Phase 2 fills the real httpx transport;
the public interface below is final and must not change.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings
from app.schemas.error import (
    InferenceFailedError,
    InvalidRegionError,
    ModelNotLoadedError,
)


class InferenceClient:
    """Client to the ml-inference service (torch side, never imported here)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._base_url = self._settings.model_service_url.rstrip("/")
        self._timeout = httpx.Timeout(self._settings.model_service_timeout_seconds)

    # ── Phase 1 stub surface (final interface) ────────────────────────────
    def health(self) -> dict[str, Any]:
        """Return model-service health; raises typed errors when degraded."""
        raise ModelNotLoadedError(
            message="Model service not wired yet (Phase 2).",
            details={"service": "ml-inference"},
        )

    def available_dates(self, region: str) -> list[str]:
        """List ISO dates with tensor coverage for a region.

        Phase 1 stub: no model service wired, so no coverage is served yet.
        Returns an empty list (honest — never fabricated dates). Phase 2 fills
        this from the model service's tensor time coordinate.
        """
        del region  # Phase 2: query the ml-inference service
        return []

    def predict_map(self, region: str, date: str) -> dict[str, Any]:
        """Raw prediction: mu/log_var grids for a region/date."""
        raise InvalidRegionError(details={"region": region})

    def predict_profile(self, region: str, date: str, lat: float, lon: float) -> dict[str, Any]:
        raise InferenceFailedError(details={"region": region, "date": date})
