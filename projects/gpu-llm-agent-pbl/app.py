import logging
import threading
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


class Question(BaseModel):
    q: str = Field(min_length=1, max_length=600)
    use_lora: bool = False


def create_app(engine):
    app = FastAPI(title="FinanceRAG")
    lock = threading.Lock()

    @app.get("/")
    def home():
        return FileResponse(Path(__file__).with_name("index.html"))

    @app.get("/api/info")
    def info():
        return {"mode": engine.mode, "adapter": engine.adapter}

    @app.post("/api/chat")
    def chat(request: Question):
        question = request.q.strip()
        if not question:
            raise HTTPException(422, "질문을 입력해 주세요.")
        if request.use_lora and not engine.adapter:
            raise HTTPException(409, "현재 모델에 연결할 LoRA 어댑터가 없습니다.")
        start = perf_counter()
        try:
            with lock:
                answer, sources = engine.ask(question, request.use_lora)
        except Exception:
            logging.getLogger(__name__).exception("질문 처리 실패")
            raise HTTPException(503, "검색 또는 생성에 실패했습니다. 서버 실행 기록을 확인해 주세요.") from None
        return {"answer": answer, "sources": sources, "elapsed_ms": round((perf_counter()-start)*1000, 2),
                "mode": engine.mode, "adapter": engine.adapter if request.use_lora else None}

    return app


def preview():
    from service import ExcerptSearch

    return create_app(ExcerptSearch())
