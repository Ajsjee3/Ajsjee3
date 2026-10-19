"""python -m scripts.load_retail 정제_디렉터리 --database-url DB_URL"""

import argparse
import json
import os
import sys
from pathlib import Path

from orderlens.db import make_engine
from orderlens.migrations import require_current_schema
from orderlens.retail_db import RetailLoadAttemptError, run_retail_load


def main() -> None:
    parser = argparse.ArgumentParser(description="정제한 공개 거래 JSONL을 DB에 적재합니다.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--database-url", default=os.getenv("ORDERLENS_DATABASE_URL"))
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url 또는 ORDERLENS_DATABASE_URL이 필요합니다.")

    engine = make_engine(args.database_url)
    try:
        require_current_schema(engine)
        try:
            result = run_retail_load(engine, args.output_dir)
        except RetailLoadAttemptError as error:
            print(
                json.dumps(
                    {
                        "attempt_id": error.attempt_id,
                        "status": "failed",
                        "error_code": error.error_code,
                        "error_message": str(error),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )
            raise SystemExit(1) from None
    finally:
        engine.dispose()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
