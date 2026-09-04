from dataclasses import dataclass, field
from typing import Any

import pytest
from qdrant_client.models import Fusion, FusionQuery, Prefetch, SparseVector

from repolens.chunking.base import Chunk, ChunkKind
from repolens.retrieval import qdrant_store


@dataclass
class _FakePoint:
    payload: dict[str, Any]
    score: float = 1.0


@dataclass
class _FakeQueryResponse:
    points: list[_FakePoint] = field(default_factory=list)


class _FakeQdrantClient:
    def __init__(self) -> None:
        self.query_points_calls: list[dict[str, Any]] = []
        self.upsert_calls: list[dict[str, Any]] = []

    def query_points(self, **kwargs: Any) -> _FakeQueryResponse:
        self.query_points_calls.append(kwargs)
        return _FakeQueryResponse()

    def upsert(self, **kwargs: Any) -> None:
        self.upsert_calls.append(kwargs)

    def delete(self, **kwargs: Any) -> None:
        pass


def _chunk(path: str = "a.py") -> Chunk:
    return Chunk(
        file_path=path, start_line=1, end_line=5, text="def f(): pass", kind=ChunkKind.CODE
    )


def test_dense_search_uses_the_dense_vector_with_no_prefetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeQdrantClient()
    monkeypatch.setattr(qdrant_store, "_client", lambda: fake)

    qdrant_store.search("repo-1", [0.1, 0.2], top_k=8, mode="dense")

    assert len(fake.query_points_calls) == 1
    call = fake.query_points_calls[0]
    assert call["query"] == [0.1, 0.2]
    assert call["using"] == "dense"
    assert call["limit"] == 8
    assert "prefetch" not in call


def test_hybrid_search_requires_a_sparse_query_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeQdrantClient()
    monkeypatch.setattr(qdrant_store, "_client", lambda: fake)

    with pytest.raises(ValueError, match="sparse_query_vector"):
        qdrant_store.search("repo-1", [0.1, 0.2], top_k=8, mode="hybrid")


def test_hybrid_search_prefetches_both_vectors_and_fuses_with_rrf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeQdrantClient()
    monkeypatch.setattr(qdrant_store, "_client", lambda: fake)
    sparse = SparseVector(indices=[1, 2], values=[0.5, 0.5])

    qdrant_store.search("repo-1", [0.1, 0.2], top_k=8, mode="hybrid", sparse_query_vector=sparse)

    assert len(fake.query_points_calls) == 1
    call = fake.query_points_calls[0]
    assert isinstance(call["query"], FusionQuery)
    assert call["query"].fusion == Fusion.RRF
    assert call["limit"] == 8

    prefetches: list[Prefetch] = call["prefetch"]
    assert {p.using for p in prefetches} == {"dense", "bm25"}
    dense_prefetch = next(p for p in prefetches if p.using == "dense")
    sparse_prefetch = next(p for p in prefetches if p.using == "bm25")
    assert dense_prefetch.query == [0.1, 0.2]
    assert sparse_prefetch.query is sparse
    # every prefetch stage carries the repo filter, not just the top-level query
    assert dense_prefetch.filter is not None
    assert sparse_prefetch.filter is not None
    assert call["query_filter"] is not None


def test_hybrid_prefetch_limit_scales_with_top_k(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeQdrantClient()
    monkeypatch.setattr(qdrant_store, "_client", lambda: fake)
    sparse = SparseVector(indices=[], values=[])

    qdrant_store.search("repo-1", [0.1], top_k=20, mode="hybrid", sparse_query_vector=sparse)

    prefetches: list[Prefetch] = fake.query_points_calls[0]["prefetch"]
    assert all(p.limit == 100 for p in prefetches)  # max(20 * 5, 50)


def test_upsert_chunks_stores_both_named_vectors(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeQdrantClient()
    monkeypatch.setattr(qdrant_store, "_client", lambda: fake)
    chunk = _chunk()
    sparse = SparseVector(indices=[7], values=[1.0])

    qdrant_store.upsert_chunks("repo-1", [chunk], [[0.1, 0.2]], [sparse])

    assert len(fake.upsert_calls) == 1
    (point,) = fake.upsert_calls[0]["points"]
    assert point.vector == {"dense": [0.1, 0.2], "bm25": sparse}
    assert point.payload["chunk_id"] == chunk.chunk_id
