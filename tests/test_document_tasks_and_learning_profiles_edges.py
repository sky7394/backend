import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException, status

from app.tasks.document_tasks import create_exam_pdf_task
from app.api.v1.endpoints.learning_profiles import (
    get_my_profile,
    upsert_my_profile,
    update_my_profile,
)
from app.schemas.learning_profile import LearningProfileCreate, LearningProfileUpdate
from app.models.learning_profile import LearningProfile
from app.models.user import User


# ==========================================
# 1. Tests for app/tasks/document_tasks.py
# ==========================================

def test_create_exam_pdf_task():
    questions_data = [
        {"question_text": "What is 2+2?", "options": ["1", "2", "3", "4"], "correct_answer": "4"}
    ]
    with patch("app.tasks.document_tasks.create_exam_pdf", return_value="https://storage.fake/exam.pdf") as mock_pdf:
        result = create_exam_pdf_task(questions_data)
        assert result == "https://storage.fake/exam.pdf"
        mock_pdf.assert_called_once_with(questions_data)


# =======================================================
# 2. Tests for app/api/v1/endpoints/learning_profiles.py
# =======================================================

@pytest.fixture
def fake_user():
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.phone_number = "09123456789"
    return user


@pytest.fixture
def fake_profile(fake_user):
    profile = MagicMock(spec=LearningProfile)
    profile.id = uuid4()
    profile.user_id = fake_user.id
    profile.target_field = "Math"
    profile.target_grade = "12"
    profile.weak_topics = ["Calculus"]
    profile.strong_topics = ["Algebra"]
    profile.daily_study_goal_minutes = 120
    profile.weekly_exam_goal_count = 2
    return profile


@pytest.mark.asyncio
async def test_get_my_profile_success(fake_user, fake_profile):
    mock_db = MagicMock()
    with patch("app.services.learning_profiles.service.get_profile", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_profile
        result = await get_my_profile(db=mock_db, current_user=fake_user)
        assert result == fake_profile
        mock_get.assert_awaited_once_with(mock_db, fake_user.id)


@pytest.mark.asyncio
async def test_get_my_profile_not_found(fake_user):
    mock_db = MagicMock()
    with patch("app.services.learning_profiles.service.get_profile", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await get_my_profile(db=mock_db, current_user=fake_user)
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Learning profile not found"


@pytest.mark.asyncio
async def test_upsert_my_profile(fake_user, fake_profile):
    mock_db = MagicMock()
    create_data = LearningProfileCreate(
        target_field="Physics",
        target_grade="11",
        weak_topics=["Optics"],
        strong_topics=["Mechanics"],
        daily_study_goal_minutes=90,
        weekly_exam_goal_count=1,
    )
    with patch("app.services.learning_profiles.service.upsert_profile", new_callable=AsyncMock) as mock_upsert:
        mock_upsert.return_value = fake_profile
        result = await upsert_my_profile(data=create_data, db=mock_db, current_user=fake_user)
        assert result == fake_profile
        mock_upsert.assert_awaited_once_with(mock_db, fake_user.id, create_data)


@pytest.mark.asyncio
async def test_update_my_profile_success(fake_user, fake_profile):
    mock_db = MagicMock()
    update_data = LearningProfileUpdate(
        target_field="Chemistry",
    )
    with patch("app.services.learning_profiles.service.get_profile", new_callable=AsyncMock) as mock_get, \
         patch("app.services.learning_profiles.service.update_profile", new_callable=AsyncMock) as mock_update:
        mock_get.return_value = fake_profile
        mock_update.return_value = fake_profile
        
        result = await update_my_profile(data=update_data, db=mock_db, current_user=fake_user)
        assert result == fake_profile
        mock_get.assert_awaited_once_with(mock_db, fake_user.id)
        mock_update.assert_awaited_once_with(mock_db, fake_profile, update_data)


@pytest.mark.asyncio
async def test_update_my_profile_not_found(fake_user):
    mock_db = MagicMock()
    update_data = LearningProfileUpdate(target_field="Chemistry")
    with patch("app.services.learning_profiles.service.get_profile", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await update_my_profile(data=update_data, db=mock_db, current_user=fake_user)
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Learning profile not found"
