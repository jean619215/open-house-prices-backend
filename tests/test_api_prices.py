"""Unit tests for the GET /api/prices/city endpoint.

Covers TASK-003 AC-13~AC-23, TC-11~TC-16. Uses a mocked AsyncSession
(via FastAPI dependency override) so no real database is required — this
environment has no docker daemon available, so TC-01/TC-02/TC-07/TC-08/TC-09
(which require a real PostgreSQL + Alembic migration run) are NOT exercised
here and should be verified in a DB-available environment (see TASK-003 card
歷程).
"""

import os
from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError

# Set dummy env vars before importing the app so pydantic-settings does not
# raise ValidationError during test collection.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY", "dummy-secret-for-tests")
os.environ.setdefault("ENVIRONMENT", "test")

from api.main import app  # noqa: E402
from shared.database import get_db_session  # noqa: E402


@dataclass
class _FakeCityStatsRow:
    """Stand-in for a SQLAlchemy Row from the city_stats query."""

    city: str
    avg_price_per_sqm: Decimal | None
    transaction_count: int


def _override_session(rows: list[_FakeCityStatsRow]) -> AsyncMock:
    """Build a mock AsyncSession whose execute() returns the given rows.

    Args:
        rows: Fake city_stats rows to return from ``result.all()``.

    Returns:
        AsyncMock configured to simulate the query result.
    """
    result_mock = MagicMock()
    result_mock.all.return_value = rows
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)
    return session


def _install_override(session: AsyncMock) -> None:
    """Install a FastAPI dependency override that yields the given session.

    Args:
        session: The mock session to inject in place of a real DB session.
    """

    async def _fake_get_db_session() -> AsyncMock:
        return session

    app.dependency_overrides[get_db_session] = _fake_get_db_session


@pytest.fixture(autouse=True)
def _clear_overrides() -> None:
    """Ensure dependency overrides never leak between tests."""
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# TC-11: basic fields and types
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_basic_response_fields_and_types() -> None:
    """TC-11 AC-14 AC-15: 200, JSON array, exact 3 snake_case keys, values correct."""
    rows = [
        _FakeCityStatsRow(
            city="台北市", avg_price_per_sqm=Decimal("150000.00"), transaction_count=3
        )
    ]
    _install_override(_override_session(rows))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/prices/city")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    item = body[0]
    assert set(item.keys()) == {"city", "avg_price_per_sqm", "transaction_count"}
    assert item["city"] == "台北市"
    assert item["avg_price_per_sqm"] == 150000.0
    assert item["transaction_count"] == 3


# ---------------------------------------------------------------------------
# TC-12: sorting — query issued with ORDER BY city ASC; AC-16: no live GROUP BY
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_sorts_by_city_and_reads_view_directly() -> None:
    """TC-12 AC-18: SQL issued sorts by city ascending.
    AC-16: queries city_stats directly, no GROUP BY against transactions.
    """
    rows = [
        _FakeCityStatsRow(city="台北市", avg_price_per_sqm=Decimal("100.00"), transaction_count=1),
        _FakeCityStatsRow(city="新北市", avg_price_per_sqm=Decimal("200.00"), transaction_count=2),
        _FakeCityStatsRow(city="高雄市", avg_price_per_sqm=Decimal("300.00"), transaction_count=3),
    ]
    session = _override_session(rows)
    _install_override(session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/prices/city")

    assert response.status_code == 200
    session.execute.assert_awaited_once()
    (executed_stmt,), _ = session.execute.await_args
    sql_text = str(executed_stmt)
    assert "city_stats" in sql_text
    assert "ORDER BY city" in sql_text
    assert "GROUP BY" not in sql_text
    assert "transactions" not in sql_text


# ---------------------------------------------------------------------------
# AC-17: no duplicate city values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_duplicate_city_values() -> None:
    """AC-17: response array contains no duplicate city values."""
    rows = [
        _FakeCityStatsRow(city="台北市", avg_price_per_sqm=Decimal("100.00"), transaction_count=1),
        _FakeCityStatsRow(city="新北市", avg_price_per_sqm=Decimal("200.00"), transaction_count=2),
    ]
    _install_override(_override_session(rows))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/prices/city")

    cities = [item["city"] for item in response.json()]
    assert len(cities) == len(set(cities))


# ---------------------------------------------------------------------------
# TC-13 / AC-20: avg_price_per_sqm null
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_avg_price_per_sqm_null_for_city_with_no_unit_price() -> None:
    """TC-13 AC-20: avg_price_per_sqm is JSON null (not omitted, 0, or "null")."""
    rows = [_FakeCityStatsRow(city="新北市", avg_price_per_sqm=None, transaction_count=2)]
    _install_override(_override_session(rows))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/prices/city")

    body = response.json()
    assert len(body) == 1
    item = body[0]
    assert "avg_price_per_sqm" in item
    assert item["avg_price_per_sqm"] is None
    assert item["transaction_count"] == 2


# ---------------------------------------------------------------------------
# TC-14 / AC-19 / AC-21: empty city_stats → 200 []
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_city_stats_returns_empty_array() -> None:
    """TC-14 AC-19 AC-21: no rows in city_stats → HTTP 200, body == []."""
    _install_override(_override_session([]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/prices/city")

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# TC-15 / AC-23: unknown query params ignored
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_query_params_are_ignored() -> None:
    """TC-15 AC-23: an undeclared query param does not affect the result."""
    rows = [
        _FakeCityStatsRow(city="台北市", avg_price_per_sqm=Decimal("100.00"), transaction_count=1)
    ]
    _install_override(_override_session(rows))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response_plain = await client.get("/api/prices/city")

    _install_override(_override_session(rows))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response_with_query = await client.get("/api/prices/city", params={"foo": "bar"})

    assert response_plain.status_code == 200
    assert response_with_query.status_code == 200
    assert response_plain.json() == response_with_query.json()


# ---------------------------------------------------------------------------
# TC-16 / AC-22: DB exception → 500
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_db_exception_returns_500() -> None:
    """TC-16 AC-22: a DB error raised during query execution surfaces as 500."""
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=SQLAlchemyError("connection lost"))
    _install_override(session)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.get("/api/prices/city")

    assert response.status_code == 500
