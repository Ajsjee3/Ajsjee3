"""정제가 끝난 공개 거래 JSONL을 전용 테이블에 원자적으로 적재합니다."""

import json
import re
from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path

from sqlalchemy import insert
from sqlalchemy.orm import Session

from orderlens.models import RetailImport, RetailLine
from orderlens.retail import decimal_text, file_sha256

BATCH_SIZE = 1_000
NORMALIZED_FIELDS = {
    "record_id",
    "source_record",
    "invoice_no",
    "stock_code",
    "invoice_at_local",
    "timezone",
    "quantity",
    "currency",
    "unit_price",
    "line_amount",
    "is_cancellation",
    "country",
    "quality_flags",
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
UNIT_PRICE_PATTERN = re.compile(r"\d{1,10}(?:\.\d{1,6})?")
LINE_AMOUNT_PATTERN = re.compile(r"-?\d{1,20}(?:\.\d{1,6})?")
TOTAL_AMOUNT_PATTERN = re.compile(r"-?\d{1,32}(?:\.\d{1,6})?")


class RetailLoadError(ValueError):
    pass


def _integer(value, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise RetailLoadError(f"{field}는 {minimum} 이상의 정수여야 합니다.")
    return value


def _text(value, field: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise RetailLoadError(f"{field}는 1~{maximum}자의 문자열이어야 합니다.")
    return value


def _sha256(value, field: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise RetailLoadError(f"{field}가 SHA-256 형식이 아닙니다.")
    return value


def _decimal(value, field: str, pattern: re.Pattern[str]) -> Decimal:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise RetailLoadError(f"{field}의 Decimal 문자열 형식이 잘못됐습니다.")
    number = Decimal(value)
    if not number.is_finite():
        raise RetailLoadError(f"{field}는 유한한 Decimal이어야 합니다.")
    return number


def read_manifest(output_dir: Path) -> dict:
    try:
        report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RetailLoadError("유효한 report.json이 필요합니다.") from error
    if not isinstance(report, dict):
        raise RetailLoadError("report.json의 최상위 값은 객체여야 합니다.")

    source_sha256 = _sha256(report.get("input_sha256"), "input_sha256")
    outputs = report.get("outputs_sha256")
    if not isinstance(outputs, dict):
        raise RetailLoadError("outputs_sha256 객체가 필요합니다.")
    for name in ("accepted.jsonl", "rejected.jsonl"):
        expected = _sha256(outputs.get(name), f"outputs_sha256.{name}")
        path = output_dir / name
        if not path.is_file() or file_sha256(path) != expected:
            raise RetailLoadError(f"{name}의 SHA-256이 보고서와 다릅니다.")

    counts = report.get("counts")
    if not isinstance(counts, dict):
        raise RetailLoadError("counts 객체가 필요합니다.")
    rows = _integer(counts.get("rows"), "counts.rows")
    accepted = _integer(counts.get("accepted"), "counts.accepted")
    rejected = _integer(counts.get("rejected"), "counts.rejected")
    cancellations = _integer(counts.get("cancellation_rows"), "counts.cancellation_rows")
    if accepted + rejected != rows or cancellations > accepted:
        raise RetailLoadError("보고서의 행 수 합계가 맞지 않습니다.")
    if report.get("currency") != "GBP" or report.get("timezone") is not None:
        raise RetailLoadError("현재 계약은 GBP와 명시되지 않은 원천 시간대만 허용합니다.")

    _text(report.get("dataset"), "dataset", maximum=120)
    _text(report.get("dataset_url"), "dataset_url", maximum=500)
    _text(report.get("provenance_scope"), "provenance_scope", maximum=40)
    for field, maximum in (("source_url", 500), ("license", 50)):
        value = report.get(field)
        if value is not None:
            _text(value, field, maximum=maximum)
    _decimal(
        report.get("accepted_signed_line_amount"),
        "accepted_signed_line_amount",
        TOTAL_AMOUNT_PATTERN,
    )
    _decimal(
        report.get("cancellation_signed_line_amount"),
        "cancellation_signed_line_amount",
        TOTAL_AMOUNT_PATTERN,
    )
    report["input_sha256"] = source_sha256
    return report


def validate_rejections(output_dir: Path, source_sha256: str, expected_rows: int) -> None:
    previous = 0
    count = 0
    with (output_dir / "rejected.jsonl").open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if len(line) > 20_000:
                raise RetailLoadError(f"rejected.jsonl {line_number}행이 너무 깁니다.")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise RetailLoadError(f"rejected.jsonl {line_number}행이 JSON이 아닙니다.") from error
            if not isinstance(record, dict):
                raise RetailLoadError(f"rejected.jsonl {line_number}행은 객체여야 합니다.")
            source_record = _integer(record.get("source_record"), "source_record", minimum=1)
            if source_record <= previous:
                raise RetailLoadError("거절 행의 source_record가 오름차순이 아닙니다.")
            if record.get("record_id") != f"{source_sha256}:{source_record}":
                raise RetailLoadError("거절 행의 record_id가 출처 위치와 다릅니다.")
            _text(record.get("code"), "code", maximum=40)
            _text(record.get("field"), "field", maximum=120)
            previous = source_record
            count += 1
    if count != expected_rows:
        raise RetailLoadError("rejected.jsonl 행 수가 보고서와 다릅니다.")


def normalized_rows(path: Path, source_sha256: str) -> Iterator[dict]:
    previous = 0
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if len(line) > 20_000:
                raise RetailLoadError(f"accepted.jsonl {line_number}행이 너무 깁니다.")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise RetailLoadError(f"accepted.jsonl {line_number}행이 JSON이 아닙니다.") from error
            if not isinstance(record, dict) or set(record) != NORMALIZED_FIELDS:
                raise RetailLoadError(f"accepted.jsonl {line_number}행의 필드 계약이 다릅니다.")

            source_record = _integer(record["source_record"], "source_record", minimum=1)
            if source_record <= previous:
                raise RetailLoadError("source_record가 중복됐거나 오름차순이 아닙니다.")
            if record["record_id"] != f"{source_sha256}:{source_record}":
                raise RetailLoadError("record_id가 파일 해시와 원본 위치에 맞지 않습니다.")
            previous = source_record

            try:
                invoice_at = datetime.fromisoformat(
                    _text(record["invoice_at_local"], "invoice_at_local", maximum=40)
                )
            except ValueError as error:
                raise RetailLoadError("invoice_at_local이 ISO datetime이 아닙니다.") from error
            if invoice_at.tzinfo is not None or record["timezone"] is not None:
                raise RetailLoadError("원천에 없는 시간대를 추정해 저장할 수 없습니다.")
            raw_quantity = record["quantity"]
            if isinstance(raw_quantity, bool) or not isinstance(raw_quantity, int):
                raise RetailLoadError("quantity는 정수여야 합니다.")
            if raw_quantity == 0 or abs(raw_quantity) > 2_147_483_647:
                raise RetailLoadError("quantity 범위를 벗어났습니다.")
            quantity = raw_quantity
            unit_price = _decimal(record["unit_price"], "unit_price", UNIT_PRICE_PATTERN)
            line_amount = _decimal(record["line_amount"], "line_amount", LINE_AMOUNT_PATTERN)
            if line_amount != unit_price * quantity:
                raise RetailLoadError("line_amount가 quantity × unit_price와 다릅니다.")
            if record["currency"] != "GBP":
                raise RetailLoadError("현재 공개 거래 계약의 통화는 GBP입니다.")
            if not isinstance(record["is_cancellation"], bool):
                raise RetailLoadError("is_cancellation은 boolean이어야 합니다.")
            flags = record["quality_flags"]
            if (
                not isinstance(flags, list)
                or any(not isinstance(flag, str) or not flag for flag in flags)
                or len(flags) != len(set(flags))
            ):
                raise RetailLoadError("quality_flags는 중복 없는 문자열 목록이어야 합니다.")

            yield {
                "source_sha256": source_sha256,
                "source_record": source_record,
                "invoice_no": _text(record["invoice_no"], "invoice_no", maximum=120),
                "stock_code": _text(record["stock_code"], "stock_code", maximum=120),
                "invoice_at_local": invoice_at,
                "invoice_timezone": None,
                "quantity": quantity,
                "currency": "GBP",
                "unit_price": unit_price,
                "line_amount": line_amount,
                "is_cancellation": record["is_cancellation"],
                "country": _text(record["country"], "country", maximum=120),
                "quality_flags": flags,
            }


def _same_import(existing: RetailImport, report: dict) -> bool:
    counts = report["counts"]
    return (
        existing.accepted_output_sha256 == report["outputs_sha256"]["accepted.jsonl"]
        and existing.rejected_output_sha256 == report["outputs_sha256"]["rejected.jsonl"]
        and existing.dataset == report["dataset"]
        and existing.dataset_url == report["dataset_url"]
        and existing.source_url == report.get("source_url")
        and existing.license == report.get("license")
        and existing.provenance_scope == report["provenance_scope"]
        and existing.currency == report["currency"]
        and existing.source_rows == counts["rows"]
        and existing.accepted_rows == counts["accepted"]
        and existing.rejected_rows == counts["rejected"]
        and existing.cancellation_rows == counts["cancellation_rows"]
        and existing.accepted_signed_line_amount
        == Decimal(report["accepted_signed_line_amount"])
        and existing.cancellation_signed_line_amount
        == Decimal(report["cancellation_signed_line_amount"])
    )


def load_retail_output(session: Session, output_dir: Path, batch_size: int = BATCH_SIZE) -> dict:
    """정제 결과를 한 트랜잭션에 적재하고 같은 파일의 재실행은 중복으로 반환합니다."""
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
        raise ValueError("batch_size는 1 이상의 정수여야 합니다.")
    report = read_manifest(output_dir)
    source_sha256 = report["input_sha256"]
    counts = report["counts"]
    validate_rejections(output_dir, source_sha256, counts["rejected"])

    with localcontext() as context:
        context.prec = 50
        with session.begin():
            existing = session.get(RetailImport, source_sha256)
            if existing is not None:
                if not _same_import(existing, report):
                    raise RetailLoadError(
                        "같은 원본 해시가 다른 정제 결과로 이미 적재되어 있습니다."
                    )
                return {
                    "source_sha256": source_sha256,
                    "status": "already_loaded",
                    "inserted": 0,
                    "duplicates": existing.accepted_rows,
                    "rows_in_database": existing.accepted_rows,
                }

            session.add(
                RetailImport(
                    source_sha256=source_sha256,
                    accepted_output_sha256=report["outputs_sha256"]["accepted.jsonl"],
                    rejected_output_sha256=report["outputs_sha256"]["rejected.jsonl"],
                    dataset=report["dataset"],
                    dataset_url=report["dataset_url"],
                    source_url=report.get("source_url"),
                    license=report.get("license"),
                    provenance_scope=report["provenance_scope"],
                    currency="GBP",
                    source_rows=counts["rows"],
                    accepted_rows=counts["accepted"],
                    rejected_rows=counts["rejected"],
                    cancellation_rows=counts["cancellation_rows"],
                    accepted_signed_line_amount=Decimal(report["accepted_signed_line_amount"]),
                    cancellation_signed_line_amount=Decimal(
                        report["cancellation_signed_line_amount"]
                    ),
                )
            )
            session.flush()

            batch = []
            inserted = 0
            cancellations = 0
            signed_amount = Decimal("0")
            cancellation_amount = Decimal("0")
            for record in normalized_rows(output_dir / "accepted.jsonl", source_sha256):
                batch.append(record)
                inserted += 1
                signed_amount += record["line_amount"]
                if record["is_cancellation"]:
                    cancellations += 1
                    cancellation_amount += record["line_amount"]
                if len(batch) == batch_size:
                    session.execute(insert(RetailLine), batch)
                    batch.clear()
            if batch:
                session.execute(insert(RetailLine), batch)

            if (
                inserted != counts["accepted"]
                or cancellations != counts["cancellation_rows"]
                or decimal_text(signed_amount) != report["accepted_signed_line_amount"]
                or decimal_text(cancellation_amount)
                != report["cancellation_signed_line_amount"]
            ):
                raise RetailLoadError("정제 행의 건수 또는 금액 합계가 보고서와 다릅니다.")

        return {
            "source_sha256": source_sha256,
            "status": "loaded",
            "inserted": inserted,
            "duplicates": 0,
            "rows_in_database": inserted,
        }
