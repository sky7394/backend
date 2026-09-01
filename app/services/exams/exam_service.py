# app/services/exams/exam_service.py
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.exam import ExamFinalizeOut, ExamGenerateRequest, ExamPreviewOut
from app.services.ai.exam_generator import generate_exam_with_ai
from app.services.ai.exceptions import AIResponseValidationError
from app.services.exams.exam_storage import create_exam


def validate_preview_exam(exam: object) -> ExamPreviewOut:
    try:
        return ExamPreviewOut.model_validate(exam)
    except ValidationError as exc:
        raise AIResponseValidationError("Generated exam preview data is invalid") from exc


def validate_finalized_exam(exam: object) -> ExamFinalizeOut:
    try:
        return ExamFinalizeOut.model_validate(exam)
    except ValidationError as exc:
        raise AIResponseValidationError("Generated finalized exam data is invalid") from exc


async def preview_exam(request: ExamGenerateRequest) -> ExamPreviewOut:
    exam = await run_in_threadpool(generate_exam_with_ai, request)
    return validate_preview_exam(exam)


async def finalize_exam(
    request: ExamGenerateRequest,
    db: AsyncSession,
    current_user: User | None = None,
) -> ExamFinalizeOut:
    exam = await run_in_threadpool(generate_exam_with_ai, request)
    preview_exam_data = validate_preview_exam(exam)
    saved_exam = await create_exam(
        db=db,
        payload=preview_exam_data,
        created_by_user_id=current_user.id if current_user is not None else None,
    )
    return validate_finalized_exam(saved_exam)
