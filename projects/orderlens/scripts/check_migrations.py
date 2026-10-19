"""임시 SQLite DB에서 초기 마이그레이션의 적용·복구·재적용을 확인합니다."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import inspect

import orderlens.models  # noqa: F401
from orderlens.db import Base, make_engine
from orderlens.migrations import (
    check_model_matches_database,
    current_revision,
    downgrade_database,
    head_revision,
    require_current_schema,
    upgrade_database,
)


def main() -> None:
    expected_tables = set(Base.metadata.tables)
    with TemporaryDirectory(prefix="orderlens-migration-") as directory:
        database_url = f"sqlite:///{directory}/migration.db"
        upgrade_database(database_url)
        check_model_matches_database(database_url)
        engine = make_engine(database_url)
        try:
            revision = require_current_schema(engine)
            created_tables = set(inspect(engine).get_table_names())
            if not expected_tables <= created_tables:
                raise AssertionError("초기 마이그레이션이 필요한 테이블을 모두 만들지 않았습니다.")
            retail_indexes = {
                item["name"]: item["column_names"]
                for item in inspect(engine).get_indexes("retail_lines")
            }
            expected_retail_index = ["country", "is_cancellation", "invoice_at_local"]
            if retail_indexes.get("ix_retail_country_cancelled_time") != expected_retail_index:
                raise AssertionError("공개 거래 집계 인덱스의 컬럼 순서가 다릅니다.")
            attempt_indexes = {
                item["name"]: item["column_names"]
                for item in inspect(engine).get_indexes("retail_load_attempts")
            }
            expected_attempt_index = ["source_sha256", "started_at"]
            if (
                attempt_indexes.get("ix_retail_load_attempt_source_started")
                != expected_attempt_index
            ):
                raise AssertionError("공개 거래 적재 시도 인덱스의 컬럼 순서가 다릅니다.")

            downgrade_database(database_url)
            remaining = set(inspect(engine).get_table_names()) & expected_tables
            if remaining or current_revision(engine) is not None:
                raise AssertionError(f"downgrade 후 남은 업무 테이블이 있습니다: {remaining}")

            upgrade_database(database_url)
            reupgraded = require_current_schema(engine)
        finally:
            engine.dispose()

    evidence = {
        "database": "temporary_sqlite",
        "head_revision": head_revision(),
        "revision_after_upgrade": revision,
        "created_tables": sorted(expected_tables),
        "model_matches_migration": True,
        "retail_query_index": {
            "name": "ix_retail_country_cancelled_time",
            "columns": expected_retail_index,
        },
        "retail_load_attempt_index": {
            "name": "ix_retail_load_attempt_source_started",
            "columns": expected_attempt_index,
        },
        "business_tables_removed_after_downgrade": True,
        "revision_after_reupgrade": reupgraded,
    }
    output = Path("artifacts/migration_check.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
