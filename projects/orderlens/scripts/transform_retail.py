"""python -m scripts.transform_retail INPUT.csv --output 새_디렉터리"""

import argparse
import json
from pathlib import Path

from orderlens.retail import transform_file


def main() -> None:
    parser = argparse.ArgumentParser(description="UCI 거래 CSV를 정제하고 품질 결과를 기록합니다.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = transform_file(args.input, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
