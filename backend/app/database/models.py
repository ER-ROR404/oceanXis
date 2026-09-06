"""SQLAlchemy ORM models (Phase 1.4: app_metadata table)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all OceanEmbed database models."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AppMetadata(Base):
    """Key/value runtime metadata (model versions, dataset fingerprints).

    Survives restarts; seeded by backend/scripts/seed_metadata.py from
    config; never stores credentials (RULE 14).
    """

    __tablename__ = "app_metadata"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<AppMetadata key={self.key!r} value={self.value!r}>"