"""고정 검색 질문으로 인용 답변 계약과 문서 관련성을 함께 평가합니다."""

from orderlens.grounded_answer import ExtractiveGroundedAnswerer, contract_errors
from orderlens.retrieval import BM25Index
from orderlens.retrieval_evaluation import load_bundled_evaluation, validate_evaluation_data
from orderlens.retrieval_policy import BM25AbstentionPolicy


def evaluate_grounded_answers(documents: list[dict], queries: dict, qrels: dict) -> dict:
    validate_evaluation_data(documents, queries, qrels)
    answerer = ExtractiveGroundedAnswerer(BM25Index(documents), BM25AbstentionPolicy())
    relevance = qrels["relevance"]
    cases = []

    for query in queries["queries"]:
        response = answerer.answer(query["text"]).as_dict()
        errors = contract_errors(response)
        citation_ids = [item["document_id"] for item in response["citations"]]
        relevant = relevance.get(query["id"], [])
        cited_relevant_document = bool(set(citation_ids) & set(relevant))
        cases.append(
            {
                "id": query["id"],
                "query": query["text"],
                "kind": query["kind"],
                "category": query["category"],
                "relevant": relevant,
                "answered": not response["abstained"],
                "abstention_reason": response["abstention_reason"],
                "citation_ids": citation_ids,
                "cited_relevant_document": cited_relevant_document,
                "contract_errors": errors,
            }
        )

    answerable = [case for case in cases if case["kind"] == "answerable"]
    unanswerable = [case for case in cases if case["kind"] == "unanswerable"]
    answered = [case for case in cases if case["answered"]]
    answered_answerable = [case for case in answerable if case["answered"]]
    supported_answerable = [case for case in answerable if case["cited_relevant_document"]]
    contract_failures = [case for case in cases if case["contract_errors"]]
    answerable_abstentions = [case for case in answerable if not case["answered"]]
    answerable_wrong_citations = [
        case for case in answered_answerable if not case["cited_relevant_document"]
    ]
    unanswerable_answers = [case for case in unanswerable if case["answered"]]

    answerable_supported_rate = len(supported_answerable) / len(answerable)
    unanswerable_abstention_rate = sum(not case["answered"] for case in unanswerable) / len(
        unanswerable
    )
    return {
        "dataset_id": queries["dataset_id"],
        "frozen_on": queries["frozen_on"],
        "response_mode": "extractive_document_quote",
        "answerable_query_count": len(answerable),
        "unanswerable_query_count": len(unanswerable),
        "answered_count": len(answered),
        "metrics": {
            "contract_integrity_rate": round(
                (len(cases) - len(contract_failures)) / len(cases), 6
            ),
            "answer_without_citation_rate": round(
                sum(
                    "answered_without_single_citation" in case["contract_errors"]
                    for case in answered
                )
                / len(answered)
                if answered
                else 0.0,
                6,
            ),
            "answer_quote_mismatch_rate": round(
                sum("answer_quote_mismatch" in case["contract_errors"] for case in answered)
                / len(answered)
                if answered
                else 0.0,
                6,
            ),
            "answerable_supported_answer_rate": round(answerable_supported_rate, 6),
            "answered_answerable_relevant_citation_rate": round(
                len(supported_answerable) / len(answered_answerable)
                if answered_answerable
                else 0.0,
                6,
            ),
            "unanswerable_abstention_rate": round(unanswerable_abstention_rate, 6),
            "balanced_task_success": round(
                (answerable_supported_rate + unanswerable_abstention_rate) / 2, 6
            ),
        },
        "failure_counts": {
            "contract_failure": len(contract_failures),
            "answerable_abstention": len(answerable_abstentions),
            "answerable_wrong_citation": len(answerable_wrong_citations),
            "unanswerable_answered": len(unanswerable_answers),
        },
        "contract_failures": contract_failures,
        "answerable_abstentions": answerable_abstentions,
        "answerable_wrong_citations": answerable_wrong_citations,
        "unanswerable_answers": unanswerable_answers,
        "cases": cases,
        "limits": [
            "답변은 검색 1위 문서 전문을 그대로 반환하며 문장을 새로 생성하거나 요약하지 않습니다.",
            "인용 형식이 완전해도 검색된 문서가 질문에 맞는다는 뜻은 아닙니다.",
            "수작업 고정 질문이며 실제 사용자 로그나 독립 평가가 아닙니다.",
        ],
    }


def evaluate_bundled_grounded_answers() -> dict:
    documents, queries, qrels = load_bundled_evaluation()
    return evaluate_grounded_answers(documents, queries, qrels)
