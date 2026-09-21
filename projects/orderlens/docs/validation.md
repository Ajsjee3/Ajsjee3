# 검증 기록 — 2026-09-21 · 0.3.0

로컬 실행 환경: Linux x86_64, Python 3.12.14, SQLite 3.53.1. 의존성 버전은 requirements.lock에 기록했습니다.

## 실행 결과

| 검증 | 결과 |
|---|---|
| Ruff 코드 검사 | 통과 |
| pytest | 61개 통과, 실패 0개; 마이그레이션 테스트 2개 포함 |
| SQLite 마이그레이션 | `20260921_01` upgrade·downgrade·재upgrade 통과 |
| 미적용 DB에서 앱 시작 | 스키마를 자동 생성하지 않고 안내 오류로 중단 |
| PostgreSQL 16.15 | GitHub Actions 임시 서비스에서 통합 검사 통과 |
| PostgreSQL 적재·재전송 | 최초 저장 300·중복 5·오류 4; 재전송 저장 0·중복 305·오류 4 |
| PostgreSQL 지표·페이지 | 재전송 전후 지표 동일; 17건씩 8페이지, 반환·고유 주문 120건 |
| PostgreSQL 스키마 | TIMESTAMP WITH TIME ZONE, 모델 차이 없음, downgrade·재upgrade 통과 |
| 합성 데이터 처리 | 입력 309행: 저장 300개, 중복 5개, 오류 4개 |
| 동일 데이터 재전송 | 새 버전 0개, 기존 버전 중복 305개, 오류 4개 |
| 재전송 전후 운영 지표 | 동일함을 비교·확인 |
| 최신 주문 집계 | 120건 |
| 예제 배송 지연 미완료 | 40건 |
| 예제 유효 주문 금액 | 481,000원 |
| 예제 배송 지연율 | 배송 완료 40건 중 20건, 0.5 |
| Uvicorn 실제 HTTP | health·적재·지표·주문 목록·경로 필터 200, 인증 누락 401 |
| 판매 경로별 지연 주문 | market_a 조회 3건 모두 요청한 경로와 일치 |
| 전체 주문 페이지 조회 | limit=17, 8페이지, 반환 120건·고유 주문 120건; 조회 중 적재 없음 |
| 주문 목록 복합 필터 | market_a·paid 조회 2건 모두 경로·상태 일치 |
| JSON·TOML·YAML | 구문 파싱 통과 |

전체 로컬 검증 명령은 `python -m scripts.check`입니다. 이 명령으로 SQLite 마이그레이션 왕복, 문서 검색 평가와 실제 HTTP 시연 서버 기동·종료도 재실행합니다.

## 어떤 위험을 확인했나요?

중복 재전송에 따른 지표 증가, 같은 버전의 내용 충돌, 이전 버전의 늦은 도착, 미래 갱신 버전 제외, 시간대 표기 차이, 기간 경계, 취소·환불 금액 제외, 분모 0, 잘못된 금액·날짜·상태, 최대 배치 크기, 트랜잭션 실패 시 전체 롤백, API 인증, 문서 근거 반환을 확인했습니다.

이번 버전에는 초기 마이그레이션이 모델의 세 테이블·UNIQUE 제약·인덱스를 만드는지, base까지 되돌렸을 때 업무 테이블과 현재 리비전이 제거되는지, 다시 적용할 수 있는지 확인하는 테스트를 추가했습니다. 마이그레이션하지 않은 DB에서 앱이 `create_all`로 문제를 가리지 않고 시작을 거부하는지도 확인했습니다.

## 검색 평가의 해석

예제 문서 6개, 관련 질문 12개, 무관한 질문 3개를 직접 구성했습니다. 관련 질문의 Top-1, Recall@3, MRR@3은 각각 1.0이었고 무관 질문 3개에서는 결과가 없었습니다.

**코드와 함께 만든 작은 예제의 결과이므로 독립 평가도, 실제 사용자 질의 정확도도 아닙니다.** 문서와 질문을 확대하고 처음 보는 질문으로 평가해야 합니다. 이 수치를 이력서의 "실무 검색 정확도 100%"로 표현해서는 안 됩니다.

