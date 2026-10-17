from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "teacher_assistant",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.exam_tasks",
        "app.tasks.document_tasks",
    ],
)
