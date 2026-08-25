import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from repolens.db.models import IndexStatus


class RepoCreateRequest(BaseModel):
    github_url: str = Field(examples=["https://github.com/psf/requests"])


class RepoResponse(BaseModel):
    id: uuid.UUID
    github_url: str
    owner: str
    name: str
    commit_sha: str | None
    status: IndexStatus
    status_detail: str | None
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
