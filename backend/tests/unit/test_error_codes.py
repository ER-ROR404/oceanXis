"""Unit tests for the contract error envelope (app/schemas/error.py)."""

from __future__ import annotations

from app.schemas.error import (
    RATE_LIMITED_CODE,
    ApiError,
    ChannelUnavailableError,
    DataNotAvailableError,
    InferenceFailedError,
    InvalidCoordinateError,
    InvalidDateError,
    InvalidDepthError,
    InvalidRegionError,
    ModelNotLoadedError,
)


class TestErrorCodes:
    def test_known_codes_are_stable(self) -> None:
        """The machine-readable codes must match error.schema.json exactly."""
        from app.schemas.error import ERROR_CODES

        assert {
            "INVALID_REGION",
            "INVALID_DATE",
            "INVALID_DEPTH",
            "INVALID_COORDINATE",
            "DATA_NOT_AVAILABLE",
            "CHANNEL_UNAVAILABLE",
            "MODEL_NOT_LOADED",
            "INFERENCE_FAILED",
            "UNKNOWN_ERROR",
            RATE_LIMITED_CODE,
        } == ERROR_CODES

    def test_http_status_mapping(self) -> None:
        assert InvalidRegionError().status_code == 400
        assert InvalidDateError().status_code == 400
        assert InvalidDepthError().status_code == 400
        assert InvalidCoordinateError().status_code == 400
        assert DataNotAvailableError().status_code == 404
        assert ChannelUnavailableError().status_code == 503
        assert ModelNotLoadedError().status_code == 503
        assert InferenceFailedError().status_code == 500

    def test_error_schema_shape(self) -> None:
        err = DataNotAvailableError(details={"region": "arabian_sea"})
        payload = err.to_payload()
        assert payload["error"]["code"] == "DATA_NOT_AVAILABLE"
        assert isinstance(payload["error"]["message"], str)
        assert payload["error"]["details"] == {"region": "arabian_sea"}

    def test_message_is_safe_for_frontend(self) -> None:
        """Messages must not leak file paths or internal names."""
        err = ModelNotLoadedError(details={"path": "/srv/models/best.pt"})
        msg = err.to_payload()["error"]["message"]
        assert "best.pt" not in msg
        assert "srv" not in msg

    def test_api_error_base_defaults(self) -> None:
        base = ApiError()
        assert base.code == "UNKNOWN_ERROR"
        assert base.status_code == 500


class TestRateLimited:
    def test_code_is_special(self) -> None:
        assert RATE_LIMITED_CODE == "RATE_LIMITED"
