"""Database loader for 實價登錄 transaction rows.

Inserts parsed rows into the transactions table via async SQLAlchemy session,
with idempotency based on the composite dedup key:
    (address, transaction_date, floor, area_sqm, price_total)
"""

import logging
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Transaction

logger = logging.getLogger(__name__)

# Dedup key columns (AC-19, TC-15)
_DEDUP_COLS = ("address", "transaction_date", "floor", "area_sqm", "price_total")


def _build_dedup_key(row: dict[str, Any]) -> tuple[Any, ...]:
    """Extract the composite dedup key from a row dict.

    Args:
        row: A parsed row dict with Transaction field names.

    Returns:
        Tuple of (address, transaction_date, floor, area_sqm, price_total).

    """
    return tuple(row.get(col) for col in _DEDUP_COLS)


async def _row_exists(session: AsyncSession, row: dict[str, Any]) -> bool:
    """Check whether a row with the same dedup key already exists in the DB.

    Args:
        session: Active async database session.
        row: Parsed row dict.

    Returns:
        ``True`` if a matching row exists, ``False`` otherwise.

    """
    conditions = []
    for col in _DEDUP_COLS:
        val = row.get(col)
        col_attr = getattr(Transaction, col)
        if val is None:
            conditions.append(col_attr.is_(None))
        else:
            conditions.append(col_attr == val)

    stmt = select(Transaction.id).where(and_(*conditions)).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def bulk_insert_rows(
    session: AsyncSession,
    rows: list[dict[str, Any]],
) -> tuple[int, int]:
    """Insert parsed rows into the transactions table, skipping duplicates.

    Each row is checked against the composite dedup key before insertion.
    Duplicate rows are skipped with a debug log message.

    Args:
        session: Active async database session. The caller is responsible for
            committing or rolling back.
        rows: List of parsed row dicts with Transaction field names.

    Returns:
        A tuple ``(inserted, skipped)`` with counts of new and duplicate rows.

    """
    inserted = 0
    skipped = 0

    for row in rows:
        if await _row_exists(session, row):
            logger.debug(
                "已存在，跳過：address=%r, transaction_date=%s, floor=%r, "
                "area_sqm=%s, price_total=%s",
                row.get("address"),
                row.get("transaction_date"),
                row.get("floor"),
                row.get("area_sqm"),
                row.get("price_total"),
            )
            skipped += 1
            continue

        txn = Transaction(**row)
        session.add(txn)
        inserted += 1

    logger.info("bulk_insert_rows: inserted=%d, skipped=%d", inserted, skipped)
    return inserted, skipped


async def load_rows(
    session: AsyncSession,
    rows: list[dict[str, Any]],
) -> tuple[int, int]:
    """High-level loader: insert rows and commit.

    Wraps ``bulk_insert_rows`` with a single commit.  On error the session is
    left in a state suitable for rollback by the caller.

    Args:
        session: Active async database session.
        rows: List of parsed row dicts.

    Returns:
        A tuple ``(inserted, skipped)``.

    """
    if not rows:
        logger.warning("load_rows: 無可匯入資料（rows 為空）")
        return 0, 0

    inserted, skipped = await bulk_insert_rows(session, rows)
    await session.commit()
    return inserted, skipped
