# app/services/learning_profiles/service.py
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning_profile import LearningProfile
from app.schemas.learning_profile import (
    LearningProfileCreate,
    LearningProfileUpdate,
)


async def get_profile(db: AsyncSession, student_id: UUID) -> LearningProfile | None:
    result = await db.execute(
        select(LearningProfile).where(LearningProfile.student_id == student_id)
    )
    return result.scalar_one_or_none()


async def create_profile(
    db: AsyncSession, student_id: UUID, data: LearningProfileCreate
) -> LearningProfile:
    profile = LearningProfile(student_id=student_id, **data.model_dump())
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def update_profile(
    db: AsyncSession,
    profile: LearningProfile,
    data: LearningProfileUpdate,
) -> LearningProfile:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile


async def upsert_profile(
    db: AsyncSession, student_id: UUID, data: LearningProfileCreate
) -> LearningProfile:
    profile = await get_profile(db, student_id)
    if profile is not None:
        return await update_profile(
            db, profile, LearningProfileUpdate(**data.model_dump())
        )

    # Race-safe: در صورت collision دو درخواست همزمان، به update برمی‌گردیم
    try:
        return await create_profile(db, student_id, data)
    except IntegrityError:
        await db.rollback()
        profile = await get_profile(db, student_id)
        if profile is None:
            raise
        return await update_profile(
            db, profile, LearningProfileUpdate(**data.model_dump())
        )


async def delete_profile(db: AsyncSession, profile: LearningProfile) -> None:
    await db.delete(profile)
    await db.commit()
