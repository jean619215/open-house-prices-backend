"""Unit tests for the GET /health endpoint.

Uses AsyncMock to mock DB and Redis connections — no real services required.
TC-03: Normal (both connected).
TC-04 simulation: DB disconnected.
TC-05 simulation: Redis disconnected.

TC-01 (Docker), TC-04 (stop container), TC-05 (stop container),
TC-08 (10 concurrent requests) are integration tests requiring Docker;
those are validated manually per the TASK-001 test plan.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Set dummy env vars before importing the app so pydantic-settings does not
# raise ValidationError during test collection.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY", "dummy-secret-for-tests")
os.environ.setdefault("ENVIRONMENT", "test")

from api.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_engine_mock(*, raise_exc: Exception | None = None) -> MagicMock:
    """Build a mock async engine whose connect() context manager succeeds or raises.

    Args:
        raise_exc: If provided, the context manager will raise this exception
            instead of returning a connection.

    Returns:
        MagicMock: A mock resembling an AsyncEngine.
    """
    conn_mock = AsyncMock()
    if raise_exc is not None:
        conn_mock.__aenter__ = AsyncMock(side_effect=raise_exc)
    else:
        conn_mock.__aenter__ = AsyncMock(return_value=AsyncMock())
    conn_mock.__aexit__ = AsyncMock(return_value=False)

    engine_mock = MagicMock()
    engine_mock.connect = MagicMock(return_value=conn_mock)
    return engine_mock


# ---------------------------------------------------------------------------
# TC-03: Both DB and Redis connected — expect 200 {"status": "ok", ...}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_all_connected() -> None:
    """TC-03: /health returns 200 when DB and Redis are both reachable."""
    engine_mock = _make_engine_mock()

    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.aclose = AsyncMock()

    with (
        patch("api.routers.health.get_engine", return_value=engine_mock),
        patch("api.routers.health.aioredis.from_url", return_value=redis_mock),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "connected"
    assert body["redis"] == "connected"


# ---------------------------------------------------------------------------
# TC-04 simulation: DB disconnected — expect 503 with db="disconnected"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_db_disconnected() -> None:
    """TC-04 (unit sim): /health returns 503 when DB is unreachable."""
    engine_mock = _make_engine_mock(raise_exc=OSError("connection refused"))

    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.aclose = AsyncMock()

    with (
        patch("api.routers.health.get_engine", return_value=engine_mock),
        patch("api.routers.health.aioredis.from_url", return_value=redis_mock),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["db"] == "disconnected"
    assert body["redis"] == "connected"


# ---------------------------------------------------------------------------
# TC-05 simulation: Redis disconnected — expect 503 with redis="disconnected"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_redis_disconnected() -> None:
    """TC-05 (unit sim): /health returns 503 when Redis is unreachable."""
    engine_mock = _make_engine_mock()

    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(side_effect=OSError("connection refused"))
    redis_mock.aclose = AsyncMock()

    with (
        patch("api.routers.health.get_engine", return_value=engine_mock),
        patch("api.routers.health.aioredis.from_url", return_value=redis_mock),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["db"] == "connected"
    assert body["redis"] == "disconnected"


# ---------------------------------------------------------------------------
# TC-07: Missing environment variable — startup raises ValidationError
# ---------------------------------------------------------------------------


def test_missing_env_var_raises_validation_error() -> None:
    """TC-07: Settings() raises ValidationError when DATABASE_URL is absent.

    pydantic-settings reads from environment variables and .env files.
    We bypass both by constructing Settings directly with _env_file=None
    and without DATABASE_URL in the environment, which triggers validation.
    """
    from pydantic import ValidationError

    from shared.config import Settings

    saved = os.environ.pop("DATABASE_URL", None)
    try:
        # _env_file=None prevents reading .env so the missing DATABASE_URL
        # is not silently sourced from disk.
        with pytest.raises(ValidationError):
            Settings(_env_file=None)  # type: ignore[call-arg]
    finally:
        if saved is not None:
            os.environ["DATABASE_URL"] = saved
