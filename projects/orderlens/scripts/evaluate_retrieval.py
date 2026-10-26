"""분리된 고정 질의·qrels로 검색 기준선을 측정합니다."""

import json
from pathlib import Path

from orderlens.retrieval_evaluation import evaluate_bundled_bm25


def main():
    report = evaluate_bundled_bm25()
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
                if key
                not in {
                    "answerable_cases",
                    "unanswerable_cases",
                    "answerable_failures",
                    "unanswerable_false_positives",
                    "limits",
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
