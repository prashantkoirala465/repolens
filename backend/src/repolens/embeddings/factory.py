from functools import lru_cache

from repolens.core.config import get_settings
from repolens.embeddings.base import Embedder
from repolens.embeddings.ollama import OllamaEmbedder
from repolens.embeddings.voyage import VoyageEmbedder


@lru_cache
def get_embedder() -> Embedder:
    """Cached per process: OllamaEmbedder's dimension probe (one local call)
    only needs to run once, not on every index/query call."""
    settings = get_settings()
    if settings.embedding_provider == "voyage":
        if not settings.voyage_api_key:
            raise ValueError("EMBEDDING_PROVIDER=voyage requires VOYAGE_API_KEY to be set")
        return VoyageEmbedder()
    return OllamaEmbedder()
