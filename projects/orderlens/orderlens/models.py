from datetime import datetime

from sqlalchemy import JSON, BigInteger, ForeignKey, Index, Integer, String, UniqueConstraint
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
