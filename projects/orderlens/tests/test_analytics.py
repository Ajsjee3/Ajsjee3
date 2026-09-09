import pytest
from conftest import order


def test_latest_version_wins_even_when_old_data_arrives_later(client):
    newest = order(revision=2, status="cancelled", updated_at="2026-09-02T00:00:00Z")
    client.post("/v1/ingestions", json={"rows": [newest, order()]})
    result = client.get("/v1/metrics", params={"as_of": "2026-09-08T00:00:00Z"}).json()["summary"]
    assert result["total_orders"] == 1
    assert result["cancelled_orders"] == 1
    assert result["booked_amount_krw"] == 0


def test_as_of_filters_source_updates_before_picking_version(client):
    client.post(
        "/v1/ingestions",
        json={
            "rows": [
                order(),
                order(revision=2, status="cancelled", updated_at="2026-09-04T00:00:00Z"),
            ]
        },
    )
    before = client.get("/v1/metrics", params={"as_of": "2026-09-03T00:00:00Z"}).json()["summary"]
    assert before["active_orders"] == 1
    assert before["overdue_open_orders"] == 0  # 마감 시각과 같을 때는 지연이 아닙니다.
    after = client.get("/v1/metrics", params={"as_of": "2026-09-04T00:00:00Z"}).json()["summary"]
    assert after["cancelled_orders"] == 1


def test_metric_denominators_refunds_and_sources(client):
    rows = [
        order("open", amount_krw=100),
        order(
            "on-time",
            status="delivered",
            amount_krw=200,
            delivered_at="2026-09-02T00:00:00Z",
            updated_at="2026-09-02T00:00:00Z",
        ),
        order(
            "late",
            source="market_b",
            status="delivered",
            amount_krw=300,
            delivered_at="2026-09-05T00:00:00Z",
            updated_at="2026-09-05T00:00:00Z",
        ),
        order("cancel", status="cancelled", amount_krw=400),
        order("refund", status="refunded", amount_krw=500),
    ]
    client.post("/v1/ingestions", json={"rows": rows})
    report = client.get("/v1/metrics", params={"as_of": "2026-09-08T00:00:00Z"}).json()
    counts = report["summary"]
    assert counts["total_orders"] == 5
    assert counts["booked_amount_krw"] == 600
    assert counts["delivered_orders"] == 2
    assert counts["late_delivered_orders"] == 1
    assert counts["late_delivery_rate"] == pytest.approx(0.5)
    assert counts["overdue_open_orders"] == 1
    assert sum(group["total_orders"] for group in report["by_source"]) == 5
    attention = client.get("/v1/orders/attention", params={"as_of": "2026-09-08T00:00:00Z"}).json()
    assert [row["order_id"] for row in attention["orders"]] == ["open"]


def test_same_order_id_in_two_sources_means_two_orders(client):
    client.post("/v1/ingestions", json={"rows": [order(), order(source="market_b")]})
    assert client.get("/v1/metrics").json()["summary"]["total_orders"] == 2


def test_empty_dataset_is_not_reported_as_perfect_delivery(client):
    counts = client.get("/v1/metrics").json()["summary"]
    assert counts["total_orders"] == 0
    assert counts["booked_amount_krw"] == 0
    assert counts["late_delivery_rate"] is None


def test_period_is_start_inclusive_end_exclusive(client):
    client.post(
        "/v1/ingestions",
        json={
            "rows": [
                order("first"),
                order(
                    "second", placed_at="2026-09-02T00:00:00Z", updated_at="2026-09-02T00:00:00Z"
                ),
            ]
        },
    )
    result = client.get(
        "/v1/metrics",
        params={
            "start_at": "2026-09-01T00:00:00Z",
            "end_at": "2026-09-02T00:00:00Z",
        },
    ).json()
    assert result["summary"]["total_orders"] == 1
    assert (
        client.get(
            "/v1/metrics",
            params={"start_at": "2026-09-03T00:00:00Z", "end_at": "2026-09-02T00:00:00Z"},
        ).status_code
        == 422
    )


def test_future_snapshot_is_excluded(client):
    client.post("/v1/ingestions", json={"rows": [order(updated_at="2026-12-01T00:00:00Z")]})
    assert (
        client.get("/v1/metrics", params={"as_of": "2026-09-08T00:00:00Z"}).json()["summary"][
            "total_orders"
        ]
        == 0
    )
