"""Unit tests for the per-IP sliding-window rate limiter (plan 3.3).

The RateLimiter is a pure-logic class — no HTTP, no FastAPI — so these
tests are fast and deterministic.  Integration tests that exercise the
HTTP 429 envelope live in ``tests/api/test_ratelimit_api.py``.
"""

from __future__ import annotations

import time

from app.core.ratelimit import RateLimiter


class TestRateLimiterUnit:
    """Behavioural contract for the sliding-window token bucket."""

    def test_allows_requests_under_limit(self) -> None:
        limiter = RateLimiter(limit=5, window_seconds=60.0)
        for _ in range(5):
            assert limiter.allow("ip-1") is True

    def test_blocks_when_limit_exceeded(self) -> None:
        limiter = RateLimiter(limit=3, window_seconds=60.0)
        for _ in range(3):
            limiter.allow("ip-1")
        assert limiter.allow("ip-1") is False

    def test_different_keys_are_independent(self) -> None:
        limiter = RateLimiter(limit=2, window_seconds=60.0)
        limiter.allow("ip-1")
        limiter.allow("ip-1")
        assert limiter.allow("ip-1") is False  # ip-1 exhausted
        assert limiter.allow("ip-2") is True   # ip-2 untouched

    def test_requests_expire_after_window(self) -> None:
        limiter = RateLimiter(limit=2, window_seconds=0.05)
        limiter.allow("ip-1")
        limiter.allow("ip-1")
        assert limiter.allow("ip-1") is False
        # Wait for the window to expire.
        time.sleep(0.06)
        assert limiter.allow("ip-1") is True

    def test_oldest_request_expires_first(self) -> None:
        limiter = RateLimiter(limit=2, window_seconds=0.05)
        limiter.allow("ip-1")  # t=0
        time.sleep(0.03)
        limiter.allow("ip-1")  # t=0.03
        assert limiter.allow("ip-1") is False  # both still in window
        time.sleep(0.03)  # now t=0.06 — first request expired
        assert limiter.allow("ip-1") is True   # first expired, second still valid

    def test_remaining_returns_correct_count(self) -> None:
        limiter = RateLimiter(limit=5, window_seconds=60.0)
        assert limiter.remaining("ip-1") == 5
        limiter.allow("ip-1")
        assert limiter.remaining("ip-1") == 4
        limiter.allow("ip-1")
        assert limiter.remaining("ip-1") == 3

    def test_remaining_never_negative(self) -> None:
        limiter = RateLimiter(limit=2, window_seconds=60.0)
        for _ in range(5):
            limiter.allow("ip-1")
        assert limiter.remaining("ip-1") == 0

    def test_reset_clears_the_bucket(self) -> None:
        limiter = RateLimiter(limit=2, window_seconds=60.0)
        limiter.allow("ip-1")
        limiter.allow("ip-1")
        assert limiter.allow("ip-1") is False
        limiter.reset("ip-1")
        assert limiter.allow("ip-1") is True
        assert limiter.remaining("ip-1") == 1

    def test_default_limit_is_reasonable(self) -> None:
        """The production constructor uses sensible defaults."""
        limiter = RateLimiter()  # default: 30 req / 60 s
        for _ in range(30):
            assert limiter.allow("ip-default") is True
        assert limiter.allow("ip-default") is False
        assert limiter.remaining("ip-default") == 0
