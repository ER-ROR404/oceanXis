"""FastAPI application factory.

Mounts routers under ``/api/v1`` per ``contracts/api/openapi.yaml``.
Registers the contract error envelope, CORS, request-ID, security-headers,
and logging middleware.  Never imports torch or training code (RULE 3).
"""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.v1.router import api_router
from app.core.config import Settings
from app.core.ratelimit import _GLOBAL_LIMITER
from app.schemas.error import RATE_LIMITED_CODE, ApiError

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised by the per-IP rate-limit dependency (maps to 429)."""

    pass


def _request_id_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


def _security_headers_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["x-xss-protection"] = "0"
        response.headers["referrer-policy"] = "strict-origin-when-cross-origin"
        return response


def _error_envelope_404(app: FastAPI) -> None:
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "UNKNOWN_ERROR",
                    "message": "The requested resource does not exist.",
                    "details": {"path": request.url.path},
                }
            },
        )


def _api_error_handler(app: FastAPI) -> None:
    """Map domain ApiError subclasses to contract error envelopes."""

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())


def _rate_limit_exception_handler(app: FastAPI) -> None:
    """429 RATE_LIMITED envelope with Retry-After header."""

    @app.exception_handler(RateLimitError)
    async def rate_limited_handler(request: Request, exc: RateLimitError):
        ip = request.client.host if request.client else "unknown"
        retry = _GLOBAL_LIMITER.retry_after(ip)
        content = {
            "error": {
                "code": RATE_LIMITED_CODE,
                "message": "Rate limit exceeded. Please wait before retrying.",
            }
        }
        return JSONResponse(
            status_code=429,
            content=content,
            headers={"Retry-After": str(int(retry) + 1)},
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the application."""
    cfg = settings or Settings()

    app = FastAPI(
        title="OceanEmbed API",
        version=cfg.app_version,
        description=(
            "Surface-driven subsurface temperature reconstruction (SIH26066). "
            "Responses conform to contracts/api/*.schema.json."
        ),
        servers=[{"url": "/api/v1"}],
    )

    app.state.settings = cfg

    # CORS — allow only the configured dev origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )

    _request_id_middleware(app)
    _security_headers_middleware(app)
    _error_envelope_404(app)
    _api_error_handler(app)
    _rate_limit_exception_handler(app)

    # Mount API routers under /api/v1 per contracts/api/openapi.yaml.
    app.include_router(api_router, prefix="/api/v1")

    # Serve built frontend if available
    dist_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if dist_path.exists():
        app.mount("/assets", StaticFiles(directory=str(dist_path / "assets")), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            if full_path.startswith("api/"):
                # API paths must never return the SPA shell or an off-contract
                # code. Raise so the registered 404 handler owns the envelope
                # (UNKNOWN_ERROR) — identical whether or not dist exists.
                raise HTTPException(status_code=404, detail="Not found")
            index_file = dist_path / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return {"error": "Frontend not built"}

    return app
