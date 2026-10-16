import re
import logging
from urllib.parse import quote
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from app.schemas.export import ExamExportRequestSchema
from app.services.documents.docx_service import generate_exam_docx_bytes
from app.services.documents.pdf_service import generate_exam_pdf_bytes

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

@router.post(
    "/pdf",
    summary="تولید فایل PDF آزمون (Stateless)",
    description="تولید و دانلود خروجی آزمون در قالب PDF بدون نیاز به ذخیره‌سازی قبلی آزمون.",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "فایل PDF آزمون با موفقیت تولید شد.",
        },
        422: {"description": "خطای اعتبارسنجی داده‌های ورودی"},
        500: {"description": "خطای داخلی سرور هنگام تولید فایل PDF"},
    },
)
async def export_exam_pdf(
    payload: ExamExportRequestSchema,
):
    try:
        exam_data = payload.model_dump()
        include_answers = exam_data.get("include_answers", True)
        pdf_bytes = generate_exam_pdf_bytes(
            exam_data=exam_data,
            include_answers=include_answers,
        )
    except Exception as exc:
        logger.exception("Failed to export exam PDF: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating PDF file",
        )

    safe_title = re.sub(r"[^\w\s-]", "", payload.title, flags=re.UNICODE).strip()
    safe_title = re.sub(r"[-\s]+", "_", safe_title) or "exam"
    encoded_title = quote(f"{safe_title}.pdf")

    content_disposition = (
        f'attachment; filename="exam.pdf"; '
        f"filename*=UTF-8''{encoded_title}"
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": content_disposition},
    )