"""Factory selecting the configured embedding provider."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.ollama_embeddings import OllamaEmbeddingProvider


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.embedding_provider.lower()
    if provider == "ollama":
        return OllamaEmbeddingProvider(
            base_url=settings.ollama_base_url,
            model=settings.embedding_model,
            dim=settings.embedding_dim,
        )
    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
