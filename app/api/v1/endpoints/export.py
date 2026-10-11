import logging
from urllib.parse import quote
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from app.schemas.export import ExamExportRequestSchema
from app.services.documents.docx_service import generate_exam_docx_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Export"])

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

@router.post(
    "/docx",
    summary="تولید و دانلود فایل Word آزمون از روی داده‌های ارسالی"
)
async def export_exam_docx(payload: ExamExportRequestSchema) -> Response:
    try:
        exam_data = payload.model_dump()
        include_answers = exam_data.pop("include_answers", True)

        docx_bytes = generate_exam_docx_bytes(
            exam_data,
            include_answers=include_answers
        )

        filename = f"{payload.title.strip().replace(' ', '_')}.docx"
        encoded_filename = quote(filename, safe="")

        return Response(
            content=docx_bytes,
            media_type=DOCX_MEDIA_TYPE,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except Exception as exc:
        logger.error("خطا در تولید فایل Word آزمون: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در تولید فایل Word آزمون"
        ) from exc
