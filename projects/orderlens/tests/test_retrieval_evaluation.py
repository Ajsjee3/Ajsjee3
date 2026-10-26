from copy import deepcopy

import pytest

from orderlens.retrieval_evaluation import (
    RetrievalEvaluationDataError,
    evaluate_bm25,
    load_bundled_evaluation,
)


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
