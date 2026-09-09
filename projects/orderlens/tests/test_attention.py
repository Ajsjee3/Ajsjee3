"""판매 경로 필터가 조회 한도·최신 상태·시간 경계와 함께 동작하는지 확인합니다."""

import pytest
from conftest import order

AS_OF = "2026-09-08T00:00:00Z"


def test_source_is_filtered_before_limit_and_keeps_priority(client):
    rows = [
        order("other-first", source="market_b", promised_by="2026-09-02T00:00:00Z"),
        order("a-later", promised_by="2026-09-04T00:00:00Z"),
        order("a-earlier", promised_by="2026-09-03T00:00:00Z"),
    ]
    assert client.post("/v1/ingestions", json={"rows": rows}).json()["accepted"] == 3
    response = client.get(
        "/v1/orders/attention", params={"as_of": AS_OF, "source": "market_a", "limit": 1}
    )
    assert response.status_code == 200
    assert [(item["source"], item["order_id"]) for item in response.json()["orders"]] == [
        ("market_a", "a-earlier")
    ]


def test_source_filter_preserves_latest_state_and_as_of(client):
    rows = [
        order("shared"),
        order("shared", revision=2, status="cancelled", updated_at="2026-09-05T00:00:00Z"),
        order("shared", source="market_b"),
        order("boundary", promised_by=AS_OF),
    ]
    assert client.post("/v1/ingestions", json={"rows": rows}).json()["accepted"] == 4
    earlier = client.get(
        "/v1/orders/attention",
        params={"as_of": "2026-09-04T00:00:00Z", "source": "market_a"},
    ).json()["orders"]
    assert [item["order_id"] for item in earlier] == ["shared"]
    later = client.get(
        "/v1/orders/attention", params={"as_of": AS_OF, "source": "market_a"}
    ).json()["orders"]
    assert later == []  # 취소된 주문과 마감 시각이 정확히 같은 주문은 제외됩니다.
    other = client.get(
        "/v1/orders/attention", params={"as_of": AS_OF, "source": "market_b"}
    ).json()["orders"]
    assert [(item["source"], item["order_id"]) for item in other] == [("market_b", "shared")]


def test_omitting_source_preserves_all_channels_and_empty_channel_is_empty(client):
    client.post("/v1/ingestions", json={"rows": [order(), order(source="market_b")]})
    all_orders = client.get("/v1/orders/attention", params={"as_of": AS_OF}).json()["orders"]
    assert {item["source"] for item in all_orders} == {"market_a", "market_b"}
    empty = client.get(
        "/v1/orders/attention", params={"as_of": AS_OF, "source": "own_store"}
    )
    assert empty.status_code == 200
    assert empty.json() == {"orders": []}


@pytest.mark.parametrize("source", ["unknown", ""])
def test_invalid_source_is_rejected_instead_of_returning_all_channels(client, source):
    response = client.get("/v1/orders/attention", params={"as_of": AS_OF, "source": source})
    assert response.status_code == 422
