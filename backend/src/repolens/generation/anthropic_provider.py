from typing import Any, cast

import anthropic
from anthropic.types import ToolChoiceToolParam, ToolParam

from repolens.core.config import get_settings
from repolens.generation.base import RawGeneration
from repolens.generation.prompts import SYSTEM_PROMPT, format_user_message
from repolens.retrieval.qdrant_store import RetrievedChunk

_ANSWER_TOOL: ToolParam = {
    "name": "submit_answer",
    "description": "Submit the final answer with citations to the chunks that support it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "The answer to the user's question, in prose.",
            },
            "cited_chunk_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "chunk_id values (e.g. 'src/foo.py:10-25') from the retrieved "
                    "chunks that support the answer."
                ),
            },
        },
        "required": ["answer", "cited_chunk_ids"],
    },
}
_TOOL_CHOICE: ToolChoiceToolParam = {"type": "tool", "name": "submit_answer"}


class AnthropicGenerator:
    def __init__(self) -> None:
        settings = get_settings()
        assert settings.anthropic_api_key is not None, "checked by the factory before construction"
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    def generate(self, question: str, retrieved: list[RetrievedChunk]) -> RawGeneration:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[_ANSWER_TOOL],
            tool_choice=_TOOL_CHOICE,
            messages=[{"role": "user", "content": format_user_message(question, retrieved)}],
        )

        tool_use = next(block for block in response.content if block.type == "tool_use")
        tool_input = cast(dict[str, Any], tool_use.input)
        return RawGeneration(
            answer=tool_input["answer"],
            cited_chunk_ids=tool_input.get("cited_chunk_ids", []),
        )
