"""Demo cache reader: fallback_demo data path when the model service is down.

Phase 1: stub (no demo cache built yet) — returns unavailable. Phase 2/4
wires the real reader against artifacts/demo_cache/.
"""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.schemas.error import DataNotAvailableError


class DemoCache:
    """Reads pre-built fallback maps/profiles from the demo cache dir."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._cache_dir = self._settings.demo_cache_dir

    @property
    def accessible(self) -> bool:
        return self._cache_dir.is_dir()

    def get_map(self, region: str, date: str, depth: int) -> dict[str, Any] | None:
        del region, date, depth  # placeholder signature (Phase 4 wiring)
        return None

    def get_profile(self, region: str, date: str, lat: float, lon: float) -> dict[str, Any] | None:
        del region, date, lat, lon
        return None

    def assert_accessible(self) -> None:
        if not self.accessible:
            raise DataNotAvailableError(message="No demo cache available in this build.")
