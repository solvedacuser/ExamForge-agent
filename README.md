# Lecture Exam Coach Agent

강의 PDF를 기반으로 시험 공부를 돕는 FastAPI 기반 Agent 서비스입니다. 현재 단계는 Prompt 1 산출물로, 실행 가능한 최소 API 서버와 이후 LangChain/LangGraph Agent 구현을 위한 프로젝트 골격을 제공합니다.

## 현재 구현 범위

- FastAPI 앱 엔트리포인트
- `/health` 헬스체크 API
- LangChain / LangGraph 구현을 위한 패키지 구조
- PDF 기반 RAG 인덱싱 및 검색 함수
- 시험공부 코치용 필수 Tool 2종
- LangGraph StateGraph 기반 Agent 흐름
- 세션 기반 메모리와 구조화된 채점 결과
- Agent, PDF 인덱싱, 세션 조회 FastAPI 엔드포인트
- 빌드 없는 정적 웹 UI
- `.env` 기반 설정 로딩
- 기본 의존성 목록

## 프로젝트 구조

```text
.
├── app
│   ├── main.py
│   ├── web
│   │   ├── index.html
│   │   └── static
│   │       ├── app.js
│   │       └── styles.css
│   ├── api
│   │   ├── chat.py
│   │   ├── errors.py
│   │   ├── health.py
│   │   ├── pdfs.py
│   │   └── sessions.py
│   ├── memory
│   │   └── store.py
│   ├── core
│   │   └── config.py
│   ├── agent
│   │   └── graph.py
│   ├── rag
│   │   ├── embeddings.py
│   │   ├── pdf_loader.py
│   │   ├── pipeline.py
│   │   ├── text_splitter.py
│   │   └── vector_store.py
│   ├── tools
│   │   └── study_tools.py
│   └── schemas
│       ├── api.py
│       ├── agent.py
│       ├── health.py
│       ├── rag.py
│       └── tools.py
├── data
│   └── pdfs
├── .env.example
├── requirements.txt
└── README.md
```

## 설치 및 실행

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 3000
```

또는 `main.py`를 직접 실행할 수 있습니다.

```bash
python app/main.py
```

실행 후 웹 UI는 아래 주소에서 확인할 수 있습니다.

```text
http://127.0.0.1:3000/
```

Windows PowerShell에서는 아래처럼 `.env` 파일을 만들고, `.env`의 `PORT` 값을 사용해 실행할 수 있습니다.

```powershell
Copy-Item .env.example .env
$env:PORT = (Get-Content .env | Where-Object { $_ -match '^PORT=' } | ForEach-Object { ($_ -split '=', 2)[1].Trim('"') })
uvicorn app.main:app --reload --port $env:PORT
```

## API Key 관리

API Key는 코드에 하드코딩하지 않고 `.env`에서만 읽습니다. 필요한 값은 `.env.example`을 복사한 뒤 `.env`에 채워 넣습니다.

```env
OPENAI_API_KEY=""
OPENAI_CHAT_MODEL="gpt-4o-mini"
PORT=3000
PDF_DIR="data/pdfs"
VECTOR_STORE_PATH="data/vector_store/index.json"
```

## RAG 파이프라인

`data/pdfs` 폴더의 PDF를 읽어 페이지 단위로 텍스트를 추출하고, 설정된 길이로 청크를 나눈 뒤 OpenAI Embedding을 생성합니다. 생성된 벡터는 `data/vector_store/index.json`에 저장되며, 이 경로는 런타임 산출물이므로 Git에는 포함하지 않습니다.

주요 함수:

```python
from app.rag import get_retriever, index_pdfs, retrieve_context

index_pdfs()
contexts = retrieve_context("HTTP 상태 코드 개념 설명해줘")
retriever = get_retriever(top_k=4)
```

검색 결과에는 Agent가 답변 출처로 사용할 수 있도록 `source`, `page`, `text`, `score`, `chunk_id`가 포함됩니다.

## Study Coach Tools

Agent가 선택해서 사용할 수 있는 필수 Tool 2가지를 구현했습니다. Tool 입력과 출력은 Pydantic 스키마로 정의되어 있습니다.

```python
from app.tools import STUDY_TOOLS, concept_explain_tool, quiz_generate_tool

concept_result = concept_explain_tool.invoke(
    {
        "user_question": "HTTP 상태 코드는 무엇인가요?",
        "rag_context": [],
    }
)

