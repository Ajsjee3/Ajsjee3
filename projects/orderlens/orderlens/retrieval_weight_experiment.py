"""개발 질의로 제목 가중치를 고르고 고정 평가로 한 번만 확인합니다."""

from collections.abc import Sequence

from orderlens.retrieval import DEFAULT_TITLE_WEIGHT
from orderlens.retrieval_evaluation import (
    calibrate_min_score,
    evaluate_abstention_policy,
    evaluate_bm25,
    load_bundled_calibration,
    load_bundled_evaluation,
)
from orderlens.retrieval_policy import DEFAULT_MIN_SCORE

TITLE_WEIGHT_CANDIDATES = (1.0, 1.5, 2.0, 3.0)


def _candidate_summary(calibration: dict) -> dict:
    return {
        "title_weight": calibration["title_weight"],
        "body_weight": calibration["body_weight"],
        "minimum_score": calibration["selected"]["minimum_score"],
        "answerable_correct_accept_rate": calibration["selected"][
            "answerable_correct_accept_rate"
        ],
        "unanswerable_abstention_rate": calibration["selected"][
            "unanswerable_abstention_rate"
        ],
        "balanced_correctness": calibration["selected"]["balanced_correctness"],
    }


def evaluate_title_weight_experiment(
    documents: list[dict],
    development_queries: dict,
    development_qrels: dict,
    frozen_queries: dict,
    frozen_qrels: dict,
    candidates: Sequence[float] = TITLE_WEIGHT_CANDIDATES,
) -> dict:
    """고정 평가는 후보 선택에 쓰지 않고 선택 결과의 채택 여부만 판단합니다."""

    unique_candidates = tuple(dict.fromkeys(candidates))
    if DEFAULT_TITLE_WEIGHT not in unique_candidates:
        raise ValueError("후보에는 현재 제목 가중치 1.0이 필요합니다.")

    development_candidates = []
    for title_weight in unique_candidates:
        calibration = calibrate_min_score(
            documents,
            development_queries,
            development_qrels,
            title_weight=title_weight,
        )
        development_candidates.append(_candidate_summary(calibration))

    selected = max(
        development_candidates,
        key=lambda item: (
            item["balanced_correctness"],
            item["answerable_correct_accept_rate"],
            -item["title_weight"],
            -item["minimum_score"],
        ),
    )
    baseline_policy = evaluate_abstention_policy(
        documents,
        frozen_queries,
        frozen_qrels,
        DEFAULT_MIN_SCORE,
        title_weight=DEFAULT_TITLE_WEIGHT,
    )
    selected_policy = evaluate_abstention_policy(
        documents,
        frozen_queries,
        frozen_qrels,
        selected["minimum_score"],
        title_weight=selected["title_weight"],
    )
    baseline_ranking = evaluate_bm25(
        documents,
        frozen_queries,
        frozen_qrels,
        title_weight=DEFAULT_TITLE_WEIGHT,
    )
    selected_ranking = evaluate_bm25(
        documents,
        frozen_queries,
        frozen_qrels,
        title_weight=selected["title_weight"],
    )

    baseline_success = baseline_policy["metrics"]["balanced_correctness"]
    selected_success = selected_policy["metrics"]["balanced_correctness"]
    adopted = selected_success > baseline_success
    return {
        "experiment_id": "orderlens-title-weight-v1",
        "development_dataset_id": development_queries["dataset_id"],
        "frozen_dataset_id": frozen_queries["dataset_id"],
        "candidate_selection_uses_frozen_evaluation": False,
        "selection_rule": (
            "highest_development_balanced_correctness_then_answerable_acceptance_"
            "then_smallest_title_weight_then_lowest_threshold"
        ),
        "go_no_go_rule": "adopt_only_if_frozen_balanced_correctness_strictly_improves",
        "development_candidates": development_candidates,
        "selected_on_development": selected,
        "frozen_comparison": {
            "runtime_baseline": {
                "ranking_metrics": baseline_ranking["metrics"],
                "policy": baseline_policy,
            },
            "development_selected": {
                "ranking_metrics": selected_ranking["metrics"],
                "policy": selected_policy,
            },
        },
        "decision": {
            "adopted": adopted,
            "runtime_title_weight": selected["title_weight"] if adopted else DEFAULT_TITLE_WEIGHT,
            "runtime_minimum_score": selected["minimum_score"] if adopted else DEFAULT_MIN_SCORE,
            "reason": (
                "frozen_balanced_correctness_improved"
                if adopted
                else "development_winner_did_not_improve_frozen_balanced_correctness"
            ),
        },
        "limits": [
            "개발·고정 질문은 수작업이며 실제 사용자 로그나 독립 평가가 아닙니다.",
            "제목 가중치는 제목 토큰 빈도에 곱하는 작은 실험이며 완전한 BM25F 구현이 아닙니다.",
            "고정 평가는 개발 후보 선택에 사용하지 않고 선택한 한 후보의 채택 여부에만 사용했습니다.",
        ],
    }


def evaluate_bundled_title_weight_experiment() -> dict:
    documents, development_queries, development_qrels = load_bundled_calibration()
    frozen_documents, frozen_queries, frozen_qrels = load_bundled_evaluation()
    if documents != frozen_documents:
        raise ValueError("개발·고정 평가의 문서 집합이 다릅니다.")
    return evaluate_title_weight_experiment(
        documents,
        development_queries,
        development_qrels,
        frozen_queries,
        frozen_qrels,
    )
