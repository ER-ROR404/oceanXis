"""API tests: GET /api/v1/ocean/profile (plan Step 3.2).

Validates: live 200 (model_prediction), land cell → all None (never 0.0),
nearest-cell snap, cached replay (cached_data), fallback_demo (demo cache),
404/503 taxonomy, INVALID_COORDINATE for region bounds, plus envelope and
payload schema conformance (ocean-profile.schema.json, prediction.schema.json).
"""

from __future__ import annotations

import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

import app.api.v1.routes.profile as profile_route
from app.domain.depths import CANONICAL_DEPTHS
from app.main import create_app
from app.schemas.error import (
    DataNotAvailableError,
    InferenceFailedError,
    ModelNotLoadedError,
)

# ── helpers ────────────────────────────────────────────────────────────────

LIVE_PROFILE_BODY = {
    "temperatures": [29.0, 28.5, None] + [25.0] * 12,
    "series_id": "hybrid_v1-2023-06-15-cell",
    "date": "2023-06-15",
    "region": "bay_of_bengal",
    "model_version": "hybrid_v1",
    "latitude": 12.0,
    "longitude": 90.0,
}

LAND_PROFILE_BODY = {
    "temperatures": [None] * 15,
    "series_id": "hybrid_v1-2023-06-15-cell",
    "date": "2023-06-15",
    "region": "bay_of_bengal",
    "model_version": "hybrid_v1",
    "latitude": 5.0,   # nearest land cell for this grid
    "longitude": 100.0,
}


def make_client() -> TestClient:
    return TestClient(create_app())


class FakeProfileClient:
    def __init__(self, *, error: Exception | None = None, body: dict | None = None) -> None:
        self.error = error
        self.body = body or LIVE_PROFILE_BODY
        self.calls = 0

    def predict_profile(self, region: str, date: str, lat: float, lon: float) -> dict:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return dict(self.body)


def write_demo_cache(root, *, date: str = "2024-06-15") -> None:
    depths_m = [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000]
    region_dir = root / "bay_of_bengal"
    region_dir.mkdir(parents=True, exist_ok=True)
    lat = [5.0, 10.0, 15.0, 20.0]
    lon = [80.0, 90.0, 100.0]
    (region_dir / "coordinates.json").write_text(
        json.dumps({
            "region": "bay_of_bengal",
            "lat": lat,
            "lon": lon,
            "depths_m": depths_m,
            "n_lat": len(lat),
            "n_lon": len(lon),
            "n_depths": 15,
        })
    )
    mu = np.full((15, len(lat), len(lon)), 5.0, dtype=np.float32)
    mu[0] = 20.0  # surface distinct
    mu[:, 0, -1] = np.nan  # land column across all depths (lat=5, lon=100)
    np.savez(region_dir / f"{date}.npz", mu=mu, log_var=np.zeros_like(mu))
    (root / "manifest.json").write_text(json.dumps({
        "format_version": 1,
        "region": "bay_of_bengal",
        "model_version": "hybrid_v1",
        "checkpoint": "best.pt",
        "epoch": 83,
        "val_loss": 0.3715,
        "trained_on": "2023-12-31",
        "dates": [date],
        "channel_status": {f"channel_{i}": "available" for i in range(7)},
        "generated_at": "2024-01-01T00:00:00+00:00",
    }))


# ── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_profile_cache():
    profile_route._profile_cache.clear()
    yield
    profile_route._profile_cache.clear()

@pytest.fixture
def fake_client(monkeypatch) -> FakeProfileClient:
    client = FakeProfileClient()
    monkeypatch.setattr(profile_route, "InferenceClient", lambda: client)
    return client

@pytest.fixture
def no_demo_cache(monkeypatch):
    class _NoneDemo:
        def get_profile(self, *a, **kw): return None
    monkeypatch.setattr(profile_route, "DemoCache", lambda settings=None: _NoneDemo())
    return _NoneDemo


# ── tests ───────────────────────────────────────────────────────────────────


