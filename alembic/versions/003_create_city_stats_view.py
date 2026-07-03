"""Create city_stats materialized view.

Revision ID: 003
Revises: 002
Create Date: 2026-07-03

Background:
    TASK-003：地圖縣市層級均價 API（GET /api/prices/city）。依 Notion「房地產
    交易地圖」系統規劃，對 transactions 依 city 分組預先算好均價與成交筆數，
    API 端點直接查詢這個 view，不對 transactions 做即時 GROUP BY。

    技術判斷（見 TASK-003 AC-06、AC-07）：
    - avg_price_per_sqm 以 ROUND(AVG(price_per_sqm), 2) 計算，對齊
      transactions.price_per_sqm 的 Numeric(12, 2) 來源精度。
    - price_per_sqm IS NULL 的列不計入均價分母，但仍計入 transaction_count
      （COUNT(*) 而非 COUNT(price_per_sqm)）。
    - city IS NULL 的列排除在分組之外（WHERE city IS NOT NULL），確保
      city_stats 不會出現 city IS NULL 的分組列。
    - 使用 CREATE MATERIALIZED VIEW ... WITH DATA（而非 WITH NO DATA），
      確保 migration 執行完當下 view 即為已 populate 狀態（即使當時
      transactions 為空、結果為 0 列），避免全新環境在第一次 ETL 執行前
      呼叫 API 就先撞到 PostgreSQL「materialized view has not been
      populated」錯誤而回傳 500。
    - 額外建立 city 唯一索引：一方面加速 API 依 city 排序查詢，一方面為
      後續若改用 REFRESH MATERIALIZED VIEW CONCURRENTLY（見 AC-11 理由）
      預先鋪路（該指令要求 view 上至少有一個唯一索引）。
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the city_stats materialized view (populated, WITH DATA)."""
    op.execute(
        """
        CREATE MATERIALIZED VIEW city_stats AS
        SELECT
            city,
            ROUND(AVG(price_per_sqm), 2) AS avg_price_per_sqm,
            COUNT(*) AS transaction_count
        FROM transactions
        WHERE city IS NOT NULL
        GROUP BY city
        WITH DATA
        """
    )
    op.execute("CREATE UNIQUE INDEX ix_city_stats_city ON city_stats (city)")


def downgrade() -> None:
    """Drop the city_stats materialized view (and its index, via cascade)."""
    op.execute("DROP MATERIALIZED VIEW city_stats")
