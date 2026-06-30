"""Engine + session factory (plan/01-data-model.md).

The engine is created lazily so importing this module never requires a live DB or
a valid URL — only the first actual query connects. That keeps metadata-only unit
tests (and Alembic offline mode) free of a database dependency.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from vcm.config import get_settings

_engine: Engine | None = None
_sessionmaker: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, future=True, pool_pre_ping=True)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = sessionmaker(bind=get_engine(), expire_on_commit=False, class_=Session)
    return _sessionmaker


def get_session() -> Iterator[Session]:
    """FastAPI dependency: yields a session, always closed."""
    with get_sessionmaker()() as session:
        yield session


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope: commit on success, rollback on error."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
