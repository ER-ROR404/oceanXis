"""Phase 4.2: seed_metadata idempotency + AppMetadata model (unit, no live DB).

Uses an in-memory SQLite engine so the test runs anywhere. Confirms:
  - seeding writes the 4 expected keys;
  - a SECOND seeding upserts (no duplicate rows) — idempotent;
  - values round-trip through the ORM and match Settings defaults.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import AppMetadata, Base
from scripts.seed_metadata import _entries, seed

EXPECTED_KEYS = ("model_version", "trained_on", "data_version", "app_version")


@pytest.fixture()
def engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def _row_count(engine) -> int:
    return len(engine.connect().execute(select(AppMetadata)).all())


def _as_dict(engine) -> dict[str, str]:
    with Session(engine) as session:
        return {row.key: row.value for row in session.scalars(select(AppMetadata))}


class TestSeedMetadata:
    def test_seed_entries_come_from_settings(self) -> None:
        settings = Settings()
        entries = _entries(settings)
        assert set(entries) == set(EXPECTED_KEYS)
        assert entries["model_version"] == settings.model_version
        assert entries["trained_on"] == settings.trained_on
        assert entries["data_version"] == settings.data_version
        assert entries["app_version"] == settings.app_version

    def test_seed_writes_all_keys(self, engine) -> None:
        settings = Settings()
        seed(engine, settings)
        stored = _as_dict(engine)
        assert set(stored) == set(EXPECTED_KEYS)
        assert stored["model_version"] == settings.model_version

    def test_seed_is_idempotent(self, engine) -> None:
        settings = Settings()
        seed(engine, settings)
        seed(engine, settings)  # second run must not duplicate rows
        assert _row_count(engine) == len(EXPECTED_KEYS)

    def test_seed_repeated_many_times_stays_single_row(self, engine) -> None:
        settings = Settings()
        for _ in range(5):
            seed(engine, settings)
        assert _row_count(engine) == len(EXPECTED_KEYS)

    def test_seed_values_round_trip(self, engine) -> None:
        settings = Settings()
        seed(engine, settings)
        stored = _as_dict(engine)
        assert stored["model_version"] == "hybrid_v1"
        assert stored["trained_on"] == "2023-12-31"
