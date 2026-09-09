import pytest
from fastapi.testclient import TestClient

from orderlens.config import Settings
from orderlens.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(
        Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", api_key="test-orderlens-api-key")
    )
    with TestClient(app, headers={"X-API-Key": "test-orderlens-api-key"}) as api:
        yield api


def order(order_id="A1", **overrides):
    row = {
        "source": "market_a",
        "order_id": order_id,
        "revision": 1,
        "placed_at": "2026-09-01T00:00:00Z",
        "updated_at": "2026-09-01T00:00:00Z",
        "promised_by": "2026-09-03T00:00:00Z",
        "delivered_at": None,
        "status": "paid",
        "amount_krw": 10000,
    }
    return {**row, **overrides}
