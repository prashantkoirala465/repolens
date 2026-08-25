import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repolens.chunking.walker import chunk_file, iter_indexable_files
from repolens.core.logging import get_logger
from repolens.db.models import IndexStatus, Repo
from repolens.embeddings.factory import get_embedder
from repolens.retrieval.qdrant_store import delete_repo_chunks, ensure_collection, upsert_chunks
from repolens.services.git import (
    CloneTimeoutError,
    RepoTooLargeError,
    cleanup,
    current_commit_sha,
    shallow_clone,
)

logger = get_logger(__name__)


async def _set_status(
    session: AsyncSession, repo_id: uuid.UUID, status: IndexStatus, detail: str | None = None
) -> None:
    repo = await session.get(Repo, repo_id)
    if repo is None:
        return
    repo.status = status
    repo.status_detail = detail
    await session.commit()


async def index_repo(session: AsyncSession, repo_id: uuid.UUID) -> None:
    """Full pipeline: clone -> discover files -> chunk -> embed -> upsert.

    Runs inside an arq worker, not the API process — cloning a repo and
    embedding hundreds of chunks is seconds-to-minutes of work that has no
    place blocking an HTTP request.
    """
    repo = await session.get(Repo, repo_id)
    if repo is None:
        logger.warning("index_repo.repo_not_found", repo_id=str(repo_id))
        return

    from repolens.services.git import parse_github_url

    parsed = parse_github_url(repo.github_url)
    checkout = None
    try:
        await _set_status(session, repo_id, IndexStatus.CLONING)
        checkout = shallow_clone(parsed)
        repo.commit_sha = current_commit_sha(checkout)

        await _set_status(session, repo_id, IndexStatus.CHUNKING)
        files = iter_indexable_files(checkout)
        chunks = [c for path in files for c in chunk_file(checkout, path)]
        logger.info(
            "index_repo.chunked",
            repo=repo.github_url,
            file_count=len(files),
            chunk_count=len(chunks),
        )

        if not chunks:
            await _set_status(
                session, repo_id, IndexStatus.FAILED, detail="no indexable files found"
            )
            return

        await _set_status(session, repo_id, IndexStatus.EMBEDDING)
        embedder = get_embedder()
        ensure_collection(embedder.dimension)
        delete_repo_chunks(str(repo_id))  # re-indexing: drop the prior version's chunks first
        vectors = embedder.embed_documents([c.text for c in chunks])
        upsert_chunks(str(repo_id), chunks, vectors)

        repo.chunk_count = len(chunks)
        await _set_status(session, repo_id, IndexStatus.READY)
        logger.info("index_repo.ready", repo=repo.github_url, chunk_count=len(chunks))

    except RepoTooLargeError as exc:
        await _set_status(session, repo_id, IndexStatus.FAILED, detail=str(exc))
    except CloneTimeoutError as exc:
        await _set_status(session, repo_id, IndexStatus.FAILED, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - surfaced to the user via status_detail, not swallowed
        logger.exception("index_repo.failed", repo=repo.github_url)
        await _set_status(
            session, repo_id, IndexStatus.FAILED, detail=f"{type(exc).__name__}: {exc}"
        )
    finally:
        if checkout is not None:
            cleanup(checkout)


async def get_repo_by_url(session: AsyncSession, github_url: str) -> Repo | None:
    result = await session.execute(select(Repo).where(Repo.github_url == github_url))
    return result.scalar_one_or_none()
