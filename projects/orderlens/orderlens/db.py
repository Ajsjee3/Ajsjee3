"""같은 데이터 모델을 SQLite와 PostgreSQL에서 사용할 수 있게 합니다."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator):
    """저장 전에 UTC로 통일하고, SQLite가 잃는 timezone 정보를 복원합니다."""

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timezone이 있는 datetime만 저장할 수 있습니다.")
        utc = value.astimezone(timezone.utc)
        return utc.replace(tzinfo=None) if dialect.name == "sqlite" else utc

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def make_engine(url: str) -> Engine:
    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        # Python 3.12+: 실제 BEGIN 이후 SAVEPOINT가 열리도록 설정합니다.
        options["connect_args"] = {"check_same_thread": False, "autocommit": False}
        if url in {"sqlite://", "sqlite:///:memory:"}:
            options["poolclass"] = StaticPool
    engine = create_engine(url, **options)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            # autocommit=False 상태에서는 PRAGMA foreign_keys가 무시될 수 있습니다.
            previous = connection.autocommit
            connection.autocommit = True
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
            connection.autocommit = previous

    return engine


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
