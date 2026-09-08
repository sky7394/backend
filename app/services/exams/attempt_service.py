"""Create, answer and grade exam attempts using an injected async session."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AttemptAnswer, ExamAttempt, ExamModel, QuestionModel
from app.schemas.exam_attempt import (
    AttemptAnswerOut,
    ExamAttemptBulkSubmitRequest,
    ExamAttemptOut,
    ExamResultOut,
)

IN_PROGRESS = "in_progress"
SUBMITTED = "submitted"
COMPLETED = "completed"
GRADED = "graded"
PENDING = "pending"
CORRECT = "correct"
INCORRECT = "incorrect"

STATUS_IN_PROGRESS = IN_PROGRESS
STATUS_SUBMITTED = SUBMITTED
STATUS_COMPLETED = COMPLETED
Exam = ExamModel
Question = QuestionModel
ExamAttemptAnswer = AttemptAnswer


def normalize_answer(text: str | None) -> str:
    if text is None:
        return ""
    replacements = {
        "ي": "ی", "ك": "ک", "ى": "ی", "ئ": "ی", "ؤ": "و",
        "إ": "ا", "أ": "ا", "\u200c": " ", "\u200f": "",
        "\u200e": "", "\u0640": "",
    }
    value = str(text)
    for source, target in replacements.items():
        value = value.replace(source, target)
    return re.sub(r"\s+", " ", value).strip().lower()


def answers_are_equal(answer1: str | None, answer2: str | None) -> bool:
    return normalize_answer(answer1) == normalize_answer(answer2)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _result_to_schema(attempt: ExamAttempt) -> ExamResultOut:
    return ExamResultOut(
        **ExamAttemptOut.model_validate(attempt).model_dump(),
        exam_title=attempt.exam.title,
    )


async def _load_attempt(
    db: AsyncSession,
    attempt_id: UUID,
    student_id: UUID | None = None,
    *,
    for_update: bool = False,
) -> ExamAttempt:
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
    if for_update:
        statement = statement.with_for_update()
    result = await db.execute(statement)
    attempt = result.scalar_one_or_none()
    if attempt is None:
        raise ValueError("Attempt not found")
    return attempt


async def start_attempt(
    db: AsyncSession, exam_id: int, student_id: UUID,
) -> ExamAttemptOut:
    result = await db.execute(
        select(ExamModel)
        .where(ExamModel.id == exam_id)
        .options(selectinload(ExamModel.questions))
    )
    exam = result.scalar_one_or_none()
    if exam is None:
        raise ValueError("Exam not found")
    attempt = ExamAttempt(
        id=uuid4(),
        exam_id=exam_id,
        student_id=student_id,
        status=IN_PROGRESS,
        started_at=_now_utc(),
        max_score=float(len(exam.questions)),
        answers=[],
    )
    try:
        db.add(attempt)
        attempt_id = attempt.id
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(attempt)
    created = await _load_attempt(db, attempt_id, student_id)
    return ExamAttemptOut.model_validate(created)


async def get_attempt(
    db: AsyncSession, attempt_id: UUID, student_id: UUID | None = None,
) -> ExamAttemptOut:
    """Omitting student_id is reserved for trusted internal callers."""
    return ExamAttemptOut.model_validate(await _load_attempt(db, attempt_id, student_id))


async def _upsert_answer(
    db: AsyncSession,
    attempt: ExamAttempt,
    question_id: int,
    submitted_answer: str,
) -> AttemptAnswer:
    question = await db.scalar(
        select(QuestionModel).where(
            QuestionModel.id == question_id,
            QuestionModel.exam_id == attempt.exam_id,
        )
    )
    if question is None:
        raise ValueError("Question does not belong to this exam")
    answer = next((a for a in attempt.answers if a.question_id == question_id), None)
    if answer is None:
        answer = ExamAttemptAnswer(
            id=uuid4(),
            attempt_id=attempt.id,
            question_id=question_id,
            submitted_answer=submitted_answer,
            grading_status=PENDING,
        )
        attempt.answers.append(answer)
        db.add(answer)
    else:
        answer.submitted_answer = submitted_answer
        answer.grading_status = PENDING
        answer.is_correct = None
        answer.awarded_score = None
        answer.feedback = None
        answer.graded_at = None
    return answer


async def save_answer(
    db: AsyncSession,
    attempt_id: UUID,
    student_id: UUID | None = None,
    question_id: int | None = None,
    submitted_answer: str | None = None,
    *,
    answer_text: str | None = None,
) -> AttemptAnswerOut:
    """Accept answer_text as the explicit legacy name for submitted_answer."""
    if submitted_answer is None:
        submitted_answer = answer_text
    elif answer_text is not None and answer_text != submitted_answer:
        raise ValueError("Conflicting answer values")
    if question_id is None or submitted_answer is None:
        raise ValueError("question_id and submitted_answer are required")
    attempt = await _load_attempt(db, attempt_id, student_id, for_update=True)
    if attempt.status != IN_PROGRESS:
        raise ValueError("This attempt is no longer editable")
    try:
        answer = await _upsert_answer(db, attempt, question_id, submitted_answer)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(answer)
    return AttemptAnswerOut.model_validate(answer)


async def bulk_grading(
    db: AsyncSession,
    attempt: ExamAttempt,
    bulk: ExamAttemptBulkSubmitRequest | None = None,
) -> dict[str, int]:
    """Upsert submitted answers and grade the full attempt without committing."""
    if bulk is not None:
        for item in bulk.answers:
            await _upsert_answer(db, attempt, item.question_id, item.submitted_answer)
    await db.flush()

    questions = {q.id: q for q in attempt.exam.questions}
    correct = 0
    graded_at = _now_utc()
    for answer in attempt.answers:
        question = questions.get(answer.question_id)
        is_correct = question is not None and answers_are_equal(
            answer.submitted_answer, question.correct_answer,
        )
        answer.is_correct = is_correct
        answer.grading_status = CORRECT if is_correct else INCORRECT
        answer.awarded_score = 1.0 if is_correct else 0.0
        answer.feedback = "پاسخ صحیح است." if is_correct else "پاسخ صحیح نیست."
        answer.graded_at = graded_at
        correct += int(is_correct)
    return {"answered": len(attempt.answers), "correct": correct, "total": len(questions)}


async def submit_attempt(
    db: AsyncSession,
    attempt_id: UUID,
    student_id: UUID,
    bulk: ExamAttemptBulkSubmitRequest | None = None,
) -> ExamResultOut:
    attempt = await _load_attempt(db, attempt_id, student_id, for_update=True)
    if attempt.status != IN_PROGRESS:
        raise ValueError("Attempt is already completed")
    try:
        results = await bulk_grading(db, attempt, bulk)
        attempt.status = COMPLETED
        attempt.total_score = float(results["correct"])
        attempt.max_score = float(results["total"])
        attempt.percentage = (
            round(100 * attempt.total_score / attempt.max_score, 2)
            if attempt.max_score else 0.0
        )
        attempt.submitted_at = _now_utc()
        attempt.graded_at = attempt.submitted_at
        # Validate and snapshot before commit can expire ORM attributes.
        output = _result_to_schema(attempt)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return output


async def get_attempt_result(
    db: AsyncSession, attempt_id: UUID, student_id: UUID | None = None,
) -> ExamResultOut:
    return _result_to_schema(await _load_attempt(db, attempt_id, student_id))


async def _list_attempts(
    db: AsyncSession, student_id: UUID, exam_id: int | None = None,
) -> list[ExamAttempt]:
    statement = (
        select(ExamAttempt)
        .where(ExamAttempt.student_id == student_id)
        .options(selectinload(ExamAttempt.answers), selectinload(ExamAttempt.exam))
        .order_by(ExamAttempt.started_at.desc())
    )
    if exam_id is not None:
        statement = statement.where(ExamAttempt.exam_id == exam_id)
    result = await db.execute(statement)
    return list(result.scalars().all())


async def list_student_attempts(
    db: AsyncSession, student_id: UUID, exam_id: int | None = None,
) -> list[ExamAttemptOut]:
    return [
        ExamAttemptOut.model_validate(attempt)
        for attempt in await _list_attempts(db, student_id, exam_id)
    ]


async def list_student_results(
    db: AsyncSession, student_id: UUID, exam_id: int | None = None,
) -> list[ExamResultOut]:
    return [
        _result_to_schema(attempt)
        for attempt in await _list_attempts(db, student_id, exam_id)
    ]


get_exam_results = list_student_results
get_attempt_detail = get_attempt
