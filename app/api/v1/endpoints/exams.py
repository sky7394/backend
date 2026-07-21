from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from app.schemas.generate import ExamGenerateRequest, ExamOut
from app.services.ai.exceptions import (
    AIProviderCommunicationError,
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIResponseParsingError,
    AIResponseValidationError,
)
from app.services.exams.exam_service import generate_exam

router = APIRouter(prefix="/exam", tags=["Exam"])


@router.post("/generate", response_model=ExamOut)
async def generate_exam_endpoint(request: ExamGenerateRequest, preview: bool = False):
    try:
        return await generate_exam(request, preview=preview)
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
            detail="Unable to generate the exam.",
        ) from exc

