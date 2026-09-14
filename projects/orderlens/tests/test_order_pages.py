"""페이지 경계와 최신 상태·판매 경로 필터를 함께 검증합니다."""

from datetime import datetime, timedelta

import pytest
from conftest import order

AS_OF = "2026-09-08T00:00:00Z"


def ingest_rows(client, rows):
    response = client.post("/v1/ingestions", json={"rows": rows})
    assert response.status_code == 200
    assert response.json()["accepted"] == len(rows)


def page(client, **params):
    response = client.get("/v1/orders", params={"as_of": AS_OF, **params})
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize("limit", [1, 2, 3, 4, 100])
def test_pages_cover_fixed_data_once_with_deterministic_ties(client, limit):
    ingest_rows(
        client,
        [
            order("S1", source="own_store"),
            order("shared", source="market_b"),
            order("A3"),
            order("A2"),
            order("shared"),
            order("newest", placed_at="2026-09-02T00:00:00Z", updated_at="2026-09-02T00:00:00Z"),
        ],
    )
    expected = [
        ("market_a", "newest"),
        ("market_a", "A2"),
        ("market_a", "A3"),
        ("market_a", "shared"),
        ("market_b", "shared"),
        ("own_store", "S1"),
    ]
    seen = []
    offset = 0
    for _ in range(len(expected)):
        result = page(client, limit=limit, offset=offset)
        assert result["offset"] == offset
        assert result["limit"] == limit
        assert result["source"] is None and result["status"] is None
        seen.extend((item["source"], item["order_id"]) for item in result["orders"])
        assert len(result["orders"]) <= limit
        assert all(set(item) == set(order()) for item in result["orders"])
        if not result["has_more"]:
            assert result["next_offset"] is None
            break
        assert result["next_offset"] == offset + limit
        offset = result["next_offset"]
    else:
        pytest.fail("마지막 페이지에 도달하지 못했습니다.")
    assert seen == expected
    assert len(set(seen)) == len(expected)


def test_filters_are_applied_after_latest_version_and_before_pagination(client):
    ingest_rows(
        client,
        [
            order("A0"),
            order("B1", source="market_b"),
            order(
                "B1",
                source="market_b",
                revision=2,
                status="cancelled",
                updated_at="2026-09-05T00:00:00Z",
            ),
            order("B2", source="market_b"),
            order("B3", source="market_b", status="shipped"),
        ],
    )
    result = page(client, source="market_b", status="paid", limit=1)
    assert [(x["order_id"], x["revision"]) for x in result["orders"]] == [("B2", 1)]
    assert result["source"] == "market_b" and result["status"] == "paid"
    assert result["has_more"] is False
    earlier = page(client, source="market_b", status="paid", as_of="2026-09-04T00:00:00Z")
    assert [x["order_id"] for x in earlier["orders"]] == ["B1", "B2"]
    cancelled = page(client, status="cancelled")
    assert [(x["source"], x["order_id"], x["revision"]) for x in cancelled["orders"]] == [
        ("market_b", "B1", 2)
    ]


@pytest.mark.parametrize("status", ["paid", "shipped", "delivered", "cancelled", "refunded"])
def test_each_status_can_be_selected(client, status):
    rows = [order("target", status=status)]
    if status == "delivered":
        rows = [
            order(
                "target",
                status=status,
                delivered_at="2026-09-02T00:00:00Z",
                updated_at="2026-09-02T00:00:00Z",
            )
        ]
    ingest_rows(client, rows)
    result = page(client, status=status)
    assert len(result["orders"]) == 1
    assert result["orders"][0]["status"] == status


@pytest.mark.parametrize("populated,offset", [(False, 0), (True, 2), (True, 200)])
def test_empty_or_past_last_page_is_success_with_no_next_page(client, populated, offset):
    if populated:
        ingest_rows(client, [order("A1"), order("A2")])
    result = page(client, offset=offset)
    assert result["orders"] == []
    assert result["has_more"] is False
    assert result["next_offset"] is None


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"limit": "abc"},
        {"offset": -1},
        {"offset": 2**63},
        {"offset": "1.5"},
        {"source": "unknown"},
        {"status": "unknown"},
        {"as_of": "2026-09-08T00:00:00"},
    ],
)
def test_invalid_page_parameters_return_422(client, params):
    assert client.get("/v1/orders", params={"as_of": AS_OF, **params}).status_code == 422


def test_as_of_is_returned_in_utc_and_excludes_later_updates(client):
    ingest_rows(client, [order("A1"), order("A2")])
    first = page(client, limit=1, as_of="2026-09-08T09:00:00+09:00")
    assert datetime.fromisoformat(first["as_of"]).utcoffset() == timedelta(0)
    assert first["as_of"] == AS_OF
    ingest_rows(
        client, [order("A2", revision=2, status="cancelled", updated_at="2026-09-09T00:00:00Z")]
    )
    second = page(client, limit=1, offset=first["next_offset"], as_of=first["as_of"])
    assert [(x["order_id"], x["revision"], x["status"]) for x in second["orders"]] == [
        ("A2", 1, "paid")
    ]


def test_default_page_returns_reusable_as_of(client):
    result = client.get("/v1/orders").json()
    assert result["offset"] == 0 and result["limit"] == 20
    assert datetime.fromisoformat(result["as_of"]).utcoffset() == timedelta(0)
    assert client.get("/v1/orders", params={"as_of": result["as_of"]}).status_code == 200


def test_backdated_ingestion_can_shift_offset_boundaries(client):
    # as_of는 원본의 갱신 시각 기준이지 페이지 사이의 DB 스냅샷이 아닙니다.
    ingest_rows(client, [order("B"), order("C")])
    first = page(client, limit=1)
    assert first["orders"][0]["order_id"] == "B"
    ingest_rows(client, [order("A")])
    second = page(client, limit=1, offset=first["next_offset"], as_of=first["as_of"])
    assert second["orders"][0]["order_id"] == "B"


def test_list_requires_api_key(client):
    client.headers.pop("X-API-Key")
    assert client.get("/v1/orders").status_code == 401
