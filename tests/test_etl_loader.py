"""Unit tests for etl.loader — database insertion with idempotency.

Covers AC-19, AC-20, AC-21, TC-15 (dedup key logic).
Uses an in-memory async mock session — no real DB required.
"""

from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from etl.loader import bulk_insert_rows, load_rows

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_row(**overrides: Any) -> dict[str, Any]:
    """Build a minimal valid transaction row dict.

    Args:
        **overrides: Fields to override from the defaults.

    Returns:
        Dict with all Transaction model fields.
    """
    base: dict[str, Any] = {
        "address": "台北市信義區松仁路100號",
        "city": "台北市",
        "district": "信義區",
        "location": None,
        "price_total": Decimal("6000000"),
        "price_per_sqm": Decimal("958677.65"),
        "area_sqm": Decimal("19.995"),
        "floor": "三層",
        "building_age": 23,
        "building_type": "公寓",
        "has_parking": True,
        "mrt_distance": None,
        "transaction_date": date(2024, 5, 15),
    }
    base.update(overrides)
    return base


def _make_session_mock(*, existing_row: bool = False) -> AsyncMock:
    """Build a mock AsyncSession.

    Args:
        existing_row: If True, _row_exists will return True (simulate duplicate).

    Returns:
        AsyncMock configured to simulate AsyncSession behaviour.
    """
    session = AsyncMock()
    # mock execute → scalar_one_or_none → row id if existing, else None
    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none.return_value = 1 if existing_row else None
    session.execute = AsyncMock(return_value=scalar_mock)
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# bulk_insert_rows tests
# ---------------------------------------------------------------------------


class TestBulkInsertRows:
    """Tests for bulk_insert_rows dedup logic."""

    @pytest.mark.asyncio
    async def test_new_row_is_inserted(self) -> None:
        """AC-21 TC-15: new row is added to session."""
        session = _make_session_mock(existing_row=False)
        row = _make_row()

        inserted, skipped = await bulk_insert_rows(session, [row])

        assert inserted == 1
        assert skipped == 0
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_row_is_skipped(self) -> None:
        """AC-19 TC-15: existing row is skipped, not re-inserted."""
        session = _make_session_mock(existing_row=True)
        row = _make_row()

        inserted, skipped = await bulk_insert_rows(session, [row])

        assert inserted == 0
        assert skipped == 1
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_new_and_duplicate(self) -> None:
        """TC-15: one existing + one new row → inserted=1, skipped=1."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()

        # First call (existing row): returns an id.  Second call (new row): None.
        scalar_existing = MagicMock()
        scalar_existing.scalar_one_or_none.return_value = 1

        scalar_new = MagicMock()
        scalar_new.scalar_one_or_none.return_value = None

        session.execute = AsyncMock(side_effect=[scalar_existing, scalar_new])

        existing = _make_row()
        new_row = _make_row(address="台北市大安區忠孝東路1號", transaction_date=date(2023, 1, 1))

        inserted, skipped = await bulk_insert_rows(session, [existing, new_row])

        assert inserted == 1
        assert skipped == 1

    @pytest.mark.asyncio
    async def test_empty_list_returns_zeros(self) -> None:
        """Empty input → 0, 0."""
        session = _make_session_mock()
        inserted, skipped = await bulk_insert_rows(session, [])
        assert inserted == 0
        assert skipped == 0


# ---------------------------------------------------------------------------
# load_rows tests
# ---------------------------------------------------------------------------


class TestLoadRows:
    """Tests for load_rows high-level loader."""

    @pytest.mark.asyncio
    async def test_empty_rows_returns_zeros_no_commit(self) -> None:
        """AC-04 TC-14: empty rows → warning logged, no commit."""
        session = _make_session_mock()
        inserted, skipped = await load_rows(session, [])
        assert inserted == 0
        assert skipped == 0
        session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_commit_called_after_insert(self) -> None:
        """AC-21: commit is called once after successful bulk insert."""
        session = _make_session_mock(existing_row=False)
        rows = [_make_row()]

        await load_rows(session, rows)

        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_commit_on_empty(self) -> None:
        """AC-04: empty rows do not trigger commit."""
        session = _make_session_mock()
        await load_rows(session, [])
        session.commit.assert_not_called()
