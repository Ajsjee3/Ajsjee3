import hmac
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from importlib.resources import files
from time import perf_counter
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import AwareDatetime
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from orderlens import __version__
from orderlens.analytics import attention_orders, metrics, order_page, quality_summary
from orderlens.config import Settings
from orderlens.db import make_engine
from orderlens.ingestion import ingest, run_summary
from orderlens.migrations import require_current_schema
from orderlens.models import IngestionRun
from orderlens.retrieval import BM25Index
from orderlens.schemas import IngestRequest, OrderPage, OrderSource, OrderStatus, SearchRequest

logger = logging.getLogger("orderlens")
key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session


Db = Annotated[Session, Depends(get_session)]


def require_api_key(request: Request, key: Annotated[str | None, Security(key_header)] = None):
    expected = request.app.state.settings.api_key
    if key is None or not hmac.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="유효한 X-API-Key가 필요합니다.")


def utc(value):
    return value.astimezone(timezone.utc) if value else datetime.now(timezone.utc)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        engine = make_engine(settings.database_url)
        try:
            require_current_schema(engine)
            app.state.engine = engine
            knowledge = json.loads(
                files("orderlens.data").joinpath("knowledge.json").read_text("utf-8")
            )
            app.state.search = BM25Index(knowledge)
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="OrderLens 주문 운영 API",
        version=__version__,
        lifespan=lifespan,
        description="주문 데이터 검증, 버전 중복 방지, 운영 지표, 업무 문서 검색을 제공하는 학습용 API.",
    )
    app.state.settings = settings

    @app.middleware("http")
    async def request_metadata(request, call_next):
        request_id = str(uuid4())
        started = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["Server-Timing"] = f"app;dur={(perf_counter() - started) * 1000:.2f}"
        # API 키와 입력 본문은 로그에 기록하지 않습니다.
        logger.info(
            "request_id=%s method=%s path=%s status=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
        )
        return response

    @app.exception_handler(OperationalError)
    async def database_unavailable(_request, _error):
        return JSONResponse(
            status_code=503, content={"detail": "데이터베이스를 사용할 수 없습니다."}
        )

    @app.get("/health", tags=["health"])
    def health(session: Db):
        session.execute(text("SELECT 1"))
        return {"status": "ok", "version": __version__}

    router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])

    @router.post("/ingestions", tags=["ingestion"])
    def ingest_orders(payload: IngestRequest, session: Db):
        return ingest(session, payload.rows)

    @router.get("/runs/{run_id}", tags=["ingestion"])
    def get_run(run_id: UUID, session: Db):
        run = session.scalar(select(IngestionRun).where(IngestionRun.id == str(run_id)))
        if run is None:
            raise HTTPException(404, "처리 이력을 찾을 수 없습니다.")
        return run_summary(session, run)

    @router.get("/quality", tags=["ingestion"])
    def quality(session: Db):
        return quality_summary(session)

    @router.get("/metrics", tags=["analytics"])
    def get_metrics(
        session: Db,
        as_of: AwareDatetime | None = None,
        start_at: AwareDatetime | None = None,
        end_at: AwareDatetime | None = None,
    ):
        if start_at and end_at and start_at >= end_at:
            raise HTTPException(422, "start_at은 end_at보다 빨라야 합니다.")
        return metrics(
            session,
            utc(as_of),
            utc(start_at) if start_at else None,
            utc(end_at) if end_at else None,
        )

    @router.get("/orders", tags=["analytics"], response_model=OrderPage)
    def get_orders(
        session: Db,
        as_of: AwareDatetime | None = None,
        source: OrderSource | None = None,
        status: OrderStatus | None = None,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0, le=9_223_372_036_854_775_807),
    ):
        return order_page(
            session, utc(as_of), source=source, status=status, limit=limit, offset=offset
        )

    @router.get("/orders/attention", tags=["analytics"])
    def get_attention(
        session: Db,
        as_of: AwareDatetime | None = None,
        limit: int = Query(20, ge=1, le=100),
        source: OrderSource | None = None,
    ):
        return {"orders": attention_orders(session, utc(as_of), limit, source)}

    @router.post("/knowledge/search", tags=["knowledge"])
    def search_knowledge(payload: SearchRequest, request: Request):
        return {
            "mode": "retrieval_only",
            "score_is_probability": False,
            "matches": request.app.state.search.search(payload.query, payload.top_k),
        }

    @router.get("/brief", tags=["analytics"])
    def brief(request: Request, session: Db, as_of: AwareDatetime | None = None):
        moment = utc(as_of)
        report = metrics(session, moment)
        counts = report["summary"]
        return {
            "mode": "rules_based_no_llm",
            "as_of": moment.isoformat(),
            "text": f"전체 {counts['total_orders']}건 중 배송 예정 시각을 넘긴 미완료 주문은 "
            f"{counts['overdue_open_orders']}건입니다. 주문 상태와 배송 이력을 확인해 주세요.",
            "metrics": counts,
            "evidence": request.app.state.search.search("배송 지연 미완료 주문", 1),
            "action_executed": False,
        }

    app.include_router(router)
    return app


app = create_app()
