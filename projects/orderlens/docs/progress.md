# 개발 기록

## 2026-10-26 · 0.8.0

운영 문서를 6개에서 10개로 늘리고, 검색 대상 `knowledge.json`, 질문 `retrieval_queries.json`, 관련 문서 정답표 `retrieval_qrels.json`을 분리했습니다. 평가 자료를 읽을 때 문서·질문 ID 중복, 비어 있는 본문, 질문 종류, 관련 문서 누락과 알 수 없는 문서 참조를 먼저 검사합니다. 질문은 실제 사용자 로그가 아닌 수작업 문장으로 2026-10-26에 고정했습니다.

관련 질문 24개와 관련 문서가 없어야 하는 질문 8개를 Top-3으로 평가했습니다. Top-1 정확도 0.625, Recall@3 0.9375, MRR@3 0.770833이었고 무관 질문에서 결과가 없었던 비율은 0.25였습니다. 관련 문서가 1위가 아니거나 모두 검색되지 않은 질문 9개와 무관 질문 오탐 6개를 [평가 결과](../artifacts/retrieval_evaluation.json)에 그대로 남겼습니다. 이전 6문서·15질문의 1.0 결과보다 어렵고 구체적인 실패 기준선입니다.

Linux x86_64, Python 3.12.14, SQLite 3.53.1의 기존 `requirements.lock` 환경에서 `python -m scripts.check`를 실행했습니다. 종료 코드 0, Ruff 통과, pytest 95개 통과, 기존 의존성 경고 2종이었습니다. 네 리비전의 마이그레이션 왕복, 강제 적재 실패·복구, 주문 재전송, 실제 HTTP 8페이지·고유 주문 120건도 함께 통과했습니다.

새 참고는 `beir-cellar/beir`의 별도 corpus·query·qrels 형식, 데이터 검사, Recall·MRR 평가, 사용자 정의 데이터 예제와 해당 변경 커밋입니다. 형식 분리와 실패 행 보존 원칙만 적용했고 BEIR 코드나 의존성은 가져오지 않았습니다. 다음 작업은 이 고정 질문을 수정하지 않고 BM25 점수 기준으로 근거 부족 질문을 보류했을 때 정답 검색과 오탐의 변화를 비교하는 것입니다.

## 2026-10-19 · 0.7.0

공개 거래 CLI 실행마다 `retail_load_attempts` 행을 만들고 `running → succeeded/failed` 상태, 원본·보고서 해시, 종료 시각, 적재·중복 행 수와 제한된 오류를 남기도록 했습니다. 실제 import와 거래 행은 별도 트랜잭션으로 유지해 실패 데이터는 전부 롤백되지만 실행 이력은 보존됩니다. 네 번째 Alembic 리비전 `20261019_04`에 상태·결과·필드 조합 CHECK 제약과 `(source_sha256, started_at)` 인덱스를 추가했습니다.

두 번째 정제 행의 금액을 일부러 틀리게 만들고 `batch_size=1`로 실행했습니다. 첫 행 INSERT 뒤 두 번째 행에서 중단됐지만 `retail_imports=0`, `retail_lines=0`이었고 `failed/data_contract` 시도만 남았습니다. 원본을 복구한 실행은 2행을 적재했고 다시 실행하면 새 행 0개·중복 2개였습니다. 세 이력은 `failed → succeeded/loaded → succeeded/already_loaded`였습니다.