## 결과 파일

- artifacts/demo_report.json: 재전송 전후 비교, 지표와 오류 기록
- artifacts/retrieval_evaluation.json: 질문별 검색 결과와 순위
- artifacts/http_smoke.json: 실제 HTTP 응답 상태
- artifacts/migration_check.json: SQLite 마이그레이션 왕복 결과
- artifacts/postgres_integration.json: PostgreSQL 원격 검사 결과와 실행 링크
- artifacts/checks.log: 실행 명령과 결과 요약; 전체 원격 로그는 PR의 Checks에서 확인

## 확인하지 않은 범위

이 환경에는 Docker 실행 파일이 없어 로컬 Compose 기동을 검증하지 않았습니다. PostgreSQL은 GitHub Actions의 새 임시 DB 한 개에서 순차 실행했으므로 기존 DB를 첫 리비전에 연결하는 절차, 두 번째 스키마 변경, 병렬 부하와 여러 앱 인스턴스의 배포 순서는 확인하지 않았습니다. 클라우드 배포, 사용자별 데이터 분리, 대용량 성능, 실제 업무 데이터, LLM 응답 품질도 아직 검증하지 않았습니다.

테스트 중 의존성에서 deprecation 경고 2종(httpx 기반 TestClient, anyio BlockingPortal 별칭)이 발생했습니다. 테스트 실패는 없었습니다. 현재 고정 버전에서는 동작을 확인했으며 이후 의존성 갱신 때 함께 정리할 항목입니다.

## 0.3.0 원격 실행 근거

2026-09-21에 [PR #3](https://github.com/Ajsjee3/Ajsjee3/pull/3)의 코드 커밋 `414ed01b6a38e0a71c4f6d75855753dfe2c90493`을 검사한 [GitHub Actions 실행](https://github.com/Ajsjee3/Ajsjee3/actions/runs/35590864397)이 success로 완료됐습니다.

`checks` job에서 고정 의존성을 새로 설치하고 `python -m scripts.check`를 실행해 Ruff와 테스트 61개, SQLite 마이그레이션 왕복, 기존 데모와 실제 HTTP 검사를 통과했습니다. 별도 `postgres-integration` job은 공식 `postgres:16` 이미지의 16.15 서버에서 `python -m scripts.check_postgres`를 실행했습니다. 원격 로그에서 리비전 `20260921_01`, 모델 차이 없음, 시간대 보존, 적재·재전송·지표·페이지 결과와 복구를 확인했습니다.

## 0.2.0 원격 실행 근거

2026-09-14에 [PR #2](https://github.com/Ajsjee3/Ajsjee3/pull/2)의 코드 커밋 `e75ae24200aa8bdaab16fcf9658d152e5134b408`을 검사한 [GitHub Actions 실행](https://github.com/Ajsjee3/Ajsjee3/actions/runs/34834324632)이 success로 완료됐습니다. 고정 의존성 설치와 `python -m scripts.check` 단계의 성공을 확인했습니다.

원격 로그에도 Ruff 통과, pytest 59개 통과, 실제 HTTP 8페이지·반환 120건·고유 주문 120건, 주문 목록 인증 누락 401이 기록됐습니다. 이후 검증 링크를 정리한 문서 변경의 상태는 [PR Checks](https://github.com/Ajsjee3/Ajsjee3/pull/2/checks)에서 확인할 수 있습니다.

## 이전 버전의 원격 실행 근거

2026-09-09에 코드 커밋 `7d840f6b4eb6941e7997074a0ff25983061b00dd`의 [GitHub Actions 실행](https://github.com/Ajsjee3/Ajsjee3/actions/runs/34298134180)이 success로 완료됐습니다. 저장소의 `projects/orderlens`에서 고정 의존성을 설치하고 `python -m scripts.check`를 실행한 결과입니다.

위 링크는 0.1.1의 기록이며 이후 버전의 성공 근거와 구분합니다.
