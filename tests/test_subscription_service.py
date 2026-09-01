from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.services.payments.subscription_service import get_active_subscription


@pytest.fixture
def current_user():
    return SimpleNamespace(id=uuid.uuid4())


@pytest.fixture
def db():
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def setup_subscription_result(db, subscription):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = subscription
    db.execute = AsyncMock(return_value=mock_result)


@pytest.mark.asyncio
async def test_get_active_subscription_returns_subscription(
    db,
    current_user,
):
    subscription = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=current_user.id,
        plan_name="pro",
        status="active",
        credits=50,
        expires_at=datetime.now(timezone.utc) + timedelta(days=28),
    )
    setup_subscription_result(db, subscription)

    result = await get_active_subscription(current_user, db)

    assert result is subscription


@pytest.mark.asyncio
async def test_get_active_subscription_raises_when_none_found(
    db,
    current_user,
):
    setup_subscription_result(db, None)

    with pytest.raises(ValueError, match="No active subscription found"):
        await get_active_subscription(current_user, db)


@pytest.mark.asyncio
async def test_get_active_subscription_expires_outdated_subscription(
    db,
    current_user,
):
    subscription = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=current_user.id,
        plan_name="pro",
        status="active",
        credits=10,
        expires_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    setup_subscription_result(db, subscription)

    with pytest.raises(ValueError, match="Subscription expired"):
        await get_active_subscription(current_user, db)

    assert subscription.status == "expired"
    db.commit.assert_awaited_once()
