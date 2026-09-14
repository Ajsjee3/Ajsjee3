# OrderLens

주문 상태 변경과 중복 전송을 처리하고, 배송이 늦어진 주문을 찾는 API입니다.

`Python 3.12` · `FastAPI` · `SQLAlchemy` · `SQLite` · `pytest`

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
| 운영 기준을 찾아야 함 | BM25 검색으로 문서 ID와 버전을 함께 반환 | [retrieval.py](orderlens/retrieval.py) |

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

명령 한 번으로 임시 DB 적재, 재전송, 지표 비교, 검색 평가, 실제 HTTP 요청까지 재실행합니다. 원본 결과는 [demo_report.json](artifacts/demo_report.json), [HTTP 결과](artifacts/http_smoke.json), [검증 기록](docs/validation.md)에 남깁니다.

## 설계에서 정한 기준

- `source + order_id + revision`이 같으면서 내용이 다르면 기존 데이터를 덮어쓰지 않고 충돌로 기록합니다.
- `as_of`보다 늦게 갱신된 버전을 제외한 뒤 최신 상태를 선택합니다.
- 목록은 주문 시각 내림차순, 판매 경로·주문 번호 오름차순입니다. `as_of`를 고정해도 과거 자료가 새로 적재되면 페이지 경계가 달라질 수 있습니다.
- 취소·환불 주문은 유효 주문 금액에서 제외합니다. 배송 완료 주문이 없으면 지연율은 `null`입니다.
- 검색 점수는 확률이 아닙니다. 현재 검색은 BM25이며 요약은 규칙 기반입니다.

상세 내용은 [설계 문서](docs/design.md)에서 확인할 수 있습니다.

## 다음 작업

현재 버전은 **0.2.0**입니다. SQLite에서 실행하며, PostgreSQL·Docker 설정은 실제 통합 검증이 남아 있습니다. 실제 고객 데이터, 외부 배포, LLM 답변 생성은 아직 포함하지 않았습니다.

다음 변경은 PostgreSQL 통합 검증과 초기 마이그레이션입니다. [작업 목록](docs/automation_and_backlog.md) · [개발 기록](docs/progress.md) · [참고 저장소](docs/references.md) · [기여 안내](CONTRIBUTING.md)
