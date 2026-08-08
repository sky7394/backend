from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OTPCode
from app.services.auth import auth_service


def make_db(*results) -> MagicMock:
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=results)
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    return db


def make_result(value) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def test_otp_code_is_registered_as_an_orm_model():
    assert OTPCode.__tablename__ == "otp_codes"


@pytest.mark.asyncio
async def test_send_login_otp_persists_code_and_offloads_sync_sms():
    db = make_db()

    with (
        patch(
            "app.services.auth.auth_service.generate_otp",
            return_value="123456",
        ),
        patch(
            "app.services.auth.auth_service.run_in_threadpool",
            new=AsyncMock(return_value=True),
        ) as run_in_threadpool,
    ):
        response = await auth_service.send_login_otp(
            "09121234567",
            db,
        )

    otp = db.add.call_args.args[0]
    assert isinstance(otp, OTPCode)
    assert otp.mobile == "09121234567"
    assert otp.code == "123456"
    assert otp.is_used is False
    db.commit.assert_awaited_once()
    run_in_threadpool.assert_awaited_once_with(
        auth_service.send_sms,
        "09121234567",
        "کد ورود شما: 123456",
    )
    assert response == {"message": "OTP sent successfully"}


@pytest.mark.asyncio
async def test_verify_login_otp_rejects_unknown_code():
    db = make_db(make_result(None))

    with pytest.raises(ValueError, match="Invalid OTP"):
        await auth_service.verify_login_otp(
            "09121234567",
            "123456",
            db,
        )

    db.execute.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_login_otp_rejects_expired_code():
    otp = SimpleNamespace(
        expires_at=auth_service._utcnow() - timedelta(seconds=1),
        is_used=False,
    )
    db = make_db(make_result(otp))

    with pytest.raises(ValueError, match="OTP expired"):
        await auth_service.verify_login_otp(
            "09121234567",
            "123456",
            db,
        )

    assert otp.is_used is False
    db.commit.assert_not_awaited()
