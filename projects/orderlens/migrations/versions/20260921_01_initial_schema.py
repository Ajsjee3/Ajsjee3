"""OrderLens의 첫 스키마를 생성합니다.

Revision ID: 20260921_01
Revises:
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260921_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted", sa.Integer(), nullable=False),
        sa.Column("duplicates", sa.Integer(), nullable=False),
        sa.Column("rejected", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_runs"),
    )
    op.create_table(
        "order_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("order_id", sa.String(length=80), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("promised_by", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("amount_krw", sa.BigInteger(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["ingestion_runs.id"],
            name="fk_order_snapshots_run_id_ingestion_runs",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_order_snapshots"),
        sa.UniqueConstraint(
            "source",
            "order_id",
            "revision",
            name="uq_order_revision",
        ),
    )
    op.create_index(
        "ix_snapshot_updated",
        "order_snapshots",
        ["updated_at"],
        unique=False,
    )
    op.create_table(
        "rejected_rows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["ingestion_runs.id"],
            name="fk_rejected_rows_run_id_ingestion_runs",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_rejected_rows"),
    )


def downgrade() -> None:
    op.drop_table("rejected_rows")
    op.drop_index("ix_snapshot_updated", table_name="order_snapshots")
    op.drop_table("order_snapshots")
    op.drop_table("ingestion_runs")
