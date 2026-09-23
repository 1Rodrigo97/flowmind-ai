"""Database engine, session factory and schema initialization."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Ensure the pgvector extension, tables and V2 columns exist."""
    # Import models so they register on Base.metadata before create_all.
    from app import models  # noqa: F401
    from app.core.config import settings

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)

    # Lightweight, idempotent migration for V2 columns added to V1 tables.
    # The profile is a controlled slug (model name + ints); still, quote defensively
    # for the DDL literal since parameters cannot bind in ALTER ... DEFAULT.
    default_profile = settings.default_index_profile.replace("'", "''")
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS raw_text TEXT"))
        conn.execute(
            text(
                "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS index_profile "
                f"VARCHAR(128) NOT NULL DEFAULT '{default_profile}'"
            )
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_chunks_index_profile ON chunks (index_profile)")
        )
        # Replace the V1 uniqueness (document_id, chunk_index) with a profile-aware one
        # so the same document can be re-chunked under multiple index profiles.
        conn.execute(text("ALTER TABLE chunks DROP CONSTRAINT IF EXISTS uq_doc_chunk"))
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_profile_chunk "
                "ON chunks (document_id, index_profile, chunk_index)"
            )
        )


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
