from typing import Any

from langgraph.graph import END, StateGraph

from app.memory import (
    append_message,
    get_session_memory,
    remember_answer,
    remember_grading_result,
    remember_question,
    remember_quiz,
)
from app.rag import retrieve_context
from app.schemas.agent import AgentState, RequestType
from app.tools import answer_grade_tool, concept_explain_tool, quiz_generate_tool


def build_study_coach_graph():
    graph = StateGraph(AgentState)

    graph.add_node("analyze_request", analyze_request)
    graph.add_node("concept_explain", run_concept_explain)
    graph.add_node("quiz_generate", run_quiz_generate)
    graph.add_node("answer_grade", run_answer_grade)
    graph.add_node("weakness_analysis", run_weakness_analysis)
    graph.add_node("review_plan", run_review_plan)
    graph.add_node("fallback", run_fallback)

    graph.set_entry_point("analyze_request")
    graph.add_conditional_edges(
        "analyze_request",
        route_by_request_type,
        {
            "concept_explain": "concept_explain",
            "quiz_generate": "quiz_generate",
            "answer_grade": "answer_grade",
            "weakness_analysis": "weakness_analysis",
            "review_plan": "review_plan",
            "fallback": "fallback",
        },
    )

    graph.add_edge("concept_explain", END)
    graph.add_edge("quiz_generate", END)
    graph.add_edge("answer_grade", "weakness_analysis")
    graph.add_edge("weakness_analysis", "review_plan")
    graph.add_edge("review_plan", END)
    graph.add_edge("fallback", END)

    return graph.compile()


def get_graph():
    return build_study_coach_graph()


def draw_workflow_mermaid() -> str:
    return get_graph().get_graph().draw_mermaid()


def analyze_request(state: AgentState) -> AgentState:
    message = state.get("user_message", "")
    request_type = _classify_request(message)
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id", "anonymous")
    memory = get_session_memory(session_id=session_id, user_id=user_id)

    if message:
        append_message(session_id, "user", message)

    recent_question = (
        message
        if request_type in ("concept_explain", "quiz_generate")
        else memory.recent_question or state.get("recent_question", message)
    )

    return {
        **state,
        "request_type": request_type,
        "recent_question": recent_question,
        "recent_quiz": state.get("recent_quiz") or memory.recent_quiz or {},
        "recent_answer": state.get("recent_answer") or memory.recent_answer or "",
        "weakness_tags": _merge_unique(
            state.get("weakness_tags", []),
            memory.weakness_tags,
        ),
        "grading_results": memory.grading_results,
    }


def route_by_request_type(state: AgentState) -> RequestType:
    return state.get("request_type", "fallback")


def run_concept_explain(state: AgentState) -> AgentState:
    question = state.get("recent_question") or state.get("user_message", "")
    rag_context = _safe_retrieve(question)
    result = concept_explain_tool.invoke(
        {
            "user_question": question,
            "rag_context": rag_context,
        }
    )
    session_id = state.get("session_id", "default")
    remember_question(session_id, question)
    append_message(session_id, "assistant", result.get("answer", ""))

    return {
        **state,
        "rag_context": rag_context,
        "tool_result": result,
        "response": result.get("answer", ""),
    }


def run_quiz_generate(state: AgentState) -> AgentState:
    topic = state.get("recent_question") or state.get("user_message", "")
    rag_context = _safe_retrieve(topic)
    result = quiz_generate_tool.invoke(
        {
            "topic": topic,
            "rag_context": rag_context,
            "question_type": "multiple_choice",
            "count": 3,
            "difficulty": "medium",
        }
    )
    response = _format_quiz_response(result)
    session_id = state.get("session_id", "default")
    remember_question(session_id, topic)
    remember_quiz(session_id, result)
    append_message(session_id, "assistant", response)

    return {
        **state,
        "rag_context": rag_context,
        "recent_quiz": result,
        "tool_result": result,
        "response": response,
    }


