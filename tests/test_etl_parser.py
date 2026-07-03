"""Unit tests for etl.parser — CSV parsing and row construction.

Covers TC-04 (floor string passthrough), TC-08 (location/mrt_distance NULL),
AC-08, AC-11, AC-12, AC-13.
"""

from decimal import Decimal

from etl.parser import parse_csv_rows

# Minimal CSV header matching real 實價登錄 不動產買賣 format
_HEADER = (
    "鄉鎮市區,交易標的,土地位置建物門牌,土地移轉總面積平方公尺,都市土地使用分區,"
    "非都市土地使用分區,非都市土地使用編定,交易年月日,交易筆棟數,移轉層次,總樓層數,"
    "建物型態,主要用途,主要建材,建築完成年月,建物移轉總面積平方公尺,建物現況格局-房,"
    "建物現況格局-廳,建物現況格局-衛,建物現況格局-隔間,有無管理組織,總價元,"
    "單價元平方公尺,車位類別,車位移轉總面積平方公尺,車位總價元,備註,編號"
)


def _make_csv(data_row: str) -> str:
    """Compose a minimal CSV string from header + one data row.

    Args:
        data_row: Comma-separated values for a single data row.

    Returns:
        Full CSV string with header and data row.
    """
    return f"{_HEADER}\n{data_row}\n"


# One complete data row
_NORMAL_ROW = (
    "信義區,房地(土地+建物),台北市信義區松仁路100號,50.00,住,,,1130515,"
    "土地1建物1車位0,三層,12層,公寓,住家用,鋼筋混凝土造,0920630,66.10,"
    "3,2,1,無,有,6000000,290000,坡道平面,25.00,1500000,,A12345"
)


