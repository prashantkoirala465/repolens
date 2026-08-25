from functools import lru_cache

from repolens.core.config import get_settings
from repolens.generation.anthropic_provider import AnthropicGenerator
from repolens.generation.base import Generator
from repolens.generation.ollama_provider import OllamaGenerator


@lru_cache
def get_generator() -> Generator:
    settings = get_settings()
    if settings.generation_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("GENERATION_PROVIDER=anthropic requires ANTHROPIC_API_KEY to be set")
        return AnthropicGenerator()
    return OllamaGenerator()
