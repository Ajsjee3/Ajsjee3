"""제목·본문 가중치 실험 결과를 재현 가능한 JSON으로 저장합니다."""

import json
from pathlib import Path

from orderlens.retrieval_weight_experiment import evaluate_bundled_title_weight_experiment


def main():
    report = evaluate_bundled_title_weight_experiment()
    destination = Path("artifacts/retrieval_field_weight_experiment.json")
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    baseline = report["frozen_comparison"]["runtime_baseline"]
    selected = report["frozen_comparison"]["development_selected"]
    print(
        json.dumps(
            {
                "selected_on_development": report["selected_on_development"],
                "frozen_baseline": {
                    "ranking": baseline["ranking_metrics"],
                    "policy": baseline["policy"]["metrics"],
                    "failures": baseline["policy"]["failure_counts"],
                },
                "frozen_selected": {
                    "ranking": selected["ranking_metrics"],
                    "policy": selected["policy"]["metrics"],
                    "failures": selected["policy"]["failure_counts"],
                },
                "decision": report["decision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
