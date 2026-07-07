from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from app.core.config import get_settings
from app.schemas.rag import RetrievedContext
from app.schemas.tools import (
    AnswerGradeInput,
    AnswerGradeOutput,
    ConceptExplainInput,
    ConceptExplainOutput,
    QuizGenerateInput,
    QuizGenerateOutput,
    QuizQuestion,
    SourceReference,
)


def explain_concept(
    user_question: str,
    rag_context: list[RetrievedContext | dict] | None = None,
) -> dict:
    contexts = _normalize_contexts(rag_context or [])

    if not get_settings().openai_api_key:
        return _fallback_concept_explanation(user_question, contexts).model_dump()

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an exam study coach. Explain concepts only from the "
                "provided lecture context. Answer in Korean. If the context is "
                "insufficient, say what is missing.",
            ),
            (
                "human",
                "Question: {question}\n\nLecture context:\n{context}\n\n"
                "Write a concise explanation, 3 key points, and 2 follow-up "
                "study questions.",
            ),
        ]
    )
    chain = prompt | _chat_model() | StrOutputParser()
    answer = chain.invoke(
        {
            "question": user_question,
            "context": _format_contexts(contexts),
        }
    )

    output = ConceptExplainOutput(
        question=user_question,
        answer=answer,
        key_points=_extract_key_points(answer),
        source_references=_source_references(contexts),
        follow_up_questions=[
            "이 개념이 시험 문제로 나오면 어떤 형태가 될까요?",
            "관련 개념과 헷갈리기 쉬운 차이는 무엇인가요?",
        ],
    )
    return output.model_dump()


def generate_quiz(
    topic: str,
    rag_context: list[RetrievedContext | dict] | None = None,
    question_type: str = "multiple_choice",
    count: int = 3,
    difficulty: str = "medium",
) -> dict:
    contexts = _normalize_contexts(rag_context or [])

    if not get_settings().openai_api_key:
        return _fallback_quiz(topic, contexts, question_type, count).model_dump()

    parser = PydanticOutputParser(pydantic_object=QuizGenerateOutput)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an exam question writer. Generate quiz questions only "
                "from the provided lecture context. Write in Korean.",
            ),
            (
                "human",
                "Topic: {topic}\nQuestion type: {question_type}\n"
                "Difficulty: {difficulty}\nCount: {count}\n\n"
                "Lecture context:\n{context}\n\n{format_instructions}",
            ),
        ]
    )
    chain = prompt | _chat_model() | StrOutputParser()
    raw_output = chain.invoke(
        {
            "topic": topic,
            "question_type": question_type,
            "difficulty": difficulty,
            "count": count,
            "context": _format_contexts(contexts),
            "format_instructions": parser.get_format_instructions(),
        }
    )

    output = parser.parse(raw_output)
    return output.model_dump()


def grade_answer(
    user_answer: str,
    question: str | None = None,
    correct_answer: str | None = None,
    rag_context: list[RetrievedContext | dict] | None = None,
) -> dict:
    contexts = _normalize_contexts(rag_context or [])

    if not get_settings().openai_api_key:
        return _fallback_grade_answer(
            user_answer=user_answer,
            correct_answer=correct_answer,
        ).model_dump()

    parser = PydanticOutputParser(pydantic_object=AnswerGradeOutput)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an exam answer grader. Grade based on the provided "
                "question, correct answer, and lecture context. Return only the "
                "requested structured output. Write Korean explanations.",
            ),
            (
                "human",
                "Question: {question}\nCorrect answer: {correct_answer}\n"
                "User answer: {user_answer}\n\nLecture context:\n{context}\n\n"
                "{format_instructions}",
            ),
        ]
    )
    chain = prompt | _chat_model() | StrOutputParser()
    raw_output = chain.invoke(
        {
            "question": question or "No previous question was provided.",
            "correct_answer": correct_answer or "No correct answer was provided.",
            "user_answer": user_answer,
            "context": _format_contexts(contexts),
            "format_instructions": parser.get_format_instructions(),
        }
    )

    return parser.parse(raw_output).model_dump()


concept_explain_tool = StructuredTool.from_function(
    func=explain_concept,
    name="concept_explain_tool",
    description=(
        "Explain a user question using retrieved lecture PDF context. "
        "Returns answer, key points, source references, and follow-up questions."
    ),
    args_schema=ConceptExplainInput,
)

quiz_generate_tool = StructuredTool.from_function(
    func=generate_quiz,
    name="quiz_generate_tool",
    description=(
        "Generate expected exam questions for a topic using retrieved lecture "
        "PDF context. Supports multiple_choice and short_answer questions."
    ),
    args_schema=QuizGenerateInput,
)

answer_grade_tool = StructuredTool.from_function(
    func=grade_answer,
    name="answer_grade_tool",
    description=(
        "Grade a user answer and return structured JSON with correctness, "
        "score, explanation, weakness tags, and the next review action."
    ),
    args_schema=AnswerGradeInput,
)

