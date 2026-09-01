from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.schemas.payment import PaymentCreateRequest
from app.services.payments import payment_service


@pytest.fixture
def current_user():
    return SimpleNamespace(id=uuid.uuid4())


@pytest.fixture
def db():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def setup_payment_and_sub_results(db, payment=None, subscription=None):
    mock_payment_res = MagicMock()
    mock_payment_res.scalar_one_or_none.return_value = payment

    mock_sub_res = MagicMock()
    mock_sub_res.scalar_one_or_none.return_value = subscription

    db.execute = AsyncMock(side_effect=[mock_payment_res, mock_sub_res])


@pytest.mark.asyncio
async def test_create_payment_creates_pending_payment_and_returns_provider_data(
    monkeypatch,
    db,
    current_user,
):
    monkeypatch.setattr(
        payment_service,
        "create_payment_request",
        lambda amount, description: {
            "authority": "AUTH-123",
            "payment_url": "https://gateway.test/start/AUTH-123",
        },
    )
    monkeypatch.setattr(payment_service.settings, "PAYMENT_PROVIDER", "test-provider")

    payload = PaymentCreateRequest(
        amount=150_000,
        description="Monthly subscription",
    )

    result = await payment_service.create_payment(payload, current_user, db)

    assert result.authority == "AUTH-123"
    assert result.payment_url == "https://gateway.test/start/AUTH-123"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()

    payment_arg = db.add.call_args[0][0]
    assert payment_arg.user_id == current_user.id
    assert payment_arg.amount == 150_000
    assert payment_arg.provider == "test-provider"
    assert payment_arg.authority == "AUTH-123"
    assert payment_arg.status == "pending"


@pytest.mark.asyncio
async def test_create_payment_rolls_back_and_reraises_database_error(
    monkeypatch,
    db,
    current_user,
):
    monkeypatch.setattr(
        payment_service,
        "create_payment_request",
        lambda amount, description: {
            "authority": "AUTH-ROLLBACK",
            "payment_url": "https://gateway.test/start/AUTH-ROLLBACK",
        },
    )

    db.commit.side_effect = RuntimeError("Database unavailable")

    payload = PaymentCreateRequest(
        amount=150_000,
        description="Monthly subscription",
    )

    with pytest.raises(RuntimeError, match="Database unavailable"):
        await payment_service.create_payment(
            payload,
            current_user,
            db,
        )

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_payment_raises_value_error_when_payment_does_not_exist(db):
    setup_payment_and_sub_results(db, payment=None)

    with pytest.raises(ValueError, match="Payment not found"):
        await payment_service.verify_user_payment("UNKNOWN-AUTHORITY", db)


@pytest.mark.asyncio
async def test_verify_payment_marks_payment_as_failed_when_provider_rejects(
    monkeypatch,
    db,
):
    user_id = uuid.uuid4()
    payment = SimpleNamespace(
        user_id=user_id,
        status="pending",
        ref_id=None,
    )
    setup_payment_and_sub_results(db, payment=payment)

    monkeypatch.setattr(
        payment_service,
        "verify_payment",
        lambda authority: {"success": False},
    )

    result = await payment_service.verify_user_payment("AUTH-FAILED", db)

    assert result.success is False
    assert payment.status == "failed"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_payment_updates_existing_subscription(
    monkeypatch,
    db,
):
    user_id = uuid.uuid4()
    payment = SimpleNamespace(
        user_id=user_id,
        status="pending",
        ref_id=None,
    )
    subscription = SimpleNamespace(
        user_id=user_id,
        plan_name="free",
        status="active",
        credits=5,
        expires_at=None,
    )
    setup_payment_and_sub_results(db, payment=payment, subscription=subscription)

    monkeypatch.setattr(
        payment_service,
        "verify_payment",
        lambda authority: {
            "success": True,
            "ref_id": "REF-12345678",
        },
    )
    monkeypatch.setattr(payment_service.settings, "DEFAULT_SUBSCRIPTION_DAYS", 30)

    result = await payment_service.verify_user_payment("AUTH-SUCCESS", db)

    assert result.success is True
    assert payment.status == "paid"
    assert payment.ref_id == "REF-12345678"
    assert subscription.plan_name == "pro"
    assert subscription.status == "active"
    assert subscription.credits == 55
    assert subscription.expires_at is not None
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_paid_payment_is_idempotent(
    monkeypatch,
    db,
):
    payment = SimpleNamespace(
        user_id=uuid.uuid4(),
        status="paid",
        ref_id="REF-ALREADY-PAID",
    )
    setup_payment_and_sub_results(db, payment=payment)

    verify_provider_mock = MagicMock()
    monkeypatch.setattr(payment_service, "verify_payment", verify_provider_mock)

    result = await payment_service.verify_user_payment("AUTH-ALREADY-PAID", db)

    assert result.success is True
    assert result.ref_id == "REF-ALREADY-PAID"
    verify_provider_mock.assert_not_called()
    db.commit.assert_not_awaited()
