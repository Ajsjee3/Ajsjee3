"""공개 거래 적재 시도의 상태와 결과를 기록합니다.

Revision ID: 20261019_04
Revises: 20261012_03
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261019_04"
down_revision: str | None = "20261012_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retail_load_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inserted_rows", sa.Integer(), nullable=False),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_retail_load_attempt_status",
        ),
        sa.CheckConstraint(
            "result IS NULL OR result IN ('loaded', 'already_loaded')",
            name="ck_retail_load_attempt_result",
        ),
        sa.CheckConstraint(
            "inserted_rows >= 0 AND duplicate_rows >= 0",
            name="ck_retail_load_attempt_counts",
        ),
        sa.CheckConstraint(
            "(status = 'running' AND finished_at IS NULL AND result IS NULL "
            "AND error_code IS NULL AND error_message IS NULL) OR "
            "(status = 'succeeded' AND finished_at IS NOT NULL AND result IS NOT NULL "
            "AND error_code IS NULL AND error_message IS NULL) OR "
            "(status = 'failed' AND finished_at IS NOT NULL AND result IS NULL "
            "AND error_code IS NOT NULL AND error_message IS NOT NULL)",
            name="ck_retail_load_attempt_terminal_fields",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_retail_load_attempts"),
    )
    op.create_index(
        "ix_retail_load_attempt_source_started",
        "retail_load_attempts",
        ["source_sha256", "started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retail_load_attempt_source_started",
        table_name="retail_load_attempts",
    )
    op.drop_table("retail_load_attempts")
