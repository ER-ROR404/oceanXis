"""Unit tests: Pydantic schemas serialize into contract-valid payloads."""

from __future__ import annotations

import pytest

from app.schemas import CommonResponse, ErrorResponse, MapResponse, ProfileResponse
from app.schemas.map import MapMetadata
from app.schemas.profile import ProfileMetadata


class TestMapSchemaConforms:
    def test_minimal_valid_map(self, validate_contract) -> None:
        payload = MapResponse(
            region="bay_of_bengal",
            date="2023-06-15",
            coordinates={
                "latitude": [12.0, 12.25, 12.5],
                "longitude": [88.0, 88.25, 88.5],
            },
            channel="temperature",
            depth=100,
            values=[[22.1, 22.2, 22.3], [22.0, 22.1, 22.2], [21.9, 22.0, 22.1]],
            sigma=[[0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, 0.5]],
            metadata=MapMetadata(
                model_version="hybrid_v1",
                data_source="glorys12v1",
                preprocessing_version="p2-harmonize-v1",
                cached=False,
                timestamp="2026-09-06T12:00:00Z",
            ),
        ).model_dump(mode="json")
        validate_contract(payload, "ocean-map")

    def test_nan_allowed_in_values(self, validate_contract) -> None:
        payload = MapResponse(
            region="bay_of_bengal",
            date="2023-06-15",
            coordinates={
                "latitude": [12.0, 12.25],
                "longitude": [88.0, 88.25],
            },
            channel="temperature",
            depth=0,
            values=[[22.1, None], [None, 22.0]],
            sigma=[[0.5, None], [None, 0.5]],
            metadata=MapMetadata(
                model_version="hybrid_v1",
                data_source="glorys12v1",
                preprocessing_version="p2-harmonize-v1",
                cached=True,
                timestamp="2026-09-06T12:00:00Z",
            ),
        ).model_dump(mode="json")
        validate_contract(payload, "ocean-map")

    def test_bad_region_rejected(self) -> None:
        with pytest.raises(ValueError):
            MapResponse(
                region="atlantis",
                date="2023-06-15",
                coordinates={"latitude": [12.0], "longitude": [88.0]},
                channel="temperature",
                values=[[22.1]],
                metadata=MapMetadata(
                    model_version="hybrid_v1",
                    data_source="glorys12v1",
                    preprocessing_version="p2-harmonize-v1",
                    cached=False,
                    timestamp="2026-09-06T12:00:00Z",
                ),
            )

    def test_bad_depth_rejected(self) -> None:
        with pytest.raises(ValueError):
            MapResponse(
                region="bay_of_bengal",
                date="2023-06-15",
                coordinates={"latitude": [12.0], "longitude": [88.0]},
                channel="temperature",
                depth=12345,
                values=[[22.1]],
                metadata=MapMetadata(
                    model_version="hybrid_v1",
                    data_source="glorys12v1",
                    preprocessing_version="p2-harmonize-v1",
                    cached=False,
                    timestamp="2026-09-06T12:00:00Z",
                ),
            )


class TestProfileSchemaConforms:
    def test_minimal_valid_profile(self, validate_contract) -> None:
        payload = ProfileResponse(
            region="bay_of_bengal",
            date="2023-06-15",
            lat=12.25,
            lon=88.25,
            depths=[0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000],
            temperatures=[28.1, 27.9, 27.5, 26.0, 24.0, 18.0, 14.0, 12.5, 11.0, 10.2, 9.5, 8.0, 6.5, 5.2, 4.0],
            sigma=[0.4, 0.4, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.4, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4],
            metadata=ProfileMetadata(
                model_version="hybrid_v1",
                data_source="glorys12v1",
                preprocessing_version="p2-harmonize-v1",
                cached=False,
                timestamp="2026-09-06T12:00:00Z",
            ),
        ).model_dump(mode="json")
        validate_contract(payload, "ocean-profile")

    def test_null_temperature_allowed(self, validate_contract) -> None:
        payload = ProfileResponse(
            region="bay_of_bengal",
            date="2023-06-15",
            lat=12.25,
            lon=88.25,
            depths=[0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000],
            temperatures=[28.1, None, 27.5, 26.0, 24.0, 18.0, 14.0, 12.5, 11.0, 10.2, 9.5, 8.0, 6.5, 5.2, 4.0],
            sigma=[0.4, None, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.4, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4],
            metadata=ProfileMetadata(
                model_version="hybrid_v1",
                data_source="glorys12v1",
                preprocessing_version="p2-harmonize-v1",
                cached=False,
                timestamp="2026-09-06T12:00:00Z",
            ),
        ).model_dump(mode="json")
        validate_contract(payload, "ocean-profile")

    def test_wrong_depth_count_rejected(self) -> None:
        with pytest.raises(ValueError):
            ProfileResponse(
                region="bay_of_bengal",
                date="2023-06-15",
                lat=12.25,
                lon=88.25,
                depths=[0, 5],
                temperatures=[28.1, 27.9],
                metadata=ProfileMetadata(
                    model_version="hybrid_v1",
                    data_source="glorys12v1",
                    preprocessing_version="p2-harmonize-v1",
                    cached=False,
                    timestamp="2026-09-06T12:00:00Z",
                ),
            )


class TestErrorEnvelopeConforms:
    def test_error_schema_shape(self, validate_contract) -> None:
        payload = ErrorResponse(
            error={
                "code": "DATA_NOT_AVAILABLE",
                "message": "No data for region arabian_sea in demo scope.",
                "details": {"region": "arabian_sea"},
            }
        ).model_dump(mode="json")
        validate_contract(payload, "error")


class TestCommonEnvelope:
    def test_prediction_envelope_not_yet_used(self) -> None:
        """CommonResponse is a marker shared by map/profile envelopes (Phase 3)."""
        assert CommonResponse is not None
