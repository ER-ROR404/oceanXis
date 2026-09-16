"""Availability: what the current stack can serve today (capability report).

The source of truth is the same cascade the map/profile routes use: live
model-service dates first, demo-cache fallback second. A region with no data
anywhere is reported as no_data with an empty date list — it is never claimed
as available (RULE 7: verified, not guessed). Provenance (checkpoint
epoch/val_loss, grid shape) comes from the same demo-cache manifest that feeds
fallback_demo, so availability and the served payloads can never disagree.
"""

from __future__ import annotations

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc
from typing import Any

from app.core.config import Settings
from app.domain.depths import CANONICAL_DEPTHS
from app.domain.regions import REGION_IDS
from app.services.cache import DemoCache
from app.services.inference_client import InferenceClient

# LOCKED canonical input channels, canonical order (config/variables.yaml,
# RULE 20). Reported as the variables each available region can serve.
VARIABLES: tuple[str, ...] = (
    "SST",
    "SSS",
    "SSH/SLA",
    "current_U",
    "current_V",
    "wind_U",
    "wind_V",
)


def available_dates(client: InferenceClient, demo: DemoCache, region: str) -> list[str]:
    """Sorted ISO dates the current stack can serve for a region.

    Live model-service dates take precedence; when the service is down (or
    serves another region), the demo-cache manifest is the honest fallback —
    exactly the cascade /ocean/map uses, so availability never promises what
    the payloads cannot deliver.
    """
    try:
        dates = client.available_dates(region)
    except Exception:
        dates = []
    if not dates:
        dates = demo.available_dates(region)
    return sorted(dates)


def available_region_ids(client: InferenceClient, demo: DemoCache) -> list[str]:
    """Declared regions that can actually serve something today (verified)."""
    return [r for r in REGION_IDS if available_dates(client, demo, r)]


def _region_entry(
    settings: Settings, demo: DemoCache, region: str, dates: list[str]
) -> dict[str, Any]:
    """Per-region availability entry. Provenance describes data that exists:
    no_data regions get no grid/checkpoint claims (never fabricated)."""
    status = "available" if dates else "no_data"
    manifest = demo.manifest
    grid: dict[str, int] | None = None
    checkpoint: dict[str, Any] | None = None
    if manifest:
        raw_grid = manifest.get("grid")
        if isinstance(raw_grid, dict) and all(
            k in raw_grid for k in ("n_lat", "n_lon", "n_depths")
        ):
            grid = {k: raw_grid[k] for k in ("n_lat", "n_lon", "n_depths")}
        if isinstance(manifest.get("epoch"), (int, float)) and isinstance(
            manifest.get("val_loss"), (int, float)
        ):
            checkpoint = {
                "file": manifest.get("checkpoint"),
                "epoch": manifest["epoch"],
                "val_loss": manifest["val_loss"],
            }
            if isinstance(manifest.get("generated_at"), str):
                checkpoint["generated_at"] = manifest["generated_at"]
    return {
        "region": region,
        "status": status,
        "dates": dates,
        "date_start": dates[0] if dates else None,
        "date_end": dates[-1] if dates else None,
        "depths": list(CANONICAL_DEPTHS) if dates else [],
        "variables": list(VARIABLES) if dates else [],
        "grid": grid if dates else None,
        "model_version": settings.model_version,
        "trained_on": settings.trained_on,
        "data_version": settings.data_version,
        "checkpoint": checkpoint if dates else None,
    }


def build_report(
    settings: Settings, client: InferenceClient, demo: DemoCache
) -> dict[str, Any]:
    """Full capability report: every declared region + model identity.

    The response conforms to contracts/api/availability.schema.json (RULE 6).
    """
    regions = [
        _region_entry(settings, demo, region, available_dates(client, demo, region))
        for region in REGION_IDS
    ]
    return {
        "regions": regions,
        "model": {
            "version": settings.model_version,
            "trained_on": settings.trained_on,
            "data_version": settings.data_version,
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }