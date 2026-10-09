import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import IntegrityError
from uuid import uuid4
from app.services.learning_profiles.service import (
    get_profile, create_profile, update_profile, upsert_profile, delete_profile
)
from app.models.learning_profile import LearningProfile
from app.schemas.learning_profile import LearningProfileCreate, LearningProfileUpdate

# تنظیم یک Mock دیتابیس هوشمند که هم sync و هم async را پشتیبانی کند
@pytest.fixture
def mock_db():
    db = MagicMock()
    # متدهایی که باید async باشند
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.delete = AsyncMock()
    # متدهایی که sync هستند (add) نیازی به AsyncMock ندارند، MagicMock کافیست
    return db

@pytest.mark.asyncio
async def test_get_profile(mock_db):
    student_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = LearningProfile(student_id=student_id)
    mock_db.execute.return_value = mock_result
    
    profile = await get_profile(mock_db, student_id)
    assert profile is not None
    assert profile.student_id == student_id

@pytest.mark.asyncio
async def test_create_profile(mock_db):
    student_id = uuid4()
    data = LearningProfileCreate(learning_style="visual")
    
    profile = await create_profile(mock_db, student_id, data)
    
    assert profile.student_id == student_id
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_update_profile(mock_db):
    profile = LearningProfile(student_id=uuid4(), learning_style="visual")
    data = LearningProfileUpdate(learning_style="auditory")
    
    updated = await update_profile(mock_db, profile, data)
    
    assert updated.learning_style == "auditory"
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_upsert_profile_update_case(mock_db):
    student_id = uuid4()
    data = LearningProfileCreate(learning_style="kinesthetic")
    
    with patch('app.services.learning_profiles.service.get_profile', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = LearningProfile(student_id=student_id, learning_style="visual")
        
        result = await upsert_profile(mock_db, student_id, data)
        
        assert result.learning_style == "kinesthetic"
        mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_upsert_profile_create_case(mock_db):
    student_id = uuid4()
    data = LearningProfileCreate(learning_style="visual")
    
    with patch('app.services.learning_profiles.service.get_profile', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        
        result = await upsert_profile(mock_db, student_id, data)
        
        assert result.student_id == student_id
        mock_db.add.assert_called_once()

@pytest.mark.asyncio
async def test_upsert_profile_collision_case(mock_db):
    student_id = uuid4()
    data = LearningProfileCreate(learning_style="visual")
    
    # اینجا patch می‌کنیم تا create_profile خطا بدهد
    with patch('app.services.learning_profiles.service.create_profile', new_callable=AsyncMock) as mock_create, \
         patch('app.services.learning_profiles.service.get_profile', new_callable=AsyncMock) as mock_get:
        
        mock_get.return_value = None 
        mock_create.side_effect = IntegrityError(None, None, None) 
        
        # بعد از خطا (rollback) دوباره فراخوانی می‌شود و این بار پروفایل را برمی‌گرداند
        mock_get.side_effect = [None, LearningProfile(student_id=student_id)]
        
        result = await upsert_profile(mock_db, student_id, data)
        
        assert result.student_id == student_id
        mock_db.rollback.assert_called_once() # حالا باید کار کند!

@pytest.mark.asyncio
async def test_delete_profile(mock_db):
    profile = LearningProfile(student_id=uuid4())
    await delete_profile(mock_db, profile)
    mock_db.delete.assert_called_once_with(profile)
    mock_db.commit.assert_called_once()