STUDY_TOOLS = [concept_explain_tool, quiz_generate_tool, answer_grade_tool]


def _chat_model() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_chat_model,
        temperature=settings.llm_temperature,
        api_key=settings.openai_api_key,
    )


def _normalize_contexts(contexts: list[RetrievedContext | dict]) -> list[RetrievedContext]:
    return [
        item if isinstance(item, RetrievedContext) else RetrievedContext.model_validate(item)
        for item in contexts
    ]


def _format_contexts(contexts: list[RetrievedContext]) -> str:
    if not contexts:
        return "No retrieved lecture context was provided."

    return "\n\n".join(
        f"[{item.source} p.{item.page} / {item.chunk_id}]\n{item.text}"
        for item in contexts
    )


def _source_references(contexts: list[RetrievedContext]) -> list[SourceReference]:
    references: list[SourceReference] = []
    seen: set[tuple[str, int, str]] = set()

    for item in contexts:
        key = (item.source, item.page, item.chunk_id)
        if key in seen:
            continue
        seen.add(key)
        references.append(
            SourceReference(
                source=item.source,
                page=item.page,
                chunk_id=item.chunk_id,
            )
        )

    return references


def _extract_key_points(answer: str) -> list[str]:
    lines = [line.strip("-* 0123456789.").strip() for line in answer.splitlines()]
    points = [line for line in lines if line][:3]
    return points or [answer[:120]]


def _fallback_concept_explanation(
    question: str,
    contexts: list[RetrievedContext],
) -> ConceptExplainOutput:
    context_preview = contexts[0].text[:600] if contexts else "검색된 강의자료 문맥이 없습니다."
    return ConceptExplainOutput(
        question=question,
        answer=(
            "OpenAI API 키가 설정되지 않아 임시 설명을 반환합니다. "
            f"검색 문맥 기준 요약: {context_preview}"
        ),
        key_points=[
            "강의자료 검색 결과를 우선 근거로 사용합니다.",
            "출처 PDF명과 페이지를 함께 유지합니다.",
            "API 키 설정 후 LLM 기반 설명으로 대체됩니다.",
        ],
        source_references=_source_references(contexts),
        follow_up_questions=[
            "이 개념의 핵심 정의는 무엇인가요?",
            "시험에서 헷갈릴 만한 예외나 비교 개념은 무엇인가요?",
        ],
    )


def _fallback_quiz(
    topic: str,
    contexts: list[RetrievedContext],
    question_type: str,
    count: int,
) -> QuizGenerateOutput:
    references = _source_references(contexts)
    questions: list[QuizQuestion] = []

    for index in range(1, count + 1):
        if question_type == "short_answer":
            questions.append(
                QuizQuestion(
                    question=f"{topic}의 핵심 개념을 한 문장으로 설명하시오. ({index})",
                    question_type="short_answer",
                    correct_answer="강의자료의 핵심 정의와 근거를 포함한 답안",
                    explanation="OpenAI API 키 설정 후 강의자료 기반 정답과 해설이 생성됩니다.",
                    source_references=references,
                )
            )
        else:
            questions.append(
                QuizQuestion(
                    question=f"{topic}에 대한 설명으로 가장 적절한 것은? ({index})",
                    question_type="multiple_choice",
                    choices=[
                        "강의자료 근거와 일치하는 설명",
                        "관련 없는 일반 설명",
                        "반대되는 개념 설명",
                        "정의와 무관한 예시",
                    ],
                    correct_answer="강의자료 근거와 일치하는 설명",
                    explanation="OpenAI API 키 설정 후 강의자료 기반 선택지와 해설이 생성됩니다.",
                    source_references=references,
                )
            )

    return QuizGenerateOutput(topic=topic, questions=questions)


def _fallback_grade_answer(
    user_answer: str,
    correct_answer: str | None,
) -> AnswerGradeOutput:
    normalized_user_answer = _normalize_text(user_answer)
    normalized_correct_answer = _normalize_text(correct_answer or "")
    is_correct = bool(
        normalized_correct_answer
        and normalized_correct_answer in normalized_user_answer
    )

    if is_correct:
        return AnswerGradeOutput(
            is_correct=True,
            score=100,
            correct_answer=correct_answer or "이전 문제의 정답 정보가 없습니다.",
            explanation="사용자 답안이 저장된 정답 문구를 포함합니다.",
            weakness_tags=[],
            next_review_action="같은 개념의 응용 문제를 풀어보세요.",
        )

    return AnswerGradeOutput(
        is_correct=False,
        score=0 if correct_answer else 50,
        correct_answer=correct_answer or "이전 문제의 정답 정보가 없습니다.",
        explanation=(
            "OpenAI API 키 또는 명확한 정답 정보가 부족해 기본 채점 결과를 반환합니다."
        ),
        weakness_tags=["needs_concept_review"],
        next_review_action="관련 개념 설명을 다시 읽고 동일 주제 문제를 1개 더 풀어보세요.",
    )


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().split())
