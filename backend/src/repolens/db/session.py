from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from repolens.core.config import get_settings

_settings = get_settings()
_engine = create_async_engine(_settings.database_url, pool_pre_ping=True)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with _session_factory() as session:
        yield session
