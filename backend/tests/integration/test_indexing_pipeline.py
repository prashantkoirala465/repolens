"""Real Postgres + real Qdrant, fake embedder: proves the actual pipeline
wiring (clone -> chunk -> embed -> upsert -> status transitions), not the
quality of any particular embedding model — that's what the eval harness
(backend/src/repolens/eval/) measures.

This is also the only automated regression coverage of Phase 3's hybrid
Prefetch+FusionQuery(RRF) query shape against a real Qdrant server —
qdrant_store's own unit tests only exercise it against a fake client.

Clones a real, tiny, permanently-stable public repo (octocat/Hello-World,
GitHub's own demo repo) rather than a local fixture: the app's whole
premise is cloning real GitHub repos, so a suite that can't touch GitHub
isn't testing the real thing.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from repolens.db.models import IndexStatus, Repo
from repolens.retrieval.qdrant_store import search
from repolens.retrieval.sparse import embed_sparse_query
from repolens.services.git import parse_github_url
from repolens.services.indexer import index_repo


async def test_indexing_hello_world_end_to_end(
    db_session: AsyncSession, repo_cleanup: list[uuid.UUID], fake_embedder
) -> None:
    github_url = "https://github.com/octocat/Hello-World"
    parsed = parse_github_url(github_url)
    repo_id = uuid.uuid4()
    repo_cleanup.append(repo_id)

    repo = Repo(
        id=repo_id,
        github_url=github_url,
        owner=parsed.owner,
        name=parsed.name,
        status=IndexStatus.QUEUED,
    )
    db_session.add(repo)
    await db_session.commit()

    await index_repo(db_session, repo_id)

    await db_session.refresh(repo)
    assert repo.status == IndexStatus.READY, repo.status_detail
    assert repo.chunk_count > 0
    assert repo.commit_sha

    dense_vector = fake_embedder.embed_query("hello world")
    dense_results = search(str(repo_id), dense_vector, top_k=5, mode="dense")
    assert dense_results
    assert all(r.chunk_id for r in dense_results)

    sparse_vector = embed_sparse_query("hello world")
    hybrid_results = search(
        str(repo_id),
        dense_vector,
        top_k=5,
        mode="hybrid",
        sparse_query_vector=sparse_vector,
    )
    assert hybrid_results


async def test_indexing_is_idempotent_on_reindex(
    db_session: AsyncSession, repo_cleanup: list[uuid.UUID], fake_embedder
) -> None:
    github_url = "https://github.com/octocat/Hello-World"
    parsed = parse_github_url(github_url)
    repo_id = uuid.uuid4()
    repo_cleanup.append(repo_id)

    repo = Repo(
        id=repo_id,
        github_url=github_url,
        owner=parsed.owner,
        name=parsed.name,
        status=IndexStatus.QUEUED,
    )
    db_session.add(repo)
    await db_session.commit()

    await index_repo(db_session, repo_id)
    first_chunk_count = repo.chunk_count

    await index_repo(db_session, repo_id)
    await db_session.refresh(repo)

    assert repo.status == IndexStatus.READY
    assert repo.chunk_count == first_chunk_count

    dense_vector = fake_embedder.embed_query("hello world")
    results = search(str(repo_id), dense_vector, top_k=50, mode="dense")
    chunk_ids = [r.chunk_id for r in results]
    assert len(chunk_ids) == len(set(chunk_ids)), "re-indexing must not duplicate chunks"
