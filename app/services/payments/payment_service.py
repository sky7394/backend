from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Payment, Subscription, User
from app.schemas.payment import PaymentCreateRequest, PaymentCreateResponse, PaymentVerifyResponse
from app.services.payments.payment_provider import create_payment_request, verify_payment


def create_payment(payload: PaymentCreateRequest, current_user: User, db: Session) -> PaymentCreateResponse:
    payment_data = create_payment_request(payload.amount, payload.description)

    payment = Payment(
        user_id=current_user.id,
        amount=payload.amount,
        provider=settings.PAYMENT_PROVIDER,
        authority=payment_data["authority"],
        status="pending",
        description=payload.description,
    )
    db.add(payment)
    db.commit()

    return PaymentCreateResponse(
        payment_url=payment_data["payment_url"],
        authority=payment_data["authority"],
    )


def verify_user_payment(authority: str, db: Session) -> PaymentVerifyResponse:
    payment = db.query(Payment).filter(Payment.authority == authority).first()
    if not payment:
        raise ValueError("Payment not found")

    result = verify_payment(authority)
    if not result["success"]:
        payment.status = "failed"
        db.commit()
        return PaymentVerifyResponse(success=False, message="Payment verification failed")

    payment.status = "paid"
    payment.ref_id = result["ref_id"]

    subscription = Subscription(
        user_id=payment.user_id,
        plan_name="monthly",
        is_active=True,
        starts_at=datetime.utcnow(),
        ends_at=datetime.utcnow() + timedelta(days=settings.DEFAULT_SUBSCRIPTION_DAYS),
    )
    db.add(subscription)
    db.commit()

    return PaymentVerifyResponse(
        success=True,
        ref_id=payment.ref_id,
        message="Payment verified and subscription activated",
    )
