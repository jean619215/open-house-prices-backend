"""CSV parser for 實價登錄 不動產買賣 data.

Parses raw CSV text into a list of row dicts, applying field transformation.
"""

import csv
import io
import logging
from datetime import date
from decimal import Decimal
from typing import Any

from etl.constants import TARGET_CITIES
from etl.transform import (
    parse_area_sqm,
    parse_building_age,
    parse_has_parking,
    parse_price_per_sqm,
    parse_price_total,
    parse_transaction_date,
)

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Column name mappings (來源欄位名稱)
# --------------------------------------------------------------------------
# These constants guard against typos and make grep-ability easy.

COL_DISTRICT = "鄉鎮市區"
COL_TRANSACTION_TYPE = "交易標的"
COL_ADDRESS = "土地位置建物門牌"
COL_TRANSFER_DATE = "交易年月日"
COL_TRANSFER_AREA = "建物移轉總面積平方公尺"
COL_FLOOR = "移轉層次"
COL_TOTAL_FLOORS = "總樓層數"
COL_BUILDING_TYPE = "建物型態"
COL_MAIN_PURPOSE = "主要用途"
COL_MAIN_MATERIAL = "主要建材"
COL_COMPLETION_DATE = "建築完成年月"
COL_UNIT_PRICE = "單價元平方公尺"
COL_PRICE_TOTAL = "總價元"
COL_PARKING_TYPE = "車位類別"
COL_PARKING_PRICE = "車位總價元"
COL_NOTE = "備註"


def _get_col(row: dict[str, str], *keys: str) -> str:
    """Return the first matching column value, or empty string.

    The MOI CSV sometimes has slight variations in column names (e.g. with/without
    whitespace). This helper tries each key in order.

    Args:
        row: A single CSV row dict.
        *keys: Column name candidates to try, in order.

    Returns:
        The stripped column value, or ``""`` if none matched.
    """
    for key in keys:
        if key in row:
            return row[key].strip()
    return ""


def _determine_city(city_code: str) -> str:
    """Map a city code to its Chinese city name.

    Args:
        city_code: MOI city code, e.g. ``"A"``.

    Returns:
        Chinese city name, e.g. ``"台北市"``.
    """
    return TARGET_CITIES.get(city_code, city_code)


def parse_csv_rows(
    csv_content: str,
    city_code: str,
    current_year: int,
) -> list[dict[str, Any]]:
    """Parse a 實價登錄 CSV string into a list of transformed row dicts.

    Each dict has keys matching the Transaction model columns.
    Unparseable values are set to ``None`` (fail-soft).
    Rows without a valid address are skipped with a warning.

    Args:
        csv_content: Raw CSV string (UTF-8, may include BOM).
        city_code: MOI city code used to derive the city name.
        current_year: Calendar year used for building_age calculation.

    Returns:
        List of row dicts ready for database insertion.
    """
    city = _determine_city(city_code)
    rows: list[dict[str, Any]] = []

    reader = csv.DictReader(io.StringIO(csv_content))
    if reader.fieldnames is None:
        logger.warning("CSV for city_code=%s has no headers; skipping", city_code)
        return rows

    for line_num, raw_row in enumerate(reader, start=2):
        address = _get_col(raw_row, COL_ADDRESS)
        if not address:
            logger.debug("Row %d: empty address; skipping", line_num)
            continue

        district = _get_col(raw_row, COL_DISTRICT)
        floor_raw = _get_col(raw_row, COL_FLOOR)
        building_type = _get_col(raw_row, COL_BUILDING_TYPE)

        transfer_date_raw = _get_col(raw_row, COL_TRANSFER_DATE)
        transaction_date: date | None = parse_transaction_date(transfer_date_raw)

        area_raw = _get_col(raw_row, COL_TRANSFER_AREA)
        area_sqm: Decimal | None = parse_area_sqm(area_raw)

        unit_price_raw = _get_col(raw_row, COL_UNIT_PRICE)
        price_per_sqm: Decimal | None = parse_price_per_sqm(unit_price_raw)

        price_total_raw = _get_col(raw_row, COL_PRICE_TOTAL)
        price_total: Decimal | None = parse_price_total(price_total_raw)

        completion_raw = _get_col(raw_row, COL_COMPLETION_DATE)
        building_age: int | None = parse_building_age(completion_raw, current_year)

        parking_type_raw = _get_col(raw_row, COL_PARKING_TYPE)
        parking_price_raw = _get_col(raw_row, COL_PARKING_PRICE)
        has_parking: bool | None = parse_has_parking(parking_type_raw, parking_price_raw)

        rows.append(
            {
                "address": address,
                "city": city,
                "district": district or None,
                "location": None,
                "price_total": price_total,
                "price_per_sqm": price_per_sqm,
                "area_sqm": area_sqm,
                "floor": floor_raw or None,
                "building_age": building_age,
                "building_type": building_type or None,
                "has_parking": has_parking,
                "mrt_distance": None,
                "transaction_date": transaction_date,
            }
        )

    logger.info("Parsed %d rows for city_code=%s", len(rows), city_code)
    return rows
