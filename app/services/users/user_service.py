import uuid

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import Subscription, User
from app.schemas.user import UserRegister


def get_profile(user: User) -> User:
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, payload: UserRegister) -> User:
    user = User(
        id=uuid.uuid4(),
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role="student",
    )
    db.add(user)
    db.flush()

    subscription = Subscription(
        id=uuid.uuid4(),
        user_id=user.id,
        plan_name="free",
        credits=5,
        status="active",
    )
    db.add(subscription)
    db.commit()
    db.refresh(user)

    return user
