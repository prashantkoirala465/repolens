from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Postgres: two-tier creds — migrations run with DDL rights, the app runs with a
    # restricted role. Never point the app at the migration URL.
    database_url: str = Field(alias="DATABASE_URL")
    migration_database_url: str = Field(alias="MIGRATION_DATABASE_URL")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="repolens_chunks", alias="QDRANT_COLLECTION")

    # Ollama is the default for both providers: it's free and self-hosted, so the
    # app boots and runs with no API keys at all. Voyage/Anthropic are opt-in
    # for better retrieval/answer quality, not required.
    embedding_provider: Literal["voyage", "ollama"] = Field(
        default="ollama", alias="EMBEDDING_PROVIDER"
    )
    generation_provider: Literal["anthropic", "ollama"] = Field(
        default="ollama", alias="GENERATION_PROVIDER"
    )

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_embedding_model: str = Field(default="nomic-embed-text", alias="OLLAMA_EMBEDDING_MODEL")
    ollama_generation_model: str = Field(default="llama3.2", alias="OLLAMA_GENERATION_MODEL")

    voyage_api_key: str | None = Field(default=None, alias="VOYAGE_API_KEY")
    voyage_model: str = Field(default="voyage-code-3", alias="VOYAGE_MODEL")

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-5", alias="ANTHROPIC_MODEL")

    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")

    cors_origins: list[str] = Field(default=["http://localhost:3000"], alias="CORS_ORIGINS")

    # Indexing bounds — an arbitrary public repo is untrusted input.
    max_repo_size_mb: int = Field(default=250, alias="MAX_REPO_SIZE_MB")
    max_file_size_kb: int = Field(default=512, alias="MAX_FILE_SIZE_KB")
    clone_timeout_s: int = Field(default=120, alias="CLONE_TIMEOUT_S")
    max_files_indexed: int = Field(default=5000, alias="MAX_FILES_INDEXED")

    embedding_batch_size: int = Field(default=64, alias="EMBEDDING_BATCH_SIZE")
    retrieval_top_k: int = Field(default=8, alias="RETRIEVAL_TOP_K")
    # Measured via `repolens-eval diff` against the psf/requests benchmark
    # (README: Measuring retrieval quality): hybrid wins on MRR (+0.071) and
    # nDCG (+0.05 at both k=5/10) with recall unchanged, at a small precision
    # cost (-0.01) — a real net win, not a clean sweep. Both vector types are
    # always indexed regardless of this setting, so flipping it never
    # requires re-indexing.
    retrieval_mode: Literal["dense", "hybrid"] = Field(default="hybrid", alias="RETRIEVAL_MODE")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
