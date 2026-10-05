import csv
import json
import subprocess
import sys
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from orderlens.db import make_engine
from orderlens.migrations import upgrade_database
from orderlens.models import RetailImport, RetailLine
from orderlens.retail import COLUMNS, file_sha256, transform_file
from orderlens.retail_db import RetailLoadError, load_retail_output


def source_row(**changes):
    return {
        "InvoiceNo": "123456",
        "StockCode": "ITEM_A",
        "Description": "demo item",
        "Quantity": "2",
        "InvoiceDate": "12/1/2010 8:26",
        "UnitPrice": "1.25",
        "CustomerID": "",
        "Country": "United Kingdom",
        **changes,
    }


def transformed_output(tmp_path, rows, name="processed"):
    source = tmp_path / f"{name}.csv"
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    output = tmp_path / name
    transform_file(source, output)
    return output


def migrated_engine(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'retail.db'}"
    upgrade_database(database_url)
    return database_url, make_engine(database_url)


def test_retail_load_preserves_decimal_and_replay_is_idempotent(tmp_path):
    output = transformed_output(tmp_path, [
        source_row(InvoiceNo="C123456", Quantity="-3", UnitPrice="0.001"),
        source_row(InvoiceNo="123457", StockCode="ITEM_B"),
        source_row(InvoiceNo="ADJUST", UnitPrice="-1"),
    ])
    _database_url, engine = migrated_engine(tmp_path)
    try:
        with Session(engine) as session:
            first = load_retail_output(session, output, batch_size=1)
            replay = load_retail_output(session, output, batch_size=1)
            imports = session.scalar(select(func.count()).select_from(RetailImport))
            lines = session.scalar(select(func.count()).select_from(RetailLine))
            cancellation = session.scalar(
                select(RetailLine).where(RetailLine.invoice_no == "C123456")
            )

        assert first["status"] == "loaded"
        assert (first["inserted"], first["duplicates"]) == (2, 0)
        assert replay["status"] == "already_loaded"
        assert (replay["inserted"], replay["duplicates"]) == (0, 2)
        assert (imports, lines) == (1, 2)
        assert cancellation.source_record == 1
        assert cancellation.unit_price == Decimal("0.001000")
        assert cancellation.line_amount == Decimal("-0.003000")
        assert cancellation.invoice_at_local.tzinfo is None
        assert cancellation.invoice_timezone is None
        assert cancellation.currency == "GBP"
        assert "subpenny_price" in cancellation.quality_flags
    finally:
        engine.dispose()


def test_same_source_with_changed_manifest_is_rejected(tmp_path):
    output = transformed_output(tmp_path, [source_row()])
    _database_url, engine = migrated_engine(tmp_path)
    try:
        with Session(engine) as session:
            load_retail_output(session, output)
            report_path = output / "report.json"
            report = json.loads(report_path.read_text())
            report["dataset"] = "changed dataset label"
            report_path.write_text(json.dumps(report))
            with pytest.raises(RetailLoadError, match="다른 정제 결과"):
                load_retail_output(session, output)
            assert session.scalar(select(func.count()).select_from(RetailLine)) == 1
    finally:
        engine.dispose()


def test_invalid_later_line_rolls_back_the_whole_import(tmp_path):
    output = transformed_output(tmp_path, [source_row(), source_row(InvoiceNo="123457")])
    accepted_path = output / "accepted.jsonl"
    records = [json.loads(line) for line in accepted_path.read_text().splitlines()]
    records[1]["line_amount"] = "999"
    accepted_path.write_text("".join(json.dumps(row) + "\n" for row in records))
    report_path = output / "report.json"
    report = json.loads(report_path.read_text())
    report["outputs_sha256"]["accepted.jsonl"] = file_sha256(accepted_path)
    report_path.write_text(json.dumps(report))

    _database_url, engine = migrated_engine(tmp_path)
    try:
        with Session(engine) as session:
            with pytest.raises(RetailLoadError, match="quantity × unit_price"):
                load_retail_output(session, output, batch_size=1)
            assert session.scalar(select(func.count()).select_from(RetailImport)) == 0
            assert session.scalar(select(func.count()).select_from(RetailLine)) == 0
    finally:
        engine.dispose()


def test_load_retail_cli_requires_migration_and_reports_replay(tmp_path):
    output = transformed_output(tmp_path, [source_row()])
    database_url, engine = migrated_engine(tmp_path)
    engine.dispose()
    command = [
        sys.executable,
        "-m",
        "scripts.load_retail",
        str(output),
        "--database-url",
        database_url,
    ]
    first = subprocess.run(command, capture_output=True, text=True, check=True)
    replay = subprocess.run(command, capture_output=True, text=True, check=True)
    assert json.loads(first.stdout)["inserted"] == 1
    assert json.loads(replay.stdout)["duplicates"] == 1
