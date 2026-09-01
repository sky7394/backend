from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.payment import (
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentVerifyResponse,
)
from app.services.payments.payment_service import (
    create_payment as create_user_payment,
)
from app.services.payments.payment_service import verify_user_payment

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/create", response_model=PaymentCreateResponse)
async def create_payment(
    payload: PaymentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentCreateResponse:
    return await create_user_payment(payload, current_user, db)


@router.get("/verify", response_model=PaymentVerifyResponse)
async def payment_verify(
    authority: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> PaymentVerifyResponse:
    try:
        return await verify_user_payment(authority, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
