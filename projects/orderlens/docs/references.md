# 참고 저장소와 적용한 부분

확인일: 2026-09-09. 공개 README, 디렉터리 구조와 아래 코드 파일을 직접 읽고 정리했습니다. 프로젝트 전체를 실행하거나 성능 수치를 재검증한 것은 아닙니다.

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
