"""Factory selecting a reranker implementation by name."""
from __future__ import annotations

from functools import lru_cache

from app.rag.reranker.base import RerankerProvider
from app.rag.reranker.lexical import LexicalReranker


@lru_cache
def get_reranker(model: str = "lexical") -> RerankerProvider:
    key = (model or "lexical").lower()
    if key in ("lexical", "bm25"):
        return LexicalReranker()
    raise ValueError(f"Unknown reranker model: {model}")
