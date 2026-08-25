import uuid
from typing import Any

from repolens.db.session import get_session
from repolens.services.indexer import index_repo


async def index_repo_task(ctx: dict[str, Any], repo_id: str) -> None:
    async for session in get_session():
        await index_repo(session, uuid.UUID(repo_id))
