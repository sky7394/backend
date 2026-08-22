from __future__ import annotations

import logging
from typing import Any, Type, TypeVar

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.schemas.exam import ExamFinalizeOut, ExamGenerateRequest, ExamPreviewOut
from app.services.ai.exceptions import (
    AIProviderCommunicationError,
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIResponseParsingError,
    AIResponseValidationError,
)
from app.services.exams.exam_service import finalize_exam, preview_exam

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exam", tags=["Exam"])

T = TypeVar("T")

require_exam_access = get_current_user


def _coerce_result_to_model(
    result: Any,
    model_cls: Type[T],
    *,
    failure_detail: str,
    validation_log_message: str,
) -> T:
    try:
        if isinstance(result, model_cls):
            return result
        return model_cls.model_validate(result)
    except (ValidationError, TypeError, ValueError):
        logger.exception(validation_log_message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=failure_detail,
        )


def _map_ai_exception(exc: Exception) -> HTTPException:
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

    if isinstance(exc, (AIProviderCommunicationError, AIProviderResponseError)):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI provider could not generate an exam.",
        )

    if isinstance(exc, AIResponseValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The generated exam data is invalid.",
        )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected exam generation error.",
    )


@router.post("/preview", response_model=ExamPreviewOut, status_code=200)
async def preview_exam_endpoint(
    request: ExamGenerateRequest,
    current_user: Any = Depends(get_current_user),
) -> ExamPreviewOut:
    _ = current_user
    try:
        result = await preview_exam(request)
        return _coerce_result_to_model(
            result,
            ExamPreviewOut,
            failure_detail="Unable to generate the exam preview.",
            validation_log_message="Unexpected error while validating exam preview output",
        )
    except (
        AIProviderConfigurationError,
        AIProviderCommunicationError,
        AIProviderResponseError,
        AIResponseParsingError,
        AIResponseValidationError,
    ) as exc:
        raise _map_ai_exception(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error while generating exam preview")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate the exam preview.",
        ) from exc


@router.post("/finalize", response_model=ExamFinalizeOut, status_code=200)
async def finalize_exam_endpoint(
    request: ExamGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> ExamFinalizeOut:
    _ = current_user
    try:
        result = await finalize_exam(request, db)
        return _coerce_result_to_model(
            result,
            ExamFinalizeOut,
            failure_detail="Unable to finalize the exam.",
            validation_log_message="Unexpected error while validating exam finalize output",
        )
    except (
        AIProviderConfigurationError,
        AIProviderCommunicationError,
        AIProviderResponseError,
        AIResponseParsingError,
        AIResponseValidationError,
    ) as exc:
        raise _map_ai_exception(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error while finalizing exam")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to finalize the exam.",
        ) from exc
