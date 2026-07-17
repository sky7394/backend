from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.models import OTPCode, User
from app.schemas.auth import TokenResponse
from app.services.messaging.otp import generate_otp
from app.services.messaging.sms import send_sms
from app.utils.phone import normalize_iran_mobile


def send_login_otp(mobile_number: str, db: Session) -> dict:
    mobile = normalize_iran_mobile(mobile_number)
    code = generate_otp()
    otp = OTPCode(
        mobile=mobile,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        is_used=False,
    )
    db.add(otp)
    db.commit()

    send_sms(mobile, f"کد ورود شما: {code}")
    return {"message": "OTP sent successfully"}


def verify_login_otp(mobile_number: str, code: str, db: Session) -> TokenResponse:
    mobile = normalize_iran_mobile(mobile_number)
    otp = (
        db.query(OTPCode)
        .filter(
            OTPCode.mobile == mobile,
            OTPCode.code == code,
            OTPCode.is_used == False,
        )
        .order_by(OTPCode.id.desc())
        .first()
    )

    if not otp:
        raise ValueError("Invalid OTP")

    if otp.expires_at < datetime.utcnow():
        raise ValueError("OTP expired")

    otp.is_used = True
    user = db.query(User).filter(User.mobile == mobile).first()
    if not user:
        user = User(mobile=mobile)
        db.add(user)
        db.flush()

    db.commit()

    token = create_access_token(subject=user.mobile)
    return TokenResponse(access_token=token)
