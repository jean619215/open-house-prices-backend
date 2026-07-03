"""Async SQLAlchemy engine and session factory.

All modules must import the engine and session from here.
Do not create separate engine instances elsewhere.
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shared.config import get_settings

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the shared async SQLAlchemy engine, creating it if necessary.

    Returns:
        AsyncEngine: The application-wide async database engine.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            echo=settings.environment == "development",
        )
        logger.info(
            "Async engine created, pool_size=%d, max_overflow=%d",
            settings.db_pool_size,
            settings.db_max_overflow,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the shared async session factory.

    Returns:
        async_sessionmaker: Factory for creating AsyncSession instances.
    """
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for use as a FastAPI dependency.

    Yields:
        AsyncSession: An active database session.
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session
