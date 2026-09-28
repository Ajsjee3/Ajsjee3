"""UCI가 제공하는 CSV를 내려받고 확인한 원본의 SHA-256과 비교합니다."""

import argparse
import json
import tempfile
import urllib.request
from pathlib import Path

from orderlens.retail import SOURCE_SHA256, SOURCE_URL, file_sha256


def download(destination: Path) -> str:
    if destination.exists():
        if file_sha256(destination) != SOURCE_SHA256:
            raise ValueError("기존 파일이 확인한 원본과 다릅니다. 다른 저장 경로를 지정해 주세요.")
        return SOURCE_SHA256
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as directory:
        pending = Path(directory) / "download.csv"
        with urllib.request.urlopen(SOURCE_URL, timeout=30) as response, pending.open("wb") as out:
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 100 * 1024 * 1024:
                    raise ValueError("다운로드 크기가 100 MiB를 넘었습니다.")
                out.write(chunk)
        if file_sha256(pending) != SOURCE_SHA256:
            raise ValueError("UCI 원본의 해시가 바뀌었습니다. 출처와 변환 규칙을 다시 확인해야 합니다.")
        # x 모드로 다른 파일을 덮어쓰지 않으며, 네트워크 실패 파일을 결과로 노출하지 않습니다.
        with pending.open("rb") as source, destination.open("xb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
    return SOURCE_SHA256


def main() -> None:
    parser = argparse.ArgumentParser(description="UCI Online Retail 원본 CSV 다운로드")
    parser.add_argument("--output", type=Path, default=Path("data/raw/online_retail.csv"))
    args = parser.parse_args()
    digest = download(args.output)
    print(json.dumps({"source_url": SOURCE_URL, "sha256": digest, "path": str(args.output)}))


if __name__ == "__main__":
    main()
