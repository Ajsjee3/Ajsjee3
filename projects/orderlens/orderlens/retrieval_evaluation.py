"""고정 질의·관련 문서 표로 BM25 검색 기준선을 재현합니다."""

import json
from importlib.resources import files

from orderlens.retrieval import BM25Index
from orderlens.retrieval_policy import DEFAULT_MIN_SCORE, BM25AbstentionPolicy


class RetrievalEvaluationDataError(ValueError):
    """평가 corpus, query, qrels 계약이 서로 맞지 않을 때 발생합니다."""


def load_bundled_evaluation() -> tuple[list[dict], dict, dict]:
    data = files("orderlens.data")
    documents = json.loads(data.joinpath("knowledge.json").read_text("utf-8"))
    queries = json.loads(data.joinpath("retrieval_queries.json").read_text("utf-8"))
    qrels = json.loads(data.joinpath("retrieval_qrels.json").read_text("utf-8"))
    validate_evaluation_data(documents, queries, qrels)
    return documents, queries, qrels


def load_bundled_calibration() -> tuple[list[dict], dict, dict]:
    data = files("orderlens.data")
    documents = json.loads(data.joinpath("knowledge.json").read_text("utf-8"))
    queries = json.loads(data.joinpath("retrieval_calibration_queries.json").read_text("utf-8"))
    qrels = json.loads(data.joinpath("retrieval_calibration_qrels.json").read_text("utf-8"))
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
    if any(
        not isinstance(item.get("text"), str) or not item["text"].strip() for item in query_rows
    ):
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
        scores = [item["score"] for item in matches]
        if query["kind"] == "unanswerable":
            unanswerable_rows.append(
                {
                    "id": query["id"],
                    "query": query["text"],
                    "category": query["category"],
                    "retrieved": retrieved,
                    "scores": scores,
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
                "scores": scores,
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
        if row["first_relevant_rank"] != 1 or row["relevant_in_top_k"] != len(row["relevant"])
    ]
    unanswerable_false_positives = [row for row in unanswerable_rows if row["returned_count"] > 0]
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


def _policy_rows(documents: list[dict], queries: dict, qrels: dict, top_k: int) -> list[dict]:
    validate_evaluation_data(documents, queries, qrels)
    index = BM25Index(documents)
    rows = []
    for query in queries["queries"]:
        matches = index.search(query["text"], top_k=top_k)
        top_document_id = matches[0]["document_id"] if matches else None
        top_score = matches[0]["score"] if matches else 0.0
        relevant = qrels["relevance"].get(query["id"], [])
        rows.append(
            {
                "id": query["id"],
                "query": query["text"],
                "kind": query["kind"],
                "category": query["category"],
                "top_document_id": top_document_id,
                "top_score": top_score,
                "top1_correct": top_document_id in relevant,
            }
        )
    return rows


def _candidate_thresholds(rows: list[dict]) -> list[float]:
    scores = sorted({0.0, *(row["top_score"] for row in rows)})
    midpoints = [round((left + right) / 2, 6) for left, right in zip(scores, scores[1:])]
    return [0.0, *midpoints, round(scores[-1] + 0.000001, 6)]


def _policy_metrics(rows: list[dict], threshold: float) -> dict:
    answerable = [row for row in rows if row["kind"] == "answerable"]
    unanswerable = [row for row in rows if row["kind"] == "unanswerable"]
    correct_accepts = sum(
        row["top1_correct"] and row["top_score"] >= threshold for row in answerable
    )
    abstentions = sum(row["top_score"] < threshold for row in unanswerable)
    answerable_rate = correct_accepts / len(answerable)
    unanswerable_rate = abstentions / len(unanswerable)
    return {
        "answerable_correct_accept_rate": round(answerable_rate, 6),
        "unanswerable_abstention_rate": round(unanswerable_rate, 6),
        "balanced_correctness": round((answerable_rate + unanswerable_rate) / 2, 6),
    }


def calibrate_min_score(documents: list[dict], queries: dict, qrels: dict, top_k: int = 3) -> dict:
    """개발용 질의에서만 점수 기준을 고릅니다. 고정 평가는 선택에 쓰지 않습니다."""
    rows = _policy_rows(documents, queries, qrels, top_k)
    candidates = []
    for threshold in _candidate_thresholds(rows):
        metrics = _policy_metrics(rows, threshold)
        candidates.append({"minimum_score": threshold, **metrics})
    selected = max(
        candidates,
        key=lambda item: (
            item["balanced_correctness"],
            item["answerable_correct_accept_rate"],
            -item["minimum_score"],
        ),
    )
    return {
        "dataset_id": queries["dataset_id"],
        "created_on": queries["created_on"],
        "query_origin": queries["query_origin"],
        "selection_metric": queries["selection_metric"],
        "tie_breaker": "higher_answerable_correct_acceptance_then_lower_threshold",
        "answerable_query_count": sum(row["kind"] == "answerable" for row in rows),
        "unanswerable_query_count": sum(row["kind"] == "unanswerable" for row in rows),
        "selected": selected,
        "cases": rows,
    }


def evaluate_abstention_policy(
    documents: list[dict],
    queries: dict,
    qrels: dict,
    minimum_score: float,
    top_k: int = 3,
) -> dict:
    rows = _policy_rows(documents, queries, qrels, top_k)
    policy = BM25AbstentionPolicy(minimum_score)
    index = BM25Index(documents)
    accepted_count = 0
    correct_accept_count = 0
    false_abstentions = []
    wrong_answerable_accepts = []
    unanswerable_false_accepts = []

    for row in rows:
        decision = policy.search(index, row["query"], top_k=top_k)
        row.update(
            {
                "accepted": not decision.abstained,
                "abstention_reason": decision.abstention_reason,
                "returned": [item["document_id"] for item in decision.matches],
            }
        )
        if not decision.abstained:
            accepted_count += 1
        if row["kind"] == "answerable":
            if not decision.abstained and row["top1_correct"]:
                correct_accept_count += 1
            elif decision.abstained:
                false_abstentions.append(row)
            else:
                wrong_answerable_accepts.append(row)
        elif not decision.abstained:
            unanswerable_false_accepts.append(row)

    metrics = _policy_metrics(rows, minimum_score)
    metrics.update(
        {
            "answerable_accept_rate": round(
                sum(row["kind"] == "answerable" and row["accepted"] for row in rows)
                / sum(row["kind"] == "answerable" for row in rows),
                6,
            ),
            "accepted_result_precision": round(
                correct_accept_count / accepted_count if accepted_count else 0.0, 6
            ),
        }
    )
    return {
        "minimum_score": minimum_score,
        "score_is_probability": False,
        "metrics": metrics,
        "failure_counts": {
            "answerable_false_abstention": len(false_abstentions),
            "wrong_answerable_accept": len(wrong_answerable_accepts),
            "unanswerable_false_accept": len(unanswerable_false_accepts),
        },
        "answerable_false_abstentions": false_abstentions,
        "wrong_answerable_accepts": wrong_answerable_accepts,
        "unanswerable_false_accepts": unanswerable_false_accepts,
        "cases": rows,
        "limits": [
            "점수 기준은 수작업 개발 질의에서 정했으며 실제 사용자 질문 분포가 아닙니다.",
            "BM25 점수는 확률이 아니고 현재 문서와 토큰화에만 적용됩니다.",
            "문서나 토큰화가 바뀌면 개발 자료로 기준을 다시 정한 뒤 새 고정 평가가 필요합니다.",
        ],
    }


def evaluate_bundled_bm25(top_k: int = 3) -> dict:
    documents, queries, qrels = load_bundled_evaluation()
    report = evaluate_bm25(documents, queries, qrels, top_k=top_k)
    calibration_documents, calibration_queries, calibration_qrels = load_bundled_calibration()
    calibration = calibrate_min_score(
        calibration_documents, calibration_queries, calibration_qrels, top_k=top_k
    )
    report["abstention_policy"] = {
        "calibration": calibration,
        "frozen_evaluation": evaluate_abstention_policy(
            documents, queries, qrels, DEFAULT_MIN_SCORE, top_k=top_k
        ),
    }
    return report
