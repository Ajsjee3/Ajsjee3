"""고정 질의·관련 문서 표로 BM25 검색 기준선을 재현합니다."""

import json
from importlib.resources import files

from orderlens.retrieval import BM25Index


class RetrievalEvaluationDataError(ValueError):
    """평가 corpus, query, qrels 계약이 서로 맞지 않을 때 발생합니다."""


def load_bundled_evaluation() -> tuple[list[dict], dict, dict]:
    data = files("orderlens.data")
    documents = json.loads(data.joinpath("knowledge.json").read_text("utf-8"))
    queries = json.loads(data.joinpath("retrieval_queries.json").read_text("utf-8"))
    qrels = json.loads(data.joinpath("retrieval_qrels.json").read_text("utf-8"))
    validate_evaluation_data(documents, queries, qrels)
    return documents, queries, qrels


def validate_evaluation_data(documents: list[dict], queries: dict, qrels: dict) -> None:
    document_ids = [item.get("id") for item in documents]
    if not document_ids or any(not isinstance(item, str) or not item for item in document_ids):
        raise RetrievalEvaluationDataError("문서에는 비어 있지 않은 id가 필요합니다.")
    if len(document_ids) != len(set(document_ids)):
        raise RetrievalEvaluationDataError("문서 id가 중복됐습니다.")

    if queries.get("dataset_id") != qrels.get("dataset_id"):
        raise RetrievalEvaluationDataError("질의와 qrels의 dataset_id가 다릅니다.")
    query_rows = queries.get("queries")
    if not isinstance(query_rows, list) or not query_rows:
        raise RetrievalEvaluationDataError("평가 질의가 없습니다.")

    query_ids = [item.get("id") for item in query_rows]
    if any(not isinstance(item, str) or not item for item in query_ids):
        raise RetrievalEvaluationDataError("질의에는 비어 있지 않은 id가 필요합니다.")
    if len(query_ids) != len(set(query_ids)):
        raise RetrievalEvaluationDataError("질의 id가 중복됐습니다.")
    if any(not isinstance(item.get("text"), str) or not item["text"].strip() for item in query_rows):
        raise RetrievalEvaluationDataError("질의 본문이 비었습니다.")
    if any(item.get("kind") not in {"answerable", "unanswerable"} for item in query_rows):
        raise RetrievalEvaluationDataError("질의 kind가 올바르지 않습니다.")

    relevance = qrels.get("relevance")
    if not isinstance(relevance, dict):
        raise RetrievalEvaluationDataError("qrels relevance가 필요합니다.")
    answerable_ids = {item["id"] for item in query_rows if item["kind"] == "answerable"}
    unanswerable_ids = {item["id"] for item in query_rows if item["kind"] == "unanswerable"}
    if not answerable_ids or not unanswerable_ids:
        raise RetrievalEvaluationDataError("answerable과 unanswerable 질의가 모두 필요합니다.")
    if set(relevance) != answerable_ids:
        raise RetrievalEvaluationDataError("answerable 질의와 qrels 키가 일치하지 않습니다.")
    if set(relevance) & unanswerable_ids:
        raise RetrievalEvaluationDataError("unanswerable 질의에는 관련 문서가 없어야 합니다.")

    known_documents = set(document_ids)
    for query_id, relevant_ids in relevance.items():
        if not isinstance(relevant_ids, list) or not relevant_ids:
            raise RetrievalEvaluationDataError(f"{query_id}의 관련 문서가 없습니다.")
        if len(relevant_ids) != len(set(relevant_ids)):
            raise RetrievalEvaluationDataError(f"{query_id}의 관련 문서가 중복됐습니다.")
        unknown = set(relevant_ids) - known_documents
        if unknown:
            raise RetrievalEvaluationDataError(
                f"{query_id}가 알 수 없는 문서를 참조합니다: {sorted(unknown)}"
            )


def evaluate_bm25(documents: list[dict], queries: dict, qrels: dict, top_k: int = 3) -> dict:
    if top_k < 1:
        raise ValueError("top_k는 1 이상이어야 합니다.")
    validate_evaluation_data(documents, queries, qrels)
    index = BM25Index(documents)
    relevance = qrels["relevance"]
    answerable_rows = []
    unanswerable_rows = []

    for query in queries["queries"]:
        matches = index.search(query["text"], top_k=top_k)
        retrieved = [item["document_id"] for item in matches]
        if query["kind"] == "unanswerable":
            unanswerable_rows.append(
                {
                    "id": query["id"],
                    "query": query["text"],
                    "category": query["category"],
                    "retrieved": retrieved,
                    "returned_count": len(retrieved),
                }
            )
            continue

        relevant = relevance[query["id"]]
        ranks = [retrieved.index(item) + 1 for item in relevant if item in retrieved]
        first_relevant_rank = min(ranks) if ranks else None
        answerable_rows.append(
            {
                "id": query["id"],
                "query": query["text"],
                "category": query["category"],
                "relevant": relevant,
                "retrieved": retrieved,
                "first_relevant_rank": first_relevant_rank,
                "relevant_in_top_k": len(ranks),
            }
        )

    answerable_count = len(answerable_rows)
    unanswerable_count = len(unanswerable_rows)
    metrics = {
        "top1_accuracy": round(
            sum(row["first_relevant_rank"] == 1 for row in answerable_rows) / answerable_count,
            6,
        ),
        f"recall_at_{top_k}": round(
            sum(row["relevant_in_top_k"] / len(row["relevant"]) for row in answerable_rows)
            / answerable_count,
            6,
        ),
        f"mrr_at_{top_k}": round(
            sum(
                1 / row["first_relevant_rank"] if row["first_relevant_rank"] else 0
                for row in answerable_rows
            )
            / answerable_count,
            6,
        ),
        "unanswerable_empty_result_rate": round(
            sum(row["returned_count"] == 0 for row in unanswerable_rows) / unanswerable_count,
            6,
        ),
    }
    answerable_failures = [
        row
        for row in answerable_rows
        if row["first_relevant_rank"] != 1
        or row["relevant_in_top_k"] != len(row["relevant"])
    ]
    unanswerable_false_positives = [
        row for row in unanswerable_rows if row["returned_count"] > 0
    ]
    return {
        "dataset_id": queries["dataset_id"],
        "frozen_on": queries["frozen_on"],
        "query_origin": queries["query_origin"],
        "retriever": "orderlens_bm25_korean_bigrams",
        "top_k": top_k,
        "score_is_probability": False,
        "document_count": len(documents),
        "answerable_query_count": answerable_count,
        "unanswerable_query_count": unanswerable_count,
        "metrics": metrics,
        "failure_counts": {
            "answerable": len(answerable_failures),
            "unanswerable_false_positive": len(unanswerable_false_positives),
        },
        "answerable_failures": answerable_failures,
        "unanswerable_false_positives": unanswerable_false_positives,
        "answerable_cases": answerable_rows,
        "unanswerable_cases": unanswerable_rows,
        "limits": [
            "질의는 수작업 고정 예제이며 실제 사용자 로그가 아닙니다.",
            "평가 자료 작성자와 검색 구현자가 분리된 독립 평가가 아닙니다.",
            "한 번의 작은 한국어 corpus 결과를 실무 정확도로 일반화하지 않습니다.",
        ],
    }


def evaluate_bundled_bm25(top_k: int = 3) -> dict:
    documents, queries, qrels = load_bundled_evaluation()
    return evaluate_bm25(documents, queries, qrels, top_k=top_k)
