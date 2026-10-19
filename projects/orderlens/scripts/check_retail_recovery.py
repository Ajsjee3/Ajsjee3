"""강제 계약 실패 뒤 적재 이력과 중복 없는 복구를 임시 SQLite에서 재현합니다."""

import csv
import json
import platform
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from orderlens.db import make_engine
from orderlens.migrations import upgrade_database
from orderlens.models import RetailImport, RetailLine, RetailLoadAttempt
from orderlens.retail import COLUMNS, file_sha256, transform_file
from orderlens.retail_db import RetailLoadError, run_retail_load


def _source_rows() -> list[dict[str, str]]:
    return [
        {
            "InvoiceNo": "123456",
            "StockCode": "ITEM_A",
            "Description": "recovery fixture one",
            "Quantity": "2",
            "InvoiceDate": "12/1/2010 8:26",
            "UnitPrice": "1.25",
            "CustomerID": "",
            "Country": "United Kingdom",
        },
        {
            "InvoiceNo": "123457",
            "StockCode": "ITEM_B",
            "Description": "recovery fixture two",
            "Quantity": "1",
            "InvoiceDate": "12/1/2010 8:27",
            "UnitPrice": "2.50",
            "CustomerID": "",
            "Country": "Germany",
        },
    ]


def main() -> None:
    with TemporaryDirectory(prefix="orderlens-retail-recovery-") as directory:
        root = Path(directory)
        source = root / "retail.csv"
        with source.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(_source_rows())

        output = root / "processed"
        transform_file(source, output)
        accepted_path = output / "accepted.jsonl"
        report_path = output / "report.json"
        valid_accepted = accepted_path.read_text(encoding="utf-8")
        valid_report = report_path.read_text(encoding="utf-8")

        records = [json.loads(line) for line in valid_accepted.splitlines()]
        records[1]["line_amount"] = "999"
        accepted_path.write_text(
            "".join(json.dumps(row) + "\n" for row in records),
            encoding="utf-8",
        )
        broken_report = json.loads(valid_report)
        broken_report["outputs_sha256"]["accepted.jsonl"] = file_sha256(accepted_path)
        report_path.write_text(json.dumps(broken_report), encoding="utf-8")

        database_url = f"sqlite:///{root / 'recovery.db'}"
        upgrade_database(database_url)
        engine = make_engine(database_url)
        try:
            try:
                run_retail_load(engine, output, batch_size=1)
            except RetailLoadError as error:
                failure_message = str(error)
            else:
                raise AssertionError("강제한 행 계약 오류가 적재를 중단하지 않았습니다.")

            with Session(engine) as session:
                failed_attempt = session.scalar(
                    select(RetailLoadAttempt).where(RetailLoadAttempt.status == "failed")
                )
                if failed_attempt is None:
                    raise AssertionError("실패한 적재 시도가 기록되지 않았습니다.")
                failed_attempt_id = failed_attempt.id
                imports_after_failure = session.scalar(
                    select(func.count()).select_from(RetailImport)
                )
                lines_after_failure = session.scalar(
                    select(func.count()).select_from(RetailLine)
                )

            accepted_path.write_text(valid_accepted, encoding="utf-8")
            report_path.write_text(valid_report, encoding="utf-8")
            recovered = run_retail_load(engine, output, batch_size=1)
            replay = run_retail_load(engine, output, batch_size=1)

            attempt_ids = [failed_attempt_id, recovered["attempt_id"], replay["attempt_id"]]
            with Session(engine) as session:
                attempts = [session.get(RetailLoadAttempt, item) for item in attempt_ids]
                if any(item is None for item in attempts):
                    raise AssertionError("적재 시도 이력 일부를 찾을 수 없습니다.")
                imports_final = session.scalar(select(func.count()).select_from(RetailImport))
                lines_final = session.scalar(select(func.count()).select_from(RetailLine))
        finally:
            engine.dispose()

    attempt_history = [
        {
            "status": item.status,
            "result": item.result,
            "inserted_rows": item.inserted_rows,
            "duplicate_rows": item.duplicate_rows,
            "error_code": item.error_code,
            "error_message": item.error_message,
        }
        for item in attempts
        if item is not None
    ]
    expected_history = [
        ("failed", None, 0, 0),
        ("succeeded", "loaded", 2, 0),
        ("succeeded", "already_loaded", 0, 2),
    ]
    actual_history = [
        (item["status"], item["result"], item["inserted_rows"], item["duplicate_rows"])
        for item in attempt_history
    ]
    if actual_history != expected_history:
        raise AssertionError(f"적재 시도 이력이 예상과 다릅니다: {actual_history}")
    if (imports_after_failure, lines_after_failure) != (0, 0):
        raise AssertionError("실패한 적재의 일부 행이 DB에 남았습니다.")
    if (imports_final, lines_final) != (1, 2):
        raise AssertionError("복구 또는 재실행 뒤 DB 행 수가 예상과 다릅니다.")

    evidence = {
        "environment": {
            "platform": platform.system(),
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
        },
        "scenario": "두 번째 정제 행의 금액 계약 위반; batch_size=1",
        "failure_message": failure_message,
        "after_failure": {
            "retail_imports": imports_after_failure,
            "retail_lines": lines_after_failure,
        },
        "attempt_history": attempt_history,
        "recovery": {
            "status": recovered["status"],
            "inserted": recovered["inserted"],
        },
        "replay": {
            "status": replay["status"],
            "duplicates": replay["duplicates"],
        },
        "final_database": {
            "retail_imports": imports_final,
            "retail_lines": lines_final,
        },
        "limits": [
            "한 프로세스의 명시적 데이터 계약 실패를 재현했습니다.",
            "프로세스 강제 종료와 동시에 시작한 여러 적재는 확인하지 않았습니다.",
        ],
    }
    artifact = Path("artifacts/retail_recovery.json")
    artifact.parent.mkdir(exist_ok=True)
    artifact.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
