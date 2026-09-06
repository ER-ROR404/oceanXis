"""Unit tests for backend settings (app/core/config.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings


class TestSettings:
    def test_defaults(self) -> None:
        s = Settings()
        assert s.model_service_url == "http://ml-inference:8080"
        assert s.app_name == "oceanembed"
        assert s.app_version is not None
        assert s.model_version == "hybrid_v1"
        assert "8000" in str(s.cors_origins) or "localhost" in "".join(s.cors_origins)

    def test_env_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OCEANEMBED_MODEL_SERVICE_URL", "http://localhost:9999")
        monkeypatch.setenv("OCEANEMBED_APP_VERSION", "9.9.9")
        s = Settings()
        assert s.model_service_url == "http://localhost:9999"
        assert s.app_version == "9.9.9"

    def test_demo_cache_dir_absolute(self, tmp_path: Path) -> None:
        s = Settings(demo_cache_dir=tmp_path)
        assert s.demo_cache_dir == tmp_path

    def test_public_fields_screen_secrets(self) -> None:
        """Config must expose no credential fields at all (RULE 14 hygiene)."""
        s = Settings()
        public = {k for k in s.model_dump()}
        assert not {"password", "token", "secret", "api_key"} & set(k.lower() for k in public)
