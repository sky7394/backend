from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from app.schemas.generate import ExamGenerateRequest, ExamOut
from app.services.ai.exam_generator import generate_exam_with_ai
from app.services.ai.exceptions import AIResponseValidationError
from app.services.exams.exam_storage import save_generated_exam


def validate_generated_exam(exam: ExamOut) -> ExamOut:
    try:
        return ExamOut.model_validate(exam)
    except ValidationError as exc:
        raise AIResponseValidationError("Generated exam data is invalid") from exc


async def generate_exam(request: ExamGenerateRequest, preview: bool = False) -> ExamOut:
    exam = await run_in_threadpool(generate_exam_with_ai, request)
    validated_exam = validate_generated_exam(exam)
    if preview:
        return validated_exam

    return save_generated_exam(validated_exam)
