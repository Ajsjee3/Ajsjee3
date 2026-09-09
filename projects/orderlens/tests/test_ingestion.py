import pytest
from conftest import order

AS_OF = "2026-09-08T00:00:00Z"


def test_partial_success_keeps_good_row_and_reports_exact_bad_row(client):
    result = client.post("/v1/ingestions", json={"rows": [order(), order("B", amount_krw=-1)]})
    assert result.status_code == 200
    body = result.json()
    assert (body["accepted"], body["duplicates"], body["rejected"]) == (1, 0, 1)
    assert body["errors"][0]["row_number"] == 2
    assert client.get(f"/v1/runs/{body['run_id']}").json() == body
    assert client.get("/v1/metrics", params={"as_of": AS_OF}).json()["summary"]["total_orders"] == 1


def test_replay_does_not_inflate_order_value(client):
    payload = {"rows": [order(), order()]}
    first = client.post("/v1/ingestions", json=payload).json()
    second = client.post("/v1/ingestions", json=payload).json()
    assert (first["accepted"], first["duplicates"]) == (1, 1)
    assert (second["accepted"], second["duplicates"]) == (0, 2)
    metrics = client.get("/v1/metrics", params={"as_of": AS_OF}).json()["summary"]
    assert metrics["total_orders"] == 1
    assert metrics["booked_amount_krw"] == 10000


def test_same_instant_in_different_timezone_is_duplicate(client):
    utc = order()
    kst = order(
        placed_at="2026-09-01T09:00:00+09:00",
        updated_at="2026-09-01T09:00:00+09:00",
        promised_by="2026-09-03T09:00:00+09:00",
    )
    result = client.post("/v1/ingestions", json={"rows": [utc, kst]}).json()
    assert (result["accepted"], result["duplicates"], result["rejected"]) == (1, 1, 0)


def test_conflicting_revision_preserves_original_value(client):
    result = client.post(
        "/v1/ingestions", json={"rows": [order(), order(amount_krw=999999)]}
    ).json()
    assert result["errors"][0]["code"] == "revision_conflict"
    summary = client.get("/v1/metrics", params={"as_of": AS_OF}).json()["summary"]
    assert summary["booked_amount_krw"] == 10000


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount_krw": 10.5},
        {"amount_krw": True},
        {"amount_krw": "10000"},
        {"placed_at": "2026-09-01T00:00:00"},
        {"placed_at": 1788220800},
        {"status": "delivered"},
        {"revision": 0},
        {"customer_email": "dummy@example.invalid"},
        {"promised_by": "2026-08-01T00:00:00Z"},
    ],
)
def test_invalid_domain_data_is_not_saved(client, overrides):
    result = client.post("/v1/ingestions", json={"rows": [order(**overrides)]}).json()
    assert (result["accepted"], result["rejected"]) == (0, 1)
    assert result["errors"][0]["code"] == "schema_error"


def test_batch_limit_prevents_accidental_large_import(client):
    assert client.post("/v1/ingestions", json={"rows": [order()] * 501}).status_code == 422
    assert client.get("/v1/quality").json()["runs"] == 0


def test_unexpected_failure_rolls_back_entire_batch(client, monkeypatch):
    def fail(*args):
        raise RuntimeError("simulated failure before commit")

    monkeypatch.setattr("orderlens.ingestion.run_summary", fail)
    with pytest.raises(RuntimeError, match="simulated failure"):
        client.post("/v1/ingestions", json={"rows": [order()]})
    assert client.get("/v1/quality").json()["runs"] == 0
    assert client.get("/v1/metrics", params={"as_of": AS_OF}).json()["summary"]["total_orders"] == 0
