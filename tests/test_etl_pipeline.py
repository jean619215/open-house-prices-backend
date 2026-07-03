"""Unit tests for etl.pipeline — end-to-end pipeline orchestration.

Covers AC-01, AC-03, AC-04, TC-01, TC-13, TC-14.
Mocks download and DB session so no real network or database is needed.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Set dummy env before importing shared modules
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY", "dummy-secret-for-tests")
os.environ.setdefault("ENVIRONMENT", "test")

from etl.pipeline import run_pipeline  # noqa: E402

# Minimal valid CSV content (header only triggers empty-CSV path; add a data row for normal path)
_CSV_HEADER = (
    "鄉鎮市區,交易標的,土地位置建物門牌,土地移轉總面積平方公尺,都市土地使用分區,"
    "非都市土地使用分區,非都市土地使用編定,交易年月日,交易筆棟數,移轉層次,總樓層數,"
    "建物型態,主要用途,主要建材,建築完成年月,建物移轉總面積平方公尺,建物現況格局-房,"
    "建物現況格局-廳,建物現況格局-衛,建物現況格局-隔間,有無管理組織,總價元,"
    "單價元平方公尺,車位類別,車位移轉總面積平方公尺,車位總價元,備註,編號"
)

_CSV_DATA_ROW = (
    "信義區,房地(土地+建物),台北市信義區松仁路100號,50.00,住,,,1130515,"
    "土地1建物1車位0,三層,12層,公寓,住家用,鋼筋混凝土造,0920630,66.10,"
    "3,2,1,無,有,6000000,290000,坡道平面,25.00,1500000,,A12345"
)

_VALID_CSV = f"{_CSV_HEADER}\n{_CSV_DATA_ROW}\n"
_EMPTY_CSV = f"{_CSV_HEADER}\n"


def _make_session_mock() -> AsyncMock:
    """Create a minimal async session mock that supports context manager.

    Returns:
        AsyncMock simulating an AsyncSession (new row, no existing records).
    """
    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none.return_value = None

    session = AsyncMock()
    session.execute = AsyncMock(return_value=scalar_mock)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()

    def _make_nested() -> AsyncMock:
        """Build a fresh mock for one ``session.begin_nested()`` call."""
        nested = AsyncMock()
        nested.__aenter__ = AsyncMock(return_value=nested)
        nested.__aexit__ = AsyncMock(return_value=False)
        return nested

    session.begin_nested = MagicMock(side_effect=_make_nested)
    # Support async context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


def _make_factory_mock(session: AsyncMock) -> MagicMock:
    """Build a mock session factory that yields the given session.

    Args:
        session: The async session mock to return from the factory.

    Returns:
        MagicMock simulating async_sessionmaker behaviour.
    """
    factory = MagicMock()
    factory.return_value = session
    return factory


class TestRunPipeline:
    """Tests for the run_pipeline orchestrator."""

    @pytest.mark.asyncio
    async def test_normal_run_calls_load(self) -> None:
        """TC-01 AC-01: successful pipeline inserts rows and returns normally."""
        session = _make_session_mock()
        factory = _make_factory_mock(session)

        with (
            patch("etl.pipeline.download_all_target_cities", return_value={"A": _VALID_CSV}),
            patch("etl.pipeline.get_session_factory", return_value=factory),
        ):
            await run_pipeline()

        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_download_http_error_raises(self) -> None:
        """TC-13 AC-03: HTTPStatusError from download propagates."""
        exc = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock(status_code=500))
        with patch(
            "etl.pipeline.download_all_target_cities",
            side_effect=exc,
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await run_pipeline()

    @pytest.mark.asyncio
    async def test_download_network_error_raises(self) -> None:
        """TC-13 AC-03: RequestError from download propagates."""
        exc = httpx.ConnectError("connection refused")
        with patch(
            "etl.pipeline.download_all_target_cities",
            side_effect=exc,
        ):
            with pytest.raises(httpx.RequestError):
                await run_pipeline()

    @pytest.mark.asyncio
    async def test_empty_csv_no_insert(self) -> None:
        """TC-14 AC-04: all CSVs empty → parse returns 0 rows → no DB write."""
        session = _make_session_mock()
        factory = _make_factory_mock(session)

        with (
            patch("etl.pipeline.download_all_target_cities", return_value={"A": _EMPTY_CSV}),
            patch("etl.pipeline.get_session_factory", return_value=factory),
        ):
            await run_pipeline()

        # No rows → load_rows not called with any data → commit never called
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_cities_downloaded_returns_early(self) -> None:
        """AC-04: download returns empty dict → pipeline returns without DB access."""
        session = _make_session_mock()
        factory = _make_factory_mock(session)

        with (
            patch("etl.pipeline.download_all_target_cities", return_value={}),
            patch("etl.pipeline.get_session_factory", return_value=factory),
        ):
            await run_pipeline()

        session.commit.assert_not_awaited()
