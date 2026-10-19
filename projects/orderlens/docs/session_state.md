# 작업 상태

현재 작업 버전은 OrderLens 0.7.0입니다. 검증 결과는 validation.md와 artifacts/에 기록합니다.

UCI 공개 거래의 전용 DB 적재·기간 집계에 이어 실행 시도 이력을 구현했습니다. 강제 실패는 데이터 0행으로 롤백하면서 오류 이력을 남기고, 수정 후 복구와 같은 파일 재실행은 별도 성공 결과로 기록합니다. 기존 원화 주문 API와는 계속 분리합니다.

이전 SQL 실행계획 변경은 [PR #6](https://github.com/Ajsjee3/Ajsjee3/pull/6)에 있습니다. 이번 0.7.0은 로컬 테스트 90개와 네 리비전 왕복, 실패·복구 재현을 통과했습니다. [PR #7의 원격 검사](https://github.com/Ajsjee3/Ajsjee3/actions/runs/39239042095)에서도 PostgreSQL 16.15의 같은 흐름이 통과했습니다. 다음 구현은 검색 질문과 정답 문서를 분리한 평가 확대입니다.

2026-09-22 대화와의 비교는 저장소 루트 docs/curriculum_alignment.md에 반영했습니다. 주 6~10시간, 첫 프로젝트를 직접 설명한 뒤 두 번째 프로젝트 선택, 금융 IT는 Java/Spring 별도 분기입니다. `learning_status=not_assessed`이므로 코드가 있다는 이유로 학습 완료로 처리하지 않습니다.

미완료 PR을 먼저 확인하며 개발 계획과 실행 상태는 저장소 루트 docs/development_plan.md, docs/portfolio_status.json에서 읽습니다. 사용자가 취업 완료·중단을 알리거나 employment_status가 employed/paused이면 코드를 변경하지 않고 반복 작업을 중지합니다.

문서는 실제 GitHub 저장소의 코드·테스트·실행 안내를 참고하되, 이 프로젝트의 동작과 검증 결과를 기준으로 작성합니다. 개인이 직접 수행한 학습 기록은 learning_log.md에 남깁니다.
