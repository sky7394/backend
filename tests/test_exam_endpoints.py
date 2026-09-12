import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, AsyncMock, patch

from app.main import app
from app.core.dependencies import get_current_user
from app.db.session import get_db

from app.schemas.exam import ExamPreviewOut, ExamFinalizeOut
from app.schemas.question import (
    QuestionPreviewOut,
    QuestionFinalizeOut,
    QuestionType,
    DifficultyLevel,
)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_user():
    """ایجاد یک کاربر ساختگی برای عبور از احراز هویت"""
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    return user


@pytest.fixture
async def mock_db():
    """شبیه‌سازی Session پایگاه‌داده جهت جلوگیری از اتصال واقعی"""
    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    yield mock_session


@pytest.fixture
async def client(mock_user, mock_db):
    """ایجاد AsyncClient با Override کردن Dependencyهای FastAPI"""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


# ==========================================
# Mock Data Generators (Helpers)
# ==========================================

def valid_generate_request_payload():
    """داده ورودی معتبر برای ارسال به اندپوینت‌ها مطابق با ExamGenerateRequest"""
    return {
        "grade": 10,
        "subject": "Physics",
        "num_questions": 1,
        "question_type": "multiple_choice",
        "difficulty": "medium",
        "topic": "Mechanics",
    }


def valid_preview_exam_object():
    """ساخت شیء معتبر Pydantic برای خروجی مرحله پیش‌نمایش"""
    question = QuestionPreviewOut(
        question_text="کدام گزینه درست است؟",
        question_type=QuestionType.multiple_choice,
        difficulty=DifficultyLevel.medium,
        grade=10,
        subject="Physics",
        topic="Mechanics",
        options=["الف", "ب", "ج", "د"],
        correct_answer="الف",
        explanation="توضیح نمونه برای سوال تستی",
    )
    return ExamPreviewOut(
        title="آزمون فیزیک دهم",
        grade=10,
        subject="Physics",
        questions=[question],
    )


def valid_finalized_exam_object():
    """ساخت شیء معتبر Pydantic برای خروجی مرحله نهایی‌سازی"""
    question = QuestionFinalizeOut(
        id=1,
        question_text="کدام گزینه درست است؟",
        question_type=QuestionType.multiple_choice,
        difficulty=DifficultyLevel.medium,
        grade=10,
        subject="Physics",
        topic="Mechanics",
        options=["الف", "ب", "ج", "د"],
        correct_answer="الف",
        explanation="توضیح نمونه برای سوال تستی",
    )
    return ExamFinalizeOut(
        id=1,
        title="آزمون فیزیک دهم",
        grade=10,
        subject="Physics",
        questions=[question],
    )


# ==========================================
# Test Cases
# ==========================================

@pytest.mark.asyncio
async def test_preview_exam_success(client):
    """تست موفقیت‌آمیز پیش‌نمایش آزمون (Preview) بدون ذخیره در دیتابیس"""
    mock_ai_result = valid_preview_exam_object()

    # چون generate_exam_with_ai همگام است و داخل threadpool اجرا می‌شود،
    # با MagicMock معمولی و تعیین return_value پچ می‌شود.
    with patch(
        "app.services.exams.exam_service.generate_exam_with_ai",
        return_value=mock_ai_result,
    ):
        response = await client.post(
            "/api/v1/exam/preview",
            json=valid_generate_request_payload(),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "آزمون فیزیک دهم"
    assert data["grade"] == 10
    assert data["subject"] == "Physics"
    assert len(data["questions"]) == 1
    assert data["questions"][0]["question_text"] == "کدام گزینه درست است؟"


@pytest.mark.asyncio
async def test_finalize_exam_success(client):
    """تست موفقیت‌آمیز ثبت نهایی آزمون و ذخیره در دیتابیس (Finalize)"""
    mock_ai_result = valid_preview_exam_object()
    mock_final_result = valid_finalized_exam_object()

    with patch(
        "app.services.exams.exam_service.generate_exam_with_ai",
        return_value=mock_ai_result,
    ), patch(
        "app.services.exams.exam_service.create_exam",
        new=AsyncMock(return_value=mock_final_result),
    ):
        response = await client.post(
            "/api/v1/exam/finalize",
            json=valid_generate_request_payload(),
        )

    assert response.status_code == 200
    data = response.json()
    
    # بررسی خروجی
    assert data["title"] == "آزمون فیزیک دهم"
    assert len(data["questions"]) == 1
    # سوالات ثبت شده باید دارای id باشند
    assert data["questions"][0]["id"] == 1


@pytest.mark.asyncio
async def test_preview_unauthorized():
    """تست بررسی رد دسترسی در صورت عدم ارائه توکن و احراز هویت"""
    # ایجاد کلاینت بدون override کردن get_current_user
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as unauth_client:
        response = await unauth_client.post(
            "/api/v1/exam/preview",
            json=valid_generate_request_payload(),
        )
        # اندپوینت باید خطای عدم دسترسی برگرداند
        assert response.status_code in (401, 403)
