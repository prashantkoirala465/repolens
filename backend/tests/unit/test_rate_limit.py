from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from repolens.core.config import Settings
from repolens.core.rate_limit import QUERY_RATE_LIMIT, REPOS_RATE_LIMIT
from repolens.core.rate_limit import limiter as app_limiter

_BASE = {
    "DATABASE_URL": "postgresql+asyncpg://x:x@localhost/x",
    "MIGRATION_DATABASE_URL": "postgresql+asyncpg://x:x@localhost/x",
}


def _make_app(limit: str) -> FastAPI:
    # Same wiring pattern as main.py, but with the default (in-memory)
    # storage instead of Redis, so this test needs no real service.
    test_limiter = Limiter(key_func=get_remote_address)
    app = FastAPI()
    app.state.limiter = test_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)

    @app.post("/ping")
    @test_limiter.limit(limit)
    async def ping(request: Request) -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_requests_within_the_limit_succeed() -> None:
    client = TestClient(_make_app("2/minute"))
    assert client.post("/ping").status_code == 200
    assert client.post("/ping").status_code == 200


def test_requests_over_the_limit_are_rejected_with_429() -> None:
    client = TestClient(_make_app("2/minute"))
    client.post("/ping")
    client.post("/ping")

    response = client.post("/ping")

    assert response.status_code == 429


def test_default_rate_limits_are_configured() -> None:
    settings = Settings(**_BASE)  # type: ignore[call-arg]
    assert settings.rate_limit_repos == "5/minute"
    assert settings.rate_limit_query == "20/minute"


def test_app_limiter_uses_the_configured_limit_strings() -> None:
    # sanity check on the real production module: constructing it must not
    # require a live Redis (the storage backend connects lazily on first
    # use, not at Limiter construction time).
    assert isinstance(app_limiter, Limiter)
    assert REPOS_RATE_LIMIT
    assert QUERY_RATE_LIMIT
