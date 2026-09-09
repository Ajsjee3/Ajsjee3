"""임시 DB로 API 적재·재실행·지표·검색을 자동 시연합니다. 기존 DB는 건드리지 않습니다."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from orderlens.config import Settings
from orderlens.main import create_app
from scripts.generate_demo import AS_OF, generate_rows


def main():
    with TemporaryDirectory(prefix="orderlens-demo-") as directory:
        app = create_app(Settings(database_url=f"sqlite:///{directory}/demo.db"))
        with TestClient(app, headers={"X-API-Key": "orderlens-local-demo-key"}) as client:
            payload = {"rows": generate_rows()}
            first = client.post("/v1/ingestions", json=payload)
            first.raise_for_status()
            params = {"as_of": AS_OF}
            before = client.get("/v1/metrics", params=params).json()
            second = client.post("/v1/ingestions", json=payload)
            second.raise_for_status()
            after = client.get("/v1/metrics", params=params).json()
            if before != after:
                raise AssertionError("재전송 후 지표가 달라졌습니다.")
            report = {
                "data_origin": "synthetic_demo_not_real_business_data",
                "database": "temporary_sqlite",
                "transport": "in_process_asgi_testclient",
                "first_ingestion": first.json(),
                "replay": second.json(),
                "metrics_before_replay": before,
                "metrics": after,
                "metrics_unchanged_by_replay": before == after,
                "quality": client.get("/v1/quality").json(),
                "brief": client.get("/v1/brief", params=params).json(),
            }
    output = Path("artifacts/demo_report.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "first_ingestion": {
                    key: report["first_ingestion"][key]
                    for key in ["accepted", "duplicates", "rejected"]
                },
                "replay_accepted": report["replay"]["accepted"],
                "metrics": report["metrics"]["summary"],
                "report": str(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
