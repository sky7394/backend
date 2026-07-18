from app.schemas.generate import ExamGenerateRequest, ExamOut
from app.services.ai.gemini_service import generate_exam


def generate_exam_with_ai(request: ExamGenerateRequest) -> ExamOut:
    return generate_exam(request)
