from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.rag import RetrievedContext


class SourceReference(BaseModel):
    source: str
    page: int = Field(ge=1)
    chunk_id: str


class ConceptExplainInput(BaseModel):
    user_question: str = Field(min_length=1)
    rag_context: list[RetrievedContext] = Field(default_factory=list)


class ConceptExplainOutput(BaseModel):
    question: str
    answer: str
    key_points: list[str]
    source_references: list[SourceReference]
    follow_up_questions: list[str]


class QuizGenerateInput(BaseModel):
    topic: str = Field(min_length=1)
    rag_context: list[RetrievedContext] = Field(default_factory=list)
    question_type: Literal["multiple_choice", "short_answer"] = "multiple_choice"
    count: int = Field(default=3, ge=1, le=10)
    difficulty: Literal["easy", "medium", "hard"] = "medium"


class QuizQuestion(BaseModel):
    question: str
    question_type: Literal["multiple_choice", "short_answer"]
    choices: list[str] = Field(default_factory=list)
    correct_answer: str
    explanation: str
    source_references: list[SourceReference]


class QuizGenerateOutput(BaseModel):
    topic: str
    questions: list[QuizQuestion]


class AnswerGradeInput(BaseModel):
    user_answer: str = Field(min_length=1)
    question: str | None = None
    correct_answer: str | None = None
    rag_context: list[RetrievedContext] = Field(default_factory=list)


class AnswerGradeOutput(BaseModel):
    is_correct: bool
    score: int = Field(ge=0, le=100)
    correct_answer: str
    explanation: str
    weakness_tags: list[str]
    next_review_action: str
