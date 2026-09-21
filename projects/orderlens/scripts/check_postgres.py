"""비어 있는 테스트용 PostgreSQL에서 마이그레이션과 핵심 API 흐름을 검증합니다."""

import json
import os

from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.engine import make_url

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
        "business_tables_removed_after_downgrade": True,
        "revision_after_reupgrade": revision_after_reupgrade,
    }
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
