"""InferenceClient unit tests (mock httpx transport — no live ml service).

Plan Step 2.2 spec: success, connect error -> ModelNotLoaded, malformed ->
InferenceFailed, cached hit returns without a second call. Responses are
re-validated against contract shape before being trusted (RULE 6).
"""

from __future__ import annotations

import httpx
import pytest

from app.core.config import Settings
from app.schemas.error import (
    DataNotAvailableError,
    InferenceFailedError,
    ModelNotLoadedError,
)
from app.services.inference_client import InferenceClient

BASE_URL = "http://ml-inference:8080"

HEALTH_OK = {
    "status": "ok",
    "model": "hybrid_v1",
    "version": "0.1.0",
    "region": "bay_of_bengal",
    "dates": ["2022-01-01", "2022-01-02"],
}

PREDICT_OK = {
    # 3x3 grid, flattened row-major (lat outer): each depth row has 9 cells.
    "mu": [[0.5, None, 1.0, 2.0, 2.5, 3.0, 4.0, None, 5.0]] * 15,
    "log_var": [[-1.0, None, 0.5, 0.2, -0.5, 1.0, -2.0, None, 0.0]] * 15,
    "latitude": [10.0, 11.0, 12.0],
    "longitude": [88.0, 89.0, 90.0],
    "series_id": "hybrid_v1-2023-06-15",
    "date": "2023-06-15",
    "region": "bay_of_bengal",
    "model_version": "hybrid_v1",
}

PROFILE_OK = {
    "temperatures": [29.0, None] + [28.5] * 13,
    "log_vars": [-1.0, None] + [-1.0] * 13,
    "series_id": "hybrid_v1-2023-06-15-cell",
    "date": "2023-06-15",
    "region": "bay_of_bengal",
    "model_version": "hybrid_v1",
    "latitude": 12.0,
    "longitude": 90.0,
}


def make_client(handler: httpx.MockTransport | None = None, **kwargs) -> InferenceClient:
    """Client over a MockTransport handler (no network)."""
    transport = httpx.MockTransport(handler) if handler is not None else httpx.MockTransport(handler or default_handler)
    client = httpx.Client(transport=transport, base_url=BASE_URL)
    settings = Settings(
        model_service_url=BASE_URL,
        model_service_timeout_seconds=5.0,
    )
    return InferenceClient(settings=settings, client=client, **kwargs)


def default_handler(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"unexpected request: {request.method} {request.url}")


