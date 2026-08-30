import json

import httpx

from repolens.core.config import get_settings
from repolens.generation.base import RawGeneration
from repolens.generation.prompts import SYSTEM_PROMPT, format_user_message
from repolens.retrieval.qdrant_store import RetrievedChunk

# Ollama's `format` constrains token-level decoding to match this schema —
# works with any served model, not just ones tuned for tool-calling, which is
# what makes it the right mechanism for an "any local model" provider. Same
# shape as the Anthropic tool's input_schema.
_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "cited_chunk_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "cited_chunk_ids"],
}


class OllamaGenerator:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = httpx.Client(base_url=settings.ollama_base_url, timeout=300.0)
        self._model = settings.ollama_generation_model

    def generate(self, question: str, retrieved: list[RetrievedChunk]) -> RawGeneration:
        response = self._client.post(
            "/api/chat",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": format_user_message(question, retrieved)},
                ],
                "format": _ANSWER_SCHEMA,
                "stream": False,
            },
        )
        response.raise_for_status()
        parsed = json.loads(response.json()["message"]["content"])
        return RawGeneration(
            answer=parsed["answer"],
            cited_chunk_ids=parsed.get("cited_chunk_ids", []),
        )
