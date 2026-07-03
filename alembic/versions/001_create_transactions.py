"""Create transactions table.

Revision ID: 001
Revises:
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from geoalchemy2 import Geometry

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the transactions table with all required columns and indexes."""
    op.create_table(
        "transactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("city", sa.VARCHAR(10), nullable=True),
        sa.Column("district", sa.VARCHAR(20), nullable=True),
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("price_total", sa.Numeric(14, 0), nullable=True),
        sa.Column("price_per_sqm", sa.Numeric(12, 2), nullable=True),
        sa.Column("area_sqm", sa.Numeric(8, 2), nullable=True),
        # floor is VARCHAR(10): raw 實價登錄 strings such as '3F', 'B1',
        # 'B全', '全', '頂層'. SMALLINT cannot represent these values.
        sa.Column("floor", sa.VARCHAR(10), nullable=True),
        sa.Column("building_age", sa.SmallInteger(), nullable=True),
        sa.Column("building_type", sa.VARCHAR(20), nullable=True),
        sa.Column("has_parking", sa.Boolean(), nullable=True),
        sa.Column("mrt_distance", sa.Numeric(8, 1), nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for common query patterns
    op.create_index(
        "ix_transactions_city",
        "transactions",
        ["city"],
    )
    op.create_index(
        "ix_transactions_district",
        "transactions",
        ["district"],
    )
    op.create_index(
        "ix_transactions_transaction_date",
        "transactions",
        ["transaction_date"],
    )
    op.create_index(
        "ix_transactions_city_district",
        "transactions",
        ["city", "district"],
    )
    # Spatial index for PostGIS queries
    op.create_index(
        "ix_transactions_location",
        "transactions",
        ["location"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    """Drop the transactions table and all associated indexes."""
    op.drop_index("ix_transactions_location", table_name="transactions")
    op.drop_index("ix_transactions_city_district", table_name="transactions")
    op.drop_index("ix_transactions_transaction_date", table_name="transactions")
    op.drop_index("ix_transactions_district", table_name="transactions")
    op.drop_index("ix_transactions_city", table_name="transactions")
    op.drop_table("transactions")
