"""Database persistence for explicitly finalized exams.

This module is part of the active stateless flow; previews are never stored here.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ExamModel, QuestionModel
from app.schemas.exam import ExamFinalizeOut, ExamPreviewOut
from app.schemas.question import QuestionFinalizeOut


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _serialize_exam(exam: ExamModel) -> ExamFinalizeOut:
    return ExamFinalizeOut(
        title=exam.title,
        grade=exam.grade,
        subject=exam.subject,
        questions=[
            QuestionFinalizeOut(
                id=question.id,
                question_text=question.question_text,
                question_type=question.question_type,
                difficulty=question.difficulty,
                grade=question.grade,
                subject=question.subject,
                topic=question.topic,
                options=question.options,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
            )
            for question in exam.questions
        ],
    )


async def create_exam(db: AsyncSession, payload: object) -> ExamFinalizeOut:
    description = (
        payload.get("description")
        if isinstance(payload, dict)
        else getattr(payload, "description", None)
    )
    exam_data = ExamPreviewOut.model_validate(payload)
    exam = ExamModel(
        title=exam_data.title,
        grade=exam_data.grade,
        subject=exam_data.subject,
        description=description,
        questions_count=len(exam_data.questions),
        questions=[
            QuestionModel(
                question_text=question.question_text,
                question_type=_enum_value(question.question_type),
                difficulty=_enum_value(question.difficulty),
                grade=question.grade,
                subject=question.subject,
                topic=question.topic,
                options=question.options,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
            )
            for question in exam_data.questions
        ],
    )

    try:
        db.add(exam)
        await db.flush()
        finalized_exam = _serialize_exam(exam)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return finalized_exam


async def get_exam_by_id(
    db: AsyncSession,
    exam_id: int,
) -> ExamFinalizeOut | None:
    result = await db.execute(
        select(ExamModel)
        .where(ExamModel.id == exam_id)
        .options(selectinload(ExamModel.questions))
    )
    exam = result.scalar_one_or_none()
    return _serialize_exam(exam) if exam is not None else None


async def list_exams(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
) -> list[ExamFinalizeOut]:
    result = await db.execute(
        select(ExamModel)
        .options(selectinload(ExamModel.questions))
        .order_by(ExamModel.id)
        .offset(skip)
        .limit(limit)
    )
    return [_serialize_exam(exam) for exam in result.scalars().unique().all()]


async def delete_exam(db: AsyncSession, exam_id: int) -> bool:
    result = await db.execute(select(ExamModel).where(ExamModel.id == exam_id))
    exam = result.scalar_one_or_none()
    if exam is None:
        return False

    try:
        await db.delete(exam)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return True