class TestHealth:
    def test_health_ok(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/health"
            return httpx.Response(200, json=HEALTH_OK)

        body = make_client(handler).health()
        assert body["status"] == "ok"
        assert len(body["dates"]) == 2

    def test_health_connect_error_raises_model_not_loaded(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        with pytest.raises(ModelNotLoadedError):
            make_client(handler).health()

    def test_health_503_raises_model_not_loaded(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"status": "error", "code": "MODEL_NOT_LOADED"})

        with pytest.raises(ModelNotLoadedError):
            make_client(handler).health()

    def test_health_malformed_raises_inference_failed(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"hello": "world"})

        with pytest.raises(InferenceFailedError):
            make_client(handler).health()

    def test_health_non_ok_status_raises_inference_failed(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"status": "error"})

        with pytest.raises(InferenceFailedError):
            make_client(handler).health()

    def test_health_timeout_raises_model_not_loaded(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timed out", request=request)

        with pytest.raises(ModelNotLoadedError):
            make_client(handler).health()


class TestAvailableDates:
    def test_available_dates_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/health"
            return httpx.Response(200, json=HEALTH_OK)

        dates = make_client(handler).available_dates("bay_of_bengal")
        assert dates == ["2022-01-01", "2022-01-02"]

    def test_available_dates_only_for_served_region(self) -> None:
        """The health payload names the region the model service actually
        serves (its loaded tensor store). Asking for any other region must
        return [] — claiming its dates would be guessing (RULE 7)."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=HEALTH_OK)  # serves bay_of_bengal

        assert make_client(handler).available_dates("arabian_sea") == []

    def test_available_dates_missing_region_rejected(self) -> None:
        """A health body without the served region cannot be trusted to answer
        region-scoped availability questions — treat as malformed."""

        def handler(request: httpx.Request) -> httpx.Response:
            bad = dict(HEALTH_OK)
            bad.pop("region")
            return httpx.Response(200, json=bad)

        with pytest.raises(InferenceFailedError):
            make_client(handler).available_dates("bay_of_bengal")

    def test_health_missing_region_rejected(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            bad = dict(HEALTH_OK)
            bad.pop("region")
            return httpx.Response(200, json=bad)

        with pytest.raises(InferenceFailedError):
            make_client(handler).health()

    def test_available_dates_connect_error_returns_empty(self) -> None:
        """Honest degraded answer (Phase 1 contract: 200 with empty list)."""

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        assert make_client(handler).available_dates("bay_of_bengal") == []

    def test_available_dates_503_returns_empty(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"status": "error", "code": "MODEL_NOT_LOADED"})

        assert make_client(handler).available_dates("bay_of_bengal") == []

    def test_available_dates_malformed_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"status": "ok"})  # missing dates

        with pytest.raises(InferenceFailedError):
            make_client(handler).available_dates("bay_of_bengal")


class TestPredictMap:
    def test_predict_map_success(self) -> None:
        import json as _json

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/predict"
            assert _json.loads(request.content)["date"] == "2023-06-15"
            return httpx.Response(200, json=PREDICT_OK)

        body = make_client(handler).predict_map("bay_of_bengal", "2023-06-15")
        assert len(body["mu"]) == 15
        assert body["series_id"].startswith("hybrid_v1-")
        # Validated surface: the response carries the grid used to build the
        # ocean-map coordinates (3.1 requirement; never guessed).
        assert body["latitude"] == [10.0, 11.0, 12.0]
        assert body["longitude"] == [88.0, 89.0, 90.0]

    def test_predict_map_missing_grid_coordinates_rejected(self) -> None:
        """Phase 3: a /predict response without lat/lon grids cannot build the
        ocean-map payload — treat as malformed (InferenceFailedError), never guess."""

        def handler(request: httpx.Request) -> httpx.Response:
            bad = dict(PREDICT_OK)
            bad.pop("latitude")
            bad.pop("longitude")
            return httpx.Response(200, json=bad)

        with pytest.raises(InferenceFailedError):
            make_client(handler).predict_map("bay_of_bengal", "2023-06-15")

    def test_predict_map_grid_dimension_mismatch_rejected(self) -> None:
        """mu rows are [H*W] flattened; H*W must equal len(lat)*len(lon)."""

        def handler(request: httpx.Request) -> httpx.Response:
            bad = dict(PREDICT_OK)
            bad["latitude"] = [10.0]  # would imply H*W == 1, but rows are length 3
            return httpx.Response(200, json=bad)

        with pytest.raises(InferenceFailedError):
            make_client(handler).predict_map("bay_of_bengal", "2023-06-15")

    def test_predict_map_connect_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        with pytest.raises(ModelNotLoadedError):
            make_client(handler).predict_map("bay_of_bengal", "2023-06-15")

    def test_predict_map_503(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"status": "error", "code": "MODEL_NOT_LOADED"})

        with pytest.raises(ModelNotLoadedError):
            make_client(handler).predict_map("bay_of_bengal", "2023-06-15")

    def test_predict_map_404_raises_data_not_available(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"status": "error", "code": "DATA_NOT_AVAILABLE"})

        with pytest.raises(DataNotAvailableError):
            make_client(handler).predict_map("bay_of_bengal", "2030-01-01")

    def test_predict_map_500_raises_inference_failed(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"status": "error"})

        with pytest.raises(InferenceFailedError):
            make_client(handler).predict_map("bay_of_bengal", "2023-06-15")

    def test_predict_map_malformed_raises_inference_failed(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"mu": "not-a-list"})

        with pytest.raises(InferenceFailedError):
            make_client(handler).predict_map("bay_of_bengal", "2023-06-15")

    def test_predict_map_cached_hit_no_second_call(self) -> None:
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(200, json=PREDICT_OK)

        client = make_client(handler)
        first = client.predict_map("bay_of_bengal", "2023-06-15")
        second = client.predict_map("bay_of_bengal", "2023-06-15")
        assert calls["n"] == 1
        assert first == second

    def test_predict_map_different_date_bypasses_cache(self) -> None:
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(200, json=PREDICT_OK)

        client = make_client(handler)
        client.predict_map("bay_of_bengal", "2023-06-15")
        client.predict_map("bay_of_bengal", "2023-06-16")
        assert calls["n"] == 2


class TestPredictProfile:
    def test_predict_profile_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/predict_profile"
            return httpx.Response(200, json=PROFILE_OK)

        body = make_client(handler).predict_profile("bay_of_bengal", "2023-06-15", 12.0, 90.0)
        assert len(body["temperatures"]) == 15
        assert body["latitude"] == 12.0

    def test_predict_profile_503(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"status": "error", "code": "MODEL_NOT_LOADED"})

        with pytest.raises(ModelNotLoadedError):
            make_client(handler).predict_profile("bay_of_bengal", "2023-06-15", 12.0, 90.0)

    def test_predict_profile_404(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"status": "error", "code": "DATA_NOT_AVAILABLE"})

        with pytest.raises(DataNotAvailableError):
            make_client(handler).predict_profile("bay_of_bengal", "2030-01-01", 12.0, 90.0)
