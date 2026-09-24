"""LLM provider abstraction.

The RAG pipeline depends only on this interface -- never on Ollama directly --
so future providers (vLLM, OpenAI-compatible endpoints) can be added without
rewriting retrieval or grounding logic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMError(RuntimeError):
    """Raised when the LLM backend is unreachable or fails."""


class LLMProvider(ABC):
    model: str

    @abstractmethod
    def generate(self, system: str, prompt: str, json_mode: bool = False) -> str:
        """Generate a completion given a system instruction and a user prompt.

        When ``json_mode`` is set, the provider is asked to return strict JSON.
        """
