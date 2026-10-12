"""공개 거래의 출처 단위를 보존한 기간 집계를 제공합니다."""

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from orderlens.models import RetailLine

RETAIL_QUERY_INDEX = "ix_retail_country_cancelled_time"


class RetailQueryError(ValueError):
    pass


@dataclass(frozen=True)
class RetailSummary:
    country: str
    start_at_local: datetime
    end_at_local_exclusive: datetime
    currency: str
    line_count: int
    quantity: int
    signed_line_amount: Decimal

    def to_dict(self) -> dict:
        return asdict(self)


def validate_retail_period(country: str, start_at: datetime, end_at: datetime) -> str:
    if not isinstance(country, str) or not country.strip() or len(country.strip()) > 120:
        raise RetailQueryError("country는 1~120자의 문자열이어야 합니다.")
    if not isinstance(start_at, datetime) or not isinstance(end_at, datetime):
        raise RetailQueryError("조회 기간은 datetime이어야 합니다.")
    if start_at.tzinfo is not None or end_at.tzinfo is not None:
        raise RetailQueryError("원천 시간대가 없으므로 조회 시각에도 시간대를 붙이지 않습니다.")
    if start_at >= end_at:
        raise RetailQueryError("start_at은 end_at보다 빨라야 합니다.")
    return country.strip()


def retail_summary_statement(country: str, start_at: datetime, end_at: datetime):
    country = validate_retail_period(country, start_at, end_at)
    return select(
        func.count(RetailLine.id).label("line_count"),
        func.sum(RetailLine.quantity).label("quantity"),
        func.sum(RetailLine.line_amount).label("signed_line_amount"),
    ).where(
        RetailLine.country == country,
        RetailLine.is_cancellation.is_(False),
        RetailLine.invoice_at_local >= start_at,
        RetailLine.invoice_at_local < end_at,
    )


def retail_summary(
    session: Session,
    country: str,
    start_at: datetime,
    end_at: datetime,
) -> RetailSummary:
    """취소 표시 행을 제외하고 [start_at, end_at) 구간을 집계합니다."""

    country = validate_retail_period(country, start_at, end_at)
    row = session.execute(
        retail_summary_statement(country, start_at, end_at)
    ).mappings().one()
    return RetailSummary(
        country=country,
        start_at_local=start_at,
        end_at_local_exclusive=end_at,
        currency="GBP",
        line_count=int(row["line_count"]),
        quantity=int(row["quantity"] or 0),
        signed_line_amount=row["signed_line_amount"] or Decimal("0"),
    )
