from __future__ import annotations

from enum import Enum
from typing import Optional

from app.schemas.base import DictComparableModel


class QuestionType(str, Enum):
    multiple_choice = "multiple_choice"
    descriptive = "descriptive"
    true_false = "true_false"


class DifficultyLevel(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionPreviewOut(DictComparableModel):
    question_text: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    grade: int
    subject: str
    topic: Optional[str] = None
    options: Optional[list[str]] = None
    correct_answer: str
    explanation: Optional[str] = None


class QuestionFinalizeOut(QuestionPreviewOut):
    id: int
