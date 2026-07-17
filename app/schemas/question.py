# app/schemas/question.py
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class QuestionType(str, Enum):
    multiple_choice = "multiple_choice"
    descriptive = "descriptive"
    true_false = "true_false"

class DifficultyLevel(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

class ExamGenerateRequest(BaseModel):
    grade: int
    subject: str
    num_questions: int = 5
    question_type: QuestionType = QuestionType.multiple_choice
    difficulty: DifficultyLevel = DifficultyLevel.medium
    topic: Optional[str] = None

class QuestionOut(BaseModel):
    id: int
    question_text: str
    question_type: str
    difficulty: str
    grade: int
    subject: str
    topic: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None

class ExamOut(BaseModel):
    title: str
    grade: int
    subject: str
    questions: List[QuestionOut]
