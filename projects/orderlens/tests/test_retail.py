import csv
import json
import subprocess
import sys
from decimal import localcontext
from pathlib import Path

import pytest

from orderlens.retail import COLUMNS, RetailRowError, normalize_record, transform_file
from scripts.fetch_retail import download


def row(**changes):
    # 검증 규칙을 확인하기 위한 합성 입력이며 실제 고객 거래를 뜻하지 않습니다.
    return {
        "InvoiceNo": "123456", "StockCode": "ITEM_A", "Description": "demo item",
        "Quantity": "3", "InvoiceDate": "12/1/2010 8:26", "UnitPrice": "0.1",
        "CustomerID": "", "Country": "United Kingdom", **changes,
    }


def make_csv(path: Path, rows: list[dict]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_exact_amount_and_source_semantics():
    record = normalize_record(row(InvoiceNo="C123456", Quantity="-3", UnitPrice="0.001"))
    assert record["line_amount"] == "-0.003"
    assert record["is_cancellation"] is True
    assert record["invoice_no"] == "C123456"
    assert record["currency"] == "GBP"
    assert record["invoice_at_local"] == "2010-12-01T08:26:00"
    assert record["timezone"] is None
    assert "subpenny_price" in record["quality_flags"]
    assert "amount_krw" not in record and "promised_by" not in record
    assert "CustomerID" not in record


@pytest.mark.parametrize(("change", "code"), [
    ({"Quantity": "1.5"}, "invalid_integer"),
    ({"Quantity": "0"}, "quantity_range"),
    ({"Quantity": "2147483648"}, "quantity_range"),
    ({"UnitPrice": "NaN"}, "invalid_decimal"),
    ({"UnitPrice": "Infinity"}, "invalid_decimal"),
    ({"UnitPrice": "-1.2"}, "negative_price"),
    ({"InvoiceDate": "2/30/2011 9:00"}, "invalid_datetime"),
    ({"InvoiceNo": " "}, "missing_value"),
    ({"Country": None}, "column_count"),
])
def test_invalid_values_are_explicit(change, code):
    with pytest.raises(RetailRowError) as caught:
        normalize_record(row(**change))
    assert caught.value.code == code


def test_zero_price_and_unmarked_negative_are_retained_as_flags():
    record = normalize_record(row(Quantity="-1", UnitPrice="0", Description=""))
    assert record["is_cancellation"] is False
    assert record["line_amount"] == "0"
    assert set(record["quality_flags"]) == {
        "missing_customer_id", "missing_description", "zero_price",
        "negative_quantity_without_cancellation",
    }


def test_trailing_zero_does_not_mean_fractional_penny():
    assert "subpenny_price" not in normalize_record(row(UnitPrice="1.230"))["quality_flags"]


def test_replay_preserves_each_source_record_and_quarantines_errors(tmp_path):
    source = make_csv(tmp_path / "input.csv", [
        row(Description="two\nlines"), row(Description="two\nlines"),
        row(InvoiceNo="C123457", Quantity="-1"), row(UnitPrice="-5"),
    ])
    first = transform_file(source, tmp_path / "first")
    replay = transform_file(source, tmp_path / "replay")
    assert first == replay
    assert first["matches_verified_source"] is False
    assert first["provenance_scope"] == "unverified_input"
    assert first["counts"] == {"rows": 4, "accepted": 3, "rejected": 1, "cancellation_rows": 1}
    assert first["accepted_signed_line_amount"] == "0.5"
    records = [json.loads(line) for line in (tmp_path / "first/accepted.jsonl").read_text().splitlines()]
    assert len({r["record_id"] for r in records}) == 3
    assert [r["source_record"] for r in records] == [1, 2, 3]
    error = json.loads((tmp_path / "first/rejected.jsonl").read_text())
    assert error["source_record"] == 4 and error["code"] == "negative_price"
    assert "CustomerID" not in error and "Description" not in error
    with pytest.raises(FileExistsError):
        transform_file(source, tmp_path / "first")
    assert json.loads((tmp_path / "first/report.json").read_text()) == first


def test_missing_headers_do_not_create_a_report(tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("InvoiceNo,Quantity\n123456,3\n")
    with pytest.raises(ValueError, match="8개 컬럼"):
        transform_file(source, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_cli_produces_report(tmp_path):
    source = make_csv(tmp_path / "input.csv", [row()])
    process = subprocess.run([
        sys.executable, "-m", "scripts.transform_retail", str(source),
        "--output", str(tmp_path / "out"),
    ], capture_output=True, text=True, check=True)
    assert json.loads(process.stdout)["accepted_signed_line_amount"] == "0.3"
    assert (tmp_path / "out/report.json").exists()


def test_downloader_never_overwrites_a_different_existing_file(tmp_path):
    target = tmp_path / "source.csv"
    target.write_text("keep this input")
    with pytest.raises(ValueError, match="기존"):
        download(target)
    assert target.read_text() == "keep this input"


def test_broken_csv_never_produces_success_report(tmp_path):
    source = tmp_path / "broken.csv"
    source.write_text(",".join(COLUMNS) + '\n123456,ITEM_A,"unclosed\n')
    with pytest.raises(csv.Error):
        transform_file(source, tmp_path / "out")
    assert not (tmp_path / "out/report.json").exists()


def test_transform_does_not_inherit_callers_low_decimal_precision(tmp_path):
    source = make_csv(tmp_path / "input.csv", [row(UnitPrice="1234.123456")])
    with localcontext() as context:
        context.prec = 5
        report = transform_file(source, tmp_path / "out")
        assert context.prec == 5
    assert report["accepted_signed_line_amount"] == "3702.370368"


def test_report_write_failure_does_not_leave_a_success_marker(tmp_path, monkeypatch):
    source = make_csv(tmp_path / "input.csv", [row()])
    dumps = json.dumps

    def fail_report(value, **kwargs):
        if kwargs.get("indent") == 2:
            raise OSError("simulated report write failure")
        return dumps(value, **kwargs)

    monkeypatch.setattr(json, "dumps", fail_report)
    with pytest.raises(OSError, match="simulated"):
        transform_file(source, tmp_path / "out")
    assert not (tmp_path / "out/report.json").exists()
