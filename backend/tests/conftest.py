"""Pytest fixtures providing isolated temporary SQLite database and FastAPI TestClient."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    db_file = tmp_path / "test_thiransetu.db"
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-with-more-than-32-chars!!")
    monkeypatch.setenv("LLM_ENABLED", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("SEED_DEMO_DATA", "true")

    from app.core.config import get_settings
    from app.core.rate_limit import limiter
    from app.db.seed import seed_jobs_if_empty
    from app.db.session import SessionLocal, configure_engine, init_db

    get_settings.cache_clear()
    limiter.reset()
    configure_engine(os.environ["DATABASE_URL"])
    init_db()
    from app.db import session as db_session

    with SessionLocal() as db:
        seed_jobs_if_empty(db)
    yield
    db_session.engine.dispose()
    get_settings.cache_clear()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    from app.main import create_app

    with TestClient(create_app()) as tc:
        yield tc


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/auth/register",
        json={"email": "student@example.com", "password": "Password1", "full_name": "Aarav Kumar"},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
