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

# @lru_cache
# def get_engine() -> AsyncEngine:
#     return create_async_engine(
#         get_settings().database_url,
#         pool_size=10,
#         max_overflow=10,
#         pool_pre_ping=True,
#         pool_recycle=1800,
#     )

#  after enabling pg-bouncer in prod yml 
@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    
    # Check if PgBouncer is enabled or in connection string
    is_pgbouncer = settings.pgbouncer_mode or ":6432" in settings.database_url
    
    connect_args = {}
    if is_pgbouncer:
        # Crucial for asyncpg with PgBouncer transaction mode:
        # Disables prepared statement caching to prevent cross-transaction collision
        connect_args = {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        }

    return create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args=connect_args,
    )



@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: One request = one transaction with leak-proof cleanup."""
    session = get_sessionmaker()()
    try:
        yield session
        await session.commit()
    except BaseException:
        await session.rollback()
        raise
    finally:
        await session.close()





async def dispose_engine() -> None:
    await get_engine().dispose()
    get_sessionmaker.cache_clear()
    get_engine.cache_clear()





@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession]:
    """Lightweight context manager for short-lived database operations.
    
    Guarantees session.close() is ALWAYS executed even on client disconnects
    or task cancellation (asyncio.CancelledError), preventing garbage collector leaks.
    """
    session = get_sessionmaker()()
    try:
        yield session
        await session.commit()
    except BaseException:
        await session.rollback()
        raise
    finally:
        await session.close()