"""Embedding provider abstraction.

Keeps embedding generation decoupled from the repository/database layer and from
any concrete backend, so new providers can be added without touching the RAG code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Turns text into fixed-size float vectors."""

    dim: int

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Embed a single string."""

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed many strings. Default is sequential; providers may override."""
        return [self.embed(t) for t in texts]
