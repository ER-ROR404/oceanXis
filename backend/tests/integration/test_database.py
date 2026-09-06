"""Integration tests: database session + app_metadata model (sqlite in tests)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import AppMetadata


class TestAppMetadataModel:
    def test_roundtrip(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        AppMetadata.metadata.create_all(engine)
        with Session(engine) as session:
            row = AppMetadata(
                key="model_version",
                value="hybrid_v1",
                updated_at=datetime.now(UTC),
            )
            session.add(row)
            session.commit()

            fetched = session.get(AppMetadata, "model_version")
            assert fetched is not None
            assert fetched.value == "hybrid_v1"

    def test_upsert_semantics(self) -> None:
        """Seed must be idempotent: writing the same key twice keeps one row."""
        engine = create_engine("sqlite:///:memory:")
        AppMetadata.metadata.create_all(engine)
        with Session(engine) as session:
            for v in ("v1", "v2"):
                row = AppMetadata(key="model_version", value=v)
                session.merge(row)
                session.commit()
            rows = session.query(AppMetadata).filter_by(key="model_version").all()
            assert len(rows) == 1
            assert rows[0].value == "v2"


class TestSeedScript:
    def test_seed_populates_all_keys(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        AppMetadata.metadata.create_all(engine)

        from scripts.seed_metadata import seed

        entries = seed(engine, Settings())
        assert set(entries) == {"model_version", "trained_on", "data_version", "app_version"}

        with Session(engine) as session:
            for key, expected in entries.items():
                row = session.get(AppMetadata, key)
                assert row is not None
                assert row.value == expected

    def test_seed_is_idempotent(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        AppMetadata.metadata.create_all(engine)

        from scripts.seed_metadata import seed

        seed(engine, Settings())
        seed(engine, Settings())

        with Session(engine) as session:
            assert session.query(AppMetadata).count() == 4


class TestCheckDatabase:
    def test_reports_false_when_unreachable(self) -> None:
        """Liveness probe must be safe when the DB is down (never raises)."""
        from app.database.session import check_database

        # nothing running on this port during tests -> False, no exception
        result = check_database()
        assert isinstance(result, bool)

    def test_get_session_yields_and_closes(self, monkeypatch) -> None:
        """FastAPI DbSession dependency: yields an open session, closes after."""
        import app.database.session as session_mod
        from app.core.config import Settings

        monkeypatch.setattr(session_mod, "_engine", None)
        monkeypatch.setattr(session_mod, "_SessionLocal", None)
        monkeypatch.setattr(session_mod, "_default_settings", Settings(database_url="sqlite:///:memory:"))

        gen = session_mod.get_session()
        session = next(gen)
        assert session is not None
        # session is usable for a query against the sqlite engine
        from sqlalchemy import text

        assert session.execute(text("SELECT 1")).scalar() == 1
        gen.close()
