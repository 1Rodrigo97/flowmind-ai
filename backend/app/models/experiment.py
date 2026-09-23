"""ORM models for the RAG evaluation lab (V2).

An experiment stores the full configuration and reproducibility metadata (commit
SHA, model, dataset, timestamp) plus the aggregated metrics. Per-question rows
are stored in the results table. No document content is persisted here.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RagExperiment(Base):
    __tablename__ = "rag_experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    index_profile: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dataset_size: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    results: Mapped[list["RagExperimentResult"]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RagExperimentResult(Base):
    __tablename__ = "rag_experiment_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("rag_experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_documents: Mapped[list] = mapped_column(JSON, nullable=False)
    hit: Mapped[bool] = mapped_column(default=False)
    reciprocal_rank: Mapped[float] = mapped_column(Float, default=0.0)
    precision_at_k: Mapped[float] = mapped_column(Float, default=0.0)
    recall_at_k: Mapped[float] = mapped_column(Float, default=0.0)
    answered: Mapped[bool] = mapped_column(default=False)
    correct_refusal: Mapped[bool] = mapped_column(default=False)
    terms_matched: Mapped[float] = mapped_column(Float, default=0.0)

    experiment: Mapped["RagExperiment"] = relationship(back_populates="results")
