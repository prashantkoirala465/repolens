"""The citation-validation logic itself (docs/adr/0005's core defense) is
exercised directly against the real function, not a hand-duplicated copy:
only chunk_ids present in the retrieved set may survive, regardless of which
generation provider produced them."""

from repolens.generation.answer import validate_citations
from repolens.generation.base import RawGeneration
from repolens.retrieval.qdrant_store import RetrievedChunk


def _retrieved(chunk_id: str) -> RetrievedChunk:
    file_path = chunk_id.split(":")[0]
    return RetrievedChunk(
        chunk_id=chunk_id,
        file_path=file_path,
        start_line=1,
        end_line=5,
        text="...",
        symbol=None,
        score=0.5,
    )


def test_valid_citations_pass_through() -> None:
    retrieved = [_retrieved("a.py:1-5"), _retrieved("b.py:10-20")]
    raw = RawGeneration(answer="x", cited_chunk_ids=["a.py:1-5"])

    result = validate_citations(raw, retrieved)

    assert result.cited_chunk_ids == ["a.py:1-5"]
    assert result.rejected_citation_count == 0


def test_hallucinated_citation_is_rejected() -> None:
    retrieved = [_retrieved("a.py:1-5")]
    raw = RawGeneration(answer="x", cited_chunk_ids=["a.py:1-5", "z.py:999-1000"])

    result = validate_citations(raw, retrieved)

    assert result.cited_chunk_ids == ["a.py:1-5"]
    assert result.rejected_citation_count == 1


def test_all_citations_hallucinated() -> None:
    retrieved = [_retrieved("a.py:1-5")]
    raw = RawGeneration(answer="x", cited_chunk_ids=["z.py:1-2", "y.py:3-4"])

    result = validate_citations(raw, retrieved)

    assert result.cited_chunk_ids == []
    assert result.rejected_citation_count == 2
