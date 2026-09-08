"""GET /api/v1/availability — capability report (what can be served today).

Answers the first question a client should ask: which regions have data right
now, over what date range, and what model built it. The report is verified
from the same sources that serve payloads (live model service, then the
demo-cache manifest) — never guessed (RULE 7). Conforms to
contracts/api/availability.schema.json (RULE 6).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.services import InferenceClient
from app.services.availability import build_report
from app.services.cache import DemoCache

router = APIRouter(tags=["capability"])


@router.get("/availability")
def get_availability(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    return build_report(settings=settings, client=InferenceClient(), demo=DemoCache())