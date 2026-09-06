"""Per-IP sliding-window rate limiter (plan 3.3).

Default budget: 30 requests per 60-second window.  The limiter is
stateful but lightweight — a deque of timestamps per key, pruned on
each ``allow()`` call.

``RateLimiter`` is a plain class with no framework dependency so it
can be unit-tested in isolation; the FastAPI dependency wiring lives
in ``rate_limit_dependency()`` at the bottom of this module.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Request


class RateLimiter:
    """Sliding-window token bucket, keyed by an arbitrary string (typically an IP)."""

    def __init__(
        self,
        limit: int = 30,
        window_seconds: float = 60.0,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow(self, key: str) -> bool:
        """Return True if the request is within budget, False otherwise."""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets[key]
            self._prune(bucket, now)
            if len(bucket) >= self.limit:
                return False
            bucket.append(now)
            return True

    def remaining(self, key: str) -> int:
        """How many requests the *key* still has in the current window."""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets[key]
            self._prune(bucket, now)
            return max(0, self.limit - len(bucket))

    def reset(self, key: str) -> None:
        """Drop all stored timestamps for *key* (manual reset)."""
        with self._lock:
            self._buckets.pop(key, None)

    def retry_after(self, key: str) -> float:
        """Seconds until the oldest request in the window expires (for Retry-After)."""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets[key]
            self._prune(bucket, now)
            if not bucket:
                return 0.0
            return max(0.0, self.window_seconds - (now - bucket[0]))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _prune(self, bucket: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()


# Module-level singleton used by the route dependency / middleware.
# Reset via ``_GLOBAL_LIMITER.reset(ip)`` in tests.
_GLOBAL_LIMITER = RateLimiter(limit=30, window_seconds=60.0)


def _client_ip(request: Request) -> str:
    """Extract client IP from X-Forwarded-For or direct connection."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_dependency(request: Request) -> None:
    """FastAPI dependency — raises RateLimitError if the IP is over budget.

    Import ``RateLimitError`` from ``app.main`` to avoid circular deps.
    Imported lazily inside the function.
    """
    from app.main import RateLimitError

    ip = _client_ip(request)
    if not _GLOBAL_LIMITER.allow(ip):
        raise RateLimitError()
