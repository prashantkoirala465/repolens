"""Qdrant collection management and dense retrieval.

Phase 1 is dense-only. Hybrid BM25+dense retrieval (docs/adr/0002) lands in
Phase 3 once the eval harness exists to actually measure the improvement
instead of asserting it.
"""

import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from repolens.chunking.base import Chunk
from repolens.core.config import get_settings


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


def ensure_collection(dimension: int) -> None:
    """dimension comes from the configured embedder (Embedder.dimension), not a
    hardcoded constant — Voyage and Ollama models don't share a vector space.
    If a collection under this name already exists with a different dimension
    (e.g. EMBEDDING_PROVIDER was switched), fail loudly instead of silently
    returning garbage retrieval."""
    settings = get_settings()
    client = _client()
    if client.collection_exists(settings.qdrant_collection):
        existing = client.get_collection(settings.qdrant_collection)
        existing_dim = existing.config.params.vectors.size  # type: ignore[union-attr]
        if existing_dim != dimension:
            raise ValueError(
                f"Qdrant collection '{settings.qdrant_collection}' was built with "
                f"{existing_dim}-dim vectors, but the configured embedder produces "
                f"{dimension}-dim vectors. Set QDRANT_COLLECTION to a new name (or "
                f"drop the old collection) after changing EMBEDDING_PROVIDER/model."
            )
        return
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
    )


def upsert_chunks(repo_id: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
    settings = get_settings()
    client = _client()
    points = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{repo_id}:{chunk.chunk_id}")),
            vector=vector,
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
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)


def search(repo_id: str, query_vector: list[float], top_k: int) -> list[RetrievedChunk]:
    settings = get_settings()
    client = _client()
    results = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        query_filter=Filter(must=[FieldCondition(key="repo_id", match=MatchValue(value=repo_id))]),
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
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[FieldCondition(key="repo_id", match=MatchValue(value=repo_id))]
        ),
    )
