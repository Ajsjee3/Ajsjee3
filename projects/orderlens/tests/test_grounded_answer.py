from copy import deepcopy

from orderlens.grounded_answer import (
    ExtractiveGroundedAnswerer,
    contract_errors,
)
from orderlens.grounded_answer_evaluation import evaluate_bundled_grounded_answers
from orderlens.retrieval import BM25Index
from orderlens.retrieval_evaluation import load_bundled_evaluation
from orderlens.retrieval_policy import BM25AbstentionPolicy


def answerer():
    documents, _, _ = load_bundled_evaluation()
    return ExtractiveGroundedAnswerer(BM25Index(documents), BM25AbstentionPolicy())


def test_answer_is_exactly_the_cited_document_quote():
    response = answerer().answer("중복 적재 버전 충돌").as_dict()

    assert response["mode"] == "extractive_document_quote"
    assert response["contract_version"] == "grounded-answer-v1"
    assert response["abstained"] is False
    assert response["answer"] == response["citations"][0]["quote"]
    assert response["citations"][0]["document_id"] == "duplicates"
    assert response["citations"][0]["version"] == "1"
    assert response["citations"][0]["retrieval_score"] == response["top_score"]
    assert contract_errors(response) == []


def test_abstention_has_neither_answer_nor_citation():
    response = answerer().answer("블랙홀 은하 천체").as_dict()

    assert response["abstained"] is True
    assert response["abstention_reason"] == "no_token_overlap"
    assert response["answer"] is None
    assert response["citations"] == []
    assert contract_errors(response) == []


def test_contract_check_finds_missing_and_mismatched_grounding():
    valid = answerer().answer("중복 적재 버전 충돌").as_dict()
    missing = deepcopy(valid)
    missing["citations"] = []
    mismatched = deepcopy(valid)
    mismatched["citations"][0]["quote"] = "근거에 없는 문장"

    assert contract_errors(missing) == ["answered_without_single_citation"]
    assert contract_errors(mismatched) == ["answer_quote_mismatch"]


def test_fixed_questions_report_contract_and_relevance_separately():
    report = evaluate_bundled_grounded_answers()

    assert report["answerable_query_count"] == 24
    assert report["unanswerable_query_count"] == 8
    assert report["answered_count"] == 23
    assert report["metrics"] == {
        "contract_integrity_rate": 1.0,
        "answer_without_citation_rate": 0.0,
        "answer_quote_mismatch_rate": 0.0,
        "answerable_supported_answer_rate": 0.625,
        "answered_answerable_relevant_citation_rate": 0.681818,
        "unanswerable_abstention_rate": 0.875,
        "balanced_task_success": 0.75,
    }
    assert report["failure_counts"] == {
        "contract_failure": 0,
        "answerable_abstention": 2,
        "answerable_wrong_citation": 7,
        "unanswerable_answered": 1,
    }
