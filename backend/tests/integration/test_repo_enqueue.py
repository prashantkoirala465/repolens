"""Real HTTP -> real Postgres row + a real job landing in real Redis.

No in-process arq worker is started here (CI doesn't run one either, and
spinning one up inside a test is exactly the kind of fragility this suite
should avoid) — this verifies the enqueue side effect directly against
Redis. Whether a worker actually processes that job correctly is covered
separately, directly, in test_indexing_pipeline.py.

Only one request to POST /repos: RATE_LIMIT_REPOS defaults to 5/minute, and
that limit is real Redis-backed state shared across every test in this
process within the same window — staying well under it here keeps this
test from becoming flaky as its neighbor, not a statement about what the
route should allow.
"""

import uuid

import arq.constants
import redis.asyncio as redis
from fastapi.testclient import TestClient

from repolens.core.config import get_settings
from repolens.db.models import IndexStatus
from repolens.main import app


async def test_create_repo_enqueues_an_indexing_job(repo_cleanup: list[uuid.UUID]) -> None:
    client = TestClient(app)
    github_url = "https://github.com/octocat/Spoon-Knife"

    response = client.post("/repos", json={"github_url": github_url})

    assert response.status_code == 201
    body = response.json()
    repo_cleanup.append(uuid.UUID(body["id"]))
    assert body["github_url"] == github_url
    assert body["status"] == IndexStatus.QUEUED.value

    redis_client = redis.from_url(get_settings().redis_url)
    try:
        queue_length = await redis_client.zcard(arq.constants.default_queue_name)
        assert queue_length >= 1
    finally:
        await redis_client.aclose()
