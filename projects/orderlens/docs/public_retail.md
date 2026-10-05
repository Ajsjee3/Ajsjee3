# 공개 거래 CSV 정제

출처 확인·다운로드: 2026-09-22. 변환 재현: 2026-09-28. DB 적재 검증: 2026-10-05. 실제 자료의 통화와 취소 행을 보존하면서 정상 행과 계약에 맞지 않는 행을 분리하고 전용 테이블에 저장합니다. 기존 원화 배송 주문 API와는 구분합니다.

## 출처와 이용 조건

- 자료: Daqing Chen (2015), [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail), DOI [10.24432/C5BW33](https://doi.org/10.24432/C5BW33)
- 라이선스: 원본 페이지의 CC BY 4.0. 이 문서는 출처를 표시하고 아래 변환 내용을 기록합니다.
- [다운로드한 CSV](https://archive.ics.uci.edu/static/public/352/data.csv): 45,038,760바이트, 거래 기간 2010-12-01~2011-12-09
- SHA-256: `a2f79bbdd4463df6db8a3f5a50b9c980ae8f645a370bf5e2c0d6097f9e817b05`

원본 CSV와 정제 JSONL은 Git에 올리지 않습니다. 결과물에는 고객 식별자·상품 설명 원문을 싣지 않고, 두 필드의 누락 여부만 집계합니다. 내려받은 자료는 현재 채용 시장이나 서비스 운영 실적을 보여 주는 자료가 아닙니다.

## 재현

`projects/orderlens`에서 고정 의존성을 설치한 뒤 실행합니다. 추가 라이브러리나 API 키는 필요하지 않습니다. 다운로드에는 네트워크가 필요하며 기본 검사는 작은 합성 입력으로 오프라인 실행합니다.

```bash
python -m scripts.fetch_retail
python -m scripts.transform_retail data/raw/online_retail.csv --output data/processed/retail-a
python -m scripts.transform_retail data/raw/online_retail.csv --output data/processed/retail-b
diff data/processed/retail-a/report.json data/processed/retail-b/report.json
python -m alembic upgrade head
python -m scripts.load_retail data/processed/retail-a --database-url sqlite:///retail.db
python -m scripts.load_retail data/processed/retail-a --database-url sqlite:///retail.db
```

다운로더는 원본 해시를 확인합니다. 이미 같은 파일이 있으면 재사용하고, 다른 내용의 파일이 있으면 덮어쓰지 않습니다. 제공처가 CSV를 바꾸면 출처와 변경 내용을 검토해 고정 해시를 갱신해야 합니다.

출력 디렉터리는 새 경로여야 합니다. `accepted.jsonl`은 정제 행, `rejected.jsonl`은 원본 위치·오류 코드·필드, `report.json`은 건수·금액·입출력 해시를 담습니다. CSV 파싱·입출력 실패 시 부분 JSONL이 남을 수 있지만 성공 보고서는 쓰지 않습니다. 성공 보고서가 있는 실행만 완료로 취급합니다. 다운로드 도중 디스크 쓰기가 실패한 파일은 다음 실행에서 해시 불일치로 거부되므로 별도 경로로 다시 받아야 합니다.

동일한 열을 가진 다른 CSV도 변환할 수 있습니다. 다만 입력 해시가 위 원본과 다르면 출처는 `unverified`, 다운로드 URL과 라이선스는 `null`로 기록합니다. 형식이 같다는 이유로 UCI 자료나 CC BY 자료로 단정하지 않습니다.

적재 명령은 먼저 DB가 Alembic head인지 확인합니다. 첫 실행은 `status=loaded`, 두 번째 실행은 `status=already_loaded`를 반환합니다. 파일 해시는 같지만 정제 JSONL 해시나 보고서 내용이 달라지면 기존 행을 덮어쓰지 않고 중단합니다. 자세한 키·트랜잭션·금액 타입은 [DB 적재 결정 기록](decisions/retail_db_ingestion.md)에 있습니다.

## 변환 계약

| 원본 | 정제·판정 |
|---|---|
| InvoiceNo | 문자열 보존. C/c 접두사가 있으면 `is_cancellation=true` |
| StockCode | 문자열 보존. 한 행은 상품별 거래 기록이며 주문 하나가 아님 |
| Quantity | 0이 아닌 부호 있는 정수, 절댓값 2,147,483,647 이하 |
| UnitPrice | GBP Decimal, 음수 제외. 소수점 이하 최대 6자리, 정수부 최대 10자리 |
| InvoiceDate | 월/일/연도 시:분 형식을 지역 시각 ISO 문자열로 변환; 원본에 시간대가 없어 `timezone=null` |
| Country | 필수 문자열. 국가별 날짜·시간대를 추정하지 않음 |
| CustomerID·Description | 원문을 결과에서 제외; 누락 플래그만 보존 |

`line_amount = quantity × unit_price`를 Decimal 정밀도 50으로 계산하고 문자열로 저장합니다. 부동소수점 반올림이나 GBP→KRW 환산을 하지 않습니다. 가격 0, 고객 식별자·상품 설명 누락, 소수 페니 가격, C 표시 없는 음수 수량은 삭제하지 않고 플래그로 남깁니다.

행 ID는 `입력 파일 SHA-256:CSV 레코드 번호`입니다. 레코드 번호는 헤더 다음부터 1이며 따옴표 안 줄바꿈을 한 레코드로 셉니다. 값이 같은 두 행도 위치가 다르면 보존합니다. 서로 다른 파일의 같은 거래를 식별하거나 취소 행과 원거래를 연결하는 키는 아직 없습니다.

## 실행 결과

Linux x86_64, Python 3.12.14에서 전체 파일을 두 번 정제했습니다. 두 보고서와 출력 파일 해시가 일치했습니다. 다운로드 스크립트로 새 파일을 받는 경로도 실제 실행했습니다.

| 항목 | 결과 |
|---|---:|
| 입력 | 541,909행 |
| 정제 통과 | 541,907행 |
| 격리 | 음수 UnitPrice 2행 |
| 통과 행 중 C 표시 | 9,288행 |
| 고객 식별자 누락 | 135,078행 |
| 상품 설명 누락 | 1,454행 |
| C 표시 없는 음수 수량 | 1,336행 |
| 가격 0 | 2,515행 |
| 소수 페니 가격 | 4행 |
| 통과 행의 부호 있는 금액 합 | GBP 9,769,872.054 |

플래그는 겹칠 수 있어 합계가 행 수와 같지 않습니다. 격리한 2행은 이 변환기의 음수 단가 제외 계약에 따른 결과입니다. 원천 회계 자료 자체가 잘못됐다고 판정한 것이 아닙니다.

금액 합은 통과한 행의 수량×단가를 더한 값입니다. 회계 조정, 취소·환불 연결, 매출 인식 기준을 검증하지 않았으므로 매출·순이익·성능 개선 실적으로 부르지 않습니다. 배송 시각도 없어 기존 배송 지연 지표의 실제 데이터 검증에 사용하지 않았습니다.

원본 실행 근거: [품질 보고서](../artifacts/retail_quality.json), [반복 실행 비교](../artifacts/retail_replay.json). 계약과 예외 사례는 [test_retail.py](../tests/test_retail.py), 구현은 [retail.py](../orderlens/retail.py)에 있습니다.

## DB 적재 결과

Linux x86_64, Python 3.12.14, SQLite 3.53.1의 임시 DB에 전체 정제 결과를 넣었습니다. 두 번째 Alembic 리비전은 `retail_imports`, `retail_lines`를 만들며 기존 주문 테이블은 바꾸지 않습니다.

| 확인 항목 | 결과 |
|---|---:|
| 첫 적재 | 541,907행 삽입 |
| 파일 출처 행 | 1개 |
| 고유 `(파일 해시, 원본 위치)` | 541,907개 |
| 같은 파일 재적재 | 새 행 0개 · 중복 541,907개 |
| DB의 부호 있는 금액 합 | GBP 9,769,872.054 |
| DB의 취소 표시 행 | 9,288개 |
| Alembic head | `20261005_02` |

[전체 적재 근거](../artifacts/retail_db_check.json)는 임시 SQLite 결과입니다. PostgreSQL에서는 PR의 합성 2행으로 NUMERIC 정밀도, 지역 시각, UNIQUE 제약, 최초·재적재와 마이그레이션 왕복을 확인합니다. 전체 541,907행을 PostgreSQL에 적재하거나 처리 시간을 비교한 결과는 아닙니다.

적재 구현은 [retail_db.py](../orderlens/retail_db.py), 예외·롤백 테스트는 [test_retail_db.py](../tests/test_retail_db.py)에 있습니다. 다음은 실제 규모에서 국가·기간·취소별 집계 SQL의 실행계획을 측정하고, 인덱스 전후를 같은 조건으로 비교하는 작업입니다. 취소와 원거래 연결 및 회계상 매출 계산은 아직 하지 않습니다.