class TestParseCsvRows:
    """Tests for parse_csv_rows function."""

    def test_returns_nonempty_for_valid_csv(self) -> None:
        """parse_csv_rows returns at least one row for valid CSV."""
        rows = parse_csv_rows(_make_csv(_NORMAL_ROW), "A", 2026)
        assert len(rows) == 1

    def test_city_set_correctly(self) -> None:
        """AC-11: city is derived from city_code, not CSV column."""
        rows = parse_csv_rows(_make_csv(_NORMAL_ROW), "A", 2026)
        assert rows[0]["city"] == "台北市"

    def test_new_taipei_city(self) -> None:
        """AC-11: city_code 'F' → 新北市."""
        rows = parse_csv_rows(_make_csv(_NORMAL_ROW), "F", 2026)
        assert rows[0]["city"] == "新北市"

    def test_floor_raw_string_preserved(self) -> None:
        """TC-04 AC-08: floor = raw string from CSV, no conversion."""
        rows = parse_csv_rows(_make_csv(_NORMAL_ROW), "A", 2026)
        assert rows[0]["floor"] == "三層"

    def test_location_is_none(self) -> None:
        """TC-08 AC-12: location is always None."""
        rows = parse_csv_rows(_make_csv(_NORMAL_ROW), "A", 2026)
        assert rows[0]["location"] is None

    def test_mrt_distance_is_none(self) -> None:
        """TC-08 AC-13: mrt_distance is always None."""
        rows = parse_csv_rows(_make_csv(_NORMAL_ROW), "A", 2026)
        assert rows[0]["mrt_distance"] is None

    def test_transaction_date_converted(self) -> None:
        """AC-05: transaction_date 1130515 → 2024-05-15."""
        from datetime import date

        rows = parse_csv_rows(_make_csv(_NORMAL_ROW), "A", 2026)
        assert rows[0]["transaction_date"] == date(2024, 5, 15)

    def test_area_stored_as_sqm(self) -> None:
        """AC-06 (決策 1): area 66.10 m² stored as-is → 66.10 (±0.01).

        No unit conversion is performed; frontend converts to ping
        via 66.10 ÷ 3.305785 ≈ 19.995 坪.
        """
        rows = parse_csv_rows(_make_csv(_NORMAL_ROW), "A", 2026)
        result = rows[0]["area_sqm"]
        assert result is not None
        assert abs(result - Decimal("66.10")) <= Decimal("0.01")

    def test_price_per_sqm_stored_as_sqm(self) -> None:
        """AC-07 (決策 1): 290000 TWD/m² stored as-is → 290000.00.

        No unit conversion is performed; frontend converts to TWD/ping
        via 290000 × 3.305785 ≈ 958678 元/坪.
        """
        rows = parse_csv_rows(_make_csv(_NORMAL_ROW), "A", 2026)
        result = rows[0]["price_per_sqm"]
        assert result is not None
        assert result == Decimal("290000.00")

    def test_price_total_direct(self) -> None:
        """AC-11: price_total = 6000000."""
        rows = parse_csv_rows(_make_csv(_NORMAL_ROW), "A", 2026)
        assert rows[0]["price_total"] == Decimal("6000000")

    def test_building_age_dynamic(self) -> None:
        """TC-05 AC-09: completion 0920630 → 2026-2003=23."""
        rows = parse_csv_rows(_make_csv(_NORMAL_ROW), "A", 2026)
        assert rows[0]["building_age"] == 2026 - 2003

    def test_has_parking_true(self) -> None:
        """TC-06 AC-10: 坡道平面 + 1500000 → True."""
        rows = parse_csv_rows(_make_csv(_NORMAL_ROW), "A", 2026)
        assert rows[0]["has_parking"] is True

    def test_empty_csv_returns_empty_list(self) -> None:
        """TC-14 AC-04: CSV with only header → empty list."""
        rows = parse_csv_rows(_HEADER + "\n", "A", 2026)
        assert rows == []

    def test_row_missing_address_skipped(self) -> None:
        """Rows without address are skipped."""
        # Replace address field (index 2) with empty value
        bad_row = (
            "信義區,房地(土地+建物),,50.00,住,,,1130515,"
            "土地1建物1車位0,三層,12層,公寓,住家用,鋼筋混凝土造,0920630,66.10,"
            "3,2,1,無,有,6000000,290000,坡道平面,25.00,1500000,,A12345"
        )
        rows = parse_csv_rows(_make_csv(bad_row), "A", 2026)
        assert rows == []

    def test_null_date_with_0000000(self) -> None:
        """TC-09 列B AC-14: transaction_date='0000000' → None, row still inserted."""
        row = _NORMAL_ROW.replace("1130515", "0000000")
        rows = parse_csv_rows(_make_csv(row), "A", 2026)
        assert len(rows) == 1
        assert rows[0]["transaction_date"] is None
        # Other fields still populated
        assert rows[0]["city"] == "台北市"
        assert rows[0]["price_total"] is not None

    def test_null_date_with_empty(self) -> None:
        """TC-09 列A AC-14: empty transaction date → None, row still inserted."""
        row = _NORMAL_ROW.replace("1130515", "")
        rows = parse_csv_rows(_make_csv(row), "A", 2026)
        assert len(rows) == 1
        assert rows[0]["transaction_date"] is None

    def test_null_area_with_nonnumeric(self) -> None:
        """TC-10 AC-15: area='--' → area_sqm=None, row still inserted."""
        # Replace area value in field position
        row = _NORMAL_ROW.replace(",66.10,", ",--,")
        rows = parse_csv_rows(_make_csv(row), "A", 2026)
        assert len(rows) == 1
        assert rows[0]["area_sqm"] is None

    def test_null_unit_price_with_empty(self) -> None:
        """TC-10 AC-16: unit price='' → price_per_sqm=None."""
        row = _NORMAL_ROW.replace(",290000,", ",,")
        rows = parse_csv_rows(_make_csv(row), "A", 2026)
        assert len(rows) == 1
        assert rows[0]["price_per_sqm"] is None

    def test_null_building_age_unparseable(self) -> None:
        """TC-11 AC-17: completion date='不詳' → building_age=None."""
        row = _NORMAL_ROW.replace("0920630", "不詳")
        rows = parse_csv_rows(_make_csv(row), "A", 2026)
        assert len(rows) == 1
        assert rows[0]["building_age"] is None

    def test_null_has_parking_both_empty(self) -> None:
        """TC-12 AC-18: parking type and price both empty → None (not False)."""
        # Replace 坡道平面,25.00,1500000 with empty type and price
        row = _NORMAL_ROW.replace(",坡道平面,25.00,1500000,", ",,25.00,,")
        rows = parse_csv_rows(_make_csv(row), "A", 2026)
        assert len(rows) == 1
        assert rows[0]["has_parking"] is None

    def test_no_parking_false(self) -> None:
        """TC-07 AC-10: 車位類別='無', price=0 → False."""
        row = _NORMAL_ROW.replace(",坡道平面,25.00,1500000,", ",無,0.00,0,")
        rows = parse_csv_rows(_make_csv(row), "A", 2026)
        assert len(rows) == 1
        assert rows[0]["has_parking"] is False
