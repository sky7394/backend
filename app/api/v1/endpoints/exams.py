from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.exam import ExamFinalizeOut, ExamGenerateRequest, ExamPreviewOut
from app.services.ai.exceptions import (
    AIProviderCommunicationError,
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIResponseParsingError,
    AIResponseValidationError,
)
from app.services.exams.exam_service import finalize_exam, preview_exam

router = APIRouter(prefix="/exam", tags=["Exam"])


@router.post("/preview", response_model=ExamPreviewOut)
async def preview_exam_endpoint(request: ExamGenerateRequest):
    try:
        return await preview_exam(request)
    except AIProviderConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI exam generation is temporarily unavailable.",
        ) from exc
    except AIResponseParsingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI provider returned an invalid response.",
        ) from exc
    except (AIProviderCommunicationError, AIProviderResponseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI provider could not generate an exam.",
        ) from exc
    except (AIResponseValidationError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The generated exam data is invalid.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate the exam preview.",
        ) from exc


@router.post("/finalize", response_model=ExamFinalizeOut)
async def finalize_exam_endpoint(
    request: ExamGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await finalize_exam(request, db)
    except AIProviderConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI exam generation is temporarily unavailable.",
        ) from exc
    except AIResponseParsingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI provider returned an invalid response.",
        ) from exc
    except (AIProviderCommunicationError, AIProviderResponseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI provider could not generate an exam.",
        ) from exc
    except (AIResponseValidationError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The generated exam data is invalid.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to finalize the exam.",
        ) from exc
