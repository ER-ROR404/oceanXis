"""API tests: GET /api/v1/availability (capability report) + truthful metadata.

The availability report must describe what the current stack can actually
serve: live model-service dates first, demo-cache fallback second, honest
no_data for regions with nothing anywhere (never claimed as available), and
provenance (checkpoint epoch/val_loss, grid) carried from the same manifest
that feeds fallback_demo. RULE 6: the response is validated against
contracts/api/availability.schema.json. RULE 7: availability is verified from
the same sources that serve payloads — never guessed.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

import app.api.v1.routes.availability as availability_route  # patching target
import app.api.v1.routes.metadata as metadata_route  # patching target
from app.main import create_app

# Concise stand-in for the verified 730-day store (2022-01-01..2023-12-31).
BOB_LIVE_DATES = ["2022-01-01", "2023-12-31"]
BOB_CACHE_DATES = ["2023-06-01", "2023-12-28"]
REGION_IDS = ["bay_of_bengal", "arabian_sea", "north_indian_ocean"]


def make_client() -> TestClient:
    app = create_app()
    return TestClient(app)


def make_manifest(*, region: str = "bay_of_bengal", dates: tuple[str, str] = BOB_CACHE_DATES) -> dict[str, Any]:
    """Demo-cache manifest shaped like ml build output (artifacts/demo_cache)."""
    return {
        "format_version": 1,
        "region": region,
        "model_version": "hybrid_v1",
        "checkpoint": "best.pt",
        "epoch": 83,
        "val_loss": 0.3715,
        "trained_on": "2023-12-31",
        "date_start": dates[0],
        "date_end": dates[-1],
        "n_dates": len(dates),
        "dates": list(dates),
        "step_days": 7,
        "n_lat": 69,
        "n_lon": 81,
        "grid": {"n_lat": 69, "n_lon": 81, "n_depths": 15},
        "channel_status": {f"channel_{i}": "available" for i in range(7)},
        "generated_at": "2026-09-06T13:48:16+00:00",
    }


class FakeClient:
    """InferenceClient fake: serves dates only for regions it claims."""

    def __init__(self, dates_by_region: dict[str, list[str]] | None = None) -> None:
        self._dates = dates_by_region or {"bay_of_bengal": list(BOB_LIVE_DATES)}

    def available_dates(self, region: str) -> list[str]:
        return list(self._dates.get(region, []))


class FakeDownClient:
    """Model service down: honest empty answer for every region."""

    def available_dates(self, region: str) -> list[str]:
        return []


class FakeDemo:
    """DemoCache fake exposing the same surface the availability service uses
    (available_dates + public manifest property)."""

    def __init__(self, manifest: dict[str, Any] | None) -> None:
        self._manifest = manifest

    @property
    def manifest(self) -> dict[str, Any] | None:
        return self._manifest

    def available_dates(self, region: str) -> list[str]:
        if not self._manifest or self._manifest.get("region") != region:
            return []
        return list(self._manifest.get("dates", []))


class TestAvailability:
    def test_availability_200_contract_shape(self, validate_contract, monkeypatch) -> None:
        """Live service serves bay_of_bengal; arabian_sea and the official
        domain have nothing anywhere and must be reported no_data."""
        monkeypatch.setattr(availability_route, "InferenceClient", lambda: FakeClient())
        monkeypatch.setattr(availability_route, "DemoCache", lambda settings=None: FakeDemo(make_manifest()))

        resp = make_client().get("/api/v1/availability")
        assert resp.status_code == 200
        body = resp.json()
        validate_contract(body, "availability")

        by_region = {r["region"]: r for r in body["regions"]}
        assert set(by_region) == set(REGION_IDS)

        bob = by_region["bay_of_bengal"]
        assert bob["status"] == "available"
        assert bob["dates"] == BOB_LIVE_DATES
        assert bob["date_start"] == "2022-01-01"
        assert bob["date_end"] == "2023-12-31"
        assert bob["depths"][0] == 0 and bob["depths"][-1] == 1000
        assert len(bob["depths"]) == 15
        assert bob["variables"] == ["SST", "SSS", "SSH/SLA", "current_U", "current_V", "wind_U", "wind_V"]

        for other in ("arabian_sea", "north_indian_ocean"):
            entry = by_region[other]
            assert entry["status"] == "no_data"
            assert entry["dates"] == []
            assert entry["date_start"] is None
            assert entry["date_end"] is None
            assert entry["depths"] == []
            assert entry["variables"] == []
            assert entry["grid"] is None
            assert entry["checkpoint"] is None

    def test_availability_falls_back_to_demo_cache_when_model_service_down(self, validate_contract, monkeypatch) -> None:
        """The model service being down must not make the demo look empty:
        availability falls back to the same demo-cache manifest fallback_demo
        serves."""
        monkeypatch.setattr(availability_route, "InferenceClient", lambda: FakeDownClient())
        monkeypatch.setattr(availability_route, "DemoCache", lambda settings=None: FakeDemo(make_manifest()))

        body = make_client().get("/api/v1/availability").json()
        validate_contract(body, "availability")
        bob = next(r for r in body["regions"] if r["region"] == "bay_of_bengal")
        assert bob["status"] == "available"
        assert bob["dates"] == list(BOB_CACHE_DATES)

    def test_availability_live_dates_take_precedence_over_cache(self, validate_contract, monkeypatch) -> None:
        """When both sources answer, the live service is the truth; the cache
        still contributes checkpoint provenance, never the date list."""
        monkeypatch.setattr(availability_route, "InferenceClient", lambda: FakeClient())
        monkeypatch.setattr(availability_route, "DemoCache", lambda settings=None: FakeDemo(make_manifest()))

        body = make_client().get("/api/v1/availability").json()
        validate_contract(body, "availability")
        bob = next(r for r in body["regions"] if r["region"] == "bay_of_bengal")
        assert bob["dates"] == BOB_LIVE_DATES  # not the cache dates

    def test_availability_provenance_carries_checkpoint_and_model_identity(self, validate_contract, monkeypatch) -> None:
        monkeypatch.setattr(availability_route, "InferenceClient", lambda: FakeClient())
        monkeypatch.setattr(availability_route, "DemoCache", lambda settings=None: FakeDemo(make_manifest()))

        body = make_client().get("/api/v1/availability").json()
        validate_contract(body, "availability")
        assert body["model"] == {
            "version": "hybrid_v1",
            "trained_on": "2023-12-31",
            "data_version": "bay_of_bengal-2022-2023-v1",
        }
        bob = next(r for r in body["regions"] if r["region"] == "bay_of_bengal")
        assert bob["checkpoint"] == {
            "file": "best.pt",
            "epoch": 83,
            "val_loss": 0.3715,
            "generated_at": "2026-09-06T13:48:16+00:00",
        }
        assert bob["grid"] == {"n_lat": 69, "n_lon": 81, "n_depths": 15}
        assert bob["model_version"] == "hybrid_v1"
        assert bob["trained_on"] == "2023-12-31"

    def test_availability_no_data_region_never_claims_provenance(self, validate_contract, monkeypatch) -> None:
        """A region with nothing served gets no grid/checkpoint claims either —
        provenance must describe data that actually exists."""
        monkeypatch.setattr(availability_route, "InferenceClient", lambda: FakeClient())
        monkeypatch.setattr(availability_route, "DemoCache", lambda settings=None: FakeDemo(None))

        body = make_client().get("/api/v1/availability").json()
        validate_contract(body, "availability")
        bob = next(r for r in body["regions"] if r["region"] == "bay_of_bengal")
        assert bob["checkpoint"] is None
        assert bob["grid"] is None


class TestMetadataTruthful:
    def test_metadata_regions_list_only_what_is_servable(self, monkeypatch) -> None:
        """The metadata region list must reflect what the current stack can
        serve — a region with no data anywhere is never advertised."""
        monkeypatch.setattr(metadata_route, "InferenceClient", lambda: FakeClient())
        monkeypatch.setattr(metadata_route, "DemoCache", lambda settings=None: FakeDemo(make_manifest()))

        body = make_client().get("/api/v1/ocean/metadata").json()
        assert body["regions"] == ["bay_of_bengal"]
        assert set(body["regions_declared"]) == set(REGION_IDS)

    def test_metadata_regions_empty_when_nothing_servable(self, monkeypatch) -> None:
        """Nothing servable anywhere is honestly an empty list — factories are
        never claimed."""
        monkeypatch.setattr(metadata_route, "InferenceClient", lambda: FakeDownClient())
        monkeypatch.setattr(metadata_route, "DemoCache", lambda settings=None: FakeDemo(None))

        body = make_client().get("/api/v1/ocean/metadata").json()
        assert body["regions"] == []
        assert set(body["regions_declared"]) == set(REGION_IDS)