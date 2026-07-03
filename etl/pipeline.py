"""Main ETL pipeline orchestrator for 實價登錄 data ingestion.

Coordinates download → parse → load for all target cities.
"""

import logging
from datetime import date
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from etl.constants import TARGET_CITIES
from etl.downloader import download_all_target_cities
from etl.parser import parse_csv_rows
from shared.database import get_session_factory

logger = logging.getLogger(__name__)


async def _refresh_city_stats(session: AsyncSession) -> None:
    """Refresh the city_stats materialized view after a successful load step.

    Must only be called once the ETL pipeline has entered its write step
    (``load_rows``) and that step has completed without raising — regardless
    of how many rows were actually inserted (TASK-003 AC-11: REFRESH is
    idempotent, so it runs even when every row in the batch was a duplicate).

    Args:
        session: Active async database session (the same session used for
            the preceding ``load_rows`` call).

    Raises:
        SQLAlchemyError: Re-raised after logging so the caller (and
            ultimately ``python -m etl.run``) exits with a non-zero status
            instead of silently leaving city_stats stale.
    """
    try:
        await session.execute(text("REFRESH MATERIALIZED VIEW city_stats"))
        await session.commit()
    except SQLAlchemyError as exc:
        logger.error("REFRESH MATERIALIZED VIEW city_stats 失敗：%s", exc)
        raise


async def run_pipeline() -> None:
    """Execute the full ETL pipeline for 台北市 and 新北市.

    Steps:
        1. Download the latest 不動產買賣 CSV for each target city.
        2. Parse each CSV into typed row dicts.
        3. Batch-insert rows into the transactions table (idempotent).
        4. Refresh the city_stats materialized view so GET /api/prices/city
           reflects the newly loaded data (TASK-003). Only runs if step 3
           was actually entered — an early return in steps 1-2 (no data to
           import) skips the refresh entirely.

    Raises:
        httpx.HTTPStatusError: If any city download returns an HTTP error.
        httpx.RequestError: If a network error occurs during download.
        Exception: Re-raises any unexpected DB, parse, or REFRESH error.

    """
    current_year = date.today().year
    logger.info(
        "ETL pipeline starting: target cities=%s, current_year=%d",
        list(TARGET_CITIES.keys()),
        current_year,
    )

    # ── Step 1: Download ───────────────────────────────────────────────────
    try:
        city_csvs: dict[str, str] = await download_all_target_cities()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.error("下載失敗：%s", exc)
        raise

    if not city_csvs:
        logger.warning("無可匯入資料：所有城市下載均無結果")
        return

    # ── Step 2: Parse ──────────────────────────────────────────────────────
    all_rows: list[dict[str, Any]] = []
    for city_code, csv_content in city_csvs.items():
        rows = parse_csv_rows(csv_content, city_code, current_year)
        if not rows:
            logger.warning("city_code=%s CSV 解析後無資料列", city_code)
        all_rows.extend(rows)

    if not all_rows:
        logger.warning("無可匯入資料：所有 CSV 解析後均無有效資料列")
        return

    # ── Step 3: Load ───────────────────────────────────────────────────────
    factory = get_session_factory()
    async with factory() as session:
        from etl.loader import load_rows  # local import to aid testability

        inserted, skipped = await load_rows(session, all_rows)

        # ── Step 4: Refresh city_stats materialized view (AC-09, AC-11) ────
        await _refresh_city_stats(session)

    logger.info(
        "匯入完成：total_parsed=%d, inserted=%d, skipped=%d",
        len(all_rows),
        inserted,
        skipped,
    )
