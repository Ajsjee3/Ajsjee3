# GPU 기반 오픈소스 LLM·AI Agent 서비스 개발 PBL

> **진행 중 · 계속 업데이트하는 개인 실습 기록 · 최종본 아님**
>
> 영남대학교 SW중심대학사업단 「2026년 실무형 AI 개발 역량 강화 교육」 (2026.11.16–11.27, 평일 18:00–21:00, 총 30시간)

[공식 교육 공지](https://www.yu.ac.kr/swedu/notice/notice.do?mode=view&articleNo=232048659) · [강의 코드](https://github.com/elliediaz/llm26-course) · [6회차 원본 노트북](https://github.com/elliediaz/llm26-course/blob/main/notebooks/s06_my_rag.ipynb)

## 목표

클라우드 GPU에서 오픈소스 LLM을 실행·비교하고, 문서 검색(RAG)과 경량 파인튜닝을 학습한 뒤 Tool Calling과 API·Web UI 연계까지 이어 가는 PBL 교육 과정입니다. **지금은 과정 중이며, Agent 서비스나 MVP 구현을 완료했다고 주장하지 않습니다.**

수업에서 제공한 `lab` 실습 코드와 노트북을 활용했습니다. 해당 교육 자료를 직접 구현한 것으로 표시하지 않으며, 개인이 구성한 금융 문서 실습·분석 기록을 구분합니다.

## 현재 진행 내용: FinanceRAG

가상의 전자부품 제조사 **가온전자**를 대상으로 매출, 영업이익, 매출채권, 재고, 물류비 등의 문서를 검색하는 RAG 실습입니다.

```text
가온전자 금융 문서
  → 청킹(문장 경계 / 고정 길이 + 중첩)
  → 청크 임베딩(강의 환경에서 1024차원)
  → 사용자 질문 임베딩
  → 코사인 유사도 + BM25 키워드 검색
  → top_k개 검색
  → 오픈소스 LLM에 근거 문서를 붙여 답변
```

| 항목 | 현재 기록 | 검증 상태 |
|---|---|---|
| GPU 환경 | RTX PRO 6000 Blackwell 실습 서버 사용 | GPU 화면 확인 |
| LLM | Qwen 계열 모델 선택 및 로딩 환경 실습 | 사용 모델·속도 최종 로그 미확보 |
| 디스크 오류 | 대형 모델 다운로드 시 quota/볼륨 공간 문제 | 오류 원인과 제약 확인 |
| RAG 문서 | 초기 3건과 확장용 합성 문서 25건 준비 | 서버 내 총 등록 개수 별도 확인 필요 |
| 청킹 | 문장 경계 방식과 글자 수·중첩 비교 | 최적 설정 미확정 |
| 임베딩 | 5개 문장 → (5, 1024) 배열 | 화면으로 확인 |
| 검색 | 의미 검색과 BM25 가중치 조절 | 구체 질문별 평가 진행 예정 |
| LoRA/Agent/API/UI | 다음 교육 단계 | 완료 전 |

**유의:** 가온전자와 관련 숫자는 실제 금융공시가 아니라 실습용으로 작성한 **가상 데이터**입니다. 검색 성능, Accuracy, Latency 등의 수치는 측정하지 않은 값으로 채워 넣지 않습니다.

## 기록

- [교육 과정과 범위](docs/course-roadmap.md)
- [날짜별 진행 기록 및 남은 작업](docs/progress.md)
- [6회차 RAG 실험 개념과 관찰](docs/rag-experiments.md)
- [데이터 구성·사용 범위](data/README.md)

## 앞으로 추가할 내용

- 같은 질문에 대한 `kw = 0 / 0.3 / 1.0` 및 `top_k` 비교 기록
- 검색 적중, 답변 적합성, 지연시간 등 평가 근거
- 7회차 LoRA/QLoRA 결과
- 8~10회차 Tool Calling, Agent, FastAPI, Web UI 결과
- 최종 구현과 재현 방법(실제로 검증한 시점에만 반영)

**'최종'이라고 명시하기 전까지 완성 프로젝트로 표기하지 않습니다.**

## 출처

- [영남대학교 SW중심대학사업단 모집 공지](https://www.yu.ac.kr/swedu/notice/notice.do?mode=view&articleNo=232048659)
- [elliediaz/llm26-course — 강의에서 제공한 코드·노트북](https://github.com/elliediaz/llm26-course)
