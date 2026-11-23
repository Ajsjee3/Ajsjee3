import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, TimeoutError


def test_probes_without_credentials(client):
    client.headers.clear()
    assert client.get("/live").status_code == 200
    assert client.get("/ready").json() == {"status": "ready"}
    assert client.get("/health").status_code == 200
    assert client.get("/v1/orders").status_code == 401


@pytest.mark.parametrize("error", [
    OperationalError("secret SQL", {}, Exception("secret password")),
    TimeoutError("secret connection"),
])
def test_connection_failure_and_recovery(client, monkeypatch, error):
    def unavailable():
        raise error

    with monkeypatch.context() as patch:
        patch.setattr(client.app.state.engine, "connect", unavailable)
        assert client.get("/live").status_code == 200
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "not_ready", "reason": "database_unavailable"}
        assert "secret" not in response.text
    assert client.get("/ready").status_code == 200


@pytest.mark.parametrize("revisions", [[], ["old_revision"], ["extra", "current"]])
def test_revision_drift_and_recovery(client, revisions):
    engine = client.app.state.engine
    expected = client.app.state.schema_revision
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM alembic_version"))
        for revision in revisions:
            connection.execute(text("INSERT INTO alembic_version VALUES (:revision)"),
                               {"revision": expected if revision == "current" else revision})
    assert client.get("/live").status_code == 200
    assert client.get("/health").status_code == 200
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["reason"] == "schema_mismatch"
    with engine.begin() as connection:
        assert len(connection.execute(text("SELECT * FROM alembic_version")).all()) == len(revisions)
        connection.execute(text("DELETE FROM alembic_version"))
        connection.execute(text("INSERT INTO alembic_version VALUES (:revision)"),
                           {"revision": expected})
    assert client.get("/ready").status_code == 200
