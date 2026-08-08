import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import Subscription, User
from app.schemas.user import UserRegister


def get_profile(user: User) -> User:
    return user


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    payload: UserRegister,
) -> User:
    try:
        user = User(
            id=uuid.uuid4(),
            email=payload.email,
            hashed_password=get_password_hash(payload.password),
            full_name=payload.full_name,
            role="student",
        )
        db.add(user)
        await db.flush()

        subscription = Subscription(
            id=uuid.uuid4(),
            user_id=user.id,
            plan_name="free",
            credits=5,
            status="active",
        )
        db.add(subscription)

        await db.commit()
        await db.refresh(user)
    except Exception:
        await db.rollback()
        raise

    return user