class TestProfileLive:
    def test_profile_live_200_contract(self, fake_client, validate_contract) -> None:
        resp = make_client().get(
            "/api/v1/ocean/profile",
            params={"region": "bay_of_bengal", "date": "2023-06-15",
                    "latitude": 12.0, "longitude": 90.0},
        )
        assert resp.status_code == 200
        body = resp.json()
        validate_contract(body, "prediction")
        validate_contract(body["payload"], "ocean-profile")
        assert body["status"] == "model_prediction"
        assert body["payload"]["lat"] == 12.0
        assert body["payload"]["lon"] == 90.0
        assert body["payload"]["depths"] == list(CANONICAL_DEPTHS)
        assert body["payload"]["temperatures"][2] is None
        assert body["payload"]["metadata"]["cached"] is False
        assert all(v == "available" for v in body["metadata"]["channel_status"].values())

    def test_profile_land_cell_null_never_zero(self, fake_client) -> None:
        """Land cell → every depth None; no fabricated 0.0 (D9)."""
        fake_client.body = LAND_PROFILE_BODY
        resp = make_client().get(
            "/api/v1/ocean/profile",
            params={"region": "bay_of_bengal", "date": "2023-06-15",
                    "latitude": 5.0, "longitude": 100.0},
        )
        body = resp.json()["payload"]
        assert body["temperatures"] == [None] * 15
        assert all(v is None for v in body["temperatures"])

    def test_profile_source_honest(self, fake_client) -> None:
        resp = make_client().get(
            "/api/v1/ocean/profile",
            params={"region": "bay_of_bengal", "date": "2023-06-15",
                    "latitude": 12.0, "longitude": 90.0},
        )
        meta = resp.json()["payload"]["metadata"]
        assert "model inference" in meta["data_source"].lower()


class TestProfileCached:
    def test_profile_cached_replay(self, fake_client, validate_contract) -> None:
        client = make_client()
        params = {"region": "bay_of_bengal", "date": "2023-06-15",
                  "latitude": 12.0, "longitude": 90.0}
        client.get("/api/v1/ocean/profile", params=params)
        second = client.get("/api/v1/ocean/profile", params=params)
        body = second.json()
        validate_contract(body, "prediction")
        assert body["status"] == "cached_data"
        assert body["payload"]["metadata"]["cached"] is True
        assert fake_client.calls == 1


class TestProfileFallback:
    def test_profile_fallback_demo_when_model_down(self, monkeypatch, validate_contract, tmp_path) -> None:
        write_demo_cache(tmp_path)
        from app.core.config import Settings
        from app.services.cache import DemoCache
        real_demo = DemoCache(settings=Settings(demo_cache_dir=str(tmp_path)))
        monkeypatch.setattr(profile_route, "DemoCache", lambda settings=None: real_demo)
        monkeypatch.setattr(profile_route, "InferenceClient", lambda: FakeProfileClient(error=ModelNotLoadedError()))

        resp = make_client().get(
            "/api/v1/ocean/profile",
            params={"region": "bay_of_bengal", "date": "2024-06-15",
                    "latitude": 10.2, "longitude": 90.3},
        )
        assert resp.status_code == 200
        body = resp.json()
        validate_contract(body, "prediction")
        validate_contract(body["payload"], "ocean-profile")
        assert body["status"] == "fallback_demo"
        # Snaps to (10.0, 90.0) → surface = 20.0
        assert body["payload"]["lat"] == 10.0
        assert body["payload"]["lon"] == 90.0
        assert body["payload"]["temperatures"][0] == 20.0
        assert body["payload"]["temperatures"][1] == 5.0
        assert body["payload"]["metadata"]["cached"] is True


class TestProfileErrors:
    def test_profile_404_when_date_absent(self, fake_client, no_demo_cache) -> None:
        fake_client.error = DataNotAvailableError()
        resp = make_client().get(
            "/api/v1/ocean/profile",
            params={"region": "bay_of_bengal", "date": "2023-06-15",
                    "latitude": 12.0, "longitude": 90.0},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "DATA_NOT_AVAILABLE"

    def test_profile_503_when_both_down(self, fake_client, no_demo_cache) -> None:
        fake_client.error = ModelNotLoadedError()
        resp = make_client().get(
            "/api/v1/ocean/profile",
            params={"region": "bay_of_bengal", "date": "2023-06-15",
                    "latitude": 12.0, "longitude": 90.0},
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "MODEL_NOT_LOADED"

    def test_profile_400_inference_failed_and_no_fallback(self, fake_client, no_demo_cache) -> None:
        fake_client.error = InferenceFailedError()
        resp = make_client().get(
            "/api/v1/ocean/profile",
            params={"region": "bay_of_bengal", "date": "2023-06-15",
                    "latitude": 12.0, "longitude": 90.0},
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["details"]["cause"] == "inference_failed"

    def test_profile_400_invalid_coordinate(self, fake_client) -> None:
        resp = make_client().get(
            "/api/v1/ocean/profile",
            params={"region": "bay_of_bengal", "date": "2023-06-15",
                    "latitude": 0.0, "longitude": 90.0},  # below 5.0 lat bound
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_COORDINATE"

    def test_profile_400_invalid_region(self, fake_client) -> None:
        resp = make_client().get(
            "/api/v1/ocean/profile",
            params={"region": "atlantis", "date": "2023-06-15",
                    "latitude": 12.0, "longitude": 90.0},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_REGION"

    def test_profile_400_invalid_date(self, fake_client) -> None:
        resp = make_client().get(
            "/api/v1/ocean/profile",
            params={"region": "bay_of_bengal", "date": "not-a-date",
                    "latitude": 12.0, "longitude": 90.0},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_DATE"
