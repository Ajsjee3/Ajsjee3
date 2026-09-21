# 참고 저장소와 적용한 부분

기존 참고 확인일: 2026-09-09. 공개 README, 디렉터리 구조와 아래 코드 파일을 직접 읽고 정리했습니다. 프로젝트 전체를 실행하거나 성능 수치를 재검증한 것은 아닙니다. 이후 새로 읽은 코드는 날짜별로 구분했습니다.

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
