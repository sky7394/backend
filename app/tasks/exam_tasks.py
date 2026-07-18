from app.schemas.generate import ExamGenerateRequest
from app.services.ai.exam_generator import generate_exam_with_ai
from app.tasks.celery_app import celery_app


@celery_app.task(name="exam.generate")
def generate_exam_task(payload: dict) -> dict:
    exam = generate_exam_with_ai(ExamGenerateRequest(**payload))
    return exam.model_dump()
