"""Unit tests: demo cache (Phase 1 shape; Phase 4 wires real readers)."""

from __future__ import annotations

from app.schemas.error import DataNotAvailableError
from app.services.cache import DemoCache


class TestDemoCache:
    def test_not_accessible_without_dir(self, tmp_path) -> None:
        cache = DemoCache.__new__(DemoCache)
        cache._settings = None
        # point at a nonexistent dir directly
        cache._cache_dir = tmp_path / "does-not-exist"
        assert not cache.accessible

    def test_assert_accessible_raises(self, tmp_path) -> None:
        cache = DemoCache.__new__(DemoCache)
        cache._settings = None
        cache._cache_dir = tmp_path / "does-not-exist"
        try:
            cache.assert_accessible()
            raise AssertionError("expected DataNotAvailableError")
        except DataNotAvailableError:
            pass

    def test_stub_readers_return_none(self, tmp_path) -> None:
        """Phase 1: readers are stubs returning no fallback (Phase 4 fills)."""
        cache = DemoCache.__new__(DemoCache)
        cache._settings = None
        cache._cache_dir = tmp_path / "does-not-exist"
        assert cache.get_map("bay_of_bengal", "2022-01-01", 0) is None
        assert cache.get_profile("bay_of_bengal", "2022-01-01", 10.0, 90.0) is None
