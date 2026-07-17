from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.db.models import User
from app.schemas.subscription import SubscriptionResponse
from app.services.payments.subscription_service import get_active_subscription

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/me", response_model=SubscriptionResponse)
def my_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        return get_active_subscription(current_user, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
