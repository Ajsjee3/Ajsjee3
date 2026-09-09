# 이호준

영남대학교 컴퓨터공학과에서 공부하고 있습니다. 데이터가 API로 들어와 저장되고, 서비스에서 쓰이는 과정에 관심이 있습니다.

Python과 FastAPI를 배우며 주문 데이터 처리 프로젝트를 만들고 있습니다. 상태가 바뀌거나 같은 데이터가 다시 들어와도 결과가 맞는지 확인하는 데 집중하고 있습니다.

## 프로젝트

### [OrderLens — 주문 데이터 분석 API](https://github.com/Ajsjee3/Ajsjee3/tree/main/projects/orderlens)

중복 전송과 주문 상태 변경을 처리하고, 판매 경로별 배송 지연 주문을 조회합니다.

- **구현:** FastAPI, SQLAlchemy, 입력 검증, 버전별 적재, SQL 집계, 운영 문서 검색
- **재현:** 합성 데이터 309행을 다시 보내도 새 주문 버전은 0개, 집계 결과는 동일
- **이번 변경:** 판매 경로별 지연 주문 필터와 조회 한도·취소 상태·시간 경계 검증
- **다음 작업:** 주문 목록 페이지 처리, PostgreSQL 통합 검증

[코드와 실행 방법](https://github.com/Ajsjee3/Ajsjee3/blob/main/projects/orderlens/README.md) · [설계](https://github.com/Ajsjee3/Ajsjee3/blob/main/projects/orderlens/docs/design.md) · [검증 결과](https://github.com/Ajsjee3/Ajsjee3/blob/main/projects/orderlens/docs/validation.md) · [개발 기록](https://github.com/Ajsjee3/Ajsjee3/blob/main/projects/orderlens/docs/progress.md)

### 기존 저장소

[LLM-project](https://github.com/Ajsjee3/LLM-project) — Unity 프로젝트와 LangChainServer 코드가 있는 저장소입니다. 실행 방법과 구현 범위를 정리할 예정입니다.

## 현재 공부하는 내용

Python · HTTP와 REST API · 관계형 데이터베이스 · SQL · 테스트

프로젝트에서 사용한 개념을 작은 입력으로 확인하고, [학습 기록](https://github.com/Ajsjee3/Ajsjee3/blob/main/projects/orderlens/docs/learning_log.md)에 정리합니다.

연락: 22110926@yu.ac.kr
