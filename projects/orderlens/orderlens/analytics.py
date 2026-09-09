"""주문별 최신 버전을 SQL 윈도 함수로 고른 뒤 운영 지표를 계산합니다."""

from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from orderlens.models import IngestionRun, OrderSnapshot, RejectedRow
from orderlens.schemas import OrderSource


def latest_orders(as_of: datetime, start_at=None, end_at=None):
    table = OrderSnapshot.__table__
    ranked = (
        select(
            *table.c,
            func.row_number()
            .over(
                partition_by=(table.c.source, table.c.order_id),
                order_by=table.c.revision.desc(),
            )
            .label("version_rank"),
        )
        .where(table.c.updated_at <= as_of)
        .subquery("ranked_orders")
    )
    query = select(ranked).where(ranked.c.version_rank == 1)
    if start_at is not None:
        query = query.where(ranked.c.placed_at >= start_at)
    if end_at is not None:
        query = query.where(ranked.c.placed_at < end_at)
    return query.subquery("latest_orders")


def aggregate_columns(current, as_of):
    c = current.c
    active = c.status.in_(["paid", "shipped"])
    delivered = c.status == "delivered"

    def count_if(predicate, name):
        return func.coalesce(func.sum(case((predicate, 1), else_=0)), 0).label(name)

    return [
        func.count().label("total_orders"),
        count_if(active, "active_orders"),
        count_if(delivered, "delivered_orders"),
        count_if(c.status == "cancelled", "cancelled_orders"),
        count_if(c.status == "refunded", "refunded_orders"),
        count_if(active & (c.promised_by < as_of), "overdue_open_orders"),
        count_if(delivered & (c.delivered_at > c.promised_by), "late_delivered_orders"),
        func.coalesce(
            func.sum(
                case(
                    (c.status.in_(["paid", "shipped", "delivered"]), c.amount_krw),
                    else_=0,
                )
            ),
            0,
        ).label("booked_amount_krw"),
    ]


def decorate_counts(row):
    result = {key: int(value) for key, value in row.items() if key != "source"}
    denominator = result["delivered_orders"]
    result["late_delivery_rate"] = (
        round(result["late_delivered_orders"] / denominator, 6) if denominator else None
    )
    return result


def metrics(session: Session, as_of: datetime, start_at=None, end_at=None) -> dict:
    current = latest_orders(as_of, start_at, end_at)
    columns = aggregate_columns(current, as_of)
    summary = session.execute(select(*columns).select_from(current)).mappings().one()
    groups = session.execute(
        select(current.c.source, *columns)
        .select_from(current)
        .group_by(current.c.source)
        .order_by(current.c.source)
    ).mappings()
    return {
        "as_of": as_of.isoformat(),
        "start_at": start_at.isoformat() if start_at else None,
        "end_at_exclusive": end_at.isoformat() if end_at else None,
        "currency": "KRW",
        "summary": decorate_counts(summary),
        "by_source": [{"source": group["source"], **decorate_counts(group)} for group in groups],
    }


def attention_orders(
    session: Session, as_of: datetime, limit=20, source: OrderSource | None = None
) -> list[dict]:
    current = latest_orders(as_of)
    query = (
        select(
            current.c.source,
            current.c.order_id,
            current.c.status,
            current.c.promised_by,
            current.c.amount_krw,
        )
        .where(
            current.c.status.in_(["paid", "shipped"]),
            current.c.promised_by < as_of,
        )
    )
    if source is not None:
        # 원하는 경로를 먼저 고른 뒤 limit을 적용해야 다른 경로가 조회 한도를 차지하지 않습니다.
        query = query.where(current.c.source == source)
    rows = session.execute(
        query.order_by(current.c.promised_by, current.c.source, current.c.order_id).limit(limit)
    ).mappings()
    return [dict(row) for row in rows]


def quality_summary(session: Session) -> dict:
    counters = (
        session.execute(
            select(
                func.count(IngestionRun.id).label("runs"),
                func.coalesce(func.sum(IngestionRun.accepted), 0).label("accepted"),
                func.coalesce(func.sum(IngestionRun.duplicates), 0).label("duplicates"),
                func.coalesce(func.sum(IngestionRun.rejected), 0).label("rejected"),
            )
        )
        .mappings()
        .one()
    )
    reasons = session.execute(
        select(
            RejectedRow.code,
            func.count().label("count"),
        )
        .group_by(RejectedRow.code)
        .order_by(RejectedRow.code)
    ).mappings()
    return {
        "scope": "ingestion_attempts_not_unique_bad_orders",
        **dict(counters),
        "rejections_by_code": [dict(row) for row in reasons],
    }
