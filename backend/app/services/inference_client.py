"""HTTP client for the ml-inference service (torch side, never imported here).

The public interface (health / available_dates / predict_map / predict_profile)
was fixed in Phase 1; Phase 2 fills the httpx transport. Responses are never
trusted without re-validating against the contract shape (RULE 6). Typed
errors map ml-service failures to contract codes:
- model service down / 503  -> ModelNotLoadedError (503)
- ml says no data           -> DataNotAvailableError (404)
- malformed payload         -> InferenceFailedError (500)
"""

from __future__ import annotations

from typing import Any

import httpx
from cachetools import TTLCache

from app.core.config import Settings
from app.domain.depths import CANONICAL_DEPTHS
from app.schemas.error import (
    DataNotAvailableError,
    InferenceFailedError,
    ModelNotLoadedError,
)

# Time-to-live for the prediction cache (ms to keep demo latencies low while
# boundable memory: 256 entries, each a full map grid).
DEFAULT_TTL_SECONDS = 60.0


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _rows_of_numbers_or_null(rows: Any, *, expected_rows: int) -> list[list[float | None]]:
    """Validate the flat [depth][H*W] layout + null-for-land encoding."""
    if not isinstance(rows, list) or len(rows) != expected_rows:
        raise ValueError("expected depth-major numeric grid")
    first_len = None
    for row in rows:
        if not isinstance(row, list):
            raise ValueError("depth row is not a list")
        if first_len is None:
            first_len = len(row)
        if len(row) != first_len or first_len == 0:
            raise ValueError("ragged or empty depth rows")
        for v in row:
            if v is not None and not _is_number(v):
                raise ValueError("non-numeric grid value")
    return rows  # type: ignore[return-value]


