# 누적 완성도 · 2026-11-23

시작 main: `930dc4734728ecc448d1345a8576f5be1b24fd5f` (0.11.0). 열린 이슈·PR 없음, 취업 상태 preparing. 이번 변경은 0.12.0이며 주 6~10시간 복습 범위로 상태 점검 하나를 보완합니다. 채용 공고 검토는 2026-10-26으로 28일 경과해 이번에는 재조사 주기에 해당하지 않습니다.

## 누적 점검

| 영역 | 판정 | 근거와 한계 |
|---|---|---|
| 문제·사용자 흐름 | 부분 완료 | 주문 적재→목록·지표→문서 인용의 HTTP 시연 존재. UCI 공개 거래 집계는 아직 CLI 중심이며 주문과 통화·의미가 달라 별도 흐름 필요 |
| 데이터 출처·품질 | 완료(구현 범위) | UCI 출처·해시·거부 행·Decimal·재적재 검증. 전체 541,907행 실행은 과거 기록이며 이번에는 작은 회귀 입력만 재실행 |
| API·DB 정합성 | 부분 완료 | 주문 버전·페이지·트랜잭션·4개 리비전 회귀 검증. 동시 최초 적재 경합 등 미완료 |
| 테스트·재현 | 완료(로컬 범위) | Python 3.12.14/SQLite 3.53.1에서 scripts.check 종료 0, Ruff·119 tests·마이그레이션 왕복·복구·실제 Uvicorn HTTP 통과. PostgreSQL은 PR CI 결과로 별도 확인 |
| 인증·배포·복구 | 부분 완료 | API 키, 적재 실패 복구와 새 live/ready 검증. 사용자별 권한·실배포·백업 복원·장기 DB 무응답 미검증 |
| 성능·검색 | 부분 완료 | SQL 과거 실측과 고정 32문항 평가 재실행. 검색 오인용 7건, 독립 사용자 평가 부재. 실험 후보 미채택 유지 |
| 문서·시연 | 부분 완료 | 실행 명령·JSON·실제 HTTP 일치 확인. 시각적 사용자 시연·공개 배포 미완료. demo_report의 오래된 검색 점수도 실제 재실행 결과로 갱신 |
| 본인 기여·설명 | 미평가 | CONTRIBUTING에 코드 작성 주체 공개. 사용자 직접 학습 확인·기록 없음; 구현을 본인 이해나 운영 경험으로 환산하지 않음 |

## 현재 파일을 다시 읽은 비교

둘 다 오래된 사례이며 2026년 최근 취업 표본은 아닙니다. 공개 경력은 본인 진술이고 독립 재직 검증은 하지 않았습니다. 아래 저장소가 합격 당시 제출본인지 확인되지 않았습니다. 외부 코드는 실행하지 않은 코드·문서 검토이며 시장 평균이나 합격 확률을 뜻하지 않습니다.

### 6mini / sixat

- [본인 2022 회고](https://yoonminlee.com/2022-retrospect): 2023-01-01 게시, 2022년 데이터 엔지니어 첫 경력에 대한 공개 진술. 확인 2026-11-23.
- main `42510b6daa3548d6a43de4cd953d8e4882354086`, [마지막 변경](https://github.com/6mini/sixat/commit/42510b6daa3548d6a43de4cd953d8e4882354086) 2022-03-25 프로젝트 종료.
- 읽은 파일: [README](https://github.com/6mini/sixat/blob/42510b6daa3548d6a43de4cd953d8e4882354086/README.md), [DAG](https://github.com/6mini/sixat/blob/42510b6daa3548d6a43de4cd953d8e4882354086/airflow/taxi-price-pipeline.py), [Compose](https://github.com/6mini/sixat/blob/42510b6daa3548d6a43de4cd953d8e4882354086/docker-compose.yml). 전처리→튜닝→학습의 의존 흐름과 목적이 드러납니다. README 실행 절차와 자체 회귀 테스트 근거는 충분히 확인하지 못했습니다. DAG의 개인 절대 경로, 오래된 이미지 설정은 복사하지 않습니다.
- 적용: 도구 수보다 실패 단계·재실행 상태를 명시하는 기준으로 비교. OrderLens는 복구 테스트가 있지만 자동 스케줄링과 사용 흐름은 부족합니다. 이번에는 서비스 준비 상태를 명시합니다.

### JaegeonYu / yesterday-s-Trip

- [본인 경력 페이지](https://jaegeonyu.github.io/developer-portfolio/): emro 2024.09 입사 표기, 확인 2026-11-23. 입사 이후 경력 성과는 신입 기준에 넣지 않았습니다.
- main `6240d83c5943953750eda8f0e7fba96e62c20d90`, [마지막 변경](https://github.com/JaegeonYu/yesterday-s-Trip/commit/6240d83c5943953750eda8f0e7fba96e62c20d90) 2024-08-13 SSE 설명 갱신.
- 읽은 파일: [README·실행 안내](https://github.com/JaegeonYu/yesterday-s-Trip/blob/6240d83c5943953750eda8f0e7fba96e62c20d90/README.md), [SecurityConfig](https://github.com/JaegeonYu/yesterday-s-Trip/blob/6240d83c5943953750eda8f0e7fba96e62c20d90/src/main/java/com/trip/back/config/SecurityConfig.java), [테스트](https://github.com/JaegeonYu/yesterday-s-Trip/blob/6240d83c5943953750eda8f0e7fba96e62c20d90/src/test/java/com/trip/back/YesterdayTripApplicationTests.java), [Dockerfile](https://github.com/JaegeonYu/yesterday-s-Trip/blob/6240d83c5943953750eda8f0e7fba96e62c20d90/Dockerfile).
- 사용자 흐름 GIF, 실행 환경 변수, JWT·역할 분기와 선택 이유가 구체적입니다. 반면 확인한 테스트는 contextLoads 하나이고 외부 서비스 자격 증명이 필요하며 넓은 CORS 설정이 있어 운영 안전성을 실행 없이 단정할 수 없습니다.
- 적용: 사용자 흐름·운영 준비의 설명을 보완합니다. OrderLens의 공유 API 키는 사용자별 권한과 다릅니다. 화면·배포는 남은 격차이며 이번에는 무료로 검증 가능한 준비 상태를 우선합니다. 코드·문구는 복사하지 않았습니다.

## 이번 완료 기준과 남은 일

DB 없이 live 200, DB 오류·리비전 불일치에서 ready 503, 복구 후 200, 오류 정보 비노출, 기존 API 회귀 통과가 완료 기준입니다. 리비전 표식 검사는 테이블 전체 무결성 검사가 아니며 시작 시 잘못된 스키마는 기존처럼 시작 거부합니다. 실제 배포, 요청 제한 시간, 장기 장애·복원은 미검증입니다.

다음은 공개 거래 집계의 읽기 전용 API입니다. 학습 과제: `tests/test_health.py`를 실행하고 왜 DB 장애에서 live는 200이어야 하는지 설명해 보세요. [계획](../../../docs/development_plan.md) · [개발 기록](progress.md).
