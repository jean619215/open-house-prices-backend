"""Unit tests for etl.transform — field conversion functions.

Covers AC-05 to AC-18, TC-02 to TC-12, including:
- ROC date parsing (AC-05, AC-14, TC-02, TC-09)
- Area passthrough m² stored as-is (AC-06, AC-15, TC-03, TC-10)
- Unit price passthrough TWD/m² stored as-is (AC-07, AC-16, TC-03, TC-10)
- Floor raw string passthrough (AC-08, TC-04)
- Building age calculation (AC-09, AC-17, TC-05, TC-11)
- Parking three-state logic (AC-10, AC-18, TC-06, TC-07, TC-12)
"""

from datetime import date
from decimal import Decimal

from etl.transform import (
    parse_area_sqm,
    parse_building_age,
    parse_has_parking,
    parse_price_per_sqm,
    parse_price_total,
    parse_transaction_date,
)

# ─────────────────────────────────────────────────────────────────────────────
# parse_transaction_date  (AC-05, AC-14, TC-02, TC-09)
# ─────────────────────────────────────────────────────────────────────────────


class TestParseTransactionDate:
    """Tests for ROC-to-Gregorian date conversion."""

    def test_normal_date_1130515(self) -> None:
        """TC-02 AC-05: 1130515 → 2024-05-15."""
        assert parse_transaction_date("1130515") == date(2024, 5, 15)

    def test_normal_date_1120101(self) -> None:
        """TC-02 AC-05: 1120101 → 2023-01-01."""
        assert parse_transaction_date("1120101") == date(2023, 1, 1)

    def test_unknown_sentinel_returns_none(self) -> None:
        """AC-14 TC-09 列B: '0000000' (日期不詳) → None."""
        assert parse_transaction_date("0000000") is None

    def test_empty_string_returns_none(self) -> None:
        """AC-14 TC-09 列A: empty string → None."""
        assert parse_transaction_date("") is None

    def test_non_digit_returns_none(self) -> None:
        """AC-14: non-7-digit string → None."""
        assert parse_transaction_date("abc1234") is None

    def test_short_string_returns_none(self) -> None:
        """AC-14: string shorter than 7 chars → None."""
        assert parse_transaction_date("11305") is None

    def test_invalid_date_components_returns_none(self) -> None:
        """AC-14: 7-digit string with invalid month 99 → None."""
        assert parse_transaction_date("1139999") is None

    def test_whitespace_stripped(self) -> None:
        """Leading/trailing whitespace is stripped before parsing."""
        assert parse_transaction_date("  1130515  ") == date(2024, 5, 15)


# ─────────────────────────────────────────────────────────────────────────────
# parse_area_sqm  (AC-06, AC-15, TC-03, TC-10)
# ─────────────────────────────────────────────────────────────────────────────


class TestParseAreaSqm:
    """Tests for parse_area_sqm — stores raw m² value, no unit conversion.

    TC-03 訂正依據（決策 1）：
        來源值 66.10 m²，DB 直接存平方公尺原始值。
        area_sqm = 66.10（±0.01 容差）
        坪換算為前端責任：66.10 ÷ 3.305785 ≈ 19.995 坪。
    """

    def test_normal_passthrough(self) -> None:
        """TC-03 AC-06: 66.10 m² stored as-is → 66.10 (±0.01)."""
        result = parse_area_sqm("66.10")
        assert result is not None
        assert abs(result - Decimal("66.10")) <= Decimal("0.01")

    def test_precision_two_decimal_places(self) -> None:
        """Result is quantized to 2 decimal places."""
        result = parse_area_sqm("66.10")
        assert result is not None
        decimal_places = len(str(result).split(".")[-1]) if "." in str(result) else 0
        assert decimal_places <= 2

    def test_empty_string_returns_none(self) -> None:
        """AC-15 TC-10: empty string → None."""
        assert parse_area_sqm("") is None

    def test_non_numeric_returns_none(self) -> None:
        """AC-15 TC-10: '--' → None."""
        assert parse_area_sqm("--") is None

    def test_whitespace_string_returns_none(self) -> None:
        """Whitespace-only → None."""
        assert parse_area_sqm("   ") is None

    def test_zero_area(self) -> None:
        """0 m² → 0.00."""
        result = parse_area_sqm("0")
        assert result == Decimal("0.00")


# ─────────────────────────────────────────────────────────────────────────────
# parse_price_per_sqm  (AC-07, AC-16, TC-03, TC-10)
# ─────────────────────────────────────────────────────────────────────────────


