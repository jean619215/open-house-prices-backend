"""City-level average price API router.

Provides GET /api/prices/city, returning the average unit price per square
metre and transaction count for each city. Data is sourced directly from the
city_stats materialized view (see alembic/versions/003_create_city_stats_view.py),
which is refreshed by the ETL pipeline after every successful load
(see etl/pipeline.py::_refresh_city_stats). This endpoint never performs a
live GROUP BY against the transactions table (TASK-003 AC-16).
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()

_CITY_STATS_QUERY = text(
    "SELECT city, avg_price_per_sqm, transaction_count FROM city_stats ORDER BY city ASC"
)


class CityPriceStat(BaseModel):
    """Average price statistics for a single city.

    Attributes:
        city: City name (e.g. 台北市).
        avg_price_per_sqm: Average unit price per square metre in TWD,
            rounded to 2 decimal places. ``None`` when the city has
            transactions but none carry a usable unit price.
        transaction_count: Number of transactions recorded for the city.

    """

    city: str
    avg_price_per_sqm: float | None
    transaction_count: int


@router.get(
    "/api/prices/city",
    summary="縣市層級均價",
    response_model=list[CityPriceStat],
)
async def get_city_prices(
    session: AsyncSession = Depends(get_db_session),
) -> list[CityPriceStat]:
    """Return average unit price and transaction count per city.

    Queries the pre-aggregated city_stats materialized view directly (no
    live GROUP BY against transactions). Results are sorted by city name in
    ascending order. Cities with no recorded transactions do not appear in
    the result, since city_stats only contains groups that exist in
    transactions.

    Args:
        session: Injected async database session.

    Returns:
        list[CityPriceStat]: One entry per city with recorded transactions,
        sorted by city name ascending.

    """
    result = await session.execute(_CITY_STATS_QUERY)
    rows = result.all()
    logger.info("GET /api/prices/city: returned %d cities", len(rows))
    return [
        CityPriceStat(
            city=row.city,
            avg_price_per_sqm=(
                float(row.avg_price_per_sqm) if row.avg_price_per_sqm is not None else None
            ),
            transaction_count=row.transaction_count,
        )
        for row in rows
    ]
