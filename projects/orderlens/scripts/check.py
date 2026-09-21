"""코드 검사, 핵심 테스트, 데모, 검색 평가를 한 명령으로 실행합니다."""

import subprocess
import sys


def main():
    commands = [
        ["-m", "ruff", "check", "."],
        ["-m", "pytest", "-q"],
        ["-m", "scripts.check_migrations"],
        ["-m", "scripts.generate_demo"],
        ["-m", "scripts.demo"],
        ["-m", "scripts.evaluate_retrieval"],
        ["-m", "scripts.smoke_http"],
    ]
    for command in commands:
        subprocess.run([sys.executable, *command], check=True)


if __name__ == "__main__":
    main()
