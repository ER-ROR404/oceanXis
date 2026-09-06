"""Contract error envelope (contracts/api/error.schema.json).

Codes are stable machine identifiers; messages are safe for the frontend.
Never leaks credentials or internal dataset details (RULE 14 hygiene).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.domain.depths import CANONICAL_DEPTHS
from app.domain.regions import REGION_IDS

# Added as part of contract update C1 (approved): the API needs a
# rate-limit error distinct from generic failures.
RATE_LIMITED_CODE = "RATE_LIMITED"

ERROR_CODES = frozenset(
    {
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
    }
)


class ErrorResponse(BaseModel):
    """Exact envelope from error.schema.json."""

    error: dict[str, Any] = Field(..., description="error envelope")


def to_error_payload(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    """Serialize a contract-conformant error envelope."""
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return payload


class ApiError(Exception):
    """Base error mapped to a contract error code + HTTP status."""

    code: str = "UNKNOWN_ERROR"
    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details

    def to_payload(self) -> dict[str, Any]:
        return to_error_payload(self.code, self.message, self.details)


class InvalidRegionError(ApiError):
    code = "INVALID_REGION"
    status_code = 400
    message = f"Unknown region. Valid regions: {', '.join(REGION_IDS)}."


class InvalidDateError(ApiError):
    code = "INVALID_DATE"
    status_code = 400
    message = "Invalid date. Use YYYY-MM-DD within the region's available coverage."


class InvalidDepthError(ApiError):
    code = "INVALID_DEPTH"
    status_code = 400
    message = (
        f"Invalid depth. Choose one of the {len(CANONICAL_DEPTHS)} canonical depths: "
        f"{', '.join(str(d) for d in CANONICAL_DEPTHS)} m."
    )


class InvalidCoordinateError(ApiError):
    code = "INVALID_COORDINATE"
    status_code = 400
    message = "Coordinates outside the region's grid. Check latitude/longitude bounds."


class DataNotAvailableError(ApiError):
    code = "DATA_NOT_AVAILABLE"
    status_code = 404
    message = "No data available for the requested region/date."


class ChannelUnavailableError(ApiError):
    code = "CHANNEL_UNAVAILABLE"
    status_code = 503
    message = "One or more input channels are unavailable; no prediction produced."


class ModelNotLoadedError(ApiError):
    code = "MODEL_NOT_LOADED"
    status_code = 503
    message = "The model service is not available right now."


class InferenceFailedError(ApiError):
    code = "INFERENCE_FAILED"
    status_code = 500
    message = "Model inference failed. Please retry later."


class UnknownError(ApiError):
    """Default 500 handler error (kept for unhandled paths)."""

    code = "UNKNOWN_ERROR"
    status_code = 500
    message = "An unexpected error occurred."
