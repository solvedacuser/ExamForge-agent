# FastAPI 시험공부 코치 Agent 구현 로드맵

## 프로젝트 목표

강의 PDF를 기반으로 사용자의 시험 공부를 돕는 개인 코치 Agent를 구현한다.

핵심 흐름은 다음 5단계로 제한한다.

1. 개념 설명
2. 예상문제 생성
3. 답안 채점
4. 약점 분석
5. 복습 계획 추천

## 필수 구현 범위

- FastAPI 기반 API 서버
- LangChain / LangGraph 기반 Agent 흐름
- 강의 PDF 기반 RAG 파이프라인
- 최소 2개 Tool
- 멀티턴 대화 메모리
- LangGraph 조건부 분기 1개 이상
- Middleware 1개 이상
- OutputParser 기반 구조화 출력 1개 이상
- README, Workflow 다이어그램, requirements.txt

## 프롬프트 단위 로드맵

### Prompt 1. 프로젝트 골격 생성

```text
FastAPI 기반 "강의자료 기반 시험 공부 코치 Agent" 프로젝트 골격을 생성해줘.

필수 조건:
- Python FastAPI 사용
- LangChain / LangGraph 사용을 전제로 한 구조
- app/main.py, app/api, app/core, app/agent, app/rag, app/tools, app/schemas 구조 생성
- .env.example, requirements.txt, README.md 초안 포함
- API Key는 .env에서만 읽도록 구성

아직 세부 Agent 로직은 구현하지 말고, 실행 가능한 최소 서버와 헬스체크 API까지만 작성해줘.
```

산출물:
- 실행 가능한 FastAPI 서버
- `/health` 엔드포인트
- 기본 프로젝트 구조

### Prompt 2. PDF RAG 파이프라인 구현

```text
강의 PDF를 업로드하거나 로컬 data/pdfs 폴더에서 읽어 RAG 검색에 사용할 수 있는 파이프라인을 구현해줘.

필수 조건:
- PDF 로더
- 텍스트 분할
- 임베딩 생성
- 벡터스토어 저장 및 검색
- 검색 결과에는 출처 PDF명과 페이지 정보를 포함
- Agent가 개념 설명과 문제 생성 시 검색 결과를 활용할 수 있도록 retriever 함수를 제공

평가 요구사항의 RAG 구현 항목에 맞게, 전처리와 검색 품질을 README에 설명할 수 있는 구조로 작성해줘.
```

산출물:
- PDF 인덱싱 함수
- Retriever
- 출처 포함 검색 결과

### Prompt 3. 시험공부 코치용 Tool 구현

```text
Agent가 자율적으로 선택할 수 있는 Tool을 최소 2개 이상 구현해줘.

필수 Tool:
1. concept_explain_tool
   - 사용자의 질문과 RAG 검색 결과를 바탕으로 강의자료 기반 개념 설명 생성

2. quiz_generate_tool
   - 특정 개념이나 범위에 대해 예상문제 생성
   - 객관식 또는 단답형 문제를 생성

추가 Tool:
3. answer_grade_tool
   - 사용자의 답안을 채점하고 정답, 해설, 오답 원인을 반환

4. review_plan_tool
   - 약점 분석 결과를 바탕으로 복습 계획 추천

Tool 입출력은 Pydantic 스키마로 명확히 정의해줘.
```

산출물:
- 최소 2개 이상 Tool
- Pydantic 기반 Tool 입력/출력 스키마
- 개념 설명, 문제 생성, 채점, 복습 계획 기능

### Prompt 4. LangGraph Agent 흐름 설계

```text
LangGraph StateGraph로 시험공부 코치 Agent의 전체 실행 흐름을 구현해줘.

필수 흐름:
- 사용자 요청 분석
- 요청 유형 분기
  - 개념 설명
  - 문제 생성
  - 답안 채점
  - 약점 분석
  - 복습 계획 추천
- 필요한 Tool 실행
- 결과 응답 생성

필수 조건:
- 조건부 분기 conditional edge 최소 1개 이상
- 대화 상태에 user_id, session_id, 최근 질문, 최근 문제, 최근 답안, 약점 목록을 저장
- 답안 채점 후 약점 분석과 복습 계획 추천으로 이어질 수 있게 구성
- get_graph().draw_mermaid()로 Workflow 다이어그램을 생성할 수 있게 해줘.
```

