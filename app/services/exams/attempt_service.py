# app/services/exams/attempt_service.py
from __future__ import annotations

import math
import unicodedata
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AttemptAnswer, ExamAttempt, ExamModel, QuestionModel
from app.schemas.exam_attempt import (
    AttemptAnswerOut,
    ExamAttemptOut,
    ExamResultOut,
    ExamResultsOut,
)


IN_PROGRESS = "in_progress"
SUBMITTED = "submitted"
GRADED = "graded"

PENDING = "pending"
CORRECT = "correct"
INCORRECT = "incorrect"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_answer(value: object) -> str:
    """نرمال‌سازی پاسخ‌های متنی فارسی برای مقایسه دقیق‌تر."""
    if value is None:
        return ""

    text = str(value)

    replacements = {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ۀ": "ه",
        "ة": "ه",
        "ؤ": "و",
        "أ": "ا",
        "إ": "ا",
        "ٱ": "ا",
        "\u200c": " ",
        "\u200d": "",
        "\u200b": "",
        "\ufeff": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = unicodedata.normalize("NFKC", text)
    text = " ".join(text.split())

    return text.strip().casefold()


def answers_are_equal(
    submitted_answer: object,
    correct_answer: object,
) -> bool:
    return normalize_answer(submitted_answer) == normalize_answer(correct_answer)


def _answer_to_schema(answer: AttemptAnswer) -> AttemptAnswerOut:
    return AttemptAnswerOut(
        id=answer.id,
        question_id=answer.question_id,
        submitted_answer=answer.submitted_answer,
        grading_status=answer.grading_status,
        is_correct=answer.is_correct,
        awarded_score=answer.awarded_score,
        feedback=answer.feedback,
        graded_at=answer.graded_at,
    )


def _attempt_to_schema(attempt: ExamAttempt) -> ExamAttemptOut:
    return ExamAttemptOut(
        id=attempt.id,
        exam_id=attempt.exam_id,
        student_id=attempt.student_id,
        status=attempt.status,
        total_score=attempt.total_score,
        max_score=attempt.max_score,
        percentage=attempt.percentage,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        graded_at=attempt.graded_at,
        answers=[
            _answer_to_schema(answer)
            for answer in sorted(attempt.answers, key=lambda item: item.question_id)
        ],
    )


def _result_to_schema(attempt: ExamAttempt) -> ExamResultOut:
    return ExamResultOut(
        id=attempt.id,
        exam_id=attempt.exam_id,
        student_id=attempt.student_id,
        status=attempt.status,
        total_score=attempt.total_score,
        max_score=attempt.max_score,
        percentage=attempt.percentage,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        graded_at=attempt.graded_at,
        answers=[
            _answer_to_schema(answer)
            for answer in sorted(attempt.answers, key=lambda item: item.question_id)
        ],
    )


async def _get_exam(
    db: AsyncSession,
    exam_id: int,
) -> ExamModel | None:
    result = await db.execute(
        select(ExamModel)
        .where(ExamModel.id == exam_id)
        .options(selectinload(ExamModel.questions)),
    )
    return result.scalar_one_or_none()


async def _get_attempt(
    db: AsyncSession,
    attempt_id: UUID,
    student_id: UUID | None = None,
) -> ExamAttempt | None:
    statement = (
        select(ExamAttempt)
        .where(ExamAttempt.id == attempt_id)
        .options(
            selectinload(ExamAttempt.answers),
            selectinload(ExamAttempt.exam).selectinload(ExamModel.questions),
        )
    )

    if student_id is not None:
        statement = statement.where(ExamAttempt.student_id == student_id)

    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def start_attempt(
    db: AsyncSession,
    exam_id: int,
    student_id: UUID,
) -> ExamAttemptOut:
    exam = await _get_exam(db, exam_id)

    if exam is None:
        raise ValueError("Exam not found")

    attempt = ExamAttempt(
        exam_id=exam.id,
        student_id=student_id,
        status=IN_PROGRESS,
        max_score=float(len(exam.questions)),
    )

    try:
        db.add(attempt)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    attempt = await _get_attempt(db, attempt.id, student_id)
    if attempt is None:
        raise RuntimeError("Attempt could not be loaded after creation")

    return _attempt_to_schema(attempt)


async def save_answer(
    db: AsyncSession,
    attempt_id: UUID,
    student_id: UUID,
    question_id: int,
    submitted_answer: str,
) -> AttemptAnswerOut:
    attempt = await _get_attempt(db, attempt_id, student_id)

    if attempt is None:
        raise ValueError("Attempt not found")

    if attempt.status != IN_PROGRESS:
        raise ValueError("This attempt is no longer editable")

    question = await db.scalar(
        select(QuestionModel).where(
            QuestionModel.id == question_id,
            QuestionModel.exam_id == attempt.exam_id,
        )
    )

    if question is None:
        raise ValueError("Question does not belong to this exam")

    answer = next(
        (
            item
            for item in attempt.answers
            if item.question_id == question_id
        ),
        None,
    )

    if answer is None:
        answer = AttemptAnswer(
            attempt_id=attempt.id,
            question_id=question_id,
            submitted_answer=submitted_answer,
            grading_status=PENDING,
        )
        db.add(answer)
    else:
        answer.submitted_answer = submitted_answer
        answer.grading_status = PENDING
        answer.is_correct = None
        answer.awarded_score = None
        answer.feedback = None
        answer.graded_at = None

    try:
        await db.commit()
        await db.refresh(answer)
    except Exception:
        await db.rollback()
        raise

    return _answer_to_schema(answer)


async def submit_attempt(
    db: AsyncSession,
    attempt_id: UUID,
    student_id: UUID,
) -> ExamResultOut:
    attempt = await _get_attempt(db, attempt_id, student_id)

    if attempt is None:
        raise ValueError("Attempt not found")

    if attempt.status != IN_PROGRESS:
        return _result_to_schema(attempt)

    questions = {
        question.id: question
        for question in attempt.exam.questions
    }

    total_score = 0.0
    max_score = float(len(questions))

    for answer in attempt.answers:
        question = questions.get(answer.question_id)

        if question is None:
            answer.grading_status = INCORRECT
            answer.is_correct = False
            answer.awarded_score = 0.0
            answer.feedback = "Question is no longer available."
            answer.graded_at = _now()
            continue

        is_correct = answers_are_equal(
            answer.submitted_answer,
            question.correct_answer,
        )

        answer.is_correct = is_correct
        answer.grading_status = CORRECT if is_correct else INCORRECT
        answer.awarded_score = 1.0 if is_correct else 0.0
        answer.feedback = (
            "پاسخ صحیح است."
            if is_correct
            else "پاسخ صحیح نیست."
        )
        answer.graded_at = _now()

        if is_correct:
            total_score += 1.0

    attempt.status = GRADED
    attempt.total_score = total_score
    attempt.max_score = max_score
    attempt.percentage = (
        math.floor((total_score / max_score) * 10000) / 100
        if max_score > 0
        else 0.0
    )
    attempt.submitted_at = _now()
    attempt.graded_at = _now()

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    attempt = await _get_attempt(db, attempt_id, student_id)
    if attempt is None:
        raise RuntimeError("Submitted attempt could not be loaded")

    return _result_to_schema(attempt)


async def get_attempt_result(
    db: AsyncSession,
    attempt_id: UUID,
    student_id: UUID,
) -> ExamResultOut:
    attempt = await _get_attempt(db, attempt_id, student_id)

    if attempt is None:
        raise ValueError("Attempt not found")

    return _result_to_schema(attempt)


async def list_student_results(
    db: AsyncSession,
    student_id: UUID,
    exam_id: int | None = None,
) -> ExamResultsOut:
    statement = (
        select(ExamAttempt)
        .where(ExamAttempt.student_id == student_id)
        .options(selectinload(ExamAttempt.answers))
        .order_by(ExamAttempt.started_at.desc())
    )

    if exam_id is not None:
        statement = statement.where(ExamAttempt.exam_id == exam_id)

    result = await db.execute(statement)
    attempts = result.scalars().unique().all()

    return ExamResultsOut(
        results=[
            _result_to_schema(attempt)
            for attempt in attempts
        ],
        total=len(attempts),
    )


async def get_exam_results(
    db: AsyncSession,
    student_id: UUID,
    exam_id: int | None = None,
) -> ExamResultsOut:
    """Backward-compatible alias for listing a student's exam results."""
    return await list_student_results(
        db=db,
        student_id=student_id,
        exam_id=exam_id,
    )
