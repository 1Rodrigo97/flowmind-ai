"""ORM models for Document Insights and automation runs (n8n pillar)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DocumentInsights(Base):
    """LLM-generated, document-grounded insights. One row per document."""

    __tablename__ = "document_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(120), default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    tasks: Mapped[list] = mapped_column(JSON, default=list)  # [{text, due_date}]
    dates: Mapped[list] = mapped_column(JSON, default=list)
    model: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")  # SUCCESS | FAILED
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped["object"] = relationship("Document")


class AutomationRun(Base):
    """One inbox-file processing attempt, for idempotency and observability."""

    __tablename__ = "automation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_uid: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    workflow: Mapped[str] = mapped_column(String(120), default="inbox")
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # PENDING | PROCESSING | SUCCESS | DUPLICATE | FAILED
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    # Ingestion vs insights are tracked separately (INGESTION_SUCCESS != INSIGHTS_SUCCESS).
    insights_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
