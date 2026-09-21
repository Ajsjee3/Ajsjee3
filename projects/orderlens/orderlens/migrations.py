"""스키마 버전을 적용하고 실행 중인 DB가 최신인지 확인합니다."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def alembic_config(database_url: str | None = None) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    if database_url is not None:
        # URL을 ini 문자열 보간에 넣지 않아 비밀번호의 %도 그대로 전달합니다.
        config.attributes["database_url"] = database_url
    return config


def head_revision() -> str:
    heads = ScriptDirectory.from_config(alembic_config()).get_heads()
    if len(heads) != 1:
        raise RuntimeError(f"마이그레이션 head가 하나여야 합니다: {heads}")
    return heads[0]


def current_revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def require_current_schema(engine: Engine) -> str:
    expected = head_revision()
    actual = current_revision(engine)
    if actual != expected:
        raise RuntimeError(
            "DB 스키마가 최신이 아닙니다. "
            f"현재={actual or '없음'}, 필요={expected}. "
            "python -m alembic upgrade head를 실행해 주세요."
        )
    return actual


def upgrade_database(database_url: str) -> None:
    command.upgrade(alembic_config(database_url), "head")


def check_model_matches_database(database_url: str) -> None:
    """모델과 현재 DB 사이에 새 마이그레이션이 필요한 차이가 없는지 확인합니다."""

    command.check(alembic_config(database_url))


def downgrade_database(database_url: str) -> None:
    command.downgrade(alembic_config(database_url), "base")
