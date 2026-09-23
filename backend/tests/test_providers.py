"""Provider abstraction tests, including controlled failure when Ollama is down.

Covers T11 (Ollama unavailable -> controlled error) without needing a live stack:
the providers point at an unreachable port and must raise their typed errors.
"""
from __future__ import annotations

import pytest

from app.embeddings.ollama_embeddings import EmbeddingError, OllamaEmbeddingProvider
from app.llm.base import LLMError
from app.llm.ollama_provider import OllamaProvider

UNREACHABLE = "http://127.0.0.1:1"  # nothing listens here


def test_llm_unavailable_raises_controlled_error():
    provider = OllamaProvider(base_url=UNREACHABLE, model="llama3.2:3b", timeout=2.0)
    with pytest.raises(LLMError):
        provider.generate(system="s", prompt="p")


def test_embeddings_unavailable_raises_controlled_error():
    provider = OllamaEmbeddingProvider(
        base_url=UNREACHABLE, model="nomic-embed-text", dim=768, timeout=2.0
    )
    with pytest.raises(EmbeddingError):
        provider.embed("hello")


def test_embedding_provider_reports_dimension():
    provider = OllamaEmbeddingProvider(
        base_url=UNREACHABLE, model="nomic-embed-text", dim=768
    )
    assert provider.dim == 768
