from copy import deepcopy

import pytest

from orderlens.retrieval_evaluation import (
    RetrievalEvaluationDataError,
    calibrate_min_score,
    evaluate_bm25,
    evaluate_bundled_bm25,
    load_bundled_calibration,
    load_bundled_evaluation,
)
from orderlens.retrieval_policy import DEFAULT_MIN_SCORE


def test_bundled_evaluation_separates_corpus_queries_and_qrels():
    documents, queries, qrels = load_bundled_evaluation()

    assert len(documents) == 10
    assert len(queries["queries"]) == 32
    assert len(qrels["relevance"]) == 24
    assert all(isinstance(relevant, list) for relevant in qrels["relevance"].values())
    assert "queries" not in qrels


def test_retrieval_report_keeps_metrics_and_failure_rows_consistent():
    documents, queries, qrels = load_bundled_evaluation()
    report = evaluate_bm25(documents, queries, qrels)

    assert report["answerable_query_count"] == 24
    assert report["unanswerable_query_count"] == 8
    assert len(report["answerable_cases"]) == 24
    assert len(report["unanswerable_cases"]) == 8
    assert report["failure_counts"]["answerable"] == len(report["answerable_failures"])
    assert report["failure_counts"]["unanswerable_false_positive"] == len(
        report["unanswerable_false_positives"]
    )
    assert report["metrics"] == {
        "top1_accuracy": 0.625,
        "recall_at_3": 0.9375,
        "mrr_at_3": 0.770833,
        "unanswerable_empty_result_rate": 0.25,
    }
    assert report["failure_counts"] == {
        "answerable": 9,
        "unanswerable_false_positive": 6,
    }


def test_calibration_is_separate_and_reproduces_bundled_threshold():
    _, evaluation_queries, _ = load_bundled_evaluation()
    documents, calibration_queries, calibration_qrels = load_bundled_calibration()

    assert {row["id"] for row in calibration_queries["queries"]}.isdisjoint(
        row["id"] for row in evaluation_queries["queries"]
    )
    assert {row["text"] for row in calibration_queries["queries"]}.isdisjoint(
        row["text"] for row in evaluation_queries["queries"]
    )
    report = calibrate_min_score(documents, calibration_queries, calibration_qrels)
    assert report["answerable_query_count"] == 16
    assert report["unanswerable_query_count"] == 10
    assert report["selected"] == {
        "minimum_score": DEFAULT_MIN_SCORE,
        "answerable_correct_accept_rate": 0.875,
        "unanswerable_abstention_rate": 0.9,
        "balanced_correctness": 0.8875,
    }


def test_frozen_evaluation_reports_abstention_tradeoff():
    policy = evaluate_bundled_bm25()["abstention_policy"]["frozen_evaluation"]

    assert policy["metrics"] == {
        "answerable_correct_accept_rate": 0.625,
        "unanswerable_abstention_rate": 0.875,
        "balanced_correctness": 0.75,
        "answerable_accept_rate": 0.916667,
        "accepted_result_precision": 0.652174,
    }
    assert policy["failure_counts"] == {
        "answerable_false_abstention": 2,
        "wrong_answerable_accept": 7,
        "unanswerable_false_accept": 1,
    }


def test_evaluation_rejects_answerable_query_without_qrel():
    documents, queries, qrels = load_bundled_evaluation()
    broken_qrels = deepcopy(qrels)
    broken_qrels["relevance"].pop("q01")

    with pytest.raises(RetrievalEvaluationDataError, match="qrels 키"):
        evaluate_bm25(documents, queries, broken_qrels)


def test_evaluation_rejects_unknown_relevant_document():
    documents, queries, qrels = load_bundled_evaluation()
    broken_qrels = deepcopy(qrels)
    broken_qrels["relevance"]["q01"] = ["missing-document"]

    with pytest.raises(RetrievalEvaluationDataError, match="알 수 없는 문서"):
        evaluate_bm25(documents, queries, broken_qrels)
