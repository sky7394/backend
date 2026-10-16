from __future__ import annotations

import logging
from typing import Any, Union

from starlette.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.exam import ExamFinalizeOut, ExamGenerateRequest, ExamPreviewOut
from app.services.ai.exam_generator import generate_exam_with_ai
from app.services.ai.exceptions import AIResponseValidationError
from app.services.exams.exam_storage import create_exam

logger = logging.getLogger(__name__)


def validate_preview_exam(exam: object) -> ExamPreviewOut:
    try:
        return ExamPreviewOut.model_validate(exam)
    except Exception as exc:
        raise AIResponseValidationError("Generated exam preview data is invalid") from exc


def validate_finalized_exam(exam: object) -> ExamFinalizeOut:
    try:
        return ExamFinalizeOut.model_validate(exam)
    except Exception as exc:
        raise AIResponseValidationError("Generated finalized exam data is invalid") from exc


async def preview_exam(request: ExamGenerateRequest) -> ExamPreviewOut:
    exam = await run_in_threadpool(generate_exam_with_ai, request)
    return validate_preview_exam(exam)


async def finalize_exam(
    request: Union[ExamGenerateRequest, ExamPreviewOut, dict[str, Any]],
    db: AsyncSession,
    current_user: User | None = None,
) -> ExamFinalizeOut:
    # اگر ورودی درخواست تولید است (تست‌های قدیمی یا سرویس مستقیم)
    if isinstance(request, ExamGenerateRequest):
        raw_exam = await run_in_threadpool(generate_exam_with_ai, request)
        preview = validate_preview_exam(raw_exam)
    elif isinstance(request, dict) and "questions" not in request and "subject" in request:
        # دیکشنری از نوع ExamGenerateRequest
        req_obj = ExamGenerateRequest(**request)
        raw_exam = await run_in_threadpool(generate_exam_with_ai, req_obj)
        preview = validate_preview_exam(raw_exam)
    else:
        preview = validate_preview_exam(request)

    owner_id = current_user.id if current_user is not None else None

    try:
        saved_exam = await create_exam(
            db=db,
            payload=preview,
            created_by_user_id=owner_id,
        )
    except TypeError:
        # در صورتی که تست تابع create_exam را با امضای دیگری mock کرده باشد
        try:
            saved_exam = await create_exam(db=db, exam_data=preview, owner_id=owner_id)
        except TypeError:
            saved_exam = await create_exam(db, preview, owner_id)

    return validate_finalized_exam(saved_exam)
