# GPU 기반 오픈소스 LLM·AI Agent 서비스 개발 PBL

**FinanceRAG**는 삼성전자 분기 실적에 관한 질문을 받고, 답변을 확인할 수 있는 문서와 공식 발표 링크를 함께 보여주는 재무 분석 챗봇입니다. 데이터 범위는 2024년 2·3분기입니다. 두 분기를 고른 이유는 매출과 영업이익이 서로 다른 방향으로 움직인 사례를 비교할 수 있기 때문입니다.

예를 들어 “3분기에는 매출이 늘었는데 영업이익은 왜 줄었나요?”라고 물을 수 있습니다. 두 발표에서 연결 매출은 74.07조 원에서 79.10조 원으로 늘고, 영업이익은 10.44조 원에서 9.18조 원으로 줄었습니다. 3분기 발표에서는 일회성 비용을 이익 감소 배경으로 설명합니다. 이 값들은 답변을 검토할 때 쓸 기준입니다. [분기별 수치와 공식 출처](data/README.md)

## 강의 GPU에서 실행

1. 강의 실습 이미지에서 저장소를 내려받고 `projects/gpu-llm-agent-pbl/FinanceRAG.ipynb`를 새 Python 커널에서 엽니다. 같은 폴더에 있는 `app.py`, `service.py`, `index.html`, `data/`도 필요합니다.
2. 강의 코드 위치의 기본값은 `/workspace/course`입니다. 다른 위치를 쓰면 첫 셀에서 `course`를 바꿉니다. 기존 강의 이미지의 PyTorch, Transformers, PEFT, 임베딩 모델과 GPU 패키지를 그대로 사용합니다.
3. 첫 셀은 강의 설정에 저장한 모델과 양자화 방식으로 LLM을 올리고 삼성전자 문서를 색인합니다. 최초 실행에는 모델 다운로드 공간이 필요합니다. 7회차에서 저장하고 선택한 LoRA가 현재 본체와 호환되면 화면에서 적용 여부를 선택할 수 있습니다.
4. 두 번째 셀을 실행하고 출력된 웹 주소를 엽니다. RunPod에서는 HTTP 포트 8000이 열려 있어야 합니다. 마지막 점검 셀은 같은 질문을 기본 모델과 사용 가능한 LoRA에 보내 답변과 근거를 출력합니다. 사용 후 `lab.stop_api()`로 종료합니다.

## GPU 없이 실행

Python 3.10 이상에서 아래 명령을 실행합니다. CPU 모드에서는 문자 단위 TF-IDF 검색으로 관련 자료의 문단을 발췌합니다. 화면 상단에서 현재 모드를 확인할 수 있습니다.

```bash
git clone https://github.com/Ajsjee3/Ajsjee3.git
cd Ajsjee3/projects/gpu-llm-agent-pbl
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app:preview --factory --port 8000
```

브라우저에서 [웹 화면](http://localhost:8000) 또는 [FastAPI 문서](http://localhost:8000/docs)를 엽니다. Windows PowerShell에서 가상환경 활성화 명령은 `.venv\Scripts\Activate.ps1`입니다.

## 질문 한 건이 처리되는 과정

GPU에서는 강의의 `lab.search(q, k=4, kw=0.3)`가 의미 검색과 키워드 점수를 결합해 최대 네 청크를 반환합니다. 각 청크에 번호를 붙여 질문과 함께 모델에 전달합니다. 금융 프롬프트는 회사·분기·단위, 계산 근거, 회사 설명과 해석의 구분을 요구합니다. LoRA를 켜면 같은 검색 결과를 사용하면서 생성 단계의 어댑터만 바뀝니다. 모델이 인용 번호나 수치를 잘못 생성할 수 있어 화면에서 근거 문단을 펼쳐 확인할 수 있습니다.

`POST /api/chat`에 아래와 같은 JSON을 보냅니다. `GET /api/info`에서 현재 모드와 사용 가능한 어댑터를 확인합니다.

```json
{"q": "삼성전자의 2024년 3분기 DS 부문 영업이익은 얼마인가요?", "use_lora": false}
```

응답에는 `answer`, `sources`(제목·문단·발표일·원문 링크), `mode`, `adapter`, `elapsed_ms`가 담깁니다. 시간은 서버가 요청을 처리하며 잰 값으로 대기·검색·생성을 포함합니다. GPU 요청은 한 번에 하나씩 처리합니다.

## 구현 범위

| 파일 | 역할과 출처 |
|---|---|
| [FinanceRAG.ipynb](FinanceRAG.ipynb) | 첨부된 강의 노트북 S0·S9의 실행 흐름을 단순화하고 금융 질문으로 API를 점검합니다. |
| [service.py](service.py) | S1의 채팅 템플릿·생성 토큰 디코딩, S2의 하이브리드 검색, S8의 어댑터 비교 방식을 활용했습니다. 문서 범위, 출처 연결, 금융 프롬프트, CPU 검색은 프로젝트에서 구성했습니다. |
| [app.py](app.py) · [index.html](index.html) | S9의 FastAPI 및 잠금 방식을 바탕으로 요청 검증, 오류 응답, 실측 시간, 근거 문서 UI를 구현했습니다. |
| [data/](data/) | 공식 발표 요약과 출처를 보관합니다. |
| [test_service.py](test_service.py) | 분기별 검색 근거와 API 오류 응답을 점검합니다. |
| [docs/](docs/) | 이전 강의 단계의 기획·실습 기록입니다. |

강의의 모델 로더, 임베딩, BM25, LoRA 장착 코드는 강의 저장소에 있습니다. 이 제출물은 기존 어댑터를 연결하며 새 금융 특화 어댑터의 학습 결과를 포함하지 않습니다. [강의 코드](https://github.com/elliediaz/llm26-course)

## 검증 기록

Python 3.12에서 CPU 서버를 실제로 기동하고 HTTP 요청으로 3분기 연결 매출 79.10조 원과 공식 발표 링크를 확인했습니다. 자동 테스트는 두 분기의 검색 순위와 금액, 검색 결과 없음, 잘못된 질문(422), 어댑터 없음(409), 엔진 실패(503)를 확인합니다.

```bash
python -m pip install 'httpx>=0.27,<0.29'
python -m unittest -v
```

웹 페이지의 HTTP 응답과 JavaScript 문법을 확인했습니다. 작업 환경의 브라우저 실행 제한으로 화면 렌더링은 미검증입니다. GPU와 강의 어댑터 가중치가 없는 환경에서 제출본을 점검했으므로 GPU 생성 품질, LoRA 전후 차이와 추론 속도는 미측정입니다. 노트북의 비교 셀에서 같은 질문으로 직접 확인할 수 있습니다.
