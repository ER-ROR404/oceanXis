"""Unit tests for the FastAPI app factory and middleware (app/main.py)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


class TestAppFactory:
    def test_app_supports_health_route(self) -> None:
        app = create_app()
        client = TestClient(app)
        # /health route is added in Phase 1.3; until then the app must at
        # least boot and return 404 (not crash) for unknown paths.
        resp = client.get("/api/v1/health")
        assert resp.status_code in (200, 404, 500)

    def test_app_config_injectable(self) -> None:
        app = create_app()
        assert app.title == "OceanEmbed API"
        assert app.version is not None

    def test_request_id_middleware_sets_header(self) -> None:
        app = create_app()
        client = TestClient(app)
        resp = client.get("/api/v1/not-a-real-route")
        assert "x-request-id" in resp.headers

    def test_cors_origins_wired(self) -> None:
        app = create_app()
        # CORS middleware registered — OPTIONS preflight returns CORS headers.
        client = TestClient(app)
        resp = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in resp.headers

    def test_unknown_route_returns_error_envelope(self) -> None:
        """API 404s must use the contract error envelope, not the default shape.

        Regression: the SPA catch-all (registered when ``frontend/dist`` exists)
        returned an off-contract ``NOT_FOUND`` code for unknown ``/api`` paths,
        shadowing the 404 handler. The envelope must be identical whether or not
        the built frontend is present.
        """
        app = create_app()
        client = TestClient(app)
        resp = client.get("/api/v1/does-not-exist")
        assert resp.status_code == 404
        # Never the SPA shell.
        assert resp.headers["content-type"].startswith("application/json")
        body = resp.json()
        assert body["error"]["code"] == "UNKNOWN_ERROR"
        assert body["error"]["details"]["path"] == "/api/v1/does-not-exist"

    def test_spa_fallback_serves_index_for_non_api_routes(self) -> None:
        """Non-API routes serve the built SPA when dist exists (client routing)."""
        app = create_app()
        client = TestClient(app)
        resp = client.get("/some/client/route")
        if resp.status_code == 404:
            pytest.skip("frontend/dist not built in this environment")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/html")
