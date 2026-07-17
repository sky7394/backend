from fastapi.concurrency import run_in_threadpool

from app.schemas.question import ExamGenerateRequest, ExamOut
from app.services.ai.exam_generator import generate_exam_with_ai
from app.services.exams.exam_storage import save_generated_exam


async def generate_exam(request: ExamGenerateRequest) -> ExamOut:
    exam = await run_in_threadpool(generate_exam_with_ai, request)
    return save_generated_exam(exam)
