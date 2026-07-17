from app.services.documents.pdf_service import create_exam_pdf
from app.tasks.celery_app import celery_app


@celery_app.task(name="document.create_exam_pdf")
def create_exam_pdf_task(questions: list[dict]) -> str:
    return create_exam_pdf(questions)
