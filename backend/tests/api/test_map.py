"""API tests: GET /api/v1/ocean/map (plan Step 3.1).

Covered: live prediction (model_prediction), route TTL replay (cached_data),
demo-cache fallback (fallback_demo), 404/503/400 taxonomy, depth default, and
the null-never-zero invariant. Every 200 envelope validates against
prediction.schema.json (cross-file refs resolved in conftest) and its payload
against ocean-map.schema.json (RULE 6).
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

# log_var = -1.0 in the live fake body → sigma = sqrt(exp(log_var)).
EXPECTED_SIGMA = math.sqrt(math.exp(-1.0))

import app.api.v1.routes.map as map_route  # noqa: E402  (patching target)
from app.main import create_app
from app.schemas.error import (
    DataNotAvailableError,
    InferenceFailedError,
    ModelNotLoadedError,
)

# ── helpers ────────────────────────────────────────────────────────────────


def make_client() -> TestClient:
    return TestClient(create_app())


def live_predict_body(date: str = "2024-01-10", region: str = "bay_of_bengal") -> dict:
    """Contract-conformant /predict body: 2x3 grid (H*W = 6 rows)."""
    rows = []
    for depth in range(15):
        base = 20.0 if depth == 0 else 5.0
        rows.append([base] * 6)
    rows[0][1] = None  # land cell at (lat0, lon1)
    return {
        "mu": rows,
        "log_var": [[-1.0] * 6] * 15,
        "latitude": [10.0, 11.0],
        "longitude": [88.0, 89.0, 90.0],
        "series_id": f"hybrid_v1-{date}",
        "date": date,
        "region": region,
        "model_version": "hybrid_v1",
    }


class FakeClient:
    """Routes call InferenceClient() per request; tests provide this stand-in."""

    def __init__(self, *, error: Exception | None = None, body: dict | None = None) -> None:
        self.error = error
        self.body = body or live_predict_body()
        self.calls = 0

    def predict_map(self, region: str, date: str) -> dict:
        self.calls += 1
        if self.error is not None:
            raise self.error
        body = dict(self.body)
        body["date"] = date
        body["region"] = region
        return body


def write_demo_cache(root, *, date: str = "2024-06-15", offset: float = 0.0) -> None:
    """Minimal ml-builder-shaped demo cache (2x3 grid, surface 20+offset)."""
    depths_m = [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000]
    region_dir = root / "bay_of_bengal"
    region_dir.mkdir(parents=True, exist_ok=True)
    (region_dir / "coordinates.json").write_text(
        json.dumps(
            {
                "region": "bay_of_bengal",
                "lat": [10.0, 11.0],
                "lon": [88.0, 89.0, 90.0],
                "depths_m": depths_m,
                "n_lat": 2,
                "n_lon": 3,
                "n_depths": 15,
            }
        )
    )
    mu = np.full((15, 2, 3), 5.0 + offset, dtype=np.float32)
    mu[0] = 20.0 + offset
    mu[0, 0, 1] = np.nan  # land cell
    np.savez(region_dir / f"{date}.npz", mu=mu, log_var=np.zeros_like(mu))
    (root / "manifest.json").write_text(
        json.dumps(
            {
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
            }
        )
    )


# ── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_map_cache():
    """Route-level TTL cache is module-global; clear per test (isolation)."""
    map_route._map_cache.clear()
    yield
    map_route._map_cache.clear()


@pytest.fixture
def fake_client(monkeypatch) -> FakeClient:
    client = FakeClient()
    monkeypatch.setattr(map_route, "InferenceClient", lambda: client)
    return client


@pytest.fixture
def no_demo_cache(monkeypatch):
    """Default for most tests: fallback returns nothing available."""

    class _NoneDemo:
        def get_map(self, *args, **kwargs):
            return None

    monkeypatch.setattr(map_route, "DemoCache", lambda settings=None: _NoneDemo())
    return _NoneDemo


# ── tests ───────────────────────────────────────────────────────────────────


class TestMapLive:
    def test_map_live_200_contract(self, fake_client, validate_contract) -> None:
        resp = make_client().get(
            "/api/v1/ocean/map",
            params={"region": "bay_of_bengal", "date": "2024-01-10", "depth": 5},
        )
        assert resp.status_code == 200
        body = resp.json()
        validate_contract(body, "prediction")
        validate_contract(body["payload"], "ocean-map")
        assert body["status"] == "model_prediction"
        assert body["payload"]["depth"] == 5
        # 2x3 grid: each lat row has W=3 lon cells.
        assert body["payload"]["values"] == [[5.0] * 3, [5.0] * 3]
        assert body["payload"]["coordinates"] == {
            "latitude": [10.0, 11.0],
            "longitude": [88.0, 89.0, 90.0],
        }
        # sigma mirrors values shape cell-for-cell; all non-null at depth 5.
        assert len(body["payload"]["sigma"]) == 2
        assert all(len(row) == 3 for row in body["payload"]["sigma"])
        for row in body["payload"]["sigma"]:
            for v in row:
                assert v is not None
                assert v == pytest.approx(EXPECTED_SIGMA)
        assert body["payload"]["metadata"]["cached"] is False
        assert set(body["metadata"]["channel_status"]) == {f"channel_{i}" for i in range(7)}
        assert all(v == "available" for v in body["metadata"]["channel_status"].values())

    def test_map_depth_defaults_to_surface(self, fake_client, validate_contract) -> None:
        resp = make_client().get(
            "/api/v1/ocean/map", params={"region": "bay_of_bengal", "date": "2024-01-10"}
        )
        assert resp.status_code == 200
        body = resp.json()
        validate_contract(body, "prediction")
        assert body["payload"]["depth"] == 0
        assert body["payload"]["values"][0][1] is None  # land stays null
        assert body["payload"]["sigma"][0][1] is None

    def test_map_land_cell_null_never_zero(self, fake_client) -> None:
        """D9 invariant: None cells survive and no 0.0 is fabricated."""
        resp = make_client().get(
            "/api/v1/ocean/map",
            params={"region": "bay_of_bengal", "date": "2024-01-10", "depth": 0},
        )
        values = resp.json()["payload"]["values"]
        assert values[0][1] is None
        assert all(v != 0.0 for row in values for v in row if v is not None)

    def test_map_source_model_inference_honest_metadata(self, fake_client) -> None:
        resp = make_client().get(
            "/api/v1/ocean/map",
            params={"region": "bay_of_bengal", "date": "2024-01-10", "depth": 0},
        )
        meta = resp.json()["payload"]["metadata"]
        assert "model inference" in meta["data_source"].lower()
        assert meta["model_version"] == "hybrid_v1"


class TestMapCached:
    def test_map_second_request_reports_cached_data(self, fake_client, validate_contract) -> None:
        client = make_client()
        params = {"region": "bay_of_bengal", "date": "2024-01-10", "depth": 0}
        first = client.get("/api/v1/ocean/map", params=params)
        second = client.get("/api/v1/ocean/map", params=params)
        assert first.status_code == 200 and second.status_code == 200
        body = second.json()
        validate_contract(body, "prediction")
        validate_contract(body["payload"], "ocean-map")
        assert body["status"] == "cached_data"
        assert body["payload"]["metadata"]["cached"] is True
        # The model service was contacted exactly once (replay served the cache).
        assert fake_client.calls == 1
        # Values are byte-identical to the live response.
        assert first.json()["payload"]["values"] == body["payload"]["values"]
        assert first.json()["payload"]["sigma"] == body["payload"]["sigma"]

    def test_map_cache_is_per_date(self, fake_client) -> None:
        client = make_client()
        params = {"region": "bay_of_bengal", "date": "2024-01-10", "depth": 0}
        client.get("/api/v1/ocean/map", params=params)
        client.get(
            "/api/v1/ocean/map",
            params={**params, "date": "2024-01-11"},
        )
        assert fake_client.calls == 2


class TestMapFallback:
    def test_map_fallback_demo_payload_from_cache(self, monkeypatch, validate_contract, tmp_path) -> None:
        write_demo_cache(tmp_path, offset=3.0)
        from app.core.config import Settings
        from app.services.cache import DemoCache

        real_demo = DemoCache(settings=Settings(demo_cache_dir=str(tmp_path)))
        monkeypatch.setattr(map_route, "DemoCache", lambda settings=None: real_demo)
        fake = FakeClient(error=ModelNotLoadedError())
        monkeypatch.setattr(map_route, "InferenceClient", lambda: fake)

        resp = make_client().get(
            "/api/v1/ocean/map",
            params={"region": "bay_of_bengal", "date": "2024-06-15", "depth": 0},
        )
        assert resp.status_code == 200
        body = resp.json()
        validate_contract(body, "prediction")
        validate_contract(body["payload"], "ocean-map")
        assert body["status"] == "fallback_demo"
        assert body["payload"]["values"] == [
            [23.0, None, 23.0],
            [23.0, 23.0, 23.0],
        ]
        # demo cache log_var = 0 → sigma = sqrt(exp(0)) = 1.0; land stays None.
        assert body["payload"]["sigma"] == [
            [1.0, None, 1.0],
            [1.0, 1.0, 1.0],
        ]
        assert body["payload"]["metadata"]["cached"] is True
        assert "demo cache" in body["payload"]["metadata"]["data_source"].lower()


class TestMapErrors:
    def test_map_404_when_date_absent_everywhere(self, monkeypatch) -> None:
        fake = FakeClient(error=DataNotAvailableError())
        monkeypatch.setattr(map_route, "InferenceClient", lambda: fake)
        monkeypatch.setattr(
            map_route,
            "DemoCache",
            lambda settings=None: type("_N", (), {"get_map": lambda *a, **k: None})(),
        )
        resp = make_client().get(
            "/api/v1/ocean/map",
            params={"region": "bay_of_bengal", "date": "2024-01-10", "depth": 0},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "DATA_NOT_AVAILABLE"

    def test_map_503_when_both_paths_down(self, fake_client, no_demo_cache) -> None:
        fake_client.error = ModelNotLoadedError()
        resp = make_client().get(
            "/api/v1/ocean/map",
            params={"region": "bay_of_bengal", "date": "2024-01-10", "depth": 0},
        )
        assert resp.status_code == 503
        body = resp.json()
        assert body["error"]["code"] == "MODEL_NOT_LOADED"
        assert body["error"]["details"]["fallback"] == "demo cache miss"

    def test_map_503_when_inference_failed_and_no_fallback(self, fake_client, no_demo_cache) -> None:
        fake_client.error = InferenceFailedError()
        resp = make_client().get(
            "/api/v1/ocean/map",
            params={"region": "bay_of_bengal", "date": "2024-01-10", "depth": 0},
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "MODEL_NOT_LOADED"
        assert resp.json()["error"]["details"]["cause"] == "inference_failed"

    def test_map_404_on_unknown_region(self, fake_client) -> None:
        resp = make_client().get(
            "/api/v1/ocean/map",
            params={"region": "atlantis", "date": "2024-01-10", "depth": 0},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_REGION"

    def test_map_400_on_invalid_depth(self, fake_client) -> None:
        resp = make_client().get(
            "/api/v1/ocean/map",
            params={"region": "bay_of_bengal", "date": "2024-01-10", "depth": 7},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_DEPTH"

    def test_map_400_on_invalid_date(self, fake_client) -> None:
        resp = make_client().get(
            "/api/v1/ocean/map",
            params={"region": "bay_of_bengal", "date": "not-a-date", "depth": 0},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_DATE"
