from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Subscription, User
from app.schemas.user import UserRegister
from app.services.users import user_service


def make_db(query_result=None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = query_result
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


def test_get_profile_returns_given_user():
    user = SimpleNamespace(email="teacher@example.com")

    assert user_service.get_profile(user) is user


@pytest.mark.asyncio
async def test_get_user_by_email_returns_matching_user():
    existing_user = SimpleNamespace(email="teacher@example.com")
    db = make_db(existing_user)

    result = await user_service.get_user_by_email(
        db,
        "teacher@example.com",
    )

    assert result is existing_user
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_by_email_returns_none_for_missing_user():
    db = make_db()

    result = await user_service.get_user_by_email(
        db,
        "missing@example.com",
    )

    assert result is None
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user_hashes_password_and_persists_user_and_subscription():
    db = make_db()
    payload = UserRegister(
        email="new@example.com",
        password="plain-password",
        full_name="New User",
    )

    with patch(
        "app.services.users.user_service.get_password_hash",
        return_value="hashed-password",
    ) as get_password_hash:
        created_user = await user_service.create_user(db, payload)

    assert isinstance(created_user, User)
    assert isinstance(created_user.id, UUID)
    assert created_user.email == "new@example.com"
    assert created_user.hashed_password == "hashed-password"
    assert created_user.full_name == "New User"
    assert created_user.role == "student"
    get_password_hash.assert_called_once_with("plain-password")

    added_objects = [call.args[0] for call in db.add.call_args_list]
    assert len(added_objects) == 2
    assert added_objects[0] is created_user
    assert isinstance(added_objects[1], Subscription)
    assert added_objects[1].user_id == created_user.id
    assert added_objects[1].plan_name == "free"
    assert added_objects[1].credits == 5
    assert added_objects[1].status == "active"
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(created_user)
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_user_accepts_missing_full_name():
    db = make_db()
    payload = UserRegister(
        email="new@example.com",
        password="plain-password",
    )

    with patch(
        "app.services.users.user_service.get_password_hash",
        return_value="hashed-password",
    ):
        created_user = await user_service.create_user(db, payload)

    assert created_user.full_name is None
    assert created_user.role == "student"


@pytest.mark.asyncio
async def test_create_user_rolls_back_and_reraises_database_errors():
    db = make_db()
    db.flush.side_effect = RuntimeError("database unavailable")
    payload = UserRegister(
        email="new@example.com",
        password="plain-password",
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        await user_service.create_user(db, payload)

    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_email_handling_is_lookup_responsibility_before_create():
    existing_user = SimpleNamespace(email="existing@example.com")
    db = make_db(existing_user)

    result = await user_service.get_user_by_email(
        db,
        "existing@example.com",
    )

    assert result is existing_user
    db.add.assert_not_called()
    db.commit.assert_not_awaited()
