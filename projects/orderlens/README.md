# OrderLens

주문 상태 변경과 중복 전송을 처리하고, 배송이 늦어진 주문을 찾는 API입니다.

`Python 3.12` · `FastAPI` · `SQLAlchemy` · `PostgreSQL` · `SQLite` · `Alembic` · `pytest`

## 어떤 문제를 다루나요?

같은 주문이라도 결제, 배송, 취소를 거치면 여러 행으로 들어옵니다. 이 행들을 그대로 합산하면 주문 수와 금액이 부풀려집니다. 이미 받은 데이터를 다시 처리했을 때도 같은 문제가 생깁니다.

OrderLens는 판매 경로와 주문 번호를 묶어 주문을 구분하고, 버전별 변경 내역을 저장합니다. 집계와 목록 조회에는 조회 시점에 해당하는 최신 버전만 사용합니다. 판매 경로·상태별 주문 목록, 지연 주문 조회와 운영 문서 검색을 제공합니다.

## 주요 구현

| 문제 | 처리 방식 | 확인할 코드 |
|---|---|---|
| 같은 데이터가 다시 들어옴 | 버전 식별자와 정규화된 내용의 해시로 중복·충돌 구분 | [ingestion.py](orderlens/ingestion.py) |
| 이전 상태가 늦게 도착함 | SQL 윈도 함수로 주문별 최신 버전 선택 | [analytics.py](orderlens/analytics.py) |
| 일부 행의 금액·날짜가 잘못됨 | 정상 행을 적재하고 오류 행의 위치와 사유를 기록 | [schemas.py](orderlens/schemas.py) |
| 특정 판매 경로의 지연 주문이 필요함 | 최신 상태와 경로를 고른 후 정렬·조회 한도 적용 | [필터 설계](docs/decisions/source_filter.md) |
| 주문 목록을 나눠 읽어야 함 | 최신 상태를 필터링하고 고정 정렬 후 SQL LIMIT·OFFSET 적용 | [페이지 조회 설계](docs/decisions/order_pagination.md) |
| DB 구조 변경 이력이 필요함 | Alembic 리비전을 적용하고 앱 시작 전에 스키마 버전 확인 | [마이그레이션 설계](docs/decisions/schema_migrations.md) |
| 공개 거래의 단위와 품질을 확인해야 함 | GBP Decimal·취소 표시를 보존하고 오류 행·출처·해시를 기록 | [공개 데이터 정제](docs/public_retail.md) |
| 같은 공개 파일이 다시 들어옴 | 파일 해시와 CSV 레코드 번호를 고유 키로 두고 한 트랜잭션에 분할 적재 | [DB 적재 설계](docs/decisions/retail_db_ingestion.md) |
| 실제 규모의 국가·기간 집계가 전체 행을 읽음 | 같은 조건의 실행계획을 비교하고 동등 조건 뒤에 시각 범위를 둔 복합 인덱스 적용 | [인덱스 비교](docs/decisions/retail_query_index.md) |
| 적재 실패가 롤백 뒤 사라짐 | 실행 시도는 먼저 남기고 데이터 트랜잭션을 분리해 실패·복구·재실행 결과 기록 | [복구 기록 설계](docs/decisions/retail_load_recovery.md) |
| 운영 기준을 찾아야 함 | BM25로 문서 ID·버전을 반환하고 별도 질문·정답표로 실패 사례까지 평가 | [retrieval_evaluation.py](orderlens/retrieval_evaluation.py) |

## 실행

저장소를 받은 뒤 `projects/orderlens`에서 실행합니다. 외부 서비스 계정이나 유료 API 키는 필요하지 않습니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m scripts.check
```

Windows 실행법, 서버 기동, 요청 예시는 [실행 안내](docs/quickstart.md)에 있습니다.

서버를 켜고 예제 데이터를 적재한 뒤 다음 요청으로 결제 상태의 주문을 2건씩 조회할 수 있습니다.

```bash
curl 'http://127.0.0.1:8000/v1/orders?source=market_a&status=paid&limit=2&offset=0&as_of=2026-09-08T00%3A00%3A00Z' \
  -H 'X-API-Key: orderlens-local-demo-key'
