"""Ollama-backed LLM provider (V1 default)."""
from __future__ import annotations

import httpx

from app.llm.base import LLMError, LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(
        self, base_url: str, model: str, timeout: float = 120.0, num_ctx: int = 4096
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._timeout = timeout
        self._num_ctx = num_ctx

    def generate(self, system: str, prompt: str) -> str:
        try:
            resp = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "system": system,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_ctx": self._num_ctx},
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama LLM unavailable: {exc}") from exc

        answer = (data.get("response") or "").strip()
        if not answer:
            raise LLMError("Ollama returned an empty response")
        return answer
