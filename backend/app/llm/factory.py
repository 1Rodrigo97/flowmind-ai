"""Factory selecting the configured LLM provider.

Future providers (VLLMProvider, OpenAICompatibleProvider) plug in here without
any change to the RAG pipeline.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.llm_timeout,
            num_ctx=settings.llm_num_ctx,
        )
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
