import pytest

from orderlens.retrieval import BM25Index
from orderlens.retrieval_weight_experiment import evaluate_bundled_title_weight_experiment


def test_title_weight_can_change_ranking_without_copying_title_text_into_body():
    documents = [
        {"id": "title", "version": "1", "title": "alpha", "text": "x"},
        {"id": "body", "version": "1", "title": "x", "text": "alpha alpha"},
    ]

    baseline = BM25Index(documents, title_weight=1.0).search("alpha")
    weighted = BM25Index(documents, title_weight=2.0).search("alpha")

    assert baseline[0]["document_id"] == "body"
    assert weighted[0]["document_id"] == "title"


@pytest.mark.parametrize("title_weight", [0.0, 0.5, float("inf"), float("nan")])
def test_title_weight_rejects_values_outside_the_experiment_contract(title_weight):
    with pytest.raises(ValueError, match="1.0 이상"):
        BM25Index([], title_weight=title_weight)


def test_development_winner_is_not_adopted_when_frozen_success_falls():
    report = evaluate_bundled_title_weight_experiment()
    baseline = report["frozen_comparison"]["runtime_baseline"]
    selected = report["frozen_comparison"]["development_selected"]

    assert report["candidate_selection_uses_frozen_evaluation"] is False
    assert report["selected_on_development"] == {
        "title_weight": 1.5,
        "body_weight": 1.0,
        "minimum_score": 4.186289,
        "answerable_correct_accept_rate": 0.8125,
        "unanswerable_abstention_rate": 1.0,
        "balanced_correctness": 0.90625,
    }
    assert baseline["policy"]["metrics"]["balanced_correctness"] == 0.75
    assert selected["policy"]["metrics"]["balanced_correctness"] == 0.729167
    assert selected["ranking_metrics"]["top1_accuracy"] == 0.666667
    assert report["decision"] == {
        "adopted": False,
        "runtime_title_weight": 1.0,
        "runtime_minimum_score": 3.197979,
        "reason": "development_winner_did_not_improve_frozen_balanced_correctness",
    }