```

다음 요청에는 응답의 `next_offset`을 넣고 `as_of`와 필터를 유지합니다. 마지막 페이지는 `has_more: false`, `next_offset: null`입니다.

## 재현 결과

기준 시각을 `2026-09-08T00:00:00Z`로 고정한 합성 주문 데이터입니다.

| 확인 항목 | 결과 |
|---|---|
| 최초 309행 입력 | 저장 300개 · 중복 5개 · 오류 4개 |
| 같은 309행 재전송 | 새 버전 0개 · 중복 305개 · 오류 4개 |
| 최신 주문 집계 | 120건 |
| 배송 예정 시각이 지난 미완료 주문 | 40건 |
| 재전송 전후 지표 | 동일 |
| 고정된 주문 목록을 17건씩 실제 HTTP 조회 | 8페이지 · 120건 · 중복·누락 0건 |
| 임시 SQLite 초기 마이그레이션 | upgrade · downgrade · 재upgrade 성공 |
| PostgreSQL 16.15 통합 검사 | 주문 재전송·120건 페이지 유지 · 공개 거래 실패·복구·재실행 · 10만 행 Index Scan · 네 리비전 왕복 |
| UCI 공개 거래의 임시 SQLite 적재 | 541,907행 · 고유 원본 위치 541,907개 · GBP 합계 9,769,872.054 |
| 같은 공개 파일 재적재 | 새 행 0개 · 중복 541,907개 · DB 행 수 유지 |
| Germany 비취소 2011년 집계 | 8,529행 · 수량 112,385 · 부호 있는 금액 GBP 213,626.000000 |
| 같은 DB의 강제 계획 비교 | 전체 스캔 중앙값 41.062 ms · 복합 인덱스 1.917 ms · 각 31회 |
| 강제 적재 실패 뒤 복구 | 실패 뒤 거래 0행 · 실패 이력 1건 · 복구 2행 · 재실행 새 행 0개 |
| BM25 고정 평가집합 | 문서 10개 · 관련 질문 24개 · 무관 질문 8개 |
| BM25 기준선 | Top-1 0.625 · Recall@3 0.9375 · MRR@3 0.770833 |
| 무관 질문 보류 | 결과 없음 2/8 · 오탐 6건 |

명령 한 번으로 임시 DB 마이그레이션, 강제 적재 실패·복구, 적재·재전송, 지표 비교, 검색 평가, 실제 HTTP 요청까지 재실행합니다. 원본 결과는 [검색 평가](artifacts/retrieval_evaluation.json), [SQLite 마이그레이션](artifacts/migration_check.json), [실패·복구](artifacts/retail_recovery.json), [공개 거래 DB 적재](artifacts/retail_db_check.json), [SQL 계획 비교](artifacts/retail_query_benchmark.json), [PostgreSQL 통합 검사](artifacts/postgres_integration.json), [demo_report.json](artifacts/demo_report.json), [HTTP 결과](artifacts/http_smoke.json), [검증 기록](docs/validation.md)에 남깁니다.

## 설계에서 정한 기준

- `source + order_id + revision`이 같으면서 내용이 다르면 기존 데이터를 덮어쓰지 않고 충돌로 기록합니다.
- `as_of`보다 늦게 갱신된 버전을 제외한 뒤 최신 상태를 선택합니다.
- 목록은 주문 시각 내림차순, 판매 경로·주문 번호 오름차순입니다. `as_of`를 고정해도 과거 자료가 새로 적재되면 페이지 경계가 달라질 수 있습니다.
- 앱은 DB 테이블을 자동 생성하지 않습니다. 서버 시작 전에 Alembic head를 적용하고, 코드와 DB의 리비전이 다르면 시작을 중단합니다.
- 공개 거래 단가는 `NUMERIC(16,6)`, 행 금액은 `NUMERIC(26,6)`으로 저장합니다. 원천에 없는 시간대와 원화 금액을 만들지 않습니다.
- 공개 거래 기간은 시작을 포함하고 종료를 제외합니다. `(country, is_cancellation, invoice_at_local)` 인덱스의 조회 이득과 저장 공간 비용을 함께 기록합니다.
- 공개 거래 적재 시도와 데이터 INSERT는 트랜잭션을 분리합니다. 실패 데이터는 롤백하되, 원본·보고서 해시와 제한된 오류는 시도 이력에 남깁니다.
- 취소·환불 주문은 유효 주문 금액에서 제외합니다. 배송 완료 주문이 없으면 지연율은 `null`입니다.
- 검색 점수는 확률이 아닙니다. 현재 검색은 BM25이며 요약은 규칙 기반입니다. 평가 질문은 실제 사용자 로그가 아니라 수작업한 고정 예제입니다.

상세 내용은 [설계 문서](docs/design.md)에서 확인할 수 있습니다.

## 다음 작업

현재 버전은 **0.8.0**입니다. 운영 문서 10개, 수작업한 관련 질문 24개와 무관 질문 8개, 별도 정답표로 검색 기준선을 다시 측정했습니다. 데이터 계약은 문서·질문·정답표의 ID와 종류를 검사하고, 관련 문서가 1위가 아니거나 무관 질문에 결과가 나온 사례를 모두 JSON에 남깁니다.

이 평가집합은 실제 사용자 로그도 독립 평가도 아닙니다. 높은 수치만 고르지 않도록 2026-10-26에 고정했고, 다음 변경에서는 질문을 바꾸지 않은 채 점수 기준으로 무관 질문을 보류했을 때 정답 검색과 오탐이 어떻게 달라지는지 비교합니다. 공개 거래 조회 API, 외부 배포와 LLM 답변 생성도 후속 작업입니다.

[PR #8](https://github.com/Ajsjee3/Ajsjee3/pull/8)의 [GitHub Actions](https://github.com/Ajsjee3/Ajsjee3/actions/runs/40310364289)에서 Python 3.12.15 일반 검사와 PostgreSQL 16.15 통합 검사가 통과했습니다.

[작업 목록](docs/automation_and_backlog.md) · [개발 기록](docs/progress.md) · [참고 저장소](docs/references.md) · [기여 안내](CONTRIBUTING.md)
