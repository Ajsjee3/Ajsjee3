# 작업 상태

현재 작업 버전은 OrderLens 0.5.0입니다. 검증 결과는 validation.md와 artifacts/에 기록합니다.

UCI 공개 거래 CSV의 다운로드·정제에 이어 전용 DB 적재를 구현했습니다. `retail_imports`는 파일·정제 결과 해시, `retail_lines`는 GBP Decimal과 원본 행 위치를 저장합니다. 전체 541,907행 적재와 같은 파일의 새 행 0개 재실행을 임시 SQLite에서 확인했습니다. 기존 원화 주문 API와는 계속 분리합니다.

이전 정제 변경은 [PR #4](https://github.com/Ajsjee3/Ajsjee3/pull/4)에 있습니다. 이번 0.5.0의 로컬 테스트는 84개이며 새 PR에서 PostgreSQL 16 검사를 확인합니다. 다음 구현은 실제 규모의 집계 SQL 실행계획과 인덱스 비교입니다.

2026-09-22 대화와의 비교는 저장소 루트 docs/curriculum_alignment.md에 반영했습니다. 주 6~10시간, 첫 프로젝트를 직접 설명한 뒤 두 번째 프로젝트 선택, 금융 IT는 Java/Spring 별도 분기입니다. `learning_status=not_assessed`이므로 코드가 있다는 이유로 학습 완료로 처리하지 않습니다.

미완료 PR을 먼저 확인하며 개발 계획과 실행 상태는 저장소 루트 docs/development_plan.md, docs/portfolio_status.json에서 읽습니다. 사용자가 취업 완료·중단을 알리거나 employment_status가 employed/paused이면 코드를 변경하지 않고 반복 작업을 중지합니다.

문서는 실제 GitHub 저장소의 코드·테스트·실행 안내를 참고하되, 이 프로젝트의 동작과 검증 결과를 기준으로 작성합니다. 개인이 직접 수행한 학습 기록은 learning_log.md에 남깁니다.
