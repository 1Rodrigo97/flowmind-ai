"""Local embedding provider backed by Ollama's /api/embeddings endpoint."""
from __future__ import annotations

import httpx

from app.embeddings.base import EmbeddingProvider


class EmbeddingError(RuntimeError):
    """Raised when the embedding backend is unreachable or returns an error."""


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self, base_url: str, model: str, dim: int, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dim = dim
        self._timeout = timeout

    def embed(self, text: str) -> list[float]:
        try:
            resp = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:  # network, timeout, non-2xx
            raise EmbeddingError(f"Ollama embeddings unavailable: {exc}") from exc

        vector = data.get("embedding")
        if not vector:
            raise EmbeddingError("Ollama returned an empty embedding")
        return vector
