from functools import lru_cache

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

    voyage_api_key: str = Field(alias="VOYAGE_API_KEY")
    voyage_model: str = Field(default="voyage-code-3", alias="VOYAGE_MODEL")

    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-5", alias="ANTHROPIC_MODEL")

    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")

    # Indexing bounds — see docs/adr/0005 (untrusted repo content is a threat surface).
    max_repo_size_mb: int = Field(default=250, alias="MAX_REPO_SIZE_MB")
    max_file_size_kb: int = Field(default=512, alias="MAX_FILE_SIZE_KB")
    clone_timeout_s: int = Field(default=120, alias="CLONE_TIMEOUT_S")
    max_files_indexed: int = Field(default=5000, alias="MAX_FILES_INDEXED")

    embedding_batch_size: int = Field(default=64, alias="EMBEDDING_BATCH_SIZE")
    retrieval_top_k: int = Field(default=8, alias="RETRIEVAL_TOP_K")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
