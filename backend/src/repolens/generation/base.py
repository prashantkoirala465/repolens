from dataclasses import dataclass
from typing import Protocol

from repolens.retrieval.qdrant_store import RetrievedChunk


@dataclass(frozen=True, slots=True)
class RawGeneration:
    """A provider's raw output, before citation validation."""

    answer: str
    cited_chunk_ids: list[str]


class Generator(Protocol):
    def generate(self, question: str, retrieved: list[RetrievedChunk]) -> RawGeneration: ...
