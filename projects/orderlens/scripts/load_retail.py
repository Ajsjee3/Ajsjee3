"""python -m scripts.load_retail 정제_디렉터리 --database-url DB_URL"""

import argparse
import json
import os
from pathlib import Path

from sqlalchemy.orm import Session

from orderlens.db import make_engine
from orderlens.migrations import require_current_schema
from orderlens.retail_db import load_retail_output


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
        with Session(engine) as session:
            result = load_retail_output(session, args.output_dir)
    finally:
        engine.dispose()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
