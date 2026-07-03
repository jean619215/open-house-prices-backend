"""Alembic environment configuration.

Supports async SQLAlchemy engine (asyncpg) via asyncio.run + run_sync.
DATABASE_URL is read from the application Settings, not from alembic.ini.
"""

import asyncio
import logging
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Ensure the project root is on sys.path so shared/ can be imported.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.config import get_settings  # noqa: E402
from shared.models import Base  # noqa: E402

logger = logging.getLogger(__name__)

# Alembic Config object — gives access to alembic.ini values.
config = context.config

# Configure Python logging from alembic.ini if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support.
target_metadata = Base.metadata


def get_database_url() -> str:
    """Read the database URL from application settings.

    Returns:
        str: The async database URL (postgresql+asyncpg://...).
    """
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL without connecting to the database.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    """Execute migrations against the given synchronous connection.

    Args:
        connection: A synchronous SQLAlchemy connection provided by run_sync.
    """
    context.configure(connection=connection, target_metadata=target_metadata)  # type: ignore[arg-type]
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine.

    Creates a temporary async engine (separate from the application pool)
    and wraps the synchronous Alembic context with run_sync.
    """
    url = get_database_url()
    connectable = create_async_engine(url, future=True)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()
    logger.info("Async migrations completed")


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
