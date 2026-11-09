"""고정 질문으로 인용 답변의 근거 누락과 문서 관련성을 재현합니다."""

import json
from pathlib import Path

from orderlens.grounded_answer_evaluation import evaluate_bundled_grounded_answers


def main():
    report = evaluate_bundled_grounded_answers()
    destination = Path("artifacts/grounded_answer_evaluation.json")
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "dataset_id": report["dataset_id"],
                "response_mode": report["response_mode"],
                "metrics": report["metrics"],
                "failures": report["failure_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
