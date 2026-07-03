"""SQLAlchemy ORM models for the application.

Defines the Transaction model corresponding to the transactions table.
"""

from datetime import date, datetime
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class Transaction(Base):
    """Real-estate transaction record from 實價登錄 (actual price registration).

    Attributes:
        id: Auto-incremented primary key.
        address: Full address string.
        city: City name (e.g. 台北市).
        district: District name (e.g. 大安區).
        location: PostGIS Point geometry in SRID 4326.
        price_total: Total transaction price in TWD (New Taiwan Dollar).
        price_per_sqm: Unit price per square metre (m²) in TWD, stored as the
            source raw value (元/平方公尺). No ping (坪) conversion is
            performed; that is the frontend's responsibility (決策 1,
            2026-06-22).
        area_sqm: Building area in square metres (m²), stored as the source
            raw value. No ping (坪) conversion is performed; that is the
            frontend's responsibility (決策 1, 2026-06-22).
        floor: Floor description as raw string from 實價登錄 source data.
            Stored as VARCHAR(10) to preserve values like '全', 'B1', 'B全',
            '頂層', '3F', etc. Numeric parsing is deferred to query time.
        building_age: Age of the building in years.
        building_type: Building type description.
        has_parking: Whether a parking space is included.
        mrt_distance: Distance to nearest MRT station in metres.
        transaction_date: Full transaction date (ROC date converted to
            Gregorian, e.g. 民國 1130515 → 2024-05-15), not truncated to
            the 1st of the month.
        created_at: Record creation timestamp (UTC).
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str | None] = mapped_column(String(10), nullable=True)
    district: Mapped[str | None] = mapped_column(String(20), nullable=True)
    location: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    price_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 0), nullable=True)
    price_per_sqm: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    # floor: VARCHAR(10) — stores raw 實價登錄 strings such as '3F', 'B1',
    # 'B全', '全', '頂層'. SMALLINT cannot represent these values; parsing is
    # done at query/ETL time. See TASK-001 歷程 for full rationale.
    floor: Mapped[str | None] = mapped_column(String(10), nullable=True)
    building_age: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    building_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_parking: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mrt_distance: Mapped[Decimal | None] = mapped_column(Numeric(8, 1), nullable=True)
    transaction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
