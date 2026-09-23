"""Shared pytest fixtures and availability guards.

Pure unit tests run everywhere. Integration tests require a live Postgres+pgvector
and a reachable Ollama; they skip automatically when those are not available.
"""
from __future__ import annotations

import httpx
import pytest
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal, engine, init_db


def _db_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _ollama_available() -> bool:
    try:
        r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


requires_db = pytest.mark.skipif(not _db_available(), reason="Postgres not available")
requires_ollama = pytest.mark.skipif(
    not _ollama_available(), reason="Ollama not available"
)
requires_stack = pytest.mark.skipif(
    not (_db_available() and _ollama_available()),
    reason="Full stack (Postgres + Ollama) not available",
)


@pytest.fixture
def db():
    """A clean database session with tables initialized and data cleared."""
    init_db()
    session = SessionLocal()
    session.execute(text("TRUNCATE chunks, documents RESTART IDENTITY CASCADE"))
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