Linux x86_64, Python 3.12.14, SQLite 3.53.1에서 `python -m scripts.check` 종료 코드 0, Ruff 통과, pytest 90개 통과, 기존 의존성 경고 2종이었습니다. 네 리비전의 upgrade·base downgrade·재upgrade와 모델 차이 없음, 강제 실패·복구 재현, 기존 주문·HTTP·검색 결과도 통과했습니다. [PR #7](https://github.com/Ajsjee3/Ajsjee3/pull/7)의 [원격 검사](https://github.com/Ajsjee3/Ajsjee3/actions/runs/39239042095)도 두 job이 통과했습니다. PostgreSQL 16.15에서 실패 뒤 import·거래 행 0건, 복구 적재 2건, 재실행 중복 2건과 네 리비전 왕복을 확인했습니다.

새 참고는 Apache Airflow의 실행 이력 모델·재시도 상태 처리·회귀 테스트·변경 커밋입니다. 실행 시도별 종료 값을 영속화하고 이력 행을 직접 검증하는 원칙만 적용했으며 Airflow 코드나 의존성, 자동 재시도 기능은 가져오지 않았습니다.

`report.json`이나 원본 SHA 자체가 잘못된 실행, 프로세스 강제 종료 뒤 남는 `running` 판정, 동시 첫 적재 경합과 자동 재시도는 아직 다루지 않았습니다. 다음 작업은 기존 BM25 검색의 별도 평가 질문과 실패 사례를 늘리고 기준선을 다시 측정하는 것입니다.

## 2026-10-12 · 0.6.0

공개 거래의 국가·취소 여부·지역 시각을 조건으로 하는 기간 집계와 Alembic 리비전 `20261012_03`을 추가했습니다. `(country, is_cancellation, invoice_at_local)` 순서로 동등 조건을 먼저, 범위 조건을 뒤에 두었습니다. 작은 테스트는 국가·기간 경계·취소 제외·GBP Decimal 합계를 확인하고, 마이그레이션은 인덱스 컬럼 순서와 upgrade·downgrade·재upgrade를 확인합니다.

전체 UCI 정제 행 541,907개를 임시 SQLite에 넣고 Germany의 비취소 2011년 거래를 같은 DB에서 비교했습니다. 전체 스캔과 인덱스 계획의 결과는 모두 8,529행·수량 112,385·부호 있는 금액 GBP 213,626.000000이었습니다. warm-cache에서 5회 예열 뒤 실행 순서를 바꾸며 31회씩 측정한 중앙값은 각각 41.062ms와 1.917ms였습니다. 이 21.42배 비율은 한 로컬 SQLite·한 조건의 결과이며 운영 성능이나 PostgreSQL 향상으로 일반화하지 않습니다. 인덱스 저장 공간은 27,430,912바이트였습니다.

Linux x86_64, Python 3.12.14, SQLite 3.53.1에서 `python -m scripts.check` 종료 코드 0, Ruff 통과, pytest 89개 통과, 기존 의존성 경고 2종이었습니다. [PR #6](https://github.com/Ajsjee3/Ajsjee3/pull/6)의 [원격 검사](https://github.com/Ajsjee3/Ajsjee3/actions/runs/38237841801)도 두 job이 통과했습니다. PostgreSQL 16.15의 10만 합성 행에서 같은 집계 결과와 기본 `Index Scan`, 인덱스 scan을 끈 `Seq Scan`, 세 리비전 왕복을 확인했습니다.

새 참고는 `eugene-khyst/postgresql-performance-essentials`의 README와 `data.sql`입니다. 실행계획을 실제로 측정하고 복합 인덱스의 선두 컬럼과 저장·쓰기 비용을 함께 확인하는 기준만 적용했으며 예제 코드와 오래된 PostgreSQL 설정은 복사하지 않았습니다.

전체 UCI 자료의 PostgreSQL 적재, cold-cache, 여러 국가·기간의 선택도, 동시 쓰기 비용은 아직 확인하지 않았습니다. 다음 작업은 적재 배치의 실패 상태·재시도·복구 관측입니다.

## 2026-10-05 · 0.5.0

공개 거래 정제 결과를 기존 원화 배송 주문과 분리해 저장하는 `retail_imports`, `retail_lines` 모델과 Alembic 리비전 `20261005_02`를 추가했습니다. 단가는 `NUMERIC(16,6)`, 행 금액은 `NUMERIC(26,6)`, 거래 시각은 원천에 시간대가 없으므로 timezone 없는 값으로 저장합니다. `(source_sha256, source_record)` UNIQUE 제약이 파일과 원본 행 위치를 함께 식별합니다.

적재 전에 보고서와 accepted/rejected JSONL 해시·행 수를 확인합니다. 첫 실행은 JSONL을 1,000행씩 한 트랜잭션에 넣고 건수·취소 행·GBP 합계를 보고서와 다시 비교합니다. 같은 파일과 같은 정제 결과의 재실행은 DB를 쓰지 않고 전체 행을 중복으로 반환합니다. 같은 원본 해시에 다른 정제 결과가 오면 덮어쓰지 않습니다. 후반부 행 오류를 만든 테스트에서는 앞서 넣은 배치와 출처 행도 롤백됐습니다.

Linux x86_64, Python 3.12.14, SQLite 3.53.1에서 `python -m scripts.check` 종료 코드 0, Ruff 통과, pytest 84개 통과, 기존 의존성 경고 2종이었습니다. 전체 UCI 정제 결과 541,907행을 임시 SQLite에 적재했고 고유 원본 위치도 541,907개였습니다. 같은 파일의 두 번째 실행은 새 행 0개·중복 541,907개였으며 DB 금액 합은 정제 보고서와 같은 GBP 9,769,872.054였습니다.

새 참고는 SQLAlchemy 공개 저장소의 bulk INSERT 예제와 실행 안내입니다. 매핑 기반 INSERT와 제한된 배치라는 방식만 적용했고 외부 성능 수치나 코드를 가져오지 않았습니다. [PR #5](https://github.com/Ajsjee3/Ajsjee3/pull/5)의 [원격 검사](https://github.com/Ajsjee3/Ajsjee3/actions/runs/37301674282)에서 테스트 84개와 PostgreSQL 16.15의 금액 정밀도·UNIQUE·합성 2행 재적재·마이그레이션 왕복이 통과했습니다.

남은 한계는 동시 프로세스의 첫 적재 경합, 공개 거래 조회 API, 취소와 원거래 연결, 회계상 매출 정의, 전체 데이터의 PostgreSQL 적재입니다. 다음 작업은 전체 규모 집계 SQL의 실행계획과 인덱스 전후 측정입니다.

## 2026-09-28 · 0.4.0

9월 22일에 시작한 공개 거래 정제 작업을 마무리했습니다. UCI Online Retail CSV를 내려받아 고정 SHA-256을 확인하고, 정제 행·오류 행·품질 보고서를 생성합니다. GBP 소수 금액, 취소 표시, 원본 레코드 번호를 보존하고 고객 식별자·상품 설명 원문은 출력에서 제외합니다. 동일한 값의 서로 다른 원본 행을 임의로 중복 제거하지 않습니다.

Linux x86_64, Python 3.12.14, SQLite 3.53.1에서 기본 검사를 실행했습니다. 실제 541,909행은 541,907행 통과·음수 단가 2행 격리였으며, 최종 코드로 두 번 정제한 보고서와 출력 파일 해시가 같았습니다. 원본 다운로드는 9월 22일에 실제 실행했고 9월 28일에는 보관한 동일 해시 파일을 사용했습니다. 결과는 [공개 데이터 안내](public_retail.md)와 artifacts/retail_quality.json, artifacts/retail_replay.json에 기록했습니다.

통화·시간대·행 단위가 기존 주문 모델과 달라 DB·API 연결은 하지 않았습니다. 금액 합은 회계상 매출로 해석하지 않습니다. CSV 파싱·결과 쓰기가 실패하면 성공 보고서가 남지 않는지, 기존 결과를 덮어쓰지 않는지도 테스트했습니다. 전체 테스트 수와 원격 검사 근거는 [검증 기록](validation.md)에서 확인합니다.

[PR #4](https://github.com/Ajsjee3/Ajsjee3/pull/4)의 [원격 검사](https://github.com/Ajsjee3/Ajsjee3/actions/runs/36410453056)도 통과했습니다. 테스트 80개와 PostgreSQL 16.15의 기존 주문 적재·재전송·페이지·마이그레이션 왕복을 로그에서 확인했습니다.

실제 GitHub 참고 파일은 dbt-labs/jaffle-shop의 README·staging SQL·키 검증 정의이며, 행 단위와 금액 단위 구분을 참고했습니다. 코드를 가져오거나 dbt를 추가하지 않았습니다. 제공된 취업 준비 대화와 공고 원문을 비교해 첫 프로젝트의 데이터 처리·복구를 먼저 완성하고 두 번째 금융·AI 프로젝트는 학습 기준 통과 후 선택하도록 계획을 수정했습니다.

다음: 공개 거래 전용 테이블과 파일 단위 재적재 방지. 학습 과제: `test_exact_amount_and_source_semantics`에서 수량 -3과 단가 0.001의 결과가 왜 GBP -0.003인지, 취소 표시를 왜 따로 남기는지 설명합니다. 이는 아직 수행 완료한 학습 기록이 아닙니다.

## 2026-09-21 · 0.3.0

Alembic 초기 리비전 `20260921_01`을 추가했습니다. 앱 시작 시 실행하던 `create_all`을 제거하고 DB의 현재 리비전이 코드의 head와 같은지 확인합니다. 마이그레이션하지 않은 DB에서는 필요한 명령을 안내하며 시작을 중단합니다.

테스트·데모·실제 HTTP 시연은 각 임시 DB에 마이그레이션을 먼저 적용합니다. Docker Compose는 PostgreSQL의 준비 상태를 기다린 뒤 일회성 migrate 서비스가 성공해야 API를 시작합니다. PostgreSQL 전용 검사는 `_test` DB만 허용하며 적재·재전송·지표·페이지 조회와 downgrade·재upgrade를 실행합니다.

로컬 검증: Linux x86_64, Python 3.12.14, SQLite 3.53.1에서 `python -m scripts.check` 종료 코드 0. Ruff 통과, pytest 61개 통과, 의존성 경고 2종. 초기 스키마의 upgrade·downgrade·재upgrade와 미적용 DB의 앱 시작 거부를 확인했습니다. 합성 데이터와 실제 HTTP 결과는 0.2.0과 같았습니다.

작업 [PR #3](https://github.com/Ajsjee3/Ajsjee3/pull/3)의 [원격 실행](https://github.com/Ajsjee3/Ajsjee3/actions/runs/35590864397)에서 PostgreSQL 16.15 통합 검사가 통과했습니다. 첫 309행은 저장 300·중복 5·오류 4, 재전송은 새 버전 0·중복 305·오류 4였고 지표가 같았습니다. 120건을 17건씩 8페이지로 읽어 고유 주문 수도 120건인지 확인했습니다. TIMESTAMP WITH TIME ZONE, 모델과 리비전 일치, downgrade 후 업무 테이블 제거와 재upgrade도 확인했습니다.

로컬 Docker와 기존 운영 DB 전환, 두 번째 스키마 변경, 병렬 요청은 아직 확인하지 않았습니다.

다음: 출처와 이용 조건이 분명한 공개 데이터 변환기를 작은 범위로 시작합니다.

## 2026-09-14 · 0.2.0

`GET /v1/orders`에 판매 경로·상태 필터와 LIMIT·OFFSET 페이지 조회를 추가했습니다. 최신 버전을 고른 뒤 상태를 거르므로 취소된 주문의 이전 결제 상태가 목록에 남지 않습니다. 주문 시각 내림차순, 판매 경로·주문 번호 오름차순으로 정렬하며 응답에 `as_of`, `has_more`, `next_offset`을 포함합니다.

별도 COUNT 대신 한 건을 더 조회해 다음 페이지 여부를 판단합니다. 데이터가 고정된 경우의 중복·누락 방지와, 과거 자료를 뒤늦게 넣어 페이지 경계가 밀리는 경우를 테스트에서 구분했습니다. 기준 시각만으로 DB 스냅샷이 고정되지는 않습니다.

검증: Python 3.12.14, SQLite 3.53.1에서 `python -m scripts.check` 실행. Ruff 통과, pytest 59개 통과, 의존성 경고 2종. 실제 Uvicorn HTTP로 고정된 주문 120건을 17건씩 8페이지로 조회했고 고유 주문 수도 120건이었습니다. 경로·상태 복합 필터와 인증 누락도 확인했습니다. 기존 합성 데이터 재전송 결과와 검색 평가 결과는 유지됐습니다.

참고: fastapi-pagination의 파라미터 검증과 SQLAlchemy 페이지 쿼리 코드를 읽었습니다. 라이브러리를 추가하거나 코드를 복사하지 않았으며, 확인한 파일과 적용 범위는 [references.md](references.md)에 남겼습니다.

[PR #2](https://github.com/Ajsjee3/Ajsjee3/pull/2)에서 변경을 설명하고 [원격 검사](https://github.com/Ajsjee3/Ajsjee3/actions/runs/34834324632)의 성공과 동일한 테스트·HTTP 결과를 확인했습니다.

다음: PostgreSQL 초기 마이그레이션과 실제 DB 통합 검증. 대용량 offset 성능, 동시 적재 중 페이지 일관성, 사용자별 권한은 이번 변경의 완료 범위가 아닙니다.

## 2026-09-09 · 0.1.1

판매 경로별 지연 주문 조회를 추가했습니다. 전체 조회 결과를 받은 뒤 경로를 걸러내면 다른 경로가 조회 한도를 차지할 수 있어, SQL에서 경로를 고른 다음 정렬과 한도를 적용했습니다.

기존 최신 버전 선택과 응답 구조는 유지했습니다. 경로를 생략하면 전체 경로, 존재하지만 주문이 없으면 빈 목록, 허용되지 않은 값이면 422를 반환합니다.

검증: `python -m scripts.check` 실행. Ruff 통과, pytest 32개 통과, 합성 주문 재전송 전후 지표 동일. 실제 Uvicorn HTTP 요청에서 market_a 3건 조회와 경로 일치를 확인했습니다. 실행 환경은 Python 3.12.14, SQLite 3.53.1입니다.

README에서 문제·구현·재현 결과를 먼저 읽을 수 있게 정리하고, 긴 실행 안내는 quickstart.md로 옮겼습니다. 실제 공개 저장소에서 확인한 구조와 적용한 부분은 references.md에 기록했습니다.

다음: 상태별 주문 목록과 페이지 처리. 지표 기준 시각과 정렬 조건을 유지하며 페이지 경계에서 중복·누락이 없는지 확인합니다.

## 2026-09-08 · 0.1.0

주문 버전 적재, 중복·충돌 구분, 최신 상태 집계, BM25 문서 검색, API 키 인증과 재현용 합성 데이터를 구성했습니다. 최초 SQLite 검증에서 테스트 27개가 통과했습니다.
