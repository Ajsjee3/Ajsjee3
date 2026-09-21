import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

import orderlens.models  # noqa: F401
from orderlens.config import Settings
from orderlens.db import Base, make_engine
from orderlens.main import create_app
from orderlens.migrations import (
    current_revision,
    downgrade_database,
    head_revision,
    require_current_schema,
    upgrade_database,
)


def test_initial_migration_can_upgrade_downgrade_and_upgrade_again(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    upgrade_database(database_url)
    engine = make_engine(database_url)
    try:
        assert require_current_schema(engine) == head_revision()
        assert set(Base.metadata.tables) <= set(inspect(engine).get_table_names())

        constraints = inspect(engine).get_unique_constraints("order_snapshots")
        assert any(item["name"] == "uq_order_revision" for item in constraints)
        indexes = inspect(engine).get_indexes("order_snapshots")
        assert any(item["name"] == "ix_snapshot_updated" for item in indexes)

        downgrade_database(database_url)
        assert not (set(inspect(engine).get_table_names()) & set(Base.metadata.tables))
        assert current_revision(engine) is None

        upgrade_database(database_url)
        assert require_current_schema(engine) == head_revision()
    finally:
        engine.dispose()


def test_application_refuses_an_unmigrated_database(tmp_path):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'unmigrated.db'}",
            api_key="test-orderlens-api-key",
        )
    )
    with pytest.raises(RuntimeError, match="python -m alembic upgrade head"):
        with TestClient(app):
            pass
