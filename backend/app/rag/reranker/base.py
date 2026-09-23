"""Reranker abstraction.

A reranker re-scores the top-N vector candidates against the query with a signal
independent from the embedding similarity, then the caller keeps the top-K. It is
decoupled from retrieval so different rerankers can be swapped via configuration.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class RerankerProvider(ABC):
    name: str

    @abstractmethod
    def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        """Return the candidate chunks reordered by relevance.

        Each returned dict is the input chunk augmented with a ``rerank_score``
        (0..1). The list is sorted by ``rerank_score`` descending. The caller is
        responsible for truncating to the final top-K.
        """
