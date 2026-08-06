from app.schemas.exam import ExamGenerateRequest, ExamPreviewOut
from app.services.ai.gpt_service import generate_exam


def generate_exam_with_ai(
    request: ExamGenerateRequest,
) -> ExamPreviewOut:
    return generate_exam(request)
