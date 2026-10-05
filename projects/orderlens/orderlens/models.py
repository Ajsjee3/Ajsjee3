from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from orderlens.db import Base, UTCDateTime, utc_now


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    accepted: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    rejected: Mapped[int] = mapped_column(Integer, default=0)


class OrderSnapshot(Base):
    __tablename__ = "order_snapshots"
    __table_args__ = (
        UniqueConstraint("source", "order_id", "revision", name="uq_order_revision"),
        Index("ix_snapshot_updated", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("ingestion_runs.id"))
    source: Mapped[str] = mapped_column(String(30))
    order_id: Mapped[str] = mapped_column(String(80))
    revision: Mapped[int] = mapped_column(Integer)
    placed_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    promised_by: Mapped[datetime] = mapped_column(UTCDateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    amount_krw: Mapped[int] = mapped_column(BigInteger)
    fingerprint: Mapped[str] = mapped_column(String(64))


class RejectedRow(Base):
    __tablename__ = "rejected_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("ingestion_runs.id"))
    row_number: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(40))
    issues: Mapped[list] = mapped_column(JSON)


class RetailImport(Base):
    """정제 결과 한 벌의 출처와 행 수를 파일 해시로 식별합니다."""

    __tablename__ = "retail_imports"

    source_sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    accepted_output_sha256: Mapped[str] = mapped_column(String(64))
    rejected_output_sha256: Mapped[str] = mapped_column(String(64))
    dataset: Mapped[str] = mapped_column(String(120))
    dataset_url: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    license: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provenance_scope: Mapped[str] = mapped_column(String(40))
    currency: Mapped[str] = mapped_column(String(3))
    source_rows: Mapped[int] = mapped_column(Integer)
    accepted_rows: Mapped[int] = mapped_column(Integer)
    rejected_rows: Mapped[int] = mapped_column(Integer)
    cancellation_rows: Mapped[int] = mapped_column(Integer)
    accepted_signed_line_amount: Mapped[Decimal] = mapped_column(Numeric(38, 6))
    cancellation_signed_line_amount: Mapped[Decimal] = mapped_column(Numeric(38, 6))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)


class RetailLine(Base):
    """UCI 거래 CSV의 한 레코드를 원본 파일 위치와 함께 보존합니다."""

    __tablename__ = "retail_lines"
    __table_args__ = (
        UniqueConstraint(
            "source_sha256",
            "source_record",
            name="uq_retail_source_record",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_sha256: Mapped[str] = mapped_column(ForeignKey("retail_imports.source_sha256"))
    source_record: Mapped[int] = mapped_column(Integer)
    invoice_no: Mapped[str] = mapped_column(String(120))
    stock_code: Mapped[str] = mapped_column(String(120))
    invoice_at_local: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    invoice_timezone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(16, 6))
    line_amount: Mapped[Decimal] = mapped_column(Numeric(26, 6))
    is_cancellation: Mapped[bool] = mapped_column(Boolean)
    country: Mapped[str] = mapped_column(String(120))
    quality_flags: Mapped[list] = mapped_column(JSON)
