"""작은 수작업 예제로 검색 기준선을 측정합니다. 실무 정확도로 해석하지 않습니다."""

import json
from importlib.resources import files
from pathlib import Path

from orderlens.retrieval import BM25Index

CASES = [
    ("배송 예정 시각을 넘긴 미완료 주문", "late-delivery"),
    ("지연 주문 운송장 상태 확인", "late-delivery"),
    ("중복 적재 버전 충돌", "duplicates"),
    ("revision 같은 내용 저장 생략", "duplicates"),
    ("유효 주문 금액 취소 환불", "money"),
    ("booked_amount_krw 회계 매출", "money"),
    ("음수 금액 오류 행 수정", "quality"),
    ("schema_error row_number", "quality"),
    ("UTC 시간대 조회 기간", "time-window"),
    ("start_at end_at 포함 제외", "time-window"),
    ("배송 지연율 분모", "delivery-rate"),
    ("late_delivery_rate 배송 완료 없으면", "delivery-rate"),
]
UNANSWERABLE = ["블랙홀 은하 천체", "피아노 바이올린", "야구 축구 배구"]


def main():
    documents = json.loads(files("orderlens.data").joinpath("knowledge.json").read_text("utf-8"))
    index = BM25Index(documents)
    rows = []
    for query, expected in CASES:
        ids = [item["document_id"] for item in index.search(query, 3)]
        rank = ids.index(expected) + 1 if expected in ids else None
        rows.append({"query": query, "expected": expected, "retrieved": ids, "rank": rank})
    unanswered = [
        {"query": query, "returned_count": len(index.search(query))} for query in UNANSWERABLE
    ]
    report = {
        "scope": "15 hand_written_demo_cases_not_independent_real_world_benchmark",
        "document_count": len(documents),
        "answerable_cases": len(rows),
        "top1_accuracy": sum(row["rank"] == 1 for row in rows) / len(rows),
        "recall_at_3": sum(row["rank"] is not None for row in rows) / len(rows),
        "mrr_at_3": sum(1 / row["rank"] if row["rank"] else 0 for row in rows) / len(rows),
        "empty_result_rate_on_unrelated": sum(row["returned_count"] == 0 for row in unanswered)
        / len(unanswered),
        "cases": rows,
        "unrelated_cases": unanswered,
    }
    destination = Path("artifacts/retrieval_evaluation.json")
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: value
                for key, value in report.items()
                if key not in {"cases", "unrelated_cases"}
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
