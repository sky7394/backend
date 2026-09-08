# tests/integration/test_exam_exports.py

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.schemas.exam import ExamFinalizeOut
from app.schemas.question import DifficultyLevel, QuestionFinalizeOut, QuestionType


@pytest.fixture
def mock_exam_data() -> ExamFinalizeOut:
    """دیتا نمونه آزمون جهت پاسخ به سرویس دریافت آزمون."""
    return ExamFinalizeOut(
        title="تست فیزیک ۱ - حرکت‌شناسی",
        grade=10,
        subject="فیزیک",
        questions=[
            QuestionFinalizeOut(
                id=1,
                question_text="معادله حرکت یک متحرک در SI به صورت x = 2t^2 + 4t است. شتاب متحرک چند m/s^2 است؟",
                question_type=QuestionType.multiple_choice,
                difficulty=DifficultyLevel.medium,
                grade=10,
                subject="فیزیک",
                topic="حرکت‌شناسی",
                options=["2", "4", "8", "0"],
                correct_answer="4",
                explanation="مشتق دوم مکان نسبت به زمان برابر شتاب است.",
            )
        ],
    )


@pytest.mark.anyio
async def test_export_requires_authentication(client: AsyncClient) -> None:
    """بررسی اینکه درخواست‌های بدون احراز هویت پاسخ 401 برمی‌گردانند."""
    dummy_exam_id = 99999

    pdf_response = await client.get(f"/api/v1/exam/{dummy_exam_id}/pdf")
    docx_response = await client.get(f"/api/v1/exam/{dummy_exam_id}/docx")

    assert pdf_response.status_code == 401
    assert docx_response.status_code == 401


@pytest.mark.anyio
async def test_export_unknown_exam_returns_404(
    authenticated_client: AsyncClient,
) -> None:
    """بررسی دریافت پاسخ 404 برای آزمون غیرموجود (با شناسه عددی معتبر)."""
    non_existent_exam_id = 2147483647

    with patch(
        "app.api.v1.endpoints.exams.get_exam_by_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        pdf_response = await authenticated_client.get(
            f"/api/v1/exam/{non_existent_exam_id}/pdf"
        )
        docx_response = await authenticated_client.get(
            f"/api/v1/exam/{non_existent_exam_id}/docx"
        )

        assert pdf_response.status_code == 404
        assert docx_response.status_code == 404


@pytest.mark.anyio
async def test_export_docx_success(
    authenticated_client: AsyncClient,
    mock_exam_data: ExamFinalizeOut,
) -> None:
    """بررسی دریافت موفقیت‌آمیز فایل DOCX با Content-Type و Headerهای مناسب."""
    sample_exam_id = 1

    with patch(
        "app.api.v1.endpoints.exams.get_exam_by_id",
        new_callable=AsyncMock,
        return_value=mock_exam_data,
    ):
        response = await authenticated_client.get(
            f"/api/v1/exam/{sample_exam_id}/docx"
        )

        assert response.status_code == 200
        assert (
            response.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert "attachment; filename=" in response.headers.get("content-disposition", "")
        assert len(response.content) > 0
