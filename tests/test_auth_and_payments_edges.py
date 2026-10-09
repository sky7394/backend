import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Column, String

from app.models.payment import Payment
from app.models.user import Subscription, User
from app.services.auth import auth_service
from app.services.payments import payment_service


# ---------------------------------------------------------------------------
# سازگاری مدل User با فیلد mobile (در صورت تعریف نشدن در اسکیما)
# ---------------------------------------------------------------------------
if not hasattr(User, "mobile"):
    setattr(User, "mobile", Column("mobile", String))


def make_dummy_user(user_id=None, mobile="09120000000"):
    """ایجاد نمونه امن از مدل User بدون برهم زدن مپر SQLAlchemy"""
    u = User()
    u.__dict__["id"] = user_id or uuid.uuid4()
    u.__dict__["mobile"] = mobile
    u.__dict__["role"] = "student"
    return u


# ---------------------------------------------------------------------------
# شبیه‌ساز نشست ناهمگام دیتابیس (FakeAsyncSession)
# ---------------------------------------------------------------------------
class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def first(self):
        return self._value

    def all(self):
        if self._value is None:
            return []
        return self._value if isinstance(self._value, list) else [self._value]


class FakeAsyncSession:
    def __init__(self, execute_results=None):
        self.execute_results = list(execute_results or [])
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0

    def add(self, instance):
        # در صورت نبود id در شی جدید، یک UUID تعیین می‌کنیم
        if getattr(instance, "id", None) is None:
            instance.__dict__["id"] = uuid.uuid4()
        self.added.append(instance)

    async def flush(self):
        self.flushes += 1

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def execute(self, statement, *args, **kwargs):
        if self.execute_results:
            res = self.execute_results.pop(0)
            if isinstance(res, Exception):
                raise res
            return FakeResult(res)
        return FakeResult(None)


# ---------------------------------------------------------------------------
# ۱. تست‌های احراز هویت (Auth Service)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_verify_login_otp_invalid_or_expired():
    db = FakeAsyncSession(execute_results=[None])
    with pytest.raises(ValueError, match="Invalid OTP"):
        await auth_service.verify_login_otp("09120000000", "00000", db)


@pytest.mark.anyio
async def test_verify_login_otp_expired_record():
    class ExpiredOTP:
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        is_used = False

    db = FakeAsyncSession(execute_results=[ExpiredOTP()])
    with pytest.raises(ValueError, match="OTP expired"):
        await auth_service.verify_login_otp("09120000000", "12345", db)


@pytest.mark.anyio
async def test_verify_login_otp_creates_new_user_if_missing(monkeypatch):
    class ValidOTP:
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)
        is_used = False

    monkeypatch.setattr(auth_service, "normalize_iran_mobile", lambda m: "09120000000")
    monkeypatch.setattr(auth_service, "create_access_token", lambda payload: "mocked_jwt_token")

    # ۱. پیدا کردن OTP معتبر / ۲. پیدا نکردن کاربر (کاربر جدید)
    db = FakeAsyncSession(execute_results=[ValidOTP(), None])

    response = await auth_service.verify_login_otp("09120000000", "12345", db)

    assert response.access_token == "mocked_jwt_token"
    assert response.token_type == "bearer"
    assert db.flushes == 1
    assert db.commits == 1
    assert len(db.added) == 1
    assert getattr(db.added[0], "mobile", None) == "09120000000"


@pytest.mark.anyio
async def test_verify_login_otp_existing_user(monkeypatch):
    class ValidOTP:
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)
        is_used = False

    existing_user = make_dummy_user(mobile="09120000000")

    monkeypatch.setattr(auth_service, "normalize_iran_mobile", lambda m: "09120000000")
    monkeypatch.setattr(auth_service, "create_access_token", lambda payload: "token_for_existing")

    # ۱. پیدا کردن OTP معتبر / ۲. پیدا کردن کاربر از قبل موجود
    db = FakeAsyncSession(execute_results=[ValidOTP(), existing_user])
    response = await auth_service.verify_login_otp("09120000000", "12345", db)

    assert response.access_token == "token_for_existing"
    assert db.commits == 1
    assert db.flushes == 0


@pytest.mark.anyio
async def test_auth_service_rollback_on_commit_failure(monkeypatch):
    class ValidOTP:
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)
        is_used = False

    existing_user = make_dummy_user()

    monkeypatch.setattr(auth_service, "normalize_iran_mobile", lambda m: "09120000000")
    monkeypatch.setattr(auth_service, "create_access_token", lambda p: "token")

    db = FakeAsyncSession(execute_results=[ValidOTP(), existing_user])

    async def exploding_commit():
        await db.rollback()
        raise RuntimeError("DB Commit Fatal Error")

    db.commit = exploding_commit

    with pytest.raises(RuntimeError, match="DB Commit Fatal Error"):
        await auth_service.verify_login_otp("09120000000", "12345", db)

    assert db.rollbacks >= 1


# ---------------------------------------------------------------------------
# ۲. تست‌های سرویس پرداخت (Payment Service)
# ---------------------------------------------------------------------------
def make_dummy_payment(status="pending", authority="auth-12345", amount=100000):
    p = Payment()
    p.__dict__["id"] = uuid.uuid4()
    p.__dict__["user_id"] = uuid.uuid4()
    p.__dict__["status"] = status
    p.__dict__["amount"] = amount
    p.__dict__["authority"] = authority
    p.__dict__["ref_id"] = "REF-OLD" if status == "paid" else None
    p.__dict__["description"] = "Test payment"
    return p


@pytest.mark.anyio
async def test_verify_payment_already_successful():
    paid_payment = make_dummy_payment(status="paid")
    db = FakeAsyncSession(execute_results=[paid_payment])

    res = await payment_service.verify_user_payment(authority=paid_payment.authority, db=db)
    assert res.success is True
    assert res.message == "Payment already verified"
    assert db.commits == 0


@pytest.mark.anyio
async def test_verify_payment_not_found():
    db = FakeAsyncSession(execute_results=[None])
    with pytest.raises(ValueError, match="Payment not found"):
        await payment_service.verify_user_payment(authority="non-existent", db=db)


@pytest.mark.anyio
async def test_verify_payment_provider_failed(monkeypatch):
    pending_payment = make_dummy_payment(status="pending")
    db = FakeAsyncSession(execute_results=[pending_payment])

    # ماک کردن پاسخ درگاه پرداخت به عنوان شکست
    monkeypatch.setattr(
        payment_service,
        "verify_payment",
        lambda authority: {"success": False, "message": "Payment canceled"},
    )

    res = await payment_service.verify_user_payment(authority=pending_payment.authority, db=db)
    assert res.success is False
    assert pending_payment.status == "failed"
    assert db.commits == 1


@pytest.mark.anyio
async def test_payment_db_exception_triggers_rollback(monkeypatch):
    pending_payment = make_dummy_payment(status="pending")
    db = FakeAsyncSession(execute_results=[pending_payment])

    monkeypatch.setattr(
        payment_service,
        "verify_payment",
        lambda authority: {"success": False, "message": "failed"},
    )

    async def fail_commit():
        await db.rollback()
        raise RuntimeError("Database connection lost during commit")

    db.commit = fail_commit

    with pytest.raises(RuntimeError, match="Database connection lost during commit"):
        await payment_service.verify_user_payment(authority=pending_payment.authority, db=db)
    assert db.rollbacks >= 1
