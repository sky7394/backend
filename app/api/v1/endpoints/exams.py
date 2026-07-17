from fastapi import APIRouter, HTTPException
from app.schemas.question import ExamGenerateRequest, ExamOut
from app.services.exams.exam_service import generate_exam

router = APIRouter(prefix="/exam", tags=["Exam"])

@router.post("/generate", response_model=ExamOut)
async def generate_exam_endpoint(request: ExamGenerateRequest):
    try:
        return await generate_exam(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

