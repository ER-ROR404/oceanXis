"""Seed script: populate app_metadata from config.

Idempotent (Upsert via merge). Never writes credentials (RULE 14).

Usage:
    OCEANEMBED_DATABASE_URL=postgresql+psycopg://... python -m scripts.seed_metadata
"""

from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import AppMetadata

logger = logging.getLogger(__name__)

SEED_KEYS = ("model_version", "trained_on", "data_version", "app_version")


def _entries(settings: Settings) -> dict[str, str]:
    return {
        "model_version": settings.model_version,
        "trained_on": settings.trained_on,
        "data_version": settings.data_version,
        "app_version": settings.app_version,
    }


def seed(engine, settings: Settings | None = None) -> dict[str, str]:
    settings = settings or Settings()
    entries = _entries(settings)
    with Session(engine) as session:
        for key, value in entries.items():
            session.merge(AppMetadata(key=key, value=value))
        session.commit()
    return entries


def main() -> None:  # pragma: no cover - CLI entry point
    url = os.environ.get(
        "OCEANEMBED_DATABASE_URL",
        "postgresql+psycopg://oceanembed:oceanembed@localhost:5432/oceanembed",
    )
    engine = create_engine(url)
    entries = seed(engine)
    logger.info("seeded %d metadata keys: %s", len(entries), sorted(entries))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
