from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class QuestionType(str, Enum):
    multiple_choice = "multiple_choice"
    true_false = "true_false"
    short_answer = "short_answer"


class DifficultyLevel(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class ExamGenerateRequest(BaseModel):
    grade: int
    subject: str
    num_questions: int
    question_type: QuestionType
    difficulty: DifficultyLevel
    topic: Optional[str] = None


class QuestionOut(BaseModel):
    id: int
    question_text: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    grade: int
    subject: str
    topic: Optional[str] = None
    options: List[str]
    correct_answer: str
    explanation: Optional[str] = None
    
    model_config = {"use_enum_values": True}


class ExamOut(BaseModel):
    title: str
    grade: int
    subject: str
    questions: List[QuestionOut]
    
    model_config = {"use_enum_values": True}
