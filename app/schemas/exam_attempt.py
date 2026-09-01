# app/schemas/exam_attempt.py
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AttemptAnswerUpsertRequest(BaseModel):
    submitted_answer: str = Field(
        ...,
        min_length=1,
        description="The submitted answer text for the question",
    )


class AttemptAnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attempt_id: UUID
    question_id: int
    submitted_answer: str
    grading_status: str
    is_correct: bool | None = None
    awarded_score: float | None = None
    feedback: str | None = None
    graded_at: datetime | None = None


class ExamAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exam_id: int
    student_id: UUID
    status: str
    total_score: float | None = None
    max_score: float = 0.0
    percentage: float | None = None
    started_at: datetime
    submitted_at: datetime | None = None
    graded_at: datetime | None = None
    answers: list[AttemptAnswerOut] = []


class ExamResultOut(ExamAttemptOut):
    exam_title: str


class ExamResultsOut(BaseModel):
    exam_id: int
    exam_title: str
    attempts: list[ExamAttemptOut] = []
