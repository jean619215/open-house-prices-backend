"""Health check router.

Provides GET /health endpoint that verifies DB and Redis connectivity.
Responds within 3 seconds; returns 503 if either service is unreachable.
"""

import asyncio
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from shared.config import get_settings
from shared.database import get_engine

logger = logging.getLogger(__name__)

router = APIRouter()

# Timeout constants (seconds)
_DB_STATEMENT_TIMEOUT_MS = 2000  # passed to PostgreSQL as statement_timeout
_DB_CONNECT_TIMEOUT = 2.0  # asyncio.wait_for outer guard
_REDIS_SOCKET_TIMEOUT = 1.0
_HEALTH_TOTAL_TIMEOUT = 3.0


async def _check_db() -> str:
    """Probe PostgreSQL with SELECT 1 under a 2-second statement timeout.

    Returns:
        "connected" if the probe succeeds, "disconnected" otherwise.
    """
    try:
        engine = get_engine()
        async with asyncio.timeout(_DB_CONNECT_TIMEOUT):
            async with engine.connect() as conn:
                await conn.execute(
                    text(f"SET LOCAL statement_timeout = {_DB_STATEMENT_TIMEOUT_MS}")
                )
                await conn.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        logger.exception("DB health check failed")
        return "disconnected"


async def _check_redis() -> str:
    """Probe Redis with PING under a 1-second socket timeout.

    Returns:
        "connected" if the probe succeeds, "disconnected" otherwise.
    """
    settings = get_settings()
    client: aioredis.Redis | None = None
    try:
        client = aioredis.from_url(
            settings.redis_url,
            socket_connect_timeout=_REDIS_SOCKET_TIMEOUT,
            socket_timeout=_REDIS_SOCKET_TIMEOUT,
        )
        await client.ping()
        return "connected"
    except Exception:
        logger.exception("Redis health check failed")
        return "disconnected"
    finally:
        if client is not None:
            await client.aclose()


@router.get("/health", summary="Service health check")
async def health_check() -> JSONResponse:
    """Check the health of all downstream services.

    Probes PostgreSQL (SELECT 1, 2 s timeout) and Redis (PING, 1 s timeout)
    concurrently. The entire handler must complete within 3 seconds.

    Returns:
        JSONResponse: HTTP 200 with status "ok" when both services respond,
            or HTTP 503 with status "error" when at least one is unreachable.
    """
    try:
        async with asyncio.timeout(_HEALTH_TOTAL_TIMEOUT):
            db_status, redis_status = await asyncio.gather(
                _check_db(),
                _check_redis(),
            )
    except TimeoutError:
        logger.error("Health check timed out after %s seconds", _HEALTH_TOTAL_TIMEOUT)
        db_status = "disconnected"
        redis_status = "disconnected"

    all_ok = db_status == "connected" and redis_status == "connected"
    http_status = 200 if all_ok else 503

    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ok" if all_ok else "error",
            "db": db_status,
            "redis": redis_status,
        },
    )
