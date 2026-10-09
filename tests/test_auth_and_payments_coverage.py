import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Column, String

from app.models.payment import Payment
from app.models.user import Subscription, User
from app.schemas.payment import PaymentCreateRequest
from app.services.auth import auth_service
from app.services.payments import payment_service
from app.services.payments import subscription_service


# ---------------------------------------------------------------------------
# سازگاری مدل User با فیلد mobile (در صورت نبودن در مدل)
# ---------------------------------------------------------------------------
if not hasattr(User, "mobile"):
    setattr(User, "mobile", Column("mobile", String))


def make_user(user_id=None, mobile="09120000000"):
    u = User()
    u.__dict__["id"] = user_id or uuid.uuid4()
    u.__dict__["mobile"] = mobile
    u.__dict__["role"] = "student"
    return u


def make_payment(authority="auth-1", status="pending", user_id=None, amount=1000):
    p = Payment()
    p.__dict__["id"] = uuid.uuid4()
    p.__dict__["authority"] = authority
    p.__dict__["status"] = status
    p.__dict__["ref_id"] = None
    p.__dict__["user_id"] = user_id or uuid.uuid4()
    p.__dict__["amount"] = amount
    p.__dict__["description"] = "desc"
    p.__dict__["provider"] = "dummy"
    return p


def make_subscription(user_id, status="active", credits=10, expires_at=None):
    s = Subscription()
    s.__dict__["id"] = uuid.uuid4()
    s.__dict__["user_id"] = user_id
    s.__dict__["plan_name"] = "basic"
    s.__dict__["status"] = status
    s.__dict__["credits"] = credits
    s.__dict__["expires_at"] = expires_at
    return s


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeAsyncSession:
    """
    execute_results: لیستی از خروجی‌های execute به ترتیب فراخوانی.
      - اگر Exception باشد raise می‌شود
      - در غیر اینصورت همان شیء در scalar_one_or_none برگشت داده می‌شود
    """
    def __init__(self, execute_results=None):
        self.execute_results = list(execute_results or [])
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0

    def add(self, instance):
        # در صورت نیاز id بساز
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
# Auth: send_login_otp
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_send_login_otp_happy_path(monkeypatch):
    db = FakeAsyncSession()

    monkeypatch.setattr(auth_service, "normalize_iran_mobile", lambda m: "09120000000")
    monkeypatch.setattr(auth_service, "generate_otp", lambda: "12345")

    sent = {}

    def fake_send_sms(mobile, text):
        sent["mobile"] = mobile
        sent["text"] = text

    async def fake_run_in_threadpool(fn, *a, **kw):
        # run sync function directly
        return fn(*a, **kw)

    monkeypatch.setattr(auth_service, "send_sms", fake_send_sms)
    monkeypatch.setattr(auth_service, "run_in_threadpool", fake_run_in_threadpool)

    res = await auth_service.send_login_otp("0912 000 0000", db)
    assert res == {"message": "OTP sent successfully"}
    assert db.commits == 1
    assert sent["mobile"] == "09120000000"
    assert "12345" in sent["text"]
    assert len(db.added) == 1  # OTPCode اضافه شده


# ---------------------------------------------------------------------------
# Payments: payment_provider (مستقیم)
# ---------------------------------------------------------------------------
def test_payment_provider_create_payment_request_shape():
    from app.services.payments import payment_provider

    out = payment_provider.create_payment_request(1000, "x")
    assert "authority" in out and "payment_url" in out
    assert out["authority"]
    assert out["payment_url"].endswith(out["authority"])


def test_payment_provider_verify_payment_shape():
    from app.services.payments import payment_provider

    out = payment_provider.verify_payment("abcdef123456")
    assert out["success"] is True
    assert out["ref_id"].startswith("REF-")


# ---------------------------------------------------------------------------
# Payments: create_payment
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_create_payment_happy_path(monkeypatch):
    current_user = make_user()
    payload = PaymentCreateRequest(amount=2000, description="hello")

    monkeypatch.setattr(
        payment_service,
        "create_payment_request",
        lambda amount, description: {
            "authority": "auth-x",
            "payment_url": "https://pay.test/start/auth-x",
        },
    )

    db = FakeAsyncSession()
    res = await payment_service.create_payment(payload, current_user, db)

    assert res.authority == "auth-x"
    assert "auth-x" in res.payment_url
    assert db.commits == 1
    assert len(db.added) == 1
    assert isinstance(db.added[0], Payment)
    assert db.added[0].status == "pending"


@pytest.mark.anyio
async def test_create_payment_commit_failure_rolls_back(monkeypatch):
    current_user = make_user()
    payload = PaymentCreateRequest(amount=2000, description="hello")

    monkeypatch.setattr(
        payment_service,
        "create_payment_request",
        lambda amount, description: {
            "authority": "auth-x",
            "payment_url": "https://pay.test/start/auth-x",
        },
    )

    db = FakeAsyncSession()

    async def exploding_commit():
        await db.rollback()
        raise RuntimeError("commit failed")

    db.commit = exploding_commit

    with pytest.raises(RuntimeError, match="commit failed"):
        await payment_service.create_payment(payload, current_user, db)

    assert db.rollbacks >= 1