class InferenceClient:
    """Client to the ml-inference service (torch side, never imported here)."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
    ) -> None:
        """Args:
        settings: overrides env config (tests).
        client: injected httpx.Client (tests use a MockTransport).
        ttl_seconds: prediction cache TTL.
        """
        self._settings = settings or Settings()
        self._base_url = self._settings.model_service_url.rstrip("/")
        self._timeout = httpx.Timeout(self._settings.model_service_timeout_seconds)
        self._client = client or httpx.Client(base_url=self._base_url, timeout=self._timeout)
        self._cache: TTLCache[tuple, dict[str, Any]] = TTLCache(maxsize=256, ttl=ttl_seconds)

    # ── public surface (fixed in Phase 1; transport is Phase 2) ──────────
    def health(self) -> dict[str, Any]:
        """Model-service health; raises typed errors when degraded."""
        try:
            resp = self._client.get("/health")
        except httpx.HTTPError as exc:
            raise ModelNotLoadedError(
                message="The model service is not available right now.",
                details={"service": "ml-inference", "reason": str(exc)[:200]},
            ) from exc
        if resp.status_code == 503:
            raise ModelNotLoadedError(
                message="The model service is not available right now.",
                details={"service": "ml-inference", "status_code": resp.status_code},
            )
        if resp.status_code != 200:
            raise InferenceFailedError(details={"service": "ml-inference", "status_code": resp.status_code})
        try:
            body = resp.json()
            _validate_health_body(body)
        except (ValueError, TypeError) as exc:
            raise InferenceFailedError(
                details={"service": "ml-inference", "reason": f"malformed health response: {exc}"}
            ) from exc
        return body

    def available_dates(self, region: str) -> list[str]:
        """ISO dates covered by the region's tensor store.

        Honest degraded behavior: when the model service is down or the model
        is not loaded, returns an empty list (Phase 1 contract: 200 + []).
        Only a malformed 200 response raises (surfacing a real bug).
        """
        del region
        try:
            resp = self._client.get("/health")
        except httpx.HTTPError:
            return []
        if resp.status_code != 200:
            return []
        try:
            body = resp.json()
            _validate_health_body(body)
        except (ValueError, TypeError) as exc:
            raise InferenceFailedError(
                details={"service": "ml-inference", "reason": f"malformed health response: {exc}"}
            ) from exc
        return list(body["dates"])

    def predict_map(self, region: str, date: str) -> dict[str, Any]:
        """Mu/log_var grids for a region/date [depth][H*W] (null = land)."""
        cache_key: tuple[str, str, str] = ("map", region, date)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        body = self._post_predict(region, date, endpoint="/predict")
        self._cache[cache_key] = body
        return body

    def predict_profile(self, region: str, date: str, lat: float, lon: float) -> dict[str, Any]:
        """Nearest-cell temperature profile [15] (null = land)."""
        cache_key: tuple[str, str, str, float, float] = ("profile", region, date, lat, lon)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            resp = self._client.post(
                "/predict_profile",
                json={"region": region, "date": date, "lat": lat, "lon": lon},
            )
        except httpx.HTTPError as exc:
            raise ModelNotLoadedError(
                message="The model service is not available right now.",
                details={"service": "ml-inference", "reason": str(exc)[:200]},
            ) from exc
        body = self._map_status_code(resp, what="profile")
        try:
            _validate_profile_body(body)
        except ValueError as exc:
            raise InferenceFailedError(
                details={"service": "ml-inference", "reason": f"malformed profile response: {exc}"}
            ) from exc
        self._cache[cache_key] = body
        return body

    # ── internals ─────────────────────────────────────────────────────────
    def _post_predict(self, region: str, date: str, *, endpoint: str) -> dict[str, Any]:
        try:
            resp = self._client.post(endpoint, json={"region": region, "date": date})
        except httpx.HTTPError as exc:
            raise ModelNotLoadedError(
                message="The model service is not available right now.",
                details={"service": "ml-inference", "reason": str(exc)[:200]},
            ) from exc
        body = self._map_status_code(resp, what="prediction")
        try:
            _validate_predict_body(body)
        except ValueError as exc:
            raise InferenceFailedError(
                details={"service": "ml-inference", "reason": f"malformed prediction response: {exc}"}
            ) from exc
        return body

    def _map_status_code(self, resp: httpx.Response, *, what: str) -> dict[str, Any]:
        if resp.status_code == 503:
            raise ModelNotLoadedError(
                message="The model service is not available right now.",
                details={"service": "ml-inference", "status_code": resp.status_code},
            )
        if resp.status_code == 404:
            raise DataNotAvailableError(
                details={"service": "ml-inference", "status_code": resp.status_code, "what": what}
            )
        if resp.status_code != 200:
            raise InferenceFailedError(
                details={"service": "ml-inference", "status_code": resp.status_code, "what": what}
            )
        body = resp.json()
        if not isinstance(body, dict):
            raise InferenceFailedError(details={"service": "ml-inference", "reason": "non-object payload"})
        return body


def _validate_health_body(body: Any) -> None:
    """Contract shape: {status: "ok", dates: [iso...]}."""
    if not isinstance(body, dict) or body.get("status") != "ok":
        raise ValueError("health status != ok")
    dates = body.get("dates")
    if not isinstance(dates, list) or not all(isinstance(d, str) and len(d) == 10 for d in dates):
        raise ValueError("health dates must be a list of ISO strings")


def _validate_predict_body(body: Any) -> None:
    """Contract shape: {mu, log_var: [15][H*W] numeric-or-null, latitude/longitude
    grids, metadata strings}. The ocean-map route builds its coordinates from
    these arrays — a grid mismatch is malformed, never silently guessed."""
    if not isinstance(body, dict):
        raise ValueError("prediction payload is not an object")
    expected = len(CANONICAL_DEPTHS)
    rows = _rows_of_numbers_or_null(body.get("mu"), expected_rows=expected)
    _rows_of_numbers_or_null(body.get("log_var"), expected_rows=expected)
    latitude = body.get("latitude")
    longitude = body.get("longitude")
    if not isinstance(latitude, list) or not isinstance(longitude, list):
        raise ValueError("missing latitude/longitude grids")
    if not latitude or not longitude:
        raise ValueError("empty latitude/longitude grids")
    if not all(_is_number(v) for v in latitude) or not all(_is_number(v) for v in longitude):
        raise ValueError("non-numeric latitude/longitude value")
    if len(rows[0]) != len(latitude) * len(longitude):
        raise ValueError("grid dims mismatch: mu row length != len(lat) * len(lon)")
    for field in ("series_id", "date", "region", "model_version"):
        if not isinstance(body.get(field), str):
            raise ValueError(f"missing string field: {field}")


def _validate_profile_body(body: Any) -> None:
    """Contract shape: {temperatures: [15] numeric-or-null, snapped coords}."""
    if not isinstance(body, dict):
        raise ValueError("profile payload is not an object")
    temps = body.get("temperatures")
    if not isinstance(temps, list) or len(temps) != len(CANONICAL_DEPTHS):
        raise ValueError("temperatures must have one entry per canonical depth")
    for v in temps:
        if v is not None and not _is_number(v):
            raise ValueError("non-numeric temperature")
    for field in ("latitude", "longitude"):
        if not _is_number(body.get(field)):
            raise ValueError(f"missing numeric field: {field}")
    for field in ("series_id", "date", "region", "model_version"):
        if not isinstance(body.get(field), str):
            raise ValueError(f"missing string field: {field}")
