"""공개 거래의 파일 출처와 정제 행을 별도 테이블에 저장합니다.

Revision ID: 20261005_02
Revises: 20260921_01
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261005_02"
down_revision: str | None = "20260921_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retail_imports",
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("accepted_output_sha256", sa.String(length=64), nullable=False),
        sa.Column("rejected_output_sha256", sa.String(length=64), nullable=False),
        sa.Column("dataset", sa.String(length=120), nullable=False),
        sa.Column("dataset_url", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("license", sa.String(length=50), nullable=True),
        sa.Column("provenance_scope", sa.String(length=40), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source_rows", sa.Integer(), nullable=False),
        sa.Column("accepted_rows", sa.Integer(), nullable=False),
        sa.Column("rejected_rows", sa.Integer(), nullable=False),
        sa.Column("cancellation_rows", sa.Integer(), nullable=False),
        sa.Column("accepted_signed_line_amount", sa.Numeric(precision=38, scale=6), nullable=False),
        sa.Column(
            "cancellation_signed_line_amount",
            sa.Numeric(precision=38, scale=6),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("source_sha256", name="pk_retail_imports"),
    )
    op.create_table(
        "retail_lines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_record", sa.Integer(), nullable=False),
        sa.Column("invoice_no", sa.String(length=120), nullable=False),
        sa.Column("stock_code", sa.String(length=120), nullable=False),
        sa.Column("invoice_at_local", sa.DateTime(timezone=False), nullable=False),
        sa.Column("invoice_timezone", sa.String(length=40), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=16, scale=6), nullable=False),
        sa.Column("line_amount", sa.Numeric(precision=26, scale=6), nullable=False),
        sa.Column("is_cancellation", sa.Boolean(), nullable=False),
        sa.Column("country", sa.String(length=120), nullable=False),
        sa.Column("quality_flags", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_sha256"],
            ["retail_imports.source_sha256"],
            name="fk_retail_lines_source_sha256_retail_imports",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_retail_lines"),
        sa.UniqueConstraint(
            "source_sha256",
            "source_record",
            name="uq_retail_source_record",
        ),
    )


def downgrade() -> None:
    op.drop_table("retail_lines")
    op.drop_table("retail_imports")
