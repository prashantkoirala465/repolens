import pytest

from repolens.core.config import Settings
from repolens.embeddings.factory import get_embedder
from repolens.embeddings.ollama import OllamaEmbedder
from repolens.generation.factory import get_generator
from repolens.generation.ollama_provider import OllamaGenerator

_BASE = {
    "DATABASE_URL": "postgresql+asyncpg://x:x@localhost/x",
    "MIGRATION_DATABASE_URL": "postgresql+asyncpg://x:x@localhost/x",
}


def test_embedder_factory_defaults_to_ollama() -> None:
    get_embedder.cache_clear()
    assert isinstance(get_embedder(), OllamaEmbedder)
    get_embedder.cache_clear()


def test_generator_factory_defaults_to_ollama() -> None:
    get_generator.cache_clear()
    assert isinstance(get_generator(), OllamaGenerator)
    get_generator.cache_clear()


def test_embedder_factory_raises_when_voyage_selected_without_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_settings = Settings(**_BASE, EMBEDDING_PROVIDER="voyage")  # type: ignore[call-arg]
    monkeypatch.setattr("repolens.embeddings.factory.get_settings", lambda: fake_settings)
    get_embedder.cache_clear()

    with pytest.raises(ValueError, match="VOYAGE_API_KEY"):
        get_embedder()

    get_embedder.cache_clear()


def test_generator_factory_raises_when_anthropic_selected_without_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_settings = Settings(**_BASE, GENERATION_PROVIDER="anthropic")  # type: ignore[call-arg]
    monkeypatch.setattr("repolens.generation.factory.get_settings", lambda: fake_settings)
    get_generator.cache_clear()

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        get_generator()

    get_generator.cache_clear()
