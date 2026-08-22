from __future__ import annotations

from typing import Optional

from app.schemas.base import DictComparableModel
from app.schemas.question import (
    DifficultyLevel,
    QuestionFinalizeOut,
    QuestionPreviewOut,
    QuestionType,
)


class ExamGenerateRequest(DictComparableModel):
    grade: int
    subject: str
    num_questions: int = 5
    question_type: QuestionType = QuestionType.multiple_choice
    difficulty: DifficultyLevel = DifficultyLevel.medium
    topic: Optional[str] = None


class ExamPreviewOut(DictComparableModel):
    title: str
    grade: int
    subject: str
    questions: list[QuestionPreviewOut]


class ExamFinalizeOut(DictComparableModel):
    title: str
    grade: int
    subject: str
    questions: list[QuestionFinalizeOut]


__all__ = [
    "DifficultyLevel",
    "ExamGenerateRequest",
    "ExamFinalizeOut",
    "ExamPreviewOut",
    "QuestionFinalizeOut",
    "QuestionPreviewOut",
    "QuestionType",
]
