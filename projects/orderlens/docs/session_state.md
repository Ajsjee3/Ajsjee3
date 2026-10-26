# 작업 상태

현재 작업 버전은 OrderLens 0.8.0입니다. 검증 결과는 validation.md와 artifacts/에 기록합니다.

운영 문서 10개, 관련 질문 24개, 무관 질문 8개와 별도 qrels로 BM25 기준선을 평가합니다. Top-1 0.625, Recall@3 0.9375, MRR@3 0.770833이고 무관 질문 결과 없음은 0.25입니다. 질문별 실패 행을 보존하며 실제 사용자 로그나 독립 평가로 표현하지 않습니다.

이전 배치 복구 변경은 [PR #7](https://github.com/Ajsjee3/Ajsjee3/pull/7)에 있습니다. 이번 0.8.0은 로컬 테스트 95개와 네 리비전 왕복, 실패·복구, 실제 HTTP 검사를 통과했습니다. 다음 구현은 고정 질문을 바꾸지 않고 BM25 점수 기준으로 근거 부족 질문을 보류했을 때 정답 검색과 오탐의 변화를 비교하는 것입니다.

2026-09-22 대화와의 비교는 저장소 루트 docs/curriculum_alignment.md에 반영했습니다. 주 6~10시간, 첫 프로젝트를 직접 설명한 뒤 두 번째 프로젝트 선택, 금융 IT는 Java/Spring 별도 분기입니다. `learning_status=not_assessed`이므로 코드가 있다는 이유로 학습 완료로 처리하지 않습니다.

미완료 PR을 먼저 확인하며 개발 계획과 실행 상태는 저장소 루트 docs/development_plan.md, docs/portfolio_status.json에서 읽습니다. 사용자가 취업 완료·중단을 알리거나 employment_status가 employed/paused이면 코드를 변경하지 않고 반복 작업을 중지합니다.

문서는 실제 GitHub 저장소의 코드·테스트·실행 안내를 참고하되, 이 프로젝트의 동작과 검증 결과를 기준으로 작성합니다. 개인이 직접 수행한 학습 기록은 learning_log.md에 남깁니다.
