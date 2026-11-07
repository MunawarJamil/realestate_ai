from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import get_settings
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(
        get_settings().database_url,
        pool_size=10,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: One request = one transaction."""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    await get_engine().dispose()
    get_sessionmaker.cache_clear()
    get_engine.cache_clear()





@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession]:
    """Lightweight context manager for short-lived database operations.
    
    Acquires an AsyncSession from the pool, commits on success, rollbacks on error,
    and unconditionally closes/releases the connection back to the pool immediately.
    Ideal for streaming workflows where long-lived requests must NOT hold DB connections.
    """
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise