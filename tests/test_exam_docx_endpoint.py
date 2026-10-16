from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.dependencies import get_current_user
from app.db.session import get_db

MOCK_EXAM_DATA = {
    "id": 101,
    "title": "آزمون فیزیک دهم",
    "grade_level": "دهم",
    "major": "ریاضی",
    "difficulty": "متوسط",
    "question_count": 2,
    "questions": [
        {
            "id": 1,
            "text": "قانون اول نیوتون چیست؟",
            "type": "descriptive",
            "score": 2.0,
            "answer": "هر جسم در وضعیت سکون یا حرکت یکنواخت باقی می‌ماند مگر اینکه نیرویی به آن وارد شود.",
        },
        {
            "id": 2,
            "text": "یکای نیرو در SI چیست؟",
            "type": "single_choice",
            "score": 1.0,
            "options": ["ژول", "نیوتون", "وات", "پاسکال"],
            "correct_option_index": 1,
        },
    ],
}


@pytest.fixture
def override_auth_and_db():
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "testuser"}
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_exam_docx_success(override_auth_and_db):
    with patch(
        "app.api.v1.endpoints.exams.get_exam_by_id",
        new=AsyncMock(return_value=MOCK_EXAM_DATA),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/api/v1/exam/101/docx")

    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    # بررسی ارسال هدر دانلود و نام فایل
    assert "Content-Disposition" in response.headers
    assert "filename*=" in response.headers["Content-Disposition"]
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_get_exam_docx_not_found(override_auth_and_db):
    with patch(
        "app.api.v1.endpoints.exams.get_exam_by_id",
        new=AsyncMock(return_value=None),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/api/v1/exam/999/docx")

    assert response.status_code == 404
    assert response.json()["detail"] == "Exam not found"
