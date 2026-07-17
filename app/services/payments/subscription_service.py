from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import Subscription, User


def get_active_subscription(current_user: User, db: Session) -> Subscription:
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.is_active == True,
        )
        .order_by(Subscription.id.desc())
        .first()
    )

    if not subscription:
        raise ValueError("No active subscription found")

    if subscription.ends_at < datetime.utcnow():
        subscription.is_active = False
        db.commit()
        raise ValueError("Subscription expired")

    return subscription
