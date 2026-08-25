"""Answer generation with server-validated citations.

Retrieved repo content is untrusted (docs/adr/0005) — a malicious README
could contain "ignore previous instructions" text. Two defenses:
  1. Retrieved chunks are wrapped in a data block, never placed where the
     model would read them as instructions (shared across providers, see
     generation/prompts.py).
  2. Every provider is forced to emit citations as chunk_ids, and every
     citation is checked against the actual retrieved set right here, before
     the answer is returned. An injected instruction can make a provider say
     something wrong; it cannot forge a citation to a chunk that wasn't
     retrieved, and cannot make the model take an action — there is no
     tool/action surface here for it to abuse. This check is not duplicated
     per provider — providers only produce raw (answer, citations).
"""

from dataclasses import dataclass

from repolens.generation.base import RawGeneration
from repolens.generation.factory import get_generator
from repolens.retrieval.qdrant_store import RetrievedChunk


@dataclass(frozen=True, slots=True)
class GeneratedAnswer:
    answer: str
    cited_chunk_ids: list[str]
    rejected_citation_count: int


def validate_citations(raw: RawGeneration, retrieved: list[RetrievedChunk]) -> GeneratedAnswer:
    valid_ids = {chunk.chunk_id for chunk in retrieved}
    cited_chunk_ids = [cid for cid in raw.cited_chunk_ids if cid in valid_ids]
    rejected = len(raw.cited_chunk_ids) - len(cited_chunk_ids)
    return GeneratedAnswer(
        answer=raw.answer, cited_chunk_ids=cited_chunk_ids, rejected_citation_count=rejected
    )


def generate_answer(question: str, retrieved: list[RetrievedChunk]) -> GeneratedAnswer:
    raw = get_generator().generate(question, retrieved)
    return validate_citations(raw, retrieved)
