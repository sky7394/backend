import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_export_docx_endpoint_success():
    payload = {
        "title": "آزمون فیزیک دهم",
        "grade": "دهم ریاضی",
        "subject": "فیزیک",
        "include_answers": True,
        "questions": [
            {
                "question_text": "یکای کار در SI چیست؟",
                "score": 2.0,
                "options": ["ژول", "نیوتون", "وات", "پاسکال"],
                "correct_answer": "ژول",
                "explanation": "یکای کار در SI ژول است."
            }
        ]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/export/docx", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    cd_header = response.headers["content-disposition"]
    assert "attachment;" in cd_header
    assert "filename*=UTF-8''" in cd_header
    assert cd_header.endswith(".docx")
    assert response.content.startswith(b"PK")

@pytest.mark.asyncio
async def test_export_docx_endpoint_without_answers():
    payload = {
        "title": "آزمون بدون پاسخ‌نامه",
        "grade": "دهم",
        "subject": "فیزیک",
        "include_answers": False,
        "questions": [
            {
                "question_text": "جرم چیست؟",
                "score": 1.0,
                "options": [],
                "correct_answer": None,
                "explanation": None
            }
        ]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/export/docx", json=payload)

    assert response.status_code == 200
    assert response.content.startswith(b"PK")

@pytest.mark.asyncio
async def test_export_docx_endpoint_validation_error():
    invalid_payload = {
        "title": "آزمون ناقص"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/export/docx", json=invalid_payload)

    assert response.status_code == 422
