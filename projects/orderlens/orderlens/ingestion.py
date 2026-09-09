"""검증 → 버전 중복 확인 → 적재 → 실패 내역 기록을 한 트랜잭션으로 처리합니다."""

import hashlib
import json
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from orderlens.models import IngestionRun, OrderSnapshot, RejectedRow
from orderlens.schemas import OrderInput


def fingerprint(record: OrderInput) -> str:
    payload = json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def existing_revision(session: Session, record: OrderInput):
    return session.scalar(
        select(OrderSnapshot).where(
            OrderSnapshot.source == record.source,
            OrderSnapshot.order_id == record.order_id,
            OrderSnapshot.revision == record.revision,
        )
    )


def run_summary(session: Session, run: IngestionRun) -> dict:
    rejected = session.scalars(
        select(RejectedRow)
        .where(
            RejectedRow.run_id == run.id,
        )
        .order_by(RejectedRow.row_number)
    ).all()
    return {
        "run_id": run.id,
        "accepted": run.accepted,
        "duplicates": run.duplicates,
        "rejected": run.rejected,
        "row_count": run.accepted + run.duplicates + run.rejected,
        "errors": [
            {"row_number": row.row_number, "code": row.code, "issues": row.issues}
            for row in rejected
        ],
    }


def ingest(session: Session, rows: list[dict]) -> dict:
    run = IngestionRun(id=str(uuid4()), accepted=0, duplicates=0, rejected=0)
    with session.begin():
        session.add(run)
        session.flush()
        for number, raw in enumerate(rows, start=1):
            try:
                record = OrderInput.model_validate(raw)
            except ValidationError as error:
                # 원문 입력은 저장하지 않습니다. 오류 위치로 원본 행을 찾아 고칩니다.
                issues = [
                    {"field": ".".join(map(str, item["loc"])), "type": item["type"]}
                    for item in error.errors(include_input=False, include_url=False)
                ]
                reject(session, run, number, "schema_error", issues)
                continue

            digest = fingerprint(record)
            existing = existing_revision(session, record)
            if existing is None:
                try:
                    # 동시 요청도 DB의 UNIQUE 제약으로 최종 중복을 막습니다.
                    with session.begin_nested():
                        session.add(
                            OrderSnapshot(
                                run_id=run.id,
                                fingerprint=digest,
                                **record.model_dump(),
                            )
                        )
                        session.flush()
                    run.accepted += 1
                    continue
                except IntegrityError:
                    existing = existing_revision(session, record)
                    if existing is None:
                        raise

            if existing.fingerprint == digest:
                run.duplicates += 1
            else:
                reject(
                    session,
                    run,
                    number,
                    "revision_conflict",
                    [
                        {
                            "field": "revision",
                            "type": "same_version_different_content",
                        }
                    ],
                )
        session.flush()
        result = run_summary(session, run)
    return result


def reject(session, run, number, code, issues):
    run.rejected += 1
    session.add(RejectedRow(run_id=run.id, row_number=number, code=code, issues=issues))