산출물:
- LangGraph StateGraph
- 조건부 분기
- Agent 상태 모델
- Mermaid Workflow 다이어그램 생성 코드

### Prompt 5. 메모리와 구조화 출력 구현

```text
멀티턴 시험 공부 대화를 지원하도록 메모리와 구조화 출력을 구현해줘.

필수 조건:
- session_id 기준 대화 이력 저장
- 이전에 생성한 문제와 사용자의 답안을 기억
- 오답 개념과 약점 목록을 누적
- OutputParser 또는 Pydantic parser를 사용해 채점 결과를 JSON 구조로 반환

채점 결과 구조:
- is_correct
- score
- correct_answer
- explanation
- weakness_tags
- next_review_action
```

산출물:
- 세션 기반 메모리
- 약점 누적 상태
- 구조화된 채점 결과

### Prompt 6. FastAPI 엔드포인트 연결

```text
FastAPI API와 Agent 기능을 연결해줘.

필수 엔드포인트:
- POST /api/chat
  - 자연어 요청을 받아 Agent 실행

- POST /api/pdfs/index
  - PDF 인덱싱 실행

- GET /api/sessions/{session_id}
  - 세션별 학습 상태 조회

필수 조건:
- 요청/응답은 Pydantic 모델 사용
- 에러 응답 형식 통일
- Agent 실행 실패 시 사용자에게 안전한 메시지 반환
```

산출물:
- Agent 호출 API
- PDF 인덱싱 API
- 세션 상태 조회 API

### Prompt 7. Middleware와 운영 안정성 추가

```text
평가 요구사항에 맞춰 FastAPI Middleware를 최소 1개 이상 적용해줘.

필수 구현:
- 요청/응답 로깅 Middleware
- 처리 시간 기록
- 예외 발생 시 공통 에러 응답 반환

가능하면 추가:
- 입력 길이 제한
- PDF 미인덱싱 상태에서 RAG 요청 시 가드레일 메시지 반환

README에 Middleware 역할과 적용 위치를 설명할 수 있게 작성해줘.
```

산출물:
- Middleware
- 공통 에러 처리
- 기본 가드레일

### Prompt 8. README와 제출 문서 정리

```text
평가 제출용 README.md를 완성해줘.

필수 포함:
- 서비스 소개
- 사용 시나리오
- 전체 아키텍처
- LangGraph Workflow 다이어그램
- 설치 및 실행 방법
- API 사용 예시
- 사용한 Tool 설명
- RAG 파이프라인 설명
- Memory / State 관리 설명
- Middleware 설명
- 한계점 및 향후 개선 방향
- 외부 오픈소스 사용 시 출처

불필요한 마케팅 문구는 빼고, 평가자가 빠르게 구조와 구현 요건을 확인할 수 있게 작성해줘.
```

산출물:
- 제출용 README
- Workflow 다이어그램
- 평가 요건 대응 설명

## 최소 완성 기준

아래 항목이 동작하면 제출 가능한 MVP로 본다.

- PDF 1개 이상 인덱싱 가능
- 사용자가 개념 질문을 하면 PDF 기반 답변 생성
- 사용자가 예상문제를 요청하면 문제 생성
- 사용자가 답안을 제출하면 채점 결과를 JSON으로 반환
- 오답 개념이 세션 상태에 저장
- 복습 계획 추천 가능
- LangGraph 분기와 Tool 호출 흐름이 README에 설명됨
- FastAPI 서버가 실행되고 API 예시가 동작함

## 제외할 범위

- 회원가입 / 로그인
- 결제
- 프론트엔드 UI
- 관리자 페이지
- 복잡한 시험 일정 관리
- 여러 과목 통합 대시보드
- 실시간 스트리밍 응답
- 고도화된 권한 관리

