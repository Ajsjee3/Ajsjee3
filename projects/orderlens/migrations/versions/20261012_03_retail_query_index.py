"""국가·취소 여부·거래 시각 조건의 공개 거래 집계 인덱스를 추가합니다.

Revision ID: 20261012_03
Revises: 20261005_02
Create Date: 2026-10-12
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261012_03"
down_revision: str | None = "20261005_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_retail_country_cancelled_time",
        "retail_lines",
        ["country", "is_cancellation", "invoice_at_local"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_retail_country_cancelled_time", table_name="retail_lines")
