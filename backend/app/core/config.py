"""Application configuration loaded from environment variables."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: backend/app/core/config.py -> parents[3].
_REPO_ROOT = Path(__file__).resolve().parents[3]
_AUTOMATION = _REPO_ROOT / "automation"


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

    # Reranking (V2). Disabled by default so the V1 pipeline is unchanged.
    reranker_enabled: bool = False
    reranker_model: str = "lexical"
    reranker_candidates: int = 15
    reranker_top_k: int = 5

    # Automation (n8n pillar). The API is the boundary: n8n calls FastAPI, which
    # owns file movement and the database.
    automation_token: str = ""  # FLOWMIND_AUTOMATION_TOKEN; empty disables auth (dev)
    automation_inbox_dir: str = str(_AUTOMATION / "inbox")
    automation_processed_dir: str = str(_AUTOMATION / "processed")
    automation_failed_dir: str = str(_AUTOMATION / "failed")
    automation_max_attempts: int = 3

    @property
    def allowed_extensions_set(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_extensions.split(",") if e.strip()}

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def index_profile(
        self,
        embedding_model: str | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        version: str = "v1",
    ) -> str:
        """Deterministic index-profile id. Chunks embedded/chunked differently must
        never be mixed in retrieval, so each profile is tagged with this string."""
        em = embedding_model or self.embedding_model
        cs = chunk_size if chunk_size is not None else self.chunk_size
        co = chunk_overlap if chunk_overlap is not None else self.chunk_overlap
        return f"{em}-{cs}-{co}-{version}"

    @property
    def default_index_profile(self) -> str:
        return self.index_profile()


settings = Settings()
