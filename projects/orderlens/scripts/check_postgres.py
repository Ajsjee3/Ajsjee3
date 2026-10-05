"""비어 있는 PostgreSQL에서 마이그레이션, 주문 API와 공개 거래 적재를 검증합니다."""

import csv
import json
import os
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

import orderlens.models  # noqa: F401
from orderlens.config import Settings
from orderlens.db import Base, make_engine
from orderlens.main import create_app
from orderlens.migrations import (
    check_model_matches_database,
    current_revision,
    downgrade_database,
    head_revision,
    require_current_schema,
    upgrade_database,
)
from orderlens.models import RetailImport, RetailLine
from orderlens.retail import COLUMNS, transform_file
from orderlens.retail_db import load_retail_output
from scripts.generate_demo import AS_OF, generate_rows


def required_test_url() -> str:
    database_url = os.getenv("ORDERLENS_POSTGRES_TEST_URL")
    if not database_url:
        raise RuntimeError("ORDERLENS_POSTGRES_TEST_URL이 필요합니다.")
    parsed = make_url(database_url)
    if not parsed.drivername.startswith("postgresql"):
        raise RuntimeError("PostgreSQL 테스트 URL만 허용합니다.")
    if not (parsed.database or "").endswith("_test"):
        raise RuntimeError("실수로 운영 DB를 지우지 않도록 이름이 _test로 끝나야 합니다.")
    return database_url


def read_all_pages(client: TestClient, limit: int = 17) -> list[tuple[str, str]]:
    seen = []
    offset = 0
    for _ in range(20):
        response = client.get(
            "/v1/orders",
            params={"as_of": AS_OF, "limit": limit, "offset": offset},
        )
        response.raise_for_status()
        page = response.json()
        seen.extend((row["source"], row["order_id"]) for row in page["orders"])
        if not page["has_more"]:
            if page["next_offset"] is not None:
                raise AssertionError("마지막 PostgreSQL 페이지의 next_offset이 null이 아닙니다.")
            return seen
        offset = page["next_offset"]
    raise AssertionError("PostgreSQL 주문 목록의 마지막 페이지에 도달하지 못했습니다.")


