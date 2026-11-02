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
                "dataset_id": report["dataset_id"],
                "baseline_metrics": report["metrics"],
                "calibration": report["abstention_policy"]["calibration"]["selected"],
                "frozen_policy_metrics": report["abstention_policy"]["frozen_evaluation"][
                    "metrics"
                ],
                "frozen_policy_failures": report["abstention_policy"]["frozen_evaluation"][
                    "failure_counts"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
