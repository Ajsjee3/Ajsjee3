from conftest import order


def test_auth_is_required_and_health_is_public(client):
    client.headers.pop("X-API-Key")
    assert client.get("/health").status_code == 200
    assert client.get("/v1/metrics").status_code == 401
    assert client.post("/v1/ingestions", json={"rows": [order()]}).status_code == 401
    response = client.get("/v1/quality", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401
    assert "X-Request-ID" in response.headers


def test_document_search_returns_evidence_with_honest_mode(client):
    body = client.post("/v1/knowledge/search", json={"query": "중복 적재 버전 충돌"}).json()
    assert body["mode"] == "retrieval_only_with_abstention"
    assert body["score_is_probability"] is False
    assert body["abstained"] is False
    assert body["abstention_reason"] is None
    assert body["top_score"] >= body["minimum_score"]
    assert body["matches"][0]["document_id"] == "duplicates"
    assert body["matches"][0]["source"] == "bundled_demo_policy"


def test_unrelated_query_has_no_evidence(client):
    response = client.post("/v1/knowledge/search", json={"query": "블랙홀 은하 천체"})
    body = response.json()
    assert body["matches"] == []
    assert body["abstained"] is True
    assert body["abstention_reason"] == "no_token_overlap"


def test_weak_domain_overlap_is_abstained(client):
    body = client.post("/v1/knowledge/search", json={"query": "배송비 할인 쿠폰 정책"}).json()

    assert body["top_score"] > 0
    assert body["top_score"] < body["minimum_score"]
    assert body["matches"] == []
    assert body["abstained"] is True
    assert body["abstention_reason"] == "top_score_below_minimum"


def test_document_search_returns_page_contract(client):
    body = client.post("/v1/knowledge/search", json={"query": "next_offset as_of 페이지"}).json()
    assert body["matches"][0]["document_id"] == "order-pages"


def test_blank_query_is_rejected(client):
    assert client.post("/v1/knowledge/search", json={"query": "   "}).status_code == 422


def test_brief_is_traceable_and_does_not_send_messages(client):
    client.post("/v1/ingestions", json={"rows": [order()]})
    body = client.get("/v1/brief", params={"as_of": "2026-09-08T00:00:00Z"}).json()
    assert body["mode"] == "rules_based_no_llm"
    assert body["action_executed"] is False
    assert body["metrics"]["overdue_open_orders"] == 1
    assert body["evidence"][0]["document_id"] == "late-delivery"