def run_answer_grade(state: AgentState) -> AgentState:
    answer = state.get("user_message", "")
    session_id = state.get("session_id", "default")
    question, correct_answer = _latest_quiz_question(state.get("recent_quiz", {}))
    result = answer_grade_tool.invoke(
        {
            "user_answer": answer,
            "question": question or state.get("recent_question"),
            "correct_answer": correct_answer,
            "rag_context": state.get("rag_context", []),
        }
    )
    remember_answer(session_id, answer)
    remember_grading_result(session_id, result)

    weakness_tags = _merge_unique(
        state.get("weakness_tags", []),
        result.get("weakness_tags", []),
    )
    grading_results = [*state.get("grading_results", []), result]

    return {
        **state,
        "recent_answer": answer,
        "weakness_tags": weakness_tags,
        "grading_results": grading_results,
        "tool_result": result,
        "response": result.get("explanation", ""),
    }


def run_weakness_analysis(state: AgentState) -> AgentState:
    weakness_tags = state.get("weakness_tags", [])
    if not weakness_tags:
        weakness_tags = ["needs_grading_result"]

    return {
        **state,
        "weakness_tags": weakness_tags,
        "tool_result": {
            **state.get("tool_result", {}),
            "weakness_tags": weakness_tags,
        },
    }


def run_review_plan(state: AgentState) -> AgentState:
    weakness_tags = state.get("weakness_tags", [])
    plan = [
        f"{tag}: 관련 강의자료를 다시 읽고 비슷한 문제를 2개 풉니다."
        for tag in weakness_tags
    ]
    response = "\n".join(plan)
    append_message(state.get("session_id", "default"), "assistant", response)

    return {
        **state,
        "tool_result": {
            **state.get("tool_result", {}),
            "review_plan": plan,
        },
        "response": response,
    }


def run_fallback(state: AgentState) -> AgentState:
    return {
        **state,
        "response": (
            "개념 설명, 예상문제 생성, 답안 채점, 약점 분석, 복습 계획 중 "
            "원하는 작업을 알려주세요."
        ),
    }


def _classify_request(message: str) -> RequestType:
    normalized = message.lower()

    if _contains_any(normalized, ["채점", "답안", "grade", "score", "정답 확인"]):
        return "answer_grade"
    if _contains_any(normalized, ["약점", "취약", "오답", "weakness"]):
        return "weakness_analysis"
    if _contains_any(normalized, ["복습", "계획", "review", "plan"]):
        return "review_plan"
    if _contains_any(normalized, ["문제", "퀴즈", "예상문제", "quiz", "question"]):
        return "quiz_generate"
    if _contains_any(normalized, ["설명", "개념", "알려줘", "explain", "what is"]):
        return "concept_explain"

    return "concept_explain" if message.strip() else "fallback"


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _merge_unique(left: list[str], right: list[str]) -> list[str]:
    merged = list(left)
    for item in right:
        if item not in merged:
            merged.append(item)
    return merged


def _latest_quiz_question(quiz: dict[str, Any]) -> tuple[str | None, str | None]:
    questions = quiz.get("questions") or []
    if not questions:
        return None, None

    first_question = questions[0]
    return first_question.get("question"), first_question.get("correct_answer")


def _safe_retrieve(query: str) -> list[dict[str, Any]]:
    try:
        return [item.model_dump() for item in retrieve_context(query)]
    except Exception:
        return []


def _format_quiz_response(result: dict[str, Any]) -> str:
    questions = result.get("questions", [])
    if not questions:
        return "생성된 문제가 없습니다."

    lines: list[str] = []
    for index, question in enumerate(questions, start=1):
        lines.append(f"{index}. {question.get('question', '')}")
        for choice_index, choice in enumerate(question.get("choices", []), start=1):
            lines.append(f"   {choice_index}) {choice}")

    return "\n".join(lines)
