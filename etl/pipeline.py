"""Main ETL pipeline orchestrator for 實價登錄 data ingestion.

Coordinates download → parse → load for all target cities.
"""

import logging
from datetime import date
from typing import Any

import httpx

from etl.constants import TARGET_CITIES
from etl.downloader import download_all_target_cities
from etl.parser import parse_csv_rows
from shared.database import get_session_factory

logger = logging.getLogger(__name__)


async def run_pipeline() -> None:
    """Execute the full ETL pipeline for 台北市 and 新北市.

    Steps:
        1. Download the latest 不動產買賣 CSV for each target city.
        2. Parse each CSV into typed row dicts.
        3. Batch-insert rows into the transactions table (idempotent).

    Raises:
        httpx.HTTPStatusError: If any city download returns an HTTP error.
        httpx.RequestError: If a network error occurs during download.
        Exception: Re-raises any unexpected DB or parse error.
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

    logger.info(
        "匯入完成：total_parsed=%d, inserted=%d, skipped=%d",
        len(all_rows),
        inserted,
        skipped,
    )