quiz_result = quiz_generate_tool.invoke(
    {
        "topic": "HTTP 상태 코드",
        "question_type": "multiple_choice",
        "count": 3,
        "difficulty": "medium",
        "rag_context": [],
    }
)
```

- `concept_explain_tool`: 사용자 질문과 RAG 검색 결과를 바탕으로 개념 설명, 핵심 포인트, 출처, 후속 질문을 반환합니다.
- `quiz_generate_tool`: 특정 주제에 대해 객관식 또는 단답형 예상문제를 생성하고 정답, 해설, 출처를 반환합니다.
- `answer_grade_tool`: 사용자의 답안을 채점하고 JSON 구조의 결과를 반환합니다.

## LangGraph Workflow

`app/agent/graph.py`는 사용자 요청을 분석한 뒤 조건부 분기로 필요한 노드를 실행합니다. 현재 실제 Tool 실행은 `concept_explain_tool`, `quiz_generate_tool`에 연결되어 있고, 답안 채점 이후의 약점 분석과 복습 계획 경로는 다음 단계에서 세부 Tool을 붙일 수 있도록 노드 흐름만 준비했습니다.

```python
from app.agent import draw_workflow_mermaid, get_graph

agent = get_graph()
result = agent.invoke(
    {
        "user_id": "demo-user",
        "session_id": "demo-session",
        "user_message": "Agentic AI 개념 설명해줘",
    }
)

mermaid = draw_workflow_mermaid()
```

현재 분기:

```text
analyze_request
├── concept_explain
├── quiz_generate
├── answer_grade -> weakness_analysis -> review_plan
├── weakness_analysis -> review_plan
├── review_plan
└── fallback
```

## Memory / Structured Output

`app/memory/store.py`는 `session_id` 기준으로 대화 이력, 최근 문제, 최근 답안, 채점 결과, 누적 약점 태그를 저장합니다. 현재는 과제 MVP에 필요한 인메모리 저장소이며, 서버 재시작 시 초기화됩니다.

채점 결과는 Pydantic parser를 사용하는 `AnswerGradeOutput` 구조로 반환됩니다.

```json
{
  "is_correct": false,
  "score": 50,
  "correct_answer": "이전 문제의 정답",
  "explanation": "채점 해설",
  "weakness_tags": ["needs_concept_review"],
  "next_review_action": "관련 개념을 다시 읽고 문제를 더 풉니다."
}
```

LangGraph에서는 `answer_grade -> weakness_analysis -> review_plan` 순서로 이어져 오답 개념과 복습 계획을 세션 상태에 누적합니다.

## API

브라우저 UI는 아래 API를 `fetch()`로 호출합니다. API Key는 서버의 `.env`에서만 읽고 화면에는 노출하지 않습니다.

### POST `/api/chat`

자연어 요청을 받아 LangGraph Agent를 실행합니다.

```bash
curl -X POST http://127.0.0.1:3000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"demo-session\",\"user_id\":\"demo-user\",\"message\":\"Agentic AI 개념 설명해줘\"}"
```

### POST `/api/pdfs/index`

`data/pdfs` 또는 요청으로 전달한 폴더의 PDF를 인덱싱합니다.

```bash
curl -X POST http://127.0.0.1:3000/api/pdfs/index \
  -H "Content-Type: application/json" \
  -d "{}"
```

### GET `/api/sessions/{session_id}`

세션별 대화 이력, 최근 문제, 최근 답안, 약점 태그, 채점 결과를 조회합니다.

```bash
curl http://127.0.0.1:3000/api/sessions/demo-session
```

API 오류는 아래처럼 공통 형식으로 반환합니다.

```json
{
  "success": false,
  "error_code": "agent_execution_failed",
  "message": "Agent 실행 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
}
```

## 헬스체크

```bash
curl http://127.0.0.1:3000/health
```

예상 응답:

```json
{
  "status": "ok",
  "service": "Lecture Exam Coach Agent",
  "version": "0.1.0",
  "environment": "local"
}
```

## Web UI

`GET /`는 `app/web/index.html`을 반환하고, `/static/*`는 CSS와 JavaScript를 제공합니다. 웹 화면에서는 다음 작업을 할 수 있습니다.

- Agent 채팅 실행
- `data/pdfs` 폴더 PDF 인덱싱
- 현재 `session_id`의 대화 이력, 최근 문제, 최근 답안, 약점 태그, 채점 결과 조회

별도 프론트엔드 빌드 과정은 없습니다.

## 다음 단계

Prompt 7부터 Middleware와 운영 안정성, 제출용 README 정리를 순서대로 구현합니다.
# agentplus
