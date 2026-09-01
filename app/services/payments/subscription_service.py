from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Subscription, User


async def get_active_subscription(
    current_user: User,
    db: AsyncSession,
) -> Subscription:
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == "active",
        )
    )
    subscription = result.scalar_one_or_none()

    if subscription is None:
        raise ValueError("No active subscription found")

    now = datetime.now(timezone.utc)

    if subscription.expires_at and subscription.expires_at < now:
        try:
            subscription.status = "expired"
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        raise ValueError("Subscription expired")

    return subscription
