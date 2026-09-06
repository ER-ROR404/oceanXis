"""Application settings (pydantic-settings).

No credentials live here (RULE 14): the backend never holds Copernicus
credentials at runtime for the local demo; when live ingestion is enabled
later, credentials come from env vars only, never from this class.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration with sane local-demo defaults.

    Every field can be overridden via ``OCEANEMBED_<FIELD>`` env vars.
    """

    model_config = SettingsConfigDict(
        env_prefix="OCEANEMBED_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App identity ──────────────────────────────────────────────────────
    app_name: str = "oceanembed"
    app_version: str = "0.1.0"
    model_version: str = "hybrid_v1"
    model_architecture: str = "oceanembed_net"

    # ── Services / wiring ─────────────────────────────────────────────────
    model_service_url: str = "http://ml-inference:8080"
    model_service_timeout_seconds: float = 30.0

    # ── Database ───────────────────────────────────────────────────────────
    # Default matches docker-compose postgres service; local tests override
    # with sqlite. Never stores credentials beyond this connection string,
    # which must not contain secrets (RULE 14).
    database_url: str = (
        "postgresql+psycopg://oceanembed:oceanembed@localhost:5432/oceanembed"
    )

    # ── Data / cache paths ────────────────────────────────────────────────
    demo_cache_dir: Path = Path("../artifacts/demo_cache")

    # ── HTTP hygiene ──────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    rate_limit_per_minute: int = 30
    request_log_level: str = "INFO"

    # ── Honesty metadata (not a realtime claim — see contract) ────────────
    trained_on: str = "2023-12-31"
    data_freshness: str = "2023-12-31"
    data_version: str = "bay_of_bengal-2022-2023-v1"
