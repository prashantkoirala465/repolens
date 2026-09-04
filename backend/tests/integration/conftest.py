"""Shared fixtures for the integration suite.

These tests hit real Postgres/Redis/Qdrant service containers (see
ci.yml) — that's the point. What they don't need is a real embedding or
generation model: FakeEmbedder/FakeGenerator are deterministic stand-ins
that satisfy the Embedder/Generator protocols, monkeypatched in at each
consumption point (matching this repo's existing test pattern — see
test_provider_factories.py — of patching `module.get_embedder`, not the
factory itself). That exercises the real pipeline wiring without requiring
Ollama/Voyage/Anthropic in CI; retrieval *quality* is what the eval harness
measures, not what this suite is for.
"""

import hashlib
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import repolens.db.session as db_session_module
from repolens.core.config import get_settings
from repolens.db.models import Repo
from repolens.db.session import get_session
from repolens.generation.base import RawGeneration
from repolens.retrieval.qdrant_store import RetrievedChunk, delete_repo_chunks


@pytest_asyncio.fixture(autouse=True, scope="session")
async def _nullpool_db_engine() -> AsyncGenerator[None]:
    """TestClient runs the ASGI app in its own background thread with its
    own event loop, separate from pytest-asyncio's session-scoped loop that
    the db_session fixture uses — and both would otherwise share
    db/session.py's process-wide QueuePool, where an asyncpg connection
    checked out under one loop breaks ("attached to a different loop") if
    handed back under another, whether that's between two tests or within
    one test that mixes db_session with a TestClient call.

    NullPool removes connection reuse entirely: every checkout is a fresh
    connection under whichever loop asks. Right tradeoff for a test suite;
    doesn't touch production pooling behavior, which never sees more than
    one loop in the first place (a single long-running uvicorn process).
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    db_session_module._engine = engine
    db_session_module._session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield
    await engine.dispose()


class FakeEmbedder:
    """Deterministic, content-sensitive vectors — different text hashes to
    a different (but stable) vector, which is enough to exercise a real
    upsert + search round-trip without needing a real embedding model."""

    @property
    def dimension(self) -> int:
        return 8

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [b / 255 for b in digest[:8]]


class FakeGenerator:
    def generate(self, question: str, retrieved: list[RetrievedChunk]) -> RawGeneration:
        cited = [retrieved[0].chunk_id] if retrieved else []
        return RawGeneration(answer=f"fake answer to: {question}", cited_chunk_ids=cited)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    async for session in get_session():
        yield session


@pytest_asyncio.fixture
async def repo_cleanup() -> AsyncGenerator[list[uuid.UUID]]:
    """Deletes every Repo row (cascades to Query rows) and its Qdrant
    chunks registered here, after the test, pass or fail — so runs don't
    leak state into each other."""
    repo_ids: list[uuid.UUID] = []

    yield repo_ids

    async for session in get_session():
        for repo_id in repo_ids:
            repo = await session.get(Repo, repo_id)
            if repo is not None:
                await session.delete(repo)
        await session.commit()
        break
    for repo_id in repo_ids:
        delete_repo_chunks(str(repo_id))


@pytest.fixture
def fake_embedder(monkeypatch: pytest.MonkeyPatch) -> FakeEmbedder:
    embedder = FakeEmbedder()
    monkeypatch.setattr("repolens.services.indexer.get_embedder", lambda: embedder)
    monkeypatch.setattr("repolens.api.routes.query.get_embedder", lambda: embedder)
    return embedder


@pytest.fixture
def fake_generator(monkeypatch: pytest.MonkeyPatch) -> FakeGenerator:
    generator = FakeGenerator()
    monkeypatch.setattr("repolens.generation.answer.get_generator", lambda: generator)
    return generator
