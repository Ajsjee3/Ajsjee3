"""검색 문서를 그대로 인용하는 결정론적 답변 계약입니다."""

from dataclasses import dataclass

from orderlens.retrieval import BM25Index
from orderlens.retrieval_policy import BM25AbstentionPolicy

CONTRACT_VERSION = "grounded-answer-v1"


@dataclass(frozen=True)
class Citation:
    document_id: str
    title: str
    source: str
    version: str
    quote: str
    retrieval_score: float

    def as_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "source": self.source,
            "version": self.version,
            "quote": self.quote,
            "retrieval_score": self.retrieval_score,
        }


@dataclass(frozen=True)
class GroundedAnswer:
    query: str
    answer: str | None
    citations: tuple[Citation, ...]
    minimum_score: float
    top_score: float | None
    abstained: bool
    abstention_reason: str | None

    def as_dict(self) -> dict:
        return {
            "mode": "extractive_document_quote",
            "contract_version": CONTRACT_VERSION,
            "score_is_probability": False,
            "query": self.query,
            "answer": self.answer,
            "citations": [citation.as_dict() for citation in self.citations],
            "minimum_score": self.minimum_score,
            "top_score": self.top_score,
            "abstained": self.abstained,
            "abstention_reason": self.abstention_reason,
        }


class ExtractiveGroundedAnswerer:
    """수용된 첫 문서만 그대로 반환해 답변과 근거가 갈라지지 않게 합니다."""

    def __init__(self, index: BM25Index, policy: BM25AbstentionPolicy):
        self.index = index
        self.policy = policy

    def answer(self, query: str) -> GroundedAnswer:
        decision = self.policy.search(self.index, query, top_k=1)
        if decision.abstained:
            return GroundedAnswer(
                query=query,
                answer=None,
                citations=(),
                minimum_score=decision.minimum_score,
                top_score=decision.top_score,
                abstained=True,
                abstention_reason=decision.abstention_reason,
            )

        match = decision.matches[0]
        citation = Citation(
            document_id=match["document_id"],
            title=match["title"],
            source=match["source"],
            version=match["version"],
            quote=match["excerpt"],
            retrieval_score=match["score"],
        )
        return GroundedAnswer(
            query=query,
            answer=citation.quote,
            citations=(citation,),
            minimum_score=decision.minimum_score,
            top_score=decision.top_score,
            abstained=False,
            abstention_reason=None,
        )


def contract_errors(response: dict) -> list[str]:
    """직렬화된 답변에서 근거 누락·불일치를 찾습니다."""

    errors = []
    if response.get("mode") != "extractive_document_quote":
        errors.append("unexpected_mode")
    if response.get("contract_version") != CONTRACT_VERSION:
        errors.append("unexpected_contract_version")
    if response.get("score_is_probability") is not False:
        errors.append("score_probability_flag_invalid")
    if not isinstance(response.get("query"), str) or not response["query"]:
        errors.append("query_missing")
    citations = response.get("citations")
    if not isinstance(citations, list):
        return ["citations_not_list"]

    if response.get("abstained"):
        if response.get("answer") is not None:
            errors.append("abstained_with_answer")
        if citations:
            errors.append("abstained_with_citation")
        if not response.get("abstention_reason"):
            errors.append("abstained_without_reason")
        return errors

    if not isinstance(response.get("answer"), str) or not response["answer"]:
        errors.append("answered_without_text")
    if len(citations) != 1:
        errors.append("answered_without_single_citation")
        return errors

    citation = citations[0]
    required = ("document_id", "title", "source", "version", "quote", "retrieval_score")
    if any(citation.get(field) in (None, "") for field in required):
        errors.append("citation_metadata_incomplete")
    if response.get("answer") != citation.get("quote"):
        errors.append("answer_quote_mismatch")
    if citation.get("retrieval_score") != response.get("top_score"):
        errors.append("citation_score_mismatch")
    if response.get("abstention_reason") is not None:
        errors.append("answered_with_abstention_reason")
    return errors