# ---------------------------------------------------------------------------
# Payments: verify_user_payment success path + subscription create/extend
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_verify_user_payment_success_creates_subscription(monkeypatch):
    pay = make_payment(authority="auth-ok", status="pending")
    # execute: 1) find payment 2) find subscription(None)
    db = FakeAsyncSession(execute_results=[pay, None])

    monkeypatch.setattr(
        payment_service,
        "verify_payment",
        lambda authority: {"success": True, "ref_id": "REF-OK"},
    )

    res = await payment_service.verify_user_payment("auth-ok", db)
    assert res.success is True
    assert res.ref_id == "REF-OK"
    assert pay.status == "paid"
    assert db.commits == 1
    # یک Subscription باید add شده باشد
    assert any(isinstance(x, Subscription) for x in db.added)


@pytest.mark.anyio
async def test_verify_user_payment_success_extends_active_subscription(monkeypatch):
    now = datetime.now(timezone.utc)
    user_id = uuid.uuid4()
    pay = make_payment(authority="auth-ok2", status="pending", user_id=user_id)

    # subscription فعال با expires_at آینده
    sub = make_subscription(
        user_id=user_id,
        status="active",
        credits=10,
        expires_at=now + timedelta(days=10),
    )

    # execute: 1) find payment 2) find subscription(sub)
    db = FakeAsyncSession(execute_results=[pay, sub])

    monkeypatch.setattr(
        payment_service,
        "verify_payment",
        lambda authority: {"success": True, "ref_id": "REF-OK2"},
    )

    res = await payment_service.verify_user_payment("auth-ok2", db)
    assert res.success is True
    assert pay.status == "paid"
    assert sub.credits == 60  # +50
    assert sub.status == "active"
    assert sub.plan_name == "pro"
    assert sub.expires_at > now + timedelta(days=10)  # تمدید از تاریخ قبلی
    assert db.commits == 1


@pytest.mark.anyio
async def test_verify_user_payment_success_extends_expired_subscription_from_now(monkeypatch):
    now = datetime.now(timezone.utc)
    user_id = uuid.uuid4()
    pay = make_payment(authority="auth-ok3", status="pending", user_id=user_id)

    # subscription منقضی (expires_at گذشته)
    sub = make_subscription(
        user_id=user_id,
        status="active",
        credits=10,
        expires_at=now - timedelta(days=1),
    )

    db = FakeAsyncSession(execute_results=[pay, sub])

    monkeypatch.setattr(
        payment_service,
        "verify_payment",
        lambda authority: {"success": True, "ref_id": "REF-OK3"},
    )

    res = await payment_service.verify_user_payment("auth-ok3", db)
    assert res.success is True
    assert sub.credits == 60
    assert sub.expires_at > now  # از now محاسبه می‌شود نه از تاریخ گذشته
    assert db.commits == 1


@pytest.mark.anyio
async def test_verify_user_payment_success_commit_failure_rolls_back(monkeypatch):
    pay = make_payment(authority="auth-ok4", status="pending")
    db = FakeAsyncSession(execute_results=[pay, None])

    monkeypatch.setattr(
        payment_service,
        "verify_payment",
        lambda authority: {"success": True, "ref_id": "REF-OK4"},
    )

    async def exploding_commit():
        await db.rollback()
        raise RuntimeError("commit failed")

    db.commit = exploding_commit

    with pytest.raises(RuntimeError, match="commit failed"):
        await payment_service.verify_user_payment("auth-ok4", db)
    assert db.rollbacks >= 1


# ---------------------------------------------------------------------------
# Subscription service: get_active_subscription
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_get_active_subscription_happy_path():
    user = make_user()
    sub = make_subscription(user_id=user.id, status="active", credits=1, expires_at=None)

    db = FakeAsyncSession(execute_results=[sub])
    out = await subscription_service.get_active_subscription(user, db)
    assert out is sub


@pytest.mark.anyio
async def test_get_active_subscription_not_found():
    user = make_user()
    db = FakeAsyncSession(execute_results=[None])
    with pytest.raises(ValueError, match="No active subscription found"):
        await subscription_service.get_active_subscription(user, db)


@pytest.mark.anyio
async def test_get_active_subscription_expired_marks_expired_and_raises():
    user = make_user()
    now = datetime.now(timezone.utc)
    sub = make_subscription(
        user_id=user.id, status="active", credits=1, expires_at=now - timedelta(seconds=1)
    )

    db = FakeAsyncSession(execute_results=[sub])

    with pytest.raises(ValueError, match="Subscription expired"):
        await subscription_service.get_active_subscription(user, db)

    assert sub.status == "expired"
    assert db.commits == 1


@pytest.mark.anyio
async def test_get_active_subscription_expired_commit_failure_rolls_back():
    user = make_user()
    now = datetime.now(timezone.utc)
    sub = make_subscription(
        user_id=user.id, status="active", credits=1, expires_at=now - timedelta(seconds=1)
    )

    db = FakeAsyncSession(execute_results=[sub])

    async def exploding_commit():
        await db.rollback()
        raise RuntimeError("commit failed")

    db.commit = exploding_commit

    with pytest.raises(RuntimeError, match="commit failed"):
        await subscription_service.get_active_subscription(user, db)

    assert db.rollbacks >= 1
