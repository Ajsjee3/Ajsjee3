"""같은 SQLite DB에서 전체 스캔과 지정 인덱스 집계를 번갈아 측정합니다."""

import argparse
import json
import math
import platform
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from statistics import median
from time import perf_counter_ns

from sqlalchemy import func, inspect, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DatabaseError

from orderlens.db import make_engine
from orderlens.migrations import require_current_schema
from orderlens.models import RetailLine
from orderlens.retail_analytics import RETAIL_QUERY_INDEX, validate_retail_period

BASELINE_SQL = """
SELECT COUNT(*), COALESCE(SUM(quantity), 0), COALESCE(SUM(line_amount), 0)
FROM retail_lines NOT INDEXED
WHERE country = ?
  AND is_cancellation = 0
  AND invoice_at_local >= ?
  AND invoice_at_local < ?
""".strip()

INDEXED_SQL = f"""
SELECT COUNT(*), COALESCE(SUM(quantity), 0), COALESCE(SUM(line_amount), 0)
FROM retail_lines INDEXED BY {RETAIL_QUERY_INDEX}
WHERE country = ?
  AND is_cancellation = 0
  AND invoice_at_local >= ?
  AND invoice_at_local < ?
""".strip()


def parse_local_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("ISO 8601 지역 시각이어야 합니다.") from error
    if parsed.tzinfo is not None:
        raise argparse.ArgumentTypeError("원천에 시간대가 없으므로 오프셋을 붙이지 않습니다.")
    return parsed


def sqlite_value(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S.%f")


def normalized_result(row) -> dict:
    amount = Decimal(str(row[2])).quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)
    return {
        "line_count": int(row[0]),
        "quantity": int(row[1]),
        "signed_line_amount_gbp": format(amount, "f"),
    }


def execute_timed(connection: Connection, sql: str, parameters: tuple[str, str, str]):
    started = perf_counter_ns()
    row = connection.exec_driver_sql(sql, parameters).one()
    elapsed_ms = (perf_counter_ns() - started) / 1_000_000
    return normalized_result(row), elapsed_ms


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    position = max(0, math.ceil(percentile_value * len(ordered)) - 1)
    return ordered[position]


def timing_summary(values: list[float]) -> dict:
    return {
        "runs": len(values),
        "minimum_ms": round(min(values), 3),
        "median_ms": round(median(values), 3),
        "p95_ms": round(percentile(values, 0.95), 3),
        "maximum_ms": round(max(values), 3),
    }


def explain(connection: Connection, sql: str, parameters: tuple[str, str, str]) -> list[str]:
    rows = connection.exec_driver_sql(f"EXPLAIN QUERY PLAN {sql}", parameters)
    return [str(row[3]) for row in rows]


def index_storage_bytes(connection: Connection) -> int | None:
    try:
        value = connection.exec_driver_sql(
            "SELECT SUM(pgsize) FROM dbstat WHERE name = ?", (RETAIL_QUERY_INDEX,)
        ).scalar_one()
    except DatabaseError:
        return None
    return int(value) if value is not None else None


def benchmark(
    database_url: str,
    *,
    country: str,
    start_at: datetime,
    end_at: datetime,
    warmups: int,
    runs: int,
) -> dict:
    country = validate_retail_period(country, start_at, end_at)
    if warmups < 0 or runs < 1:
        raise ValueError("warmups는 0 이상, runs는 1 이상이어야 합니다.")
    engine = make_engine(database_url)
    try:
        if engine.dialect.name != "sqlite":
            raise RuntimeError("이 비교 스크립트는 SQLite의 NOT INDEXED/INDEXED BY를 사용합니다.")
        revision = require_current_schema(engine)
        available_indexes = {
            item["name"]: item["column_names"]
            for item in inspect(engine).get_indexes("retail_lines")
        }
        expected_columns = ["country", "is_cancellation", "invoice_at_local"]
        if available_indexes.get(RETAIL_QUERY_INDEX) != expected_columns:
            raise RuntimeError(f"{RETAIL_QUERY_INDEX}가 현재 스키마에 없습니다.")

        parameters = (country, sqlite_value(start_at), sqlite_value(end_at))
        scan_times: list[float] = []
        index_times: list[float] = []
        with engine.connect() as connection:
            baseline_plan = explain(connection, BASELINE_SQL, parameters)
            indexed_plan = explain(connection, INDEXED_SQL, parameters)
            for _ in range(warmups):
                execute_timed(connection, BASELINE_SQL, parameters)
                execute_timed(connection, INDEXED_SQL, parameters)
            baseline_result = None
            indexed_result = None
            for run in range(runs):
                ordered = (
                    ((BASELINE_SQL, scan_times), (INDEXED_SQL, index_times))
                    if run % 2 == 0
                    else ((INDEXED_SQL, index_times), (BASELINE_SQL, scan_times))
                )
                for sql, measurements in ordered:
                    result, elapsed_ms = execute_timed(connection, sql, parameters)
                    measurements.append(elapsed_ms)
                    if sql == BASELINE_SQL:
                        baseline_result = result
                    else:
                        indexed_result = result
            if baseline_result != indexed_result:
                raise AssertionError("전체 스캔과 인덱스 조회의 집계 결과가 다릅니다.")
            row_count = connection.scalar(select(func.count()).select_from(RetailLine))
            sqlite_version = connection.exec_driver_sql("SELECT sqlite_version()").scalar_one()
            index_bytes = index_storage_bytes(connection)

        scan_summary = timing_summary(scan_times)
        index_summary = timing_summary(index_times)
        ratio = median(scan_times) / median(index_times)
        database_path = Path(engine.url.database or "")
        return {
            "scope": "one local warm-cache SQLite comparison; not a production guarantee",
            "comparison": "same database, NOT INDEXED versus INDEXED BY",
            "environment": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "sqlite": sqlite_version,
            },
            "schema_revision": revision,
            "database_rows": int(row_count or 0),
            "database_bytes": database_path.stat().st_size if database_path.is_file() else None,
            "index": {
                "name": RETAIL_QUERY_INDEX,
                "columns": expected_columns,
                "storage_bytes": index_bytes,
            },
            "query": {
                "country": country,
                "is_cancellation": False,
                "start_at_local_inclusive": start_at.isoformat(),
                "end_at_local_exclusive": end_at.isoformat(),
            },
            "result": baseline_result,
            "measurement": {
                "warmups_per_query": warmups,
                "alternating_runs_per_query": runs,
                "forced_full_scan": {"plan": baseline_plan, **scan_summary},
                "forced_composite_index": {"plan": indexed_plan, **index_summary},
                "median_ratio_scan_over_index": round(ratio, 2),
            },
            "limits": [
                "SQLite 한 파일과 한 국가·기간 조건만 측정했습니다.",
                "OS 캐시를 비우지 않은 warm-cache 결과입니다.",
                "PostgreSQL 실행계획은 별도 통합 검사에서 확인합니다.",
            ],
        }
    finally:
        engine.dispose()


def positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("1 이상의 정수여야 합니다.")
    return number


def nonnegative_integer(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("0 이상의 정수여야 합니다.")
    return number


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--country", default="Germany")
    parser.add_argument("--start", type=parse_local_datetime, default="2011-01-01T00:00:00")
    parser.add_argument("--end", type=parse_local_datetime, default="2012-01-01T00:00:00")
    parser.add_argument("--warmups", type=nonnegative_integer, default=5)
    parser.add_argument("--runs", type=positive_integer, default=31)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = benchmark(
        args.database_url,
        country=args.country,
        start_at=args.start,
        end_at=args.end,
        warmups=args.warmups,
        runs=args.runs,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
