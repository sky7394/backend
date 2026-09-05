from datetime import UTC, datetime, timedelta

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.db.models import OTPCode
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.services.messaging.otp import generate_otp
from app.services.messaging.sms import send_sms
from app.utils.phone import normalize_iran_mobile


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def send_login_otp(mobile_number: str, db: AsyncSession) -> dict:
    mobile = normalize_iran_mobile(mobile_number)
    code = generate_otp()
    otp = OTPCode(
        mobile=mobile,
        code=code,
        expires_at=_utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        is_used=False,
    )
    db.add(otp)
    await db.commit()

    await run_in_threadpool(send_sms, mobile, f"کد ورود شما: {code}")
    return {"message": "OTP sent successfully"}


async def verify_login_otp(mobile_number: str, code: str, db: AsyncSession) -> TokenResponse:
    mobile = normalize_iran_mobile(mobile_number)

    result = await db.execute(
        select(OTPCode)
        .where(
            OTPCode.mobile == mobile,
            OTPCode.code == code,
            OTPCode.is_used.is_(False),
        )
        .order_by(OTPCode.id.desc())
        .limit(1)
    )
    otp = result.scalar_one_or_none()

    if not otp:
        raise ValueError("Invalid OTP")

    if otp.expires_at < _utcnow():
        raise ValueError("OTP expired")

    otp.is_used = True

    result = await db.execute(select(User).where(User.mobile == mobile))
    user = result.scalar_one_or_none()

    if not user:
        user = User(mobile=mobile)
        db.add(user)
        await db.flush()

    await db.commit()

    token = create_access_token(subject=user.mobile)
    return TokenResponse(access_token=token)
