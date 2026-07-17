from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.db.models import User
from app.schemas.payment import (
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentVerifyResponse
)
from app.services.payments.payment_service import create_payment as create_user_payment
from app.services.payments.payment_service import verify_user_payment

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/create", response_model=PaymentCreateResponse)
def create_payment(
    payload: PaymentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_user_payment(payload, current_user, db)


@router.get("/verify", response_model=PaymentVerifyResponse)
def payment_verify(authority: str = Query(...), db: Session = Depends(get_db)):
    try:
        return verify_user_payment(authority, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
