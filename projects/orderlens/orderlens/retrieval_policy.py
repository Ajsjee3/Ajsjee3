"""BM25 점수 기준으로 근거가 약한 검색 결과를 보류합니다."""

from dataclasses import dataclass

from orderlens.retrieval import BM25Index

# retrieval_calibration_v1에서 재현한 값입니다. BM25 점수는 확률이 아니며,
# corpus나 토큰화가 바뀌면 scripts.evaluate_retrieval로 다시 확인해야 합니다.
DEFAULT_MIN_SCORE = 3.197979


@dataclass(frozen=True)
class RetrievalDecision:
    matches: list[dict]
    minimum_score: float
    top_score: float | None
    abstained: bool
    abstention_reason: str | None

    def as_dict(self) -> dict:
        return {
            "minimum_score": self.minimum_score,
            "top_score": self.top_score,
            "abstained": self.abstained,
            "abstention_reason": self.abstention_reason,
            "matches": self.matches,
        }


class BM25AbstentionPolicy:
    def __init__(self, minimum_score: float = DEFAULT_MIN_SCORE):
        if minimum_score <= 0:
            raise ValueError("minimum_score는 0보다 커야 합니다.")
        self.minimum_score = minimum_score

    def apply(self, matches: list[dict]) -> RetrievalDecision:
        top_score = matches[0]["score"] if matches else None
        filtered = [item for item in matches if item["score"] >= self.minimum_score]
        if filtered:
            reason = None
        elif matches:
            reason = "top_score_below_minimum"
        else:
            reason = "no_token_overlap"
        return RetrievalDecision(
            matches=filtered,
            minimum_score=self.minimum_score,
            top_score=top_score,
            abstained=not filtered,
            abstention_reason=reason,
        )

    def search(self, index: BM25Index, query: str, top_k: int = 3) -> RetrievalDecision:
        return self.apply(index.search(query, top_k=top_k))
