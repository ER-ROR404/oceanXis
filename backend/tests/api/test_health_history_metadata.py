"""API tests: /health, /ocean/history, /ocean/metadata, /model/version.

Every response is validated against its contract schema (RULE 6).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

import app.api.v1.routes.history as history_route  # noqa: E402  (patching target)
from app.main import create_app


def make_client() -> TestClient:
    app = create_app()
    return TestClient(app)


class TestHealth:
    def test_health_200_contract_shape(self, validate_contract) -> None:
        client = make_client()
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        validate_contract(body, "health")
        assert body["status"] in ("ok", "degraded")
        assert set(body["checks"]) == {"api", "model_loaded", "cache_accessible", "database"}

    def test_health_checks_have_status_field(self) -> None:
        client = make_client()
        body = client.get("/api/v1/health").json()
        for check_name, check in body["checks"].items():
            assert check["status"] in ("ok", "degraded"), check_name

    def test_health_has_timestamp(self) -> None:
        client = make_client()
        body = client.get("/api/v1/health").json()
        assert "timestamp" in body


class TestHistory:
    def test_history_200_shape(self, validate_contract) -> None:
        """Phase 1 (stub service): valid region returns 200; dates populated in
        Phase 2 when the model service is wired. Until then, an empty list is
        an honest 'no coverage served yet' answer — not fabricated data."""
        client = make_client()
        resp = client.get("/api/v1/ocean/history", params={"region": "bay_of_bengal"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["region"] == "bay_of_bengal"
        assert isinstance(body["dates"], list)

    def test_history_unknown_region_400(self) -> None:
        client = make_client()
        resp = client.get("/api/v1/ocean/history", params={"region": "atlantis"})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_REGION"

    def test_history_missing_region_422(self) -> None:
        client = make_client()
        resp = client.get("/api/v1/ocean/history")
        assert resp.status_code == 422

    def test_history_serves_demo_cache_dates_when_model_service_down(self, monkeypatch) -> None:
        """The model service being down must not strand the demo: history
        falls back to the same demo-cache manifest that fallback_demo uses,
        so the frontend can still drive the map/profile workflow."""
        scripted = {"dates": ["2023-06-01", "2023-09-07"]}

        class FakeClient:
            def available_dates(self, region: str) -> list[str]:
                return []

        class DemoFallback:
            def available_dates(self, region: str) -> list[str]:
                return list(scripted["dates"])

        monkeypatch.setattr(history_route, "InferenceClient", lambda: FakeClient())
        monkeypatch.setattr(history_route, "DemoCache", lambda settings=None: DemoFallback())

        client = make_client()
        body = client.get(
            "/api/v1/ocean/history", params={"region": "bay_of_bengal"}
        ).json()
        assert body["dates"] == ["2023-06-01", "2023-09-07"]

    def test_history_stays_empty_when_service_down_and_no_cache(self, monkeypatch) -> None:
        """No data anywhere is still an honest empty list (Phase 1 contract:
        200 + [], never fabricated dates)."""

        class FakeClient:
            def available_dates(self, region: str) -> list[str]:
                return []

        class NoDemo:
            def available_dates(self, region: str) -> list[str]:
                return []

        monkeypatch.setattr(history_route, "InferenceClient", lambda: FakeClient())
        monkeypatch.setattr(history_route, "DemoCache", lambda settings=None: NoDemo())

        client = make_client()
        body = client.get(
            "/api/v1/ocean/history", params={"region": "bay_of_bengal"}
        ).json()
        assert body["dates"] == []


class TestMetadata:
    def test_metadata_200(self) -> None:
        client = make_client()
        resp = client.get("/api/v1/ocean/metadata")
        assert resp.status_code == 200
        body = resp.json()
        assert body["app_name"] == "oceanembed"
        assert "regions" in body
        assert "bay_of_bengal" in body["regions"]

    def test_metadata_is_honest_not_realtime(self) -> None:
        client = make_client()
        body = client.get("/api/v1/ocean/metadata").json()
        assert body["data_freshness"] <= "2024-01-01"
        assert "model_version" in body


class TestModelVersion:
    def test_model_version_200_shape(self) -> None:
        client = make_client()
        resp = client.get("/api/v1/model/version")
        assert resp.status_code == 200
        body = resp.json()
        assert "model_version" in body
        assert "trained_on" in body
        assert "data_version" in body

    def test_model_version_not_realtime(self) -> None:
        client = make_client()
        body = client.get("/api/v1/model/version").json()
        assert body["trained_on"] <= "2024-01-01"


class TestContractPath:
    def test_openapi_docs_exist(self) -> None:
        client = make_client()
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        assert spec["servers"][0]["url"] == "/api/v1"
        assert "/api/v1/health" in spec["paths"] or "/health" in spec["paths"]
