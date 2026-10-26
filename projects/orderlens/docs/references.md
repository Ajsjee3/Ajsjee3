# 참고 저장소와 적용한 부분

## 2026-10-26 · 검색 평가 자료와 실패 행

[beir-cellar/beir](https://github.com/beir-cellar/beir/tree/ef83d29307061c65d04b035b4f4e7c18bd8374af)의 검색 평가 형식·코드·실행 예제와 관련 변경 기록을 직접 읽었습니다. 큰 벤치마크 라이브러리를 도입하지 않고, 작은 OrderLens 자료에서 문서·질문·정답표를 분리하고 순위 지표와 실패 행을 남기는 원칙만 적용했습니다.

| 확인한 파일·변경 | 확인한 내용 | 이번 변경에 적용한 부분 |
|---|---|---|
| [README.md](https://github.com/beir-cellar/beir/blob/ef83d29307061c65d04b035b4f4e7c18bd8374af/README.md) | corpus·query·qrels로 검색 자료를 구성하고 여러 순위 지표로 평가 | 검색 대상·질문·관련 문서 표를 서로 다른 JSON에 보존 |
| [data_loader.py](https://github.com/beir-cellar/beir/blob/ef83d29307061c65d04b035b4f4e7c18bd8374af/beir/datasets/data_loader.py) | `corpus.jsonl`, `queries.jsonl`, `qrels/test.tsv`를 따로 읽고 ID 연결을 검사 | 중복 ID, 빈 질문, 정답 누락과 알 수 없는 문서 참조를 실행 전에 거부 |
| [evaluation.py](https://github.com/beir-cellar/beir/blob/ef83d29307061c65d04b035b4f4e7c18bd8374af/beir/retrieval/evaluation.py) | NDCG·MAP·Recall·Precision과 MRR 계산 | 작은 이진 정답표에 맞춰 Top-1·Recall@3·MRR@3을 직접 계산 |
| [dataset README](https://github.com/beir-cellar/beir/blob/ef83d29307061c65d04b035b4f4e7c18bd8374af/examples/dataset/README.md) | 질문·정답의 출처와 split을 데이터 설명에 함께 둠 | 수작업 질문, 고정일, 실제 사용자 로그가 아니라는 한계를 결과에 포함 |
| [BM25 평가 예제](https://github.com/beir-cellar/beir/blob/ef83d29307061c65d04b035b4f4e7c18bd8374af/examples/retrieval/evaluation/lexical/evaluate_bm25.py) | 검색 실행과 평가를 한 명령으로 재현 | `python -m scripts.check` 안에서 기준선을 다시 만들고 JSON 저장 |
| [사용자 자료 예제](https://github.com/beir-cellar/beir/blob/ef83d29307061c65d04b035b4f4e7c18bd8374af/examples/retrieval/evaluation/custom/evaluate_custom_dataset_files.py) | 별도 corpus·query·qrels 파일의 최소 스키마 | 작은 저장소에 맞는 JSON 스키마와 계약 테스트 작성 |
| [변경 커밋](https://github.com/beir-cellar/beir/commit/845dfe9eb250bd27159e295a3b4b0d90c45cb721) | 사용자 정의 파일 로더와 실행 예제를 코드·문서로 함께 추가 | 평가 입력과 실행 스크립트·테스트·설명을 한 변경으로 연결 |

확인한 Git blob SHA는 순서대로 `e0e7e1019c116dc091deb7ce44657d7c887ed08e`, `b4223f4ab30a55868becece044cc4b2b86181233`, `91aaf2bff505b7a9d8669d3c98c39a0bf3394715`, `447d10732053f4c78f69af4d9ecbd3ad573980d1`, `f4524f3d54321371259bdbe924ef99650d021b27`, `9c5f27a2f2511ed2c876d3af4a92e0ac5455638`입니다. BEIR 소스·데이터·측정값을 복사하지 않았고 의존성도 추가하지 않았습니다. OrderLens의 질문과 관련 문서 표는 현재 기능을 기준으로 새로 작성했습니다.

## 2026-10-19 · 실행 시도별 실패·재시도 이력

[apache/airflow](https://github.com/apache/airflow/tree/66b803d5efbbb743c357f2b4696f49a22aa662b8)의 실행 이력 구현과 변경 기록을 직접 읽었습니다. Airflow 전체 오케스트레이터를 도입하지 않고, 작은 적재 CLI에 필요한 실행 단위와 감사 이력 원칙만 적용했습니다.

| 확인한 파일·변경 | 확인한 내용 | 이번 변경에 적용한 부분 |
|---|---|---|
| [README.md](https://github.com/apache/airflow/blob/66b803d5efbbb743c357f2b4696f49a22aa662b8/README.md) | 데이터 작업은 다시 실행해도 목적지에 중복을 만들지 않는 멱등성이 중요하다고 설명 | 강제 실패 뒤 복구와 이미 성공한 파일의 재실행을 모두 검증 |
| [taskinstancehistory.py](https://github.com/apache/airflow/blob/66b803d5efbbb743c357f2b4696f49a22aa662b8/airflow-core/src/airflow/models/taskinstancehistory.py) | 실행 시도마다 상태·시작·종료·try 번호·제한된 재시도 사유를 별도 행에 보존 | 공개 거래 적재 한 번마다 UUID·상태·종료 시각·행 수·오류 코드를 별도 행으로 기록 |
| [task_instances.py](https://github.com/apache/airflow/blob/66b803d5efbbb743c357f2b4696f49a22aa662b8/airflow-core/src/airflow/api_fastapi/execution_api/routes/task_instances.py) | 다음 시도로 넘어가기 전에 현재 시도의 종료 값과 최대 500자 사유를 이력에 복사 | 실패가 롤백돼도 남는 트랜잭션에서 종료 상태를 확정하고 계약 오류 설명을 500자로 제한 |
| [test_task_instances.py](https://github.com/apache/airflow/blob/66b803d5efbbb743c357f2b4696f49a22aa662b8/airflow-core/tests/unit/api_fastapi/execution_api/versions/head/test_task_instances.py) | live 행만 확인하지 않고 재시도 뒤 history 행의 사유·종료 시각을 조회하는 회귀 테스트 | 실패·복구·재재실행 뒤 세 이력과 최종 거래 행 수를 DB에서 함께 확인 |
| [tasks.rst](https://github.com/apache/airflow/blob/66b803d5efbbb743c357f2b4696f49a22aa662b8/airflow-core/docs/core-concepts/tasks.rst) | `running`, `failed`, `up_for_retry`, `success` 등 상태 의미와 재시도 경계를 문서화 | OrderLens가 실제로 쓰는 `running/succeeded/failed`와 결과 필드의 조합을 CHECK 제약과 결정 기록에 명시 |
| [변경 커밋](https://github.com/apache/airflow/commit/66b803d5efbbb743c357f2b4696f49a22aa662b8) | 재시도 이력에 실제 종료 시각과 최종 값을 보존하도록 소스·테스트를 함께 수정 | 시도 종료 값을 갱신한 뒤 DB에서 직접 읽는 테스트와 재현 스크립트 추가 |

확인한 Git blob SHA는 순서대로 `72391c87cf3423c29f7c35fdbe5369fec8ac0b26`, `47cfdb68ae57733065b491016e3fe3fe054b16cb`, `b813c4c8f7e2ee25952d3a8361bdcb4804c6b75f`, `da6ea74337df5fc3944b74e504fbae738088ccdc`, `95d9846dd5e5ded3c41974087e65721ca0a175ee`입니다. 외부 코드를 복사하거나 Airflow 의존성을 추가하지 않았고, 자동 스케줄링·재시도 정책도 구현한 것으로 표현하지 않습니다.

## 2026-09-22 · 거래 행의 단위와 정제 경계

[dbt-labs/jaffle-shop](https://github.com/dbt-labs/jaffle-shop)의 다음 파일을 직접 읽었습니다. 가상의 식당 데이터를 사용하는 교육용 프로젝트이며 실제 거래 자료나 저자의 채용 성과를 보여 주는 저장소로 취급하지 않았습니다.

| 파일 | 확인한 내용 | 적용한 부분 |
|---|---|---|
| [README.md](https://github.com/dbt-labs/jaffle-shop/blob/main/README.md) | 가상 데이터와 실행 단계 안내 | 실제 자료·합성 예제의 용도를 구분하고 재현 명령 제공 |
| [stg_order_items.sql](https://github.com/dbt-labs/jaffle-shop/blob/main/models/staging/stg_order_items.sql) | 상품 거래 행 ID와 주문 ID를 분리 | UCI의 한 행을 주문 한 건으로 세지 않고 원본 행 ID를 부여 |
| [stg_order_items.yml](https://github.com/dbt-labs/jaffle-shop/blob/main/models/staging/stg_order_items.yml) | 행 단위, 고유·필수 키, 주문 참조 관계의 검증 정의 | 변환 후 고유 행 ID·원본 위치 보존을 테스트 |
| [stg_orders.sql](https://github.com/dbt-labs/jaffle-shop/blob/main/models/staging/stg_orders.sql) | 원본 금액 단위와 환산 값을 명시 | GBP 단위와 Decimal 문자열을 명시하고 원화로 임의 환산하지 않음 |

확인한 Git blob SHA는 순서대로 `7f8e41f725957f2ab8db264614a7d8d3787504af`, `5459a84b0b8561550c2d39be159519c3b78ef82d`, `89086233858e1ac1787e24efd09f8b0480b2ef7d`, `61408c082bf7ea43d542aff34c24e57aaa4075f7`입니다. 외부 코드를 복사하거나 dbt 의존성을 추가하지 않았고 외부 프로젝트의 테스트도 실행하지 않았습니다. 실제 데이터의 출처와 변환 계약은 [UCI 자료 안내](public_retail.md)에 별도로 기록했습니다.

기존 참고 확인일: 2026-09-09. 공개 README, 디렉터리 구조와 아래 코드 파일을 직접 읽고 정리했습니다. 프로젝트 전체를 실행하거나 성능 수치를 재검증한 것은 아닙니다. 이후 새로 읽은 코드는 날짜별로 구분했습니다.

## 2026-10-05 · 대량 행을 DB에 전달하는 경계

[sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy)의 성능 예제 두 파일을 직접 읽었습니다. OrderLens가 사용하는 라이브러리의 공개 저장소이며, 특정 지원자의 취업 성과와는 관계가 없습니다.

| 확인한 파일 | 코드·안내에서 확인한 점 | 이번 변경에 적용한 부분 |
|---|---|---|
| [bulk_inserts.py](https://github.com/sqlalchemy/sqlalchemy/blob/main/examples/performance/bulk_inserts.py) | ORM flush 예제는 1,000행 단위로 나누고, Core 예제는 매핑 목록을 INSERT에 전달 | `RetailLine` 객체 541,907개를 한꺼번에 만들지 않고 최대 1,000개 매핑을 `insert()`에 전달 |
| [performance/__init__.py](https://github.com/sqlalchemy/sqlalchemy/blob/main/examples/performance/__init__.py) | Core·ORM 등 여러 접근을 동일 개수와 DB URL로 실행·프로파일링하는 방법 | 현재 변경에서는 처리 속도를 주장하지 않고, 다음 SQL 실험에서 데이터·DB·명령 조건을 고정하도록 계획 |

확인한 Git blob SHA는 각각 `9172ab3eb398fe03c5e06cf8949f23abb0205b3c`, `3854fdbea52448debc07bd08a52d26c2af1c69c6`입니다. 참고 예제의 모델·코드·측정값은 복사하지 않았고 해당 저장소의 성능 suite도 실행하지 않았습니다. 예제의 Core INSERT는 전체 입력 목록을 만들지만, OrderLens는 실제 541,907행 입력 때문에 JSONL을 읽으며 1,000행씩 비우는 방식으로 범위를 더 작게 정했습니다. 이 배치 크기가 최적이라는 성능 결론은 아직 내리지 않았습니다.

## 2026-10-12 · 실행계획과 복합 인덱스

[eugene-khyst/postgresql-performance-essentials](https://github.com/eugene-khyst/postgresql-performance-essentials/tree/8a9eaddaeee2917ddd72587f4cad6044d6d2b566)의 실제 파일을 읽었습니다. SQL 실행계획을 설명하는 공개 학습 저장소이며, 저자의 채용 여부나 성과는 판단하지 않았습니다.

| 확인한 파일 | 코드·안내에서 확인한 점 | 이번 변경에 적용한 부분 |
|---|---|---|
| [README.md](https://github.com/eugene-khyst/postgresql-performance-essentials/blob/8a9eaddaeee2917ddd72587f4cad6044d6d2b566/README.md) | `EXPLAIN ANALYZE`와 BUFFERS, Seq/Bitmap/Index Scan 구분, 복합 인덱스의 선두 컬럼, 인덱스 과다 생성 비용 | 고정 SQL의 실제 계획과 실행을 함께 기록하고 동등 조건 뒤에 범위 컬럼 배치, 저장 공간도 함께 측정 |
| [data.sql](https://github.com/eugene-khyst/postgresql-performance-essentials/blob/8a9eaddaeee2917ddd72587f4cad6044d6d2b566/data.sql) | `generate_series`로 planner가 구분할 수 있는 규모의 반복 자료 생성 | PostgreSQL CI에서 10만 행·Germany 1%의 고정 fixture를 SQL로 만들고 `ANALYZE` 뒤 계획 확인 |

확인한 Git blob SHA는 각각 `f1ee6381aa61637a594aab0c03d1db62fbf09a50`, `ca5e2dbf5a27dfd413a0b213470306d0ae09118f`입니다. 외부 SQL이나 측정값을 복사하지 않았고, 참고 저장소의 PostgreSQL 13 구성도 현재 PostgreSQL 16 검사에 사용하지 않았습니다. OrderLens의 컬럼·분포·기간 조건으로 별도 구현했으며 한 번의 CI 실행 시간은 성능 수치로 해석하지 않습니다.

| 저장소 | 확인한 구성 | OrderLens에 적용한 부분 |
|---|---|---|
| [Solar-See](https://github.com/techforimpact-archive/TFI_CAMPUS_KAIST_24fall_Solar-See) | 문제 정의, 데모, 실행 안내, 데이터 출처와 팀 역할 | README 앞부분에 다루는 문제를 쓰고 실행 결과·설계 링크를 연결 |
| [TnT-Server](https://github.com/YAPP-Github/TnT-Server) | 서비스 문제와 사용자 구분, 계층별 테스트, PR 빌드 검사 | 업무 조건의 경계 사례를 API 테스트로 검증하고 변경 이유를 기록 |
| [sixat](https://github.com/6mini/sixat) | 데이터 전처리·튜닝·학습을 분리한 파이프라인 | 검증·적재·집계·검색을 나누고 재실행 방법을 한 명령으로 제공 |

## 코드에서 확인한 점

TnT의 [PtLessonTest.java](https://github.com/YAPP-Github/TnT-Server/blob/develop/src/test/java/com/tnt/pt/domain/PtLessonTest.java)는 메모 길이 제한과 회차 변경을 검증합니다. [CI 설정](https://github.com/YAPP-Github/TnT-Server/blob/develop/.github/workflows/ci.yml)은 PR에서 Gradle 빌드를 실행합니다. OrderLens에서는 주문의 취소 상태, 시간 경계, 경로별 조회 한도를 검증 대상으로 잡았습니다.

sixat의 [DAG](https://github.com/6mini/sixat/blob/main/airflow/taxi-price-pipeline.py)는 전처리, 하이퍼파라미터 조정, 학습 순서를 연결합니다. 다만 코드에 개인 컴퓨터의 절대 경로가 들어 있습니다. OrderLens는 저장소 기준 경로와 임시 DB를 사용해 다른 환경에서도 같은 예제를 실행할 수 있게 했습니다. 이 저장소는 오래된 구현이므로 현재 라이브러리 버전의 기준으로 사용하지 않았습니다.

Solar-See의 한국어 실행 안내에는 서버 중단과 데모 영상 이용이 명시돼 있습니다. OrderLens도 현재 실행 가능한 범위와 후속 작업을 구분해 적었습니다.

참고한 것은 문제를 설명하고 구현을 확인할 수 있게 연결하는 방식입니다. 각 저장소의 코드·이미지·소개 문구는 가져오지 않았습니다. 적용 내용은 OrderLens의 규모와 데이터 계약을 기준으로 정했습니다.

## 2026-09-14 · 페이지 조회 코드

[uriyyo/fastapi-pagination](https://github.com/uriyyo/fastapi-pagination)의 다음 파일을 직접 읽었습니다. 이 저장소는 페이지 조회 구현의 참고이며, 저자의 취업 여부나 채용 성과를 확인한 자료는 아닙니다.

| 확인한 파일 | 코드에서 확인한 점 | 이번 변경에 적용한 부분 |
|---|---|---|
| [limit_offset.py](https://github.com/uriyyo/fastapi-pagination/blob/main/fastapi_pagination/limit_offset.py) | limit의 1~100 제한과 음수 offset 거부, 페이지 응답의 조회 위치 | API 입력 경계를 명시하고 잘못된 값의 422 응답을 테스트 |
| [ext/sqlalchemy.py](https://github.com/uriyyo/fastapi-pagination/blob/main/fastapi_pagination/ext/sqlalchemy.py) | create_paginate_query와 _limit_offset_flow에서 SQL에 페이지 범위를 적용, 별도 count 쿼리 구성 | 전체 결과를 Python으로 가져와 자르지 않고 DB에서 OFFSET·LIMIT 적용 |

확인한 파일의 Git blob SHA는 각각 `f136c2fbb1d8f8e1864a81f194e1983721963c03`, `7f5301d86136ebb8e26380fa9dfdb4c72dfc08bb`입니다. README만 읽고 동작을 추정한 것이 아니라 해당 파라미터와 SQL 생성 경로를 확인했습니다. 외부 프로젝트의 테스트 실행이나 성능 검증은 하지 않았습니다.

OrderLens의 기본 limit=20, 최신 주문 선택 후 필터, 정렬 키, `limit + 1`로 다음 페이지를 판단하고 total을 생략하는 응답은 이 프로젝트의 요구에 맞춰 별도로 정했습니다. fastapi-pagination 의존성이나 소스 코드는 가져오지 않았습니다. 코드와 테스트의 연결은 [페이지 조회 설계](decisions/order_pagination.md)에서 확인할 수 있습니다.

## 2026-09-21 · PostgreSQL과 마이그레이션

[fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template)의 실제 마이그레이션·실행·검사 파일을 읽었습니다. 확인 당시 저장소의 마지막 push는 2026-09-18이었습니다.

| 확인한 파일 | 코드에서 확인한 점 | 이번 변경에 적용한 부분 |
|---|---|---|
| [alembic/env.py](https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/alembic/env.py) | 앱 설정의 DB URL과 모델 metadata를 Alembic 실행 환경에 연결 | OrderLens 환경 변수·SQLAlchemy metadata를 연결하고 타입 비교 활성화 |
| [초기 리비전](https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/alembic/versions/e2412789c190_initialize_models.py) | upgrade에서 테이블·인덱스를 만들고 downgrade에서 역순 제거 | 현재 세 테이블·제약·인덱스를 첫 리비전에 명시하고 양방향 검사 |
| [prestart.sh](https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/scripts/prestart.sh) | 앱의 초기 데이터 작업 전에 `alembic upgrade head` 실행 | Compose에서 migrate 성공 후 API 시작 |
| [test-backend.yml](https://github.com/fastapi/full-stack-fastapi-template/blob/master/.github/workflows/test-backend.yml) | DB 컨테이너를 준비하고 마이그레이션한 뒤 백엔드 테스트 실행 | 별도 PostgreSQL 서비스에서 마이그레이션과 핵심 데이터 흐름 검사 |

확인한 Git blob SHA는 차례로 `919eebf5de6ea6717c99bf61affd0571e7ea2468`, `7529ea91fa7ceb3d0b3b1a4c4769565dea1d3af9`, `e67852ba079343c58e48935ed607e07880c9bab8`, `300386a790433a7b93ee5517792cd68babe38304`입니다.

참고 저장소의 현재 설정은 Python 3.14, PostgreSQL 18과 더 큰 서비스 구성을 사용합니다. OrderLens에는 그 버전이나 구조를 그대로 옮기지 않고 기존 Python 3.12·PostgreSQL 16 범위와 세 테이블에 맞췄습니다. 테스트 DB 이름을 검사하는 보호 장치, 시작 시 리비전 불일치 거부, SQLite 왕복 검사와 309행 재전송 검증은 OrderLens의 조건으로 추가했습니다. 외부 코드나 문구를 복사하지 않았습니다.
