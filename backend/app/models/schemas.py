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


class RetrievedChunk(BaseModel):
    document_id: int
    document: str
    section: str | None = None
    page: int | None = None
    excerpt: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[RetrievedChunk]


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
