import uuid

from fastapi import APIRouter, HTTPException

from repolens.api.deps import SessionDep
from repolens.core.config import get_settings
from repolens.db.models import IndexStatus, Query, Repo
from repolens.embeddings.voyage import VoyageEmbedder
from repolens.generation.answer import generate_answer
from repolens.retrieval.qdrant_store import search
from repolens.schemas.query import QueryRequest, QueryResponse, RetrievedChunkResponse

router = APIRouter(prefix="/repos/{repo_id}/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def query_repo(
    repo_id: uuid.UUID, request: QueryRequest, session: SessionDep
) -> QueryResponse:
    repo = await session.get(Repo, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="repo not found")
    if repo.status != IndexStatus.READY:
        raise HTTPException(
            status_code=409, detail=f"repo is not ready to query (status={repo.status.value})"
        )

    embedder = VoyageEmbedder()
    query_vector = embedder.embed_query(request.question)
    retrieved = search(str(repo_id), query_vector, top_k=get_settings().retrieval_top_k)

    if not retrieved:
        raise HTTPException(status_code=404, detail="no indexed content found for this repo")

    generated = generate_answer(request.question, retrieved)

    query_record = Query(
        id=uuid.uuid4(),
        repo_id=repo_id,
        question=request.question,
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
