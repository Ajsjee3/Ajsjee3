"""임시 Uvicorn 서버의 실제 HTTP 경로를 확인하고 종료합니다."""

import http.client
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.generate_demo import AS_OF, generate_rows


def request(port, method, path, payload=None, authenticated=True):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"Content-Type": "application/json"}
    if authenticated:
        headers["X-API-Key"] = "orderlens-http-smoke-key"
    try:
        connection.request(
            method, path, body=json.dumps(payload) if payload else None, headers=headers
        )
        response = connection.getresponse()
        return (
            response.status,
            json.loads(response.read()),
            bool(response.getheader("X-Request-ID")),
        )
    finally:
        connection.close()


def main():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with TemporaryDirectory(prefix="orderlens-http-") as directory:
        environment = os.environ.copy()
        environment["ORDERLENS_DATABASE_URL"] = f"sqlite:///{directory}/http.db"
        environment["ORDERLENS_API_KEY"] = "orderlens-http-smoke-key"
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "orderlens.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "error",
            ],
            env=environment,
            stdout=subprocess.DEVNULL,
        )
        try:
            deadline = time.monotonic() + 10
            while True:
                try:
                    status, _, has_request_id = request(port, "GET", "/health", authenticated=False)
                    if status == 200:
                        break
                except (OSError, http.client.HTTPException):
                    pass
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("HTTP 시연 서버가 준비되지 않았습니다.")
                time.sleep(0.1)
            ingest_status, ingestion, _ = request(
                port, "POST", "/v1/ingestions", {"rows": generate_rows()}
            )
            metric_status, report, _ = request(port, "GET", f"/v1/metrics?as_of={AS_OF}")
            attention_status, attention, _ = request(
                port, "GET", f"/v1/orders/attention?as_of={AS_OF}&source=market_a&limit=3"
            )
            if attention_status != 200 or len(attention["orders"]) != 3:
                raise AssertionError("판매 경로별 지연 주문의 실제 HTTP 조회에 실패했습니다.")
            if any(item["source"] != "market_a" for item in attention["orders"]):
                raise AssertionError("지연 주문 목록에 다른 판매 경로가 섞였습니다.")
            unauthorized_status, _, _ = request(port, "GET", "/v1/quality", authenticated=False)
            if (ingest_status, metric_status, unauthorized_status) != (200, 200, 401):
                raise AssertionError("HTTP 상태 검증에 실패했습니다.")
            if ingestion["accepted"] != 300 or report["summary"]["total_orders"] != 120:
                raise AssertionError("실제 HTTP 지표 검증에 실패했습니다.")
            evidence = {
                "transport": "real_loopback_http_to_uvicorn",
                "database": "temporary_sqlite",
                "health": status,
                "ingest": ingest_status,
                "metrics": metric_status,
                "unauthenticated": unauthorized_status,
                "request_id_present": has_request_id,
                "accepted_versions": ingestion["accepted"],
                "orders": report["summary"]["total_orders"],
                "attention_filter": {
                    "status": attention_status,
                    "source": "market_a",
                    "limit": 3,
                    "returned": len(attention["orders"]),
                    "only_requested_source": True,
                },
            }
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    output = Path("artifacts/http_smoke.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
