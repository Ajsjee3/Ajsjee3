import csv
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from orderlens.db import make_engine
from orderlens.migrations import upgrade_database
from orderlens.retail import COLUMNS, transform_file
from orderlens.retail_analytics import RetailQueryError, retail_summary
from orderlens.retail_db import load_retail_output
from scripts.benchmark_retail_sql import benchmark


def source_row(invoice_no: str, invoice_at: str, **changes) -> dict:
    return {
        "InvoiceNo": invoice_no,
        "StockCode": "ITEM_A",
        "Description": "query fixture",
        "Quantity": "1",
        "InvoiceDate": invoice_at,
        "UnitPrice": "1.00",
        "CustomerID": "",
        "Country": "Germany",
        **changes,
    }


def loaded_database(tmp_path) -> str:
    source = tmp_path / "retail.csv"
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows([
            source_row("BEFORE", "12/31/2010 23:59", Quantity="9"),
            source_row("START", "01/01/2011 00:00", Quantity="2", UnitPrice="1.25"),
            source_row("MIDDLE", "06/01/2011 12:30", Quantity="3", UnitPrice="2.00"),
            source_row("CANCEL", "06/02/2011 12:30", Quantity="-1"),
            source_row("FRANCE", "06/03/2011 12:30", Country="France", Quantity="7"),
            source_row("END", "01/01/2012 00:00", Quantity="8"),
        ])
    output = tmp_path / "processed"
    transform_file(source, output)
    database_url = f"sqlite:///{tmp_path / 'retail.db'}"
    upgrade_database(database_url)
    engine = make_engine(database_url)
    try:
        with Session(engine) as session:
            load_retail_output(session, output)
    finally:
        engine.dispose()
    return database_url


def test_retail_summary_uses_exact_country_half_open_period_and_excludes_cancellations(
    tmp_path,
):
    database_url = loaded_database(tmp_path)
    engine = make_engine(database_url)
    try:
        with Session(engine) as session:
            result = retail_summary(
                session,
                " Germany ",
                datetime(2011, 1, 1),
                datetime(2012, 1, 1),
            )
    finally:
        engine.dispose()

    assert result.country == "Germany"
    assert result.currency == "GBP"
    assert result.line_count == 2
    assert result.quantity == 5
    assert result.signed_line_amount == Decimal("8.500000")


@pytest.mark.parametrize(
    ("country", "start_at", "end_at", "message"),
    [
        (" ", datetime(2011, 1, 1), datetime(2012, 1, 1), "country"),
        ("Germany", datetime(2012, 1, 1), datetime(2011, 1, 1), "빨라야"),
        (
            "Germany",
            datetime(2011, 1, 1, tzinfo=timezone.utc),
            datetime(2012, 1, 1, tzinfo=timezone.utc),
            "시간대",
        ),
    ],
)
def test_retail_summary_rejects_ambiguous_scope(country, start_at, end_at, message, tmp_path):
    database_url = loaded_database(tmp_path)
    engine = make_engine(database_url)
    try:
        with Session(engine) as session:
            with pytest.raises(RetailQueryError, match=message):
                retail_summary(session, country, start_at, end_at)
    finally:
        engine.dispose()


def test_sqlite_benchmark_compares_identical_results_and_records_plans(tmp_path):
    report = benchmark(
        loaded_database(tmp_path),
        country="Germany",
        start_at=datetime(2011, 1, 1),
        end_at=datetime(2012, 1, 1),
        warmups=0,
        runs=2,
    )

    assert report["result"] == {
        "line_count": 2,
        "quantity": 5,
        "signed_line_amount_gbp": "8.500000",
    }
    assert "SCAN retail_lines" in report["measurement"]["forced_full_scan"]["plan"]
    assert any(
        "ix_retail_country_cancelled_time" in line
        for line in report["measurement"]["forced_composite_index"]["plan"]
    )
    assert report["index"]["columns"] == [
        "country",
        "is_cancellation",
        "invoice_at_local",
    ]
