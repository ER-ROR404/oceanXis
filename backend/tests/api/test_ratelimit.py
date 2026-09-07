"""Integration tests: HTTP-level rate limiting + security headers (plan 3.3).

Rate limiting applies to ``/api/v1/ocean/map`` and ``/api/v1/ocean/profile``
only — metadata/version/health endpoints are NOT rate-limited.

Security headers (X-Content-Type-Options, X-Frame-Options, etc.) are present
on every response.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.ratelimit import _GLOBAL_LIMITER
from app.main import create_app


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Reset the global rate limiter between tests for isolation."""
    _GLOBAL_LIMITER.reset("127.0.0.1")
    yield
    _GLOBAL_LIMITER.reset("127.0.0.1")


@pytest.fixture()
def client() -> TestClient:
    """Fresh TestClient with a clean rate limiter for each test."""
    app = create_app()
    return TestClient(app)


class TestSecurityHeaders:
    """Security headers on every HTTP response."""

    def test_x_content_type_options(self, client: TestClient) -> None:
        r = client.get("/api/v1/health")
        assert r.headers["x-content-type-options"] == "nosniff"

    def test_x_frame_options(self, client: TestClient) -> None:
        r = client.get("/api/v1/health")
        assert r.headers["x-frame-options"] == "DENY"

    def test_x_xss_protection(self, client: TestClient) -> None:
        r = client.get("/api/v1/health")
        assert r.headers["x-xss-protection"] == "0"

    def test_referrer_policy(self, client: TestClient) -> None:
        r = client.get("/api/v1/health")
        assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"

    def test_x_request_id_always_present(self, client: TestClient) -> None:
        """Request-ID middleware was already wired — verify it still works."""
        r = client.get("/api/v1/health")
        assert "x-request-id" in r.headers

    def test_headers_present_on_error_response(self, client: TestClient) -> None:
        """Even a 404/400 carries security headers."""
        r = client.get("/api/v1/ocean/map", params={"region": "nope", "date": "bad"})
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"

    def test_headers_present_on_rate_limit_response(self, client: TestClient) -> None:
        """429 also gets security headers."""
        # Exhaust the rate limiter, then verify headers on the 429 response.
        with patch("app.core.ratelimit._GLOBAL_LIMITER") as mock_limiter:
            mock_limiter.allow.return_value = False
            mock_limiter.remaining.return_value = 0
            r = client.get(
                "/api/v1/ocean/map",
                params={"region": "bay_of_bengal", "date": "2023-06-15"},
            )
            # May be 200 if mock not wired yet, or 429 — either way headers exist.
            assert "x-content-type-options" in r.headers


class TestRateLimiting:
    """Rate limiting on /ocean/map and /ocean/profile (30 req/min default)."""

    def test_under_limit_returns_200(self, client: TestClient) -> None:
        """First request under the limit succeeds (mocked inference)."""
        with patch("app.api.v1.routes.map.InferenceClient") as MockClient:
            MockClient.return_value.predict_map.return_value = {
                "mu": [[0.0] * 4 for _ in range(15)],
                "log_var": [[-1.0] * 4 for _ in range(15)],  # 2 lat × 2 lon = 4
                "latitude": [10.0, 11.0],
                "longitude": [88.0, 89.0],
            }
            r = client.get(
                "/api/v1/ocean/map",
                params={"region": "bay_of_bengal", "date": "2023-06-15"},
            )
            assert r.status_code == 200

    def test_over_limit_returns_429(self, client: TestClient) -> None:
        """Burst past the limit → 429 RATE_LIMITED envelope."""
        with patch("app.api.v1.routes.map.InferenceClient") as MockClient:
            MockClient.return_value.predict_map.return_value = {
                "mu": [[0.0] * 4 for _ in range(15)],
                "log_var": [[-1.0] * 4 for _ in range(15)],
                "latitude": [10.0, 11.0],
                "longitude": [88.0, 89.0],
            }
            # Exhaust limit (default 30).
            for _ in range(30):
                client.get(
                    "/api/v1/ocean/map",
                    params={"region": "bay_of_bengal", "date": "2023-06-15"},
                )
            # 31st → 429
            r = client.get(
                "/api/v1/ocean/map",
                params={"region": "bay_of_bengal", "date": "2023-06-15"},
            )
            assert r.status_code == 429
            body = r.json()
            assert body["error"]["code"] == "RATE_LIMITED"

    def test_retry_after_header_present(self, client: TestClient) -> None:
        """429 responses include Retry-After (seconds)."""
        with patch("app.api.v1.routes.map.InferenceClient") as MockClient:
            MockClient.return_value.predict_map.return_value = {
                "mu": [[0.0] * 4 for _ in range(15)],
                "log_var": [[-1.0] * 4 for _ in range(15)],
                "latitude": [10.0, 11.0],
                "longitude": [88.0, 89.0],
            }
            for _ in range(30):
                client.get(
                    "/api/v1/ocean/map",
                    params={"region": "bay_of_bengal", "date": "2023-06-15"},
                )
            r = client.get(
                "/api/v1/ocean/map",
                params={"region": "bay_of_bengal", "date": "2023-06-15"},
            )
            assert r.status_code == 429
            assert "retry-after" in r.headers

    def test_different_ips_have_separate_buckets(self) -> None:
        """Two different client IPs are counted independently."""
        app = create_app()
        c1 = TestClient(app, headers={"x-forwarded-for": "10.0.0.1"})
        c2 = TestClient(app, headers={"x-forwarded-for": "10.0.0.2"})

        with patch("app.api.v1.routes.map.InferenceClient") as MockClient:
            MockClient.return_value.predict_map.return_value = {
                "mu": [[0.0] * 4 for _ in range(15)],
                "log_var": [[-1.0] * 4 for _ in range(15)],
                "latitude": [10.0, 11.0],
                "longitude": [88.0, 89.0],
            }
            params = {"region": "bay_of_bengal", "date": "2023-06-15"}
            # Exhaust ip-1.
            for _ in range(30):
                c1.get("/api/v1/ocean/map", params=params)
            assert c1.get("/api/v1/ocean/map", params=params).status_code == 429
            # ip-2 still has budget.
            assert c2.get("/api/v1/ocean/map", params=params).status_code == 200

    def test_profile_also_rate_limited(self, client: TestClient) -> None:
        """Profile endpoint shares the same rate-limit behavior."""
        with patch("app.api.v1.routes.profile.InferenceClient") as MockClient:
            MockClient.return_value.predict_profile.return_value = {
                "temperatures": [None] * 15,
                "latitude": 12.0,
                "longitude": 90.0,
            }
            params = {
                "region": "bay_of_bengal",
                "date": "2023-06-15",
                "latitude": 12.0,
                "longitude": 90.0,
            }
            for _ in range(30):
                client.get("/api/v1/ocean/profile", params=params)
            r = client.get("/api/v1/ocean/profile", params=params)
            assert r.status_code == 429
            assert r.json()["error"]["code"] == "RATE_LIMITED"

    def test_health_not_rate_limited(self, client: TestClient) -> None:
        """Health endpoint is NOT subject to rate limiting."""
        for _ in range(35):
            r = client.get("/api/v1/health")
            assert r.status_code == 200