def main() -> None:
    database_url = required_test_url()
    expected_tables = set(Base.metadata.tables)
    engine = make_engine(database_url)
    try:
        before = set(inspect(engine).get_table_names()) - {"alembic_version"}
        if before:
            raise RuntimeError(f"비어 있는 전용 테스트 DB가 필요합니다: {sorted(before)}")
    finally:
        engine.dispose()

    upgrade_database(database_url)
    check_model_matches_database(database_url)
    engine = make_engine(database_url)
    try:
        revision = require_current_schema(engine)
        inspector = inspect(engine)
        created_tables = set(inspector.get_table_names())
        if not expected_tables <= created_tables:
            raise AssertionError("PostgreSQL에 필요한 테이블이 모두 생성되지 않았습니다.")
        timestamp_columns = {
            column["name"]: column for column in inspector.get_columns("order_snapshots")
        }
        if not timestamp_columns["updated_at"]["type"].timezone:
            raise AssertionError("PostgreSQL updated_at이 time zone 정보를 보존하지 않습니다.")
        retail_columns = {
            column["name"]: column for column in inspector.get_columns("retail_lines")
        }
        if (
            retail_columns["unit_price"]["type"].precision,
            retail_columns["unit_price"]["type"].scale,
        ) != (16, 6):
            raise AssertionError("PostgreSQL 공개 거래 단가가 NUMERIC(16, 6)이 아닙니다.")
        if (
            retail_columns["line_amount"]["type"].precision,
            retail_columns["line_amount"]["type"].scale,
        ) != (26, 6):
            raise AssertionError("PostgreSQL 공개 거래 금액이 NUMERIC(26, 6)이 아닙니다.")
        if retail_columns["invoice_at_local"]["type"].timezone:
            raise AssertionError("원천에 없는 공개 거래 시간대가 추가됐습니다.")
        retail_constraints = inspector.get_unique_constraints("retail_lines")
        if not any(item["name"] == "uq_retail_source_record" for item in retail_constraints):
            raise AssertionError("공개 거래의 파일 해시·레코드 번호 UNIQUE 제약이 없습니다.")
        server_version = ".".join(map(str, engine.dialect.server_version_info))
    finally:
        engine.dispose()

    app = create_app(Settings(database_url=database_url, api_key="orderlens-postgres-ci-key"))
    with TestClient(app, headers={"X-API-Key": "orderlens-postgres-ci-key"}) as client:
        health = client.get("/health")
        health.raise_for_status()
        payload = {"rows": generate_rows()}
        first = client.post("/v1/ingestions", json=payload)
        first.raise_for_status()
        metrics_before = client.get("/v1/metrics", params={"as_of": AS_OF})
        metrics_before.raise_for_status()
        seen = read_all_pages(client)
        replay = client.post("/v1/ingestions", json=payload)
        replay.raise_for_status()
        metrics_after = client.get("/v1/metrics", params={"as_of": AS_OF})
        metrics_after.raise_for_status()

    first_result = first.json()
    replay_result = replay.json()
    summary = metrics_after.json()["summary"]
    if (first_result["accepted"], first_result["duplicates"], first_result["rejected"]) != (
        300,
        5,
        4,
    ):
        raise AssertionError("PostgreSQL 최초 적재 결과가 기준과 다릅니다.")
    if (replay_result["accepted"], replay_result["duplicates"], replay_result["rejected"]) != (
        0,
        305,
        4,
    ):
        raise AssertionError("PostgreSQL 재전송 결과가 기준과 다릅니다.")
    if metrics_before.json() != metrics_after.json() or summary["total_orders"] != 120:
        raise AssertionError("PostgreSQL 재전송 전후 지표가 다릅니다.")
    if len(seen) != 120 or len(set(seen)) != 120:
        raise AssertionError("PostgreSQL 페이지 조회에 중복 또는 누락이 있습니다.")

    with TemporaryDirectory(prefix="orderlens-retail-postgres-") as directory:
        source = Path(directory) / "retail.csv"
        with source.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows([
                {
                    "InvoiceNo": "C123456",
                    "StockCode": "ITEM_A",
                    "Description": "demo cancellation",
                    "Quantity": "-3",
                    "InvoiceDate": "12/1/2010 8:26",
                    "UnitPrice": "0.001",
                    "CustomerID": "",
                    "Country": "United Kingdom",
                },
                {
                    "InvoiceNo": "123457",
                    "StockCode": "ITEM_B",
                    "Description": "demo sale",
                    "Quantity": "2",
                    "InvoiceDate": "12/1/2010 8:27",
                    "UnitPrice": "1.25",
                    "CustomerID": "",
                    "Country": "United Kingdom",
                },
            ])
        output = Path(directory) / "processed"
        transform_file(source, output)
        engine = make_engine(database_url)
        try:
            with Session(engine) as session:
                retail_first = load_retail_output(session, output, batch_size=1)
                retail_replay = load_retail_output(session, output, batch_size=1)
                retail_imports = session.scalar(select(func.count()).select_from(RetailImport))
                retail_lines = session.scalar(select(func.count()).select_from(RetailLine))
                cancellation = session.scalar(
                    select(RetailLine).where(RetailLine.invoice_no == "C123456")
                )
        finally:
            engine.dispose()

    if (retail_first["inserted"], retail_first["duplicates"]) != (2, 0):
        raise AssertionError("PostgreSQL 공개 거래 최초 적재 결과가 다릅니다.")
    if (retail_replay["inserted"], retail_replay["duplicates"]) != (0, 2):
        raise AssertionError("PostgreSQL 공개 거래 재적재 결과가 다릅니다.")
    if (retail_imports, retail_lines) != (1, 2):
        raise AssertionError("PostgreSQL 공개 거래 행 수가 다릅니다.")
    if (
        cancellation.unit_price != Decimal("0.001000")
        or cancellation.line_amount != Decimal("-0.003000")
        or cancellation.invoice_at_local.tzinfo is not None
    ):
        raise AssertionError("PostgreSQL이 GBP 소수 금액·지역 시각을 보존하지 못했습니다.")

    downgrade_database(database_url)
    engine = make_engine(database_url)
    try:
        remaining = set(inspect(engine).get_table_names()) & expected_tables
        if remaining or current_revision(engine) is not None:
            raise AssertionError(f"PostgreSQL downgrade 후 남은 테이블: {sorted(remaining)}")
    finally:
        engine.dispose()
    upgrade_database(database_url)
    engine = make_engine(database_url)
    try:
        revision_after_reupgrade = require_current_schema(engine)
    finally:
        engine.dispose()

    evidence = {
        "database": "ephemeral_postgresql_service",
        "postgresql_version": server_version,
        "head_revision": head_revision(),
        "revision_after_upgrade": revision,
        "created_tables": sorted(expected_tables),
        "timestamp_with_timezone": True,
        "model_matches_migration": True,
        "first_ingestion": {
            key: first_result[key] for key in ("accepted", "duplicates", "rejected")
        },
        "replay": {key: replay_result[key] for key in ("accepted", "duplicates", "rejected")},
        "metrics_unchanged_by_replay": True,
        "total_orders": summary["total_orders"],
        "page_limit": 17,
        "page_count": 8,
        "returned_orders": len(seen),
        "unique_orders": len(set(seen)),
        "retail_import": {
            "first_inserted": retail_first["inserted"],
            "replay_duplicates": retail_replay["duplicates"],
            "imports_in_database": retail_imports,
            "lines_in_database": retail_lines,
            "unit_price": str(cancellation.unit_price),
            "line_amount": str(cancellation.line_amount),
            "invoice_timezone": cancellation.invoice_timezone,
        },
        "business_tables_removed_after_downgrade": True,
        "revision_after_reupgrade": revision_after_reupgrade,
    }
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
