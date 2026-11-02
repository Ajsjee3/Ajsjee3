import pytest

from orderlens.retrieval_policy import BM25AbstentionPolicy


def test_policy_keeps_only_matches_at_or_above_boundary():
    policy = BM25AbstentionPolicy(3.0)
    decision = policy.apply(
        [
            {"document_id": "kept", "score": 3.0},
            {"document_id": "removed", "score": 2.999999},
        ]
    )

    assert [item["document_id"] for item in decision.matches] == ["kept"]
    assert decision.abstained is False
    assert decision.top_score == 3.0


def test_policy_explains_low_score_and_empty_result_differently():
    policy = BM25AbstentionPolicy(3.0)

    low = policy.apply([{"document_id": "weak", "score": 2.0}])
    empty = policy.apply([])

    assert low.abstention_reason == "top_score_below_minimum"
    assert low.top_score == 2.0
    assert empty.abstention_reason == "no_token_overlap"
    assert empty.top_score is None


def test_policy_rejects_non_positive_threshold():
    with pytest.raises(ValueError, match="0보다 커야"):
        BM25AbstentionPolicy(0)
