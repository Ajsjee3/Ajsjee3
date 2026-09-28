"""UCI 거래 CSV를 정제합니다. 배송 주문과 통화·시간의 의미가 달라 별도로 다룹니다."""

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path

SOURCE_URL = "https://archive.ics.uci.edu/static/public/352/data.csv"
SOURCE_PAGE = "https://archive.ics.uci.edu/dataset/352/online+retail"
SOURCE_SHA256 = "a2f79bbdd4463df6db8a3f5a50b9c980ae8f645a370bf5e2c0d6097f9e817b05"
COLUMNS = (
    "InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate",
    "UnitPrice", "CustomerID", "Country",
)


class RetailRowError(ValueError):
    def __init__(self, code: str, field: str):
        super().__init__(f"{field}: {code}")
        self.code = code
        self.field = field


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def normalize_record(raw: dict) -> dict:
    if None in raw or any(value is None for value in raw.values()):
        raise RetailRowError("column_count", "row")
    values = {key: value.strip() for key, value in raw.items()}
    for field in ("InvoiceNo", "StockCode", "InvoiceDate", "Country"):
        if not values[field]:
            raise RetailRowError("missing_value", field)
        if len(values[field]) > 120:
            raise RetailRowError("value_too_long", field)

    if not re.fullmatch(r"[+-]?\d{1,10}", values["Quantity"]):
        raise RetailRowError("invalid_integer", "Quantity")
    quantity = int(values["Quantity"])
    if quantity == 0 or abs(quantity) > 2_147_483_647:
        raise RetailRowError("quantity_range", "Quantity")

    # float로 계산하거나 원화/펜스로 반올림하지 않습니다. 원본에는 0.001 GBP도 있습니다.
    if not re.fullmatch(r"[+-]?\d{1,10}(?:\.\d{1,6})?", values["UnitPrice"]):
        raise RetailRowError("invalid_decimal", "UnitPrice")
    price = Decimal(values["UnitPrice"])
    if price < 0:
        raise RetailRowError("negative_price", "UnitPrice")
    try:
        invoice_at = datetime.strptime(values["InvoiceDate"], "%m/%d/%Y %H:%M")
    except ValueError as error:
        raise RetailRowError("invalid_datetime", "InvoiceDate") from error

    cancellation = values["InvoiceNo"].lower().startswith("c")
    flags = []
    if not values["CustomerID"]:
        flags.append("missing_customer_id")
    if not values["Description"]:
        flags.append("missing_description")
    if price == 0:
        flags.append("zero_price")
    if price % Decimal("0.01") != 0:
        flags.append("subpenny_price")
    if quantity < 0 and not cancellation:
        flags.append("negative_quantity_without_cancellation")
    if cancellation and quantity > 0:
        flags.append("positive_cancellation_quantity")

    return {
        "invoice_no": values["InvoiceNo"],
        "stock_code": values["StockCode"],
        "invoice_at_local": invoice_at.isoformat(),
        "timezone": None,  # 원천이 시간대를 명시하지 않아 UTC로 추정하지 않습니다.
        "quantity": quantity,
        "currency": "GBP",
        "unit_price": decimal_text(price),
        "line_amount": decimal_text(price * quantity),
        "is_cancellation": cancellation,
        "country": values["Country"],
        "quality_flags": flags,
    }


def write_json_line(stream, value: dict) -> None:
    stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def transform_file(input_path: Path, output_dir: Path) -> dict:
    """새 디렉터리에 정상 행·거절 사유를 기록하고 성공한 경우에만 보고서를 만듭니다."""
    with localcontext() as context:
        # 허용한 수량·단가 범위의 큰 금액을 합산해도 소수부를 유지합니다.
        context.prec = 50
        return _transform_file(input_path, output_dir)


def _transform_file(input_path: Path, output_dir: Path) -> dict:
    digest = file_sha256(input_path)
    counts = Counter(rows=0, accepted=0, rejected=0, cancellation_rows=0)
    warnings = Counter()
    rejections = Counter()
    signed_amount = Decimal("0")
    cancellation_amount = Decimal("0")
    with input_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        if len(reader.fieldnames or []) != len(COLUMNS) or set(reader.fieldnames) != set(COLUMNS):
            raise ValueError("UCI Online Retail의 8개 컬럼이 중복 없이 필요합니다.")
        # 기존 결과를 덮어쓰지 않습니다. 재실행 비교에는 다른 출력 경로를 사용합니다.
        output_dir.mkdir(parents=True, exist_ok=False)
        with (
            (output_dir / "accepted.jsonl").open("x", encoding="utf-8") as accepted,
            (output_dir / "rejected.jsonl").open("x", encoding="utf-8") as rejected,
        ):
            for number, raw in enumerate(reader, start=1):
                counts["rows"] += 1
                # 같은 값이 반복돼도 서로 다른 원천 행일 수 있으므로 값으로 중복 제거하지 않습니다.
                provenance = {"record_id": f"{digest}:{number}", "source_record": number}
                try:
                    record = normalize_record(raw)
                except RetailRowError as error:
                    counts["rejected"] += 1
                    rejections[error.code] += 1
                    write_json_line(rejected, {**provenance, "code": error.code, "field": error.field})
                    continue
                write_json_line(accepted, {**provenance, **record})
                counts["accepted"] += 1
                warnings.update(record["quality_flags"])
                signed_amount += Decimal(record["line_amount"])
                if record["is_cancellation"]:
                    counts["cancellation_rows"] += 1
                    cancellation_amount += Decimal(record["line_amount"])

    if file_sha256(input_path) != digest:
        raise RuntimeError("처리 중 입력 파일이 바뀌었습니다. 새 경로로 다시 실행해 주세요.")
    report = {
        "dataset": "UCI Online Retail" if digest == SOURCE_SHA256 else "unverified UCI-format input",
        "source_url": SOURCE_URL if digest == SOURCE_SHA256 else None,
        "dataset_url": SOURCE_PAGE,
        "citation": "Chen, D. (2015). Online Retail. https://doi.org/10.24432/C5BW33",
        "license": "CC BY 4.0" if digest == SOURCE_SHA256 else None,
        "input_sha256": digest,
        "matches_verified_source": digest == SOURCE_SHA256,
        "provenance_scope": "verified_uci_file" if digest == SOURCE_SHA256 else "unverified_input",
        "row_numbering": "1-based CSV records after header, not physical lines",
        "counts": dict(counts),
        "rejection_codes": dict(sorted(rejections.items())),
        "accepted_row_flags": dict(sorted(warnings.items())),
        "currency": "GBP",
        "accepted_signed_line_amount": decimal_text(signed_amount),
        "cancellation_signed_line_amount": decimal_text(cancellation_amount),
        "amount_definition": "sum(quantity * unit_price) of accepted lines; not recognized revenue",
        "timezone": None,
        "outputs_sha256": {
            name: file_sha256(output_dir / name)
            for name in ("accepted.jsonl", "rejected.jsonl")
        },
    }
    pending_report = output_dir / "report.json.tmp"
    with pending_report.open("x", encoding="utf-8") as target:
        target.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    pending_report.rename(output_dir / "report.json")
    return report
