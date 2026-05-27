from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .orm_models import Base, SettingORM
from .schema_migrations import ensure_user_profile_schema
from .settings import get_settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _expand_sqlite_url(url: str) -> str:
    if not url.startswith("sqlite:"):
        return url
    if url.startswith("sqlite:////"):
        return url
    if url.startswith("sqlite:///"):
        raw_path = url[len("sqlite:///") :]
        if raw_path in ("", ":memory:"):
            return url
        path = Path(raw_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"
    return url


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite:"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True, "pool_recycle": 3600}


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db() -> None:
    global _engine, _SessionLocal
    settings = get_settings()
    url = _expand_sqlite_url(settings.resolved_database_url())
    _engine = create_engine(url, **_engine_kwargs(url))
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(_engine)
    ensure_user_profile_schema(_engine)
    _seed_default_settings()
    logger.info("database ready at %s", url)


def _seed_default_settings() -> None:
    defaults = {
        "strategy": "failover",
        "billing_budget_usd": "50",
    }
    if _SessionLocal is None:
        return
    with _SessionLocal() as session:
        for key, value in defaults.items():
            existing = session.get(SettingORM, key)
            if existing is None:
                session.add(SettingORM(setting_key=key, setting_value=value))
        session.commit()


def get_engine() -> Engine:
    if _engine is None:
        init_db()
    assert _engine is not None
    return _engine


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        init_db()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        init_db()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
