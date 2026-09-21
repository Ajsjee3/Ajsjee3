# 작업 상태

현재 작업 버전은 OrderLens 0.3.0입니다. 검증 결과는 validation.md와 artifacts/에 기록합니다.

Alembic 초기 리비전, 앱의 스키마 버전 확인과 PostgreSQL 전용 통합 검사를 구현했습니다. 로컬 SQLite 검증은 통과했고 PostgreSQL 16 결과는 작업 PR에서 확인할 예정입니다. 원격 검사가 성공하면 다음 구현은 실제 공개 데이터 변환입니다. 미완료 PR이 있으면 먼저 확인하며, 개발 계획과 실행 상태는 저장소 루트 docs/development_plan.md, docs/portfolio_status.json에서 확인합니다.

문서는 실제 GitHub 저장소의 코드·테스트·실행 안내를 참고하되, 이 프로젝트의 동작과 검증 결과를 기준으로 작성합니다. 개인이 직접 수행한 학습 기록은 learning_log.md에 남깁니다.
