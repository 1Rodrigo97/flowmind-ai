"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    size_bytes: int
    chunk_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class UploadResult(BaseModel):
    document_id: int
    filename: str
    chunks: int
    status: str
    duplicate: bool = False


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    # When set, overrides the server default so the RAG Explorer can toggle reranking.
    reranker: bool | None = None


class RetrievedChunk(BaseModel):
    document_id: int
    document: str
    section: str | None = None
    page: int | None = None
    excerpt: str
    score: float
    rerank_score: float | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[RetrievedChunk]
    reranker: str | None = None
    # Vector-order results before reranking (present only when reranking is on),
    # so the RAG Explorer can show the reordering.
    original: list[RetrievedChunk] | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)


class ChatResponse(BaseModel):
    answer: str
    sources: list[RetrievedChunk]
    status: str  # "answered" | "insufficient_context"


class StatsResponse(BaseModel):
    documents: int
    chunks: int
    file_types: dict[str, int]
    recent: list[DocumentOut]


# ---- Evaluation lab (V2) ----


class ExperimentConfig(BaseModel):
    name: str = Field(min_length=1)
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    chunk_size: int = Field(default=700, ge=100, le=4000)
    chunk_overlap: int = Field(default=100, ge=0, le=1000)
    top_k: int = Field(default=5, ge=1, le=50)
    similarity_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    reranker_enabled: bool = False
    reranker_model: str = "lexical"
    reranker_candidates: int = Field(default=15, ge=1, le=100)


class RunRequest(BaseModel):
    config: ExperimentConfig
    dataset: str = "default"
    include_answer: bool = False


class ExperimentSummary(BaseModel):
    id: int
    name: str
    index_profile: str
    dataset_name: str
    dataset_size: int
    config: dict
    metrics: dict
    commit_sha: str | None = None
    duration_ms: float
    created_at: datetime

    class Config:
        from_attributes = True


class ExperimentDetail(ExperimentSummary):
    results: list[dict]


class CompareRequest(BaseModel):
    experiment_ids: list[int] = Field(min_length=2)


class CompareRow(BaseModel):
    id: int
    name: str
    metrics: dict


class CompareResponse(BaseModel):
    experiments: list[CompareRow]
    deltas: dict
