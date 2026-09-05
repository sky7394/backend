from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.payment import Payment
from app.models.user import Subscription, User
from app.schemas.payment import (
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentVerifyResponse,
)
from app.services.payments.payment_provider import (
    create_payment_request,
    verify_payment,
)


async def create_payment(
    payload: PaymentCreateRequest,
    current_user: User,
    db: AsyncSession,
) -> PaymentCreateResponse:
    payment_data = create_payment_request(payload.amount, payload.description)

    payment = Payment(
        user_id=current_user.id,
        amount=payload.amount,
        provider=settings.PAYMENT_PROVIDER,
        authority=payment_data["authority"],
        status="pending",
        description=payload.description,
    )

    try:
        db.add(payment)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return PaymentCreateResponse(
        payment_url=payment_data["payment_url"],
        authority=payment_data["authority"],
    )


async def verify_user_payment(
    authority: str,
    db: AsyncSession,
) -> PaymentVerifyResponse:
    result = await db.execute(select(Payment).where(Payment.authority == authority))
    payment = result.scalar_one_or_none()

    if payment is None:
        raise ValueError("Payment not found")

    # Idempotency: callback تکراری از درگاه نباید دوباره credit اضافه کند.
    if payment.status == "paid":
        return PaymentVerifyResponse(
            success=True,
            ref_id=payment.ref_id,
            message="Payment already verified",
        )

    provider_result = verify_payment(authority)

    if not provider_result.get("success"):
        try:
            payment.status = "failed"
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        return PaymentVerifyResponse(
            success=False,
            message="Payment verification failed",
        )

    now = datetime.now(timezone.utc)

    try:
        payment.status = "paid"
        payment.ref_id = provider_result.get("ref_id")

        subscription_result = await db.execute(
            select(Subscription).where(Subscription.user_id == payment.user_id)
        )
        subscription = subscription_result.scalar_one_or_none()

        if subscription is None:
            subscription = Subscription(
                user_id=payment.user_id,
                plan_name="pro",
                credits=50,
                status="active",
                expires_at=now + timedelta(days=settings.DEFAULT_SUBSCRIPTION_DAYS),
            )
            db.add(subscription)
        else:
            # تمدید اشتراک نباید تاریخ انقضای معتبر فعلی را کوتاه کند.
            base_expires_at = (
                subscription.expires_at
                if subscription.expires_at and subscription.expires_at > now
                else now
            )

            subscription.plan_name = "pro"
            subscription.status = "active"
            subscription.credits += 50
            subscription.expires_at = base_expires_at + timedelta(
                days=settings.DEFAULT_SUBSCRIPTION_DAYS
            )

        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return PaymentVerifyResponse(
        success=True,
        ref_id=payment.ref_id,
        message="Payment verified and subscription activated",
    )
