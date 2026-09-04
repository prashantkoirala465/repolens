import uuid

from fastapi import APIRouter, HTTPException, Request

from repolens.api.deps import SessionDep
from repolens.core.config import get_settings
from repolens.core.rate_limit import QUERY_RATE_LIMIT, limiter
from repolens.db.models import IndexStatus, Query, Repo
from repolens.embeddings.factory import get_embedder
from repolens.generation.answer import generate_answer
from repolens.retrieval.qdrant_store import search
from repolens.retrieval.sparse import embed_sparse_query
from repolens.schemas.query import QueryRequest, QueryResponse, RetrievedChunkResponse

router = APIRouter(prefix="/repos/{repo_id}/query", tags=["query"])


@router.post("", response_model=QueryResponse)
@limiter.limit(QUERY_RATE_LIMIT)
async def query_repo(
    request: Request, repo_id: uuid.UUID, payload: QueryRequest, session: SessionDep
) -> QueryResponse:
    repo = await session.get(Repo, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="repo not found")
    if repo.status != IndexStatus.READY:
        raise HTTPException(
            status_code=409, detail=f"repo is not ready to query (status={repo.status.value})"
        )

    settings = get_settings()
    embedder = get_embedder()
    query_vector = embedder.embed_query(payload.question)
    sparse_query_vector = (
        embed_sparse_query(payload.question) if settings.retrieval_mode == "hybrid" else None
    )
    retrieved = search(
        str(repo_id),
        query_vector,
        top_k=settings.retrieval_top_k,
        mode=settings.retrieval_mode,
        sparse_query_vector=sparse_query_vector,
    )

    if not retrieved:
        raise HTTPException(status_code=404, detail="no indexed content found for this repo")

    generated = generate_answer(payload.question, retrieved)

    query_record = Query(
        id=uuid.uuid4(),
        repo_id=repo_id,
        question=payload.question,
        answer=generated.answer,
        retrieved_chunk_ids=[c.chunk_id for c in retrieved],
        cited_chunk_ids=generated.cited_chunk_ids,
        rejected_citation_count=generated.rejected_citation_count,
    )
    session.add(query_record)
    await session.commit()

    cited = set(generated.cited_chunk_ids)
    return QueryResponse(
        query_id=query_record.id,
        answer=generated.answer,
        rejected_citation_count=generated.rejected_citation_count,
        retrieved_chunks=[
            RetrievedChunkResponse(
                chunk_id=c.chunk_id,
                file_path=c.file_path,
                start_line=c.start_line,
                end_line=c.end_line,
                symbol=c.symbol,
                score=c.score,
                cited=c.chunk_id in cited,
            )
            for c in retrieved
        ],
    )
