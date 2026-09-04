"""Real Postgres + real Qdrant, fake embedder + generator: proves the query
route's full wiring (retrieve -> generate -> citation validation -> persist)
without needing Ollama/Voyage/Anthropic in CI.

Chunks are pre-seeded directly via qdrant_store.upsert_chunks rather than
going through the indexing pipeline — this test is about the query route,
which test_indexing_pipeline.py already covers separately.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repolens.chunking.base import Chunk, ChunkKind
from repolens.db.models import IndexStatus, Query, Repo
from repolens.main import app
from repolens.retrieval.qdrant_store import ensure_collection, upsert_chunks
from repolens.retrieval.sparse import embed_sparse_documents


async def test_query_route_returns_a_cited_answer(
    db_session: AsyncSession, repo_cleanup: list[uuid.UUID], fake_embedder, fake_generator
) -> None:
    repo_id = uuid.uuid4()
    repo_cleanup.append(repo_id)
    repo = Repo(
        id=repo_id,
        github_url=f"https://github.com/octocat/query-route-test-{repo_id}",
        owner="octocat",
        name=f"query-route-test-{repo_id}",
        status=IndexStatus.READY,
        chunk_count=1,
    )
    db_session.add(repo)
    await db_session.commit()

    chunk = Chunk(
        file_path="README.md",
        start_line=1,
        end_line=1,
        text="RepoLens indexes GitHub repositories for retrieval.",
        kind=ChunkKind.DOC,
        symbol="Overview",
    )
    ensure_collection(fake_embedder.dimension)
    dense_vectors = fake_embedder.embed_documents([chunk.text])
    sparse_vectors = embed_sparse_documents([chunk.text])
    upsert_chunks(str(repo_id), [chunk], dense_vectors, sparse_vectors)

    client = TestClient(app)
    response = client.post(f"/repos/{repo_id}/query", json={"question": "What does this repo do?"})

    assert response.status_code == 200
    body = response.json()
    assert body["retrieved_chunks"]
    assert any(c["chunk_id"] == chunk.chunk_id for c in body["retrieved_chunks"])
    assert body["answer"]

    result = await db_session.execute(select(Query).where(Query.repo_id == repo_id))
    query_record = result.scalar_one()
    assert query_record.answer == body["answer"]
    assert query_record.question == "What does this repo do?"
