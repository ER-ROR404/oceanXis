"""SQLAlchemy engine/session with graceful degradation.

The demo must run even when postgres is not reachable: health reports the
databse check as degraded (never down), and no request path requires the DB.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal: sessionmaker | None = None
_default_settings = Settings()


def _get_engine(settings: Settings):
    global _engine, _SessionLocal
    if _engine is None:
        database_url = settings.database_url
        connect_args = {"connect_timeout": 2} if database_url.startswith("postgresql") else {}
        _engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def engine(settings: Settings | None = None) -> object:
    return _get_engine(settings or _default_settings)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a DB session."""
    _get_engine(_default_settings)  # ensure engine + sessionmaker exist
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


def check_database() -> bool:
    """SELECT 1 liveness probe; never raises."""
    try:
        with engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # pragma: no cover - probe must not raise
        logger.warning("database check failed: %s", exc)
        return False


DbSession = Annotated[Session, Depends(get_session)]