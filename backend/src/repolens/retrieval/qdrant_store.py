"""Qdrant collection management and retrieval: dense-only, or hybrid
(BM25 sparse + dense, fused server-side via Qdrant's Query API).

Every point carries two named vectors — "dense" (from the configured
embedder) and "bm25" (retrieval/sparse.py) — regardless of which mode a
given query runs in. Sparse vectors are pure-Python to compute, so there's
no cost to always storing them, and no reason switching RETRIEVAL_MODE
should ever require re-indexing.
"""

import uuid
from dataclasses import dataclass
from typing import Literal

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    Modifier,
    PointStruct,
    Prefetch,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from repolens.chunking.base import Chunk
from repolens.core.config import get_settings

_DENSE_VECTOR_NAME = "dense"
_SPARSE_VECTOR_NAME = "bm25"
_PREFETCH_MULTIPLIER = 5
_MIN_PREFETCH_LIMIT = 50


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: str
    file_path: str
    start_line: int
    end_line: int
    text: str
    symbol: str | None
    score: float


def _client() -> QdrantClient:
    return QdrantClient(url=get_settings().qdrant_url)


def _repo_filter(repo_id: str) -> Filter:
    return Filter(must=[FieldCondition(key="repo_id", match=MatchValue(value=repo_id))])


def ensure_collection(dimension: int) -> None:
    """dimension comes from the configured embedder (Embedder.dimension), not a
    hardcoded constant — Voyage and Ollama models don't share a vector space.
    If a collection under this name already exists but doesn't match the
    expected schema (wrong dense dimension, e.g. EMBEDDING_PROVIDER was
    switched, or missing the "bm25" sparse vector, e.g. it predates hybrid
    retrieval) fail loudly instead of silently returning garbage retrieval."""
    settings = get_settings()
    client = _client()
    if client.collection_exists(settings.qdrant_collection):
        params = client.get_collection(settings.qdrant_collection).config.params
        existing_vectors = params.vectors
        existing_dim = (
            existing_vectors[_DENSE_VECTOR_NAME].size
            if isinstance(existing_vectors, dict) and _DENSE_VECTOR_NAME in existing_vectors
            else None
        )
        has_sparse = bool(params.sparse_vectors) and _SPARSE_VECTOR_NAME in (
            params.sparse_vectors or {}
        )
        if existing_dim != dimension or not has_sparse:
            raise ValueError(
                f"Qdrant collection '{settings.qdrant_collection}' doesn't match the "
                f"expected schema: found a '{_DENSE_VECTOR_NAME}' vector of size "
                f"{existing_dim!r} and sparse_vectors={'bm25' if has_sparse else 'none'}, "
                f"expected size {dimension} plus a named '{_SPARSE_VECTOR_NAME}' sparse "
                f"vector. This usually means the collection predates hybrid retrieval, or "
                f"the embedder changed. Set QDRANT_COLLECTION to a new name (or drop the "
                f"old collection)."
            )
        return
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config={_DENSE_VECTOR_NAME: VectorParams(size=dimension, distance=Distance.COSINE)},
        sparse_vectors_config={_SPARSE_VECTOR_NAME: SparseVectorParams(modifier=Modifier.IDF)},
    )


def upsert_chunks(
    repo_id: str,
    chunks: list[Chunk],
    dense_vectors: list[list[float]],
    sparse_vectors: list[SparseVector],
) -> None:
    settings = get_settings()
    client = _client()
    points = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{repo_id}:{chunk.chunk_id}")),
            vector={_DENSE_VECTOR_NAME: dense_vector, _SPARSE_VECTOR_NAME: sparse_vector},
            payload={
                "repo_id": repo_id,
                "chunk_id": chunk.chunk_id,
                "file_path": chunk.file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "text": chunk.text,
                "symbol": chunk.symbol,
                "kind": chunk.kind.value,
            },
        )
        for chunk, dense_vector, sparse_vector in zip(
            chunks, dense_vectors, sparse_vectors, strict=True
        )
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)


def search(
    repo_id: str,
    dense_query_vector: list[float],
    top_k: int,
    *,
    mode: Literal["dense", "hybrid"] = "dense",
    sparse_query_vector: SparseVector | None = None,
) -> list[RetrievedChunk]:
    if mode == "hybrid" and sparse_query_vector is None:
        raise ValueError("mode='hybrid' requires a sparse_query_vector")

    settings = get_settings()
    client = _client()
    repo_filter = _repo_filter(repo_id)

    if mode == "hybrid":
        assert sparse_query_vector is not None
        # The same filter goes on every prefetch stage *and* the top-level
        # query, rather than relying on it being inherited — cheap insurance
        # against cross-repo leakage in the fused result.
        prefetch_limit = max(top_k * _PREFETCH_MULTIPLIER, _MIN_PREFETCH_LIMIT)
        results = client.query_points(
            collection_name=settings.qdrant_collection,
            prefetch=[
                Prefetch(
                    query=dense_query_vector,
                    using=_DENSE_VECTOR_NAME,
                    filter=repo_filter,
                    limit=prefetch_limit,
                ),
                Prefetch(
                    query=sparse_query_vector,
                    using=_SPARSE_VECTOR_NAME,
                    filter=repo_filter,
                    limit=prefetch_limit,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            query_filter=repo_filter,
            limit=top_k,
        )
    else:
        results = client.query_points(
            collection_name=settings.qdrant_collection,
            query=dense_query_vector,
            using=_DENSE_VECTOR_NAME,
            query_filter=repo_filter,
            limit=top_k,
        )

    retrieved: list[RetrievedChunk] = []
    for point in results.points:
        assert point.payload is not None, "upserted points always carry a payload"
        retrieved.append(
            RetrievedChunk(
                chunk_id=point.payload["chunk_id"],
                file_path=point.payload["file_path"],
                start_line=point.payload["start_line"],
                end_line=point.payload["end_line"],
                text=point.payload["text"],
                symbol=point.payload.get("symbol"),
                score=point.score,
            )
        )
    return retrieved


def delete_repo_chunks(repo_id: str) -> None:
    settings = get_settings()
    client = _client()
    client.delete(collection_name=settings.qdrant_collection, points_selector=_repo_filter(repo_id))
