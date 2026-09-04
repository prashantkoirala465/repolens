import uuid

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, HTTPException, Request

from repolens.api.deps import SessionDep
from repolens.core.config import get_settings
from repolens.core.rate_limit import REPOS_RATE_LIMIT, limiter
from repolens.db.models import IndexStatus, Repo
from repolens.schemas.repo import RepoCreateRequest, RepoResponse
from repolens.services.git import InvalidRepoUrlError, parse_github_url
from repolens.services.indexer import get_repo_by_url

router = APIRouter(prefix="/repos", tags=["repos"])


@router.post("", response_model=RepoResponse, status_code=201)
@limiter.limit(REPOS_RATE_LIMIT)
async def create_repo(request: Request, payload: RepoCreateRequest, session: SessionDep) -> Repo:
    try:
        parsed = parse_github_url(payload.github_url)
    except InvalidRepoUrlError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    existing = await get_repo_by_url(session, payload.github_url)
    if existing is not None:
        return existing

    repo = Repo(
        id=uuid.uuid4(),
        github_url=payload.github_url,
        owner=parsed.owner,
        name=parsed.name,
        status=IndexStatus.QUEUED,
    )
    session.add(repo)
    await session.commit()
    await session.refresh(repo)

    redis = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    await redis.enqueue_job("index_repo_task", str(repo.id))
    await redis.close()

    return repo


@router.get("/{repo_id}", response_model=RepoResponse)
async def get_repo(repo_id: uuid.UUID, session: SessionDep) -> Repo:
    repo = await session.get(Repo, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="repo not found")
    return repo
