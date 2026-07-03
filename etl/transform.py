"""Field transformation functions for 實價登錄 CSV data.

Converts raw CSV strings into typed values suitable for the transactions table.
All functions follow a fail-soft pattern: unparseable values return None.

Note:
    DB stores area in square metres (m²) and unit price in TWD/m² — the raw
    values from the MOI source data.  Conversion to ping (坪) is the
    frontend's responsibility:  坪 = 平方公尺 ÷ 3.305785

"""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from etl.constants import (
    PARKING_TYPE_NONE_VALUES,
    UNKNOWN_DATE_VALUE,
)

logger = logging.getLogger(__name__)


def parse_transaction_date(raw: str) -> date | None:
    """Convert ROC (民國) date string to a Python date object.

    Args:
        raw: 7-digit ROC date string, e.g. ``"1130515"`` (YYYMMDD).
            The value ``"0000000"`` is treated as unknown and returns None.

    Returns:
        A Python ``date`` for the parsed date, or ``None`` if the input is
        empty, not a valid 7-digit string, or equals ``"0000000"``.

    """
    value = raw.strip()
    if not value or len(value) != 7 or not value.isdigit():
        logger.debug("parse_transaction_date: unparseable value %r → None", raw)
        return None
    if value == UNKNOWN_DATE_VALUE:
        logger.debug("parse_transaction_date: unknown date sentinel %r → None", raw)
        return None
    try:
        roc_year = int(value[:3])
        month = int(value[3:5])
        day = int(value[5:7])
        year = roc_year + 1911
        return date(year, month, day)
    except ValueError:
        logger.debug("parse_transaction_date: invalid date parts in %r → None", raw)
        return None


def parse_area_sqm(raw: str) -> Decimal | None:
    """Parse building area in square metres from a raw string.

    The value is stored as-is (no unit conversion).  Conversion to ping
    (坪 = m² ÷ 3.305785) is the frontend's responsibility.

    Args:
        raw: String representation of area in square metres, e.g. ``"66.10"``.

    Returns:
        Area in m² rounded to 2 decimal places, or ``None`` if unparseable.

    """
    value = raw.strip()
    if not value:
        logger.debug("parse_area_sqm: empty string → None")
        return None
    try:
        sqm = Decimal(value)
        return sqm.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        logger.debug("parse_area_sqm: unparseable value %r → None", raw)
        return None


def parse_price_per_sqm(raw: str) -> Decimal | None:
    """Parse unit price in TWD/m² from a raw string.

    The value is stored as-is (no unit conversion).  Conversion to TWD/ping
    (元/坪 = 元/m² × 3.305785) is the frontend's responsibility.

    Args:
        raw: String representation of unit price in TWD per square metre,
            e.g. ``"290000"``.

    Returns:
        Unit price in TWD/m² rounded to 2 decimal places, or ``None``
        if unparseable.

    """
    value = raw.strip()
    if not value:
        logger.debug("parse_price_per_sqm: empty string → None")
        return None
    try:
        per_sqm = Decimal(value)
        return per_sqm.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        logger.debug("parse_price_per_sqm: unparseable value %r → None", raw)
        return None


def parse_price_total(raw: str) -> Decimal | None:
    """Parse total transaction price in TWD.

    Args:
        raw: String representation of total price, e.g. ``"6000000"``.

    Returns:
        Total price as Decimal, or ``None`` if unparseable.

    """
    value = raw.strip()
    if not value:
        logger.debug("parse_price_total: empty string → None")
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        logger.debug("parse_price_total: unparseable value %r → None", raw)
        return None


def parse_building_age(raw_completion_date: str, current_year: int) -> int | None:
    """Calculate building age in whole years from ROC completion date.

    Age = current_year − (ROC_year + 1911). Only the year component is used;
    month and day are intentionally ignored to avoid boundary instability.
    Negative results (future completion dates) are stored as None.

    Args:
        raw_completion_date: 7-digit ROC date string, e.g. ``"0920630"``
            (民國 92 年 6 月 30 日 → completion year 2003).
        current_year: The calendar year in which the ETL is executed.

    Returns:
        Building age as a non-negative integer, or ``None`` if the input is
        empty, unparseable, or yields a negative age.

    """
    value = raw_completion_date.strip()
    if not value or len(value) < 3 or not value[:3].isdigit():
        logger.debug("parse_building_age: unparseable value %r → None", raw_completion_date)
        return None
    try:
        roc_year = int(value[:3])
        completion_year = roc_year + 1911
        age = current_year - completion_year
        if age < 0:
            logger.debug(
                "parse_building_age: negative age %d for %r → None",
                age,
                raw_completion_date,
            )
            return None
        return age
    except ValueError:
        logger.debug("parse_building_age: ValueError for %r → None", raw_completion_date)
        return None


def parse_has_parking(parking_type: str, parking_price: str) -> bool | None:
    """Derive three-state parking flag from 車位類別 and 車位總價.

    Logic (三態):
    - TRUE  : 車位類別 not in {空白, "無"} OR 車位總價 > 0.
    - FALSE : 車位類別 == "無" AND 車位總價 == 0 (or empty).
    - NULL  : Both fields are missing / unparseable / ambiguous.

    Args:
        parking_type: Raw string from 車位類別 column.
        parking_price: Raw string from 車位總價 column.

    Returns:
        ``True``, ``False``, or ``None`` according to three-state logic.

    """
    ptype = parking_type.strip()
    pprice_raw = parking_price.strip()

    # Attempt to parse parking price
    pprice: Decimal | None
    if pprice_raw:
        try:
            pprice = Decimal(pprice_raw)
        except (InvalidOperation, ValueError):
            pprice = None
    else:
        pprice = None

    # Both fields are completely absent / unparseable → NULL
    if ptype == "" and pprice is None:
        return None

    # Positive parking price → has parking
    if pprice is not None and pprice > 0:
        return True

    # Non-empty, non-"無" type → has parking
    if ptype not in PARKING_TYPE_NONE_VALUES:
        return True

    # Explicit "無" type and zero/absent price → no parking
    if ptype == "無":
        return False

    # Remaining ambiguous: e.g. empty type + zero price
    return None
