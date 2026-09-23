"""Semantic search endpoint (retrieval only, no LLM)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.embeddings.ollama_embeddings import EmbeddingError
from app.models.schemas import SearchRequest, SearchResponse
from app.rag import search as rag_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def semantic_search(req: SearchRequest, db: Session = Depends(get_db)):
    try:
        result = rag_search(db, req.query, req.top_k, req.reranker)
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return SearchResponse(**result)
