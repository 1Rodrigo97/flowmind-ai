"""Application configuration loaded from environment variables."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg://flowmind:flowmind@localhost:5432/flowmind"

    # LLM provider
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    llm_timeout: float = 120.0
    # Bounded context window keeps memory predictable on modest/local hardware.
    llm_num_ctx: int = 4096

    # Embeddings
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768

    # RAG
    retrieval_top_k: int = 5
    # Minimum cosine similarity (0..1) a chunk must reach to be trusted as context.
    # Calibrated for nomic-embed-text: on-topic chunks score ~0.75+, unrelated ~0.40.
    similarity_threshold: float = 0.55

    # Ingestion / upload
    max_upload_mb: int = 25
    allowed_extensions: str = "pdf,docx,md,txt"
    upload_dir: str = "uploads"
    chunk_size: int = 900
    chunk_overlap: int = 150

    @property
    def allowed_extensions_set(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_extensions.split(",") if e.strip()}

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
