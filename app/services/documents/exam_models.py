from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ExamHeaderStyle(str, Enum):
    SCHOOL = "school"
    OFFICIAL = "official"


class ExamLayoutType(str, Enum):
    GENERAL = "general"
    LANGUAGE = "language"
    STEM = "stem"


class ExamHeaderConfig(BaseModel):
    school_name: str = "بسمه تعالی"
    course_name: str = "آزمون کتبی"
    grade_field: Optional[str] = None
    exam_term: Optional[str] = None
    exam_date: Optional[str] = None
    exam_duration: Optional[str] = None
    teacher_name: Optional[str] = None
    header_style: ExamHeaderStyle = ExamHeaderStyle.SCHOOL
    layout_type: ExamLayoutType = ExamLayoutType.GENERAL
    logo_path: Optional[str] = None
    student_name: Optional[str] = None
    candidate_number: Optional[str] = None
    class_name: Optional[str] = None


class NormalizedQuestion(BaseModel):
    number: int = 1
    question_text: str
    options: List[str] = Field(default_factory=list)
    answer: Optional[str] = None
    points: Optional[float] = None
    section: Optional[str] = None
    formula: Optional[str] = None
    image_path: Optional[str] = None
    explanation: Optional[str] = None
    answer_lines: int = Field(default=3, ge=0, le=20)
