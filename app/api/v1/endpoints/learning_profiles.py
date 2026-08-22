from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.learning_profile import (
    LearningProfileCreate,
    LearningProfileRead,
    LearningProfileUpdate,
)
from app.services.learning_profiles import service

router = APIRouter(prefix="/learning-profiles", tags=["learning-profiles"])


@router.get("/me", response_model=LearningProfileRead)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await service.get_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning profile not found",
        )
    return profile


@router.put("/me", response_model=LearningProfileRead)
async def upsert_my_profile(
    data: LearningProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.upsert_profile(db, current_user.id, data)


@router.patch("/me", response_model=LearningProfileRead)
async def update_my_profile(
    data: LearningProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await service.get_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning profile not found",
        )
    return await service.update_profile(db, profile, data)
