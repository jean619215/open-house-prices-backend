"""Alter building_type column from VARCHAR(20) to TEXT.

Revision ID: 002
Revises: 001
Create Date: 2026-06-22

Background:
    實價登錄 來源「建物型態」字串（如「公寓(5樓含以下無電梯)」）可能超過 20 字元。
    改為 TEXT 無長度限制，消除截斷風險。
    決策來源：需求方 2026-06-22 決策 2（選 B：改 TEXT）。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Alter building_type from VARCHAR(20) to TEXT."""
    op.alter_column(
        "transactions",
        "building_type",
        existing_type=sa.VARCHAR(20),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert building_type from TEXT back to VARCHAR(20)."""
    op.alter_column(
        "transactions",
        "building_type",
        existing_type=sa.Text(),
        type_=sa.VARCHAR(20),
        existing_nullable=True,
    )