class TestParsePricePerSqm:
    """Tests for parse_price_per_sqm — stores raw TWD/m² value, no unit conversion.

    TC-03 訂正依據（決策 1）：
        來源值 290000 元/m²，DB 直接存平方公尺原始值。
        price_per_sqm = 290000.00
        坪換算為前端責任：290000 × 3.305785 ≈ 958678 元/坪。
    """

    def test_normal_passthrough(self) -> None:
        """TC-03 AC-07: 290000 TWD/m² stored as-is → 290000.00."""
        result = parse_price_per_sqm("290000")
        assert result is not None
        assert result == Decimal("290000.00")

    def test_empty_string_returns_none(self) -> None:
        """AC-16 TC-10: empty string → None."""
        assert parse_price_per_sqm("") is None

    def test_non_numeric_returns_none(self) -> None:
        """AC-16 TC-10: non-numeric → None."""
        assert parse_price_per_sqm("N/A") is None

    def test_zero_price(self) -> None:
        """0 TWD/m² → 0.00."""
        result = parse_price_per_sqm("0")
        assert result == Decimal("0.00")


# ─────────────────────────────────────────────────────────────────────────────
# parse_price_total  (AC-11)
# ─────────────────────────────────────────────────────────────────────────────


class TestParsePriceTotal:
    """Tests for total price parsing."""

    def test_normal_price(self) -> None:
        """AC-11: integer price string → Decimal."""
        assert parse_price_total("6000000") == Decimal("6000000")

    def test_empty_returns_none(self) -> None:
        """Empty string → None."""
        assert parse_price_total("") is None

    def test_non_numeric_returns_none(self) -> None:
        """Non-numeric → None."""
        assert parse_price_total("abc") is None


# ─────────────────────────────────────────────────────────────────────────────
# parse_building_age  (AC-09, AC-17, TC-05, TC-11)
# ─────────────────────────────────────────────────────────────────────────────


class TestParseBuildingAge:
    """Tests for building age calculation."""

    def test_normal_age_dynamic(self) -> None:
        """TC-05 AC-09: completion 0920630 (year 2003) → current_year - 2003."""
        current_year = 2026
        result = parse_building_age("0920630", current_year)
        assert result == current_year - 2003  # = 23 for 2026

    def test_age_ignores_month_day(self) -> None:
        """AC-09: only year component is used; month/day are ignored."""
        # Same year, different months — should yield the same age
        result_jan = parse_building_age("0920101", 2026)
        result_dec = parse_building_age("0921231", 2026)
        assert result_jan == result_dec == 2026 - 2003

    def test_empty_string_returns_none(self) -> None:
        """AC-17 TC-11: empty string → None."""
        assert parse_building_age("", 2026) is None

    def test_unparseable_returns_none(self) -> None:
        """AC-17 TC-11: '不詳' → None."""
        assert parse_building_age("不詳", 2026) is None

    def test_negative_age_returns_none(self) -> None:
        """AC-09: future completion year yields negative age → None."""
        # Completion year 2027 with current_year 2026 → age -1 → None
        assert parse_building_age("1160101", 2026) is None

    def test_zero_age(self) -> None:
        """Completion year == current_year → age 0 (not None)."""
        result = parse_building_age("1150101", 2026)
        assert result == 0

    def test_short_input_returns_none(self) -> None:
        """Input shorter than 3 digits → None."""
        assert parse_building_age("09", 2026) is None

    def test_unknown_sentinel_returns_none(self) -> None:
        """AC-17: '0000000' (日期不詳 sentinel) must not be parsed as a valid
        completion date; should return None instead of a false building_age
        (e.g. completion_year=1911).
        """
        assert parse_building_age("0000000", 2026) is None


# ─────────────────────────────────────────────────────────────────────────────
# parse_has_parking  (AC-10, AC-18, TC-06, TC-07, TC-12)
# ─────────────────────────────────────────────────────────────────────────────


class TestParseHasParking:
    """Tests for three-state parking derivation."""

    def test_has_parking_by_type(self) -> None:
        """TC-06 AC-10: non-empty non-'無' type → True."""
        assert parse_has_parking("坡道平面", "1500000") is True

    def test_has_parking_type_only(self) -> None:
        """AC-10: valid parking type with zero price → True."""
        assert parse_has_parking("坡道平面", "0") is True

    def test_no_parking(self) -> None:
        """TC-07 AC-10: 車位類別='無', 車位總價=0 → False."""
        assert parse_has_parking("無", "0") is False

    def test_no_parking_empty_price(self) -> None:
        """AC-10: 車位類別='無', 車位總價='' → False."""
        assert parse_has_parking("無", "") is False

    def test_null_both_empty(self) -> None:
        """AC-18 TC-12: both fields empty → None."""
        assert parse_has_parking("", "") is None

    def test_null_both_missing(self) -> None:
        """AC-18 TC-12: both fields whitespace → None."""
        assert parse_has_parking("  ", "  ") is None

    def test_has_parking_by_price_only(self) -> None:
        """AC-10: empty type but positive price → True."""
        assert parse_has_parking("", "500000") is True

    def test_has_parking_explicit_type_with_price(self) -> None:
        """AC-10: 車位總價 > 0 always → True regardless of type."""
        assert parse_has_parking("無", "1") is True
