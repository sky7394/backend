import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.exam import ExamFinalizeOut, ExamGenerateRequest, ExamPreviewOut
from app.services.ai.exceptions import (
    AIProviderCommunicationError,
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIResponseParsingError,
    AIResponseValidationError,
)
from app.services.exams.exam_service import finalize_exam, preview_exam
from app.services.exams.exam_storage import get_exam_by_id, list_exams
from fastapi import Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exam")

# Alias used by tests when overriding endpoint dependencies.
require_exam_access = get_current_user


def map_ai_exception_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, (AIResponseValidationError, ValueError)):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The generated exam data is invalid.",
        )

    if isinstance(exc, AIProviderConfigurationError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI exam generation is temporarily unavailable.",
        )

    if isinstance(exc, AIResponseParsingError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI provider returned an invalid response.",
        )

    if isinstance(
        exc,
        (AIProviderCommunicationError, AIProviderResponseError),
    ):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI provider could not generate an exam.",
        )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error",
    )


def _coerce_preview_result(result: Any) -> ExamPreviewOut:
    try:
        if isinstance(result, dict):
            return ExamPreviewOut(**result)

        return result
    except Exception as exc:
        logger.exception("Failed to parse internal preview result into response schema")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate the exam preview.",
        ) from exc


def _coerce_finalize_result(result: Any) -> ExamFinalizeOut:
    try:
        if isinstance(result, dict):
            return ExamFinalizeOut(**result)

        return result
    except Exception as exc:
        logger.exception("Failed to parse internal finalize result into response schema")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to finalize the exam.",
        ) from exc


@router.post(
    "/preview",
    response_model=ExamPreviewOut,
    status_code=status.HTTP_200_OK,
)
async def preview_exam_endpoint(
    request: ExamGenerateRequest,
    current_user: Any = Depends(require_exam_access),
) -> ExamPreviewOut:
    try:
        result = await preview_exam(request)
    except HTTPException:
        raise
    except (
        AIProviderConfigurationError,
        AIProviderCommunicationError,
        AIProviderResponseError,
        AIResponseParsingError,
        AIResponseValidationError,
        ValueError,
    ) as exc:
        raise map_ai_exception_to_http(exc) from exc
    except Exception as exc:
        logger.exception("Unexpected error while generating exam preview")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate the exam preview.",
        ) from exc

    return _coerce_preview_result(result)


@router.post(
    "/finalize",
    response_model=ExamFinalizeOut,
    status_code=status.HTTP_200_OK,
)
async def finalize_exam_endpoint(
    request: ExamGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExamFinalizeOut:
    try:
        result = await finalize_exam(request, db)
    except HTTPException:
        raise
    except (
        AIProviderConfigurationError,
        AIProviderCommunicationError,
        AIProviderResponseError,
        AIResponseParsingError,
        AIResponseValidationError,
        ValueError,
    ) as exc:
        raise map_ai_exception_to_http(exc) from exc
    except Exception as exc:
        logger.exception("Unexpected error while finalizing exam")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to finalize the exam.",
        ) from exc

    return _coerce_finalize_result(result)


@router.get(
    "/{exam_id}",
    response_model=ExamFinalizeOut,
    status_code=status.HTTP_200_OK,
)
async def get_exam_endpoint(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExamFinalizeOut:
    exam = await get_exam_by_id(db, exam_id)

    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )

    return exam


@router.get(
    "/",
    response_model=list[ExamFinalizeOut],
    status_code=status.HTTP_200_OK,
)
async def list_exams_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[ExamFinalizeOut]:
    return await list_exams(
        db,
        skip=skip,
        limit=limit,
    )
