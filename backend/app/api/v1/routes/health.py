"""GET /api/v1/health — liveness probe; never triggers expensive downloads."""

from __future__ import annotations

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc
from typing import Any

from fastapi import APIRouter, Request

from app.database.session import check_database
from app.services import DemoCache, InferenceClient

router = APIRouter(tags=["health"])


def _check(status: str, detail: str | None = None) -> dict[str, str]:
    out = {"status": status}
    if detail:
        out["detail"] = detail
    return out


def _build_checks(request: Request) -> dict[str, dict[str, str]]:
    """Avoid hard failure paths: checks report degraded, never crash."""
    checks: dict[str, dict[str, str]] = {}

    # api: we are executing, so ok.
    checks["api"] = _check("ok")

    # model_loaded: probe the ml-inference service.
    client = InferenceClient()
    try:
        client.health()
        checks["model_loaded"] = _check("ok")
    except Exception as exc:
        checks["model_loaded"] = _check("degraded", detail=str(exc)[:120])

    # cache_accessible: demo cache dir present and readable.
    demo_cache = DemoCache()
    if demo_cache.accessible:
        checks["cache_accessible"] = _check("ok")
    else:
        checks["cache_accessible"] = _check("degraded", detail="demo cache dir missing")

    # database: SELECT 1.
    checks["database"] = _check("ok") if check_database() else _check("degraded", detail="db unreachable")

    return checks


@router.get("/health")
def get_health(request: Request) -> dict[str, Any]:
    """Liveness: contract shape from contracts/api/health.schema.json."""
    checks = _build_checks(request)
    status = "ok" if all(c["status"] == "ok" for c in checks.values()) else "degraded"
    return {
        "status": status,
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat(),
    }
