"""SQLAlchemy engine/session management (SQLite by default; PostgreSQL-ready via DATABASE_URL)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    eng = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    if url.startswith("sqlite"):

        @event.listens_for(eng, "connect")
        def _sqlite_pragmas(dbapi_connection, _record) -> None:  # pragma: no cover - driver hook
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return eng


engine = _make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def configure_engine(url: str) -> None:
    """Rebind the global engine/session factory (used by tests)."""
    global engine
    engine = _make_engine(url)
    SessionLocal.configure(bind=engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from sqlalchemy import text

    from app.db import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            user_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(users)"))}
            if "refresh_jti" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN refresh_jti VARCHAR(64)"))
            job_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(jobs)"))}
            if "last_verified_date" not in job_cols:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN last_verified_date DATE"))
            if "verification_status" not in job_cols:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN verification_status VARCHAR(30) DEFAULT 'Pending Verification'"))
            conn.execute(
                text(
                    "UPDATE jobs SET verification_status = 'Synthetic Demo', last_verified_date = NULL "
                    "WHERE is_demo = 1 AND verification_status = 'Verified'"
                )
            )
