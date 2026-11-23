"""연결과 리비전 표식만 읽는 준비 상태 검사. 스키마를 수정하지 않습니다."""

from alembic.migration import MigrationContext
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError


def readiness(engine: Engine, expected_revision: str) -> dict:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            heads = MigrationContext.configure(connection).get_current_heads()
    except SQLAlchemyError:
        # 드라이버 오류에 포함될 수 있는 접속 정보와 SQL은 반환하지 않습니다.
        return {"status": "not_ready", "reason": "database_unavailable"}
    if heads != (expected_revision,):
        return {"status": "not_ready", "reason": "schema_mismatch"}
    return {"status": "ready"}
