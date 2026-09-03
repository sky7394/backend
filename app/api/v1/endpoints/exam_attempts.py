from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.exam_attempt import (
    AttemptAnswerOut,
    AttemptAnswerUpsertRequest,
    ExamAttemptBulkSubmitRequest,
    ExamAttemptOut,
    ExamResultOut,
)
from app.services.exams.attempt_service import (
    get_attempt,
    list_student_attempts,
    save_answer,
    start_attempt,
    submit_attempt,
)

router = APIRouter(prefix="/exam-attempts", tags=["Exam Attempts"])


def _bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    )


@router.post(
    "/exams/{exam_id}/start",
    response_model=ExamAttemptOut,
    status_code=status.HTTP_201_CREATED,
)
async def start_exam_attempt(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExamAttemptOut:
    try:
        return await start_attempt(db, exam_id, current_user.id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.put(
    "/{attempt_id}/answers/{question_id}",
    response_model=AttemptAnswerOut,
)
async def save_exam_attempt_answer(
    attempt_id: UUID,
    question_id: int,
    payload: AttemptAnswerUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttemptAnswerOut:
    try:
        return await save_answer(
            db,
            attempt_id,
            current_user.id,
            question_id,
            payload.submitted_answer,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post(
    "/{attempt_id}/submit",
    response_model=ExamResultOut,
)
async def submit_exam_attempt(
    attempt_id: UUID,
    payload: ExamAttemptBulkSubmitRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExamResultOut:
    try:
        return await submit_attempt(
            db,
            attempt_id,
            current_user.id,
            payload,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/{attempt_id}", response_model=ExamAttemptOut)
async def get_exam_attempt(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExamAttemptOut:
    try:
        return await get_attempt(db, attempt_id, current_user.id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/", response_model=list[ExamAttemptOut])
async def list_exam_attempts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExamAttemptOut]:
    return await list_student_attempts(db, current_user.id)
