from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints import auth
from app.schemas.user import UserRegister


def make_db(user=None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_login_accepts_form_data_and_returns_tokens():
    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id,
        email="teacher@example.com",
        hashed_password="hashed-password",
        full_name="Teacher",
        role="teacher",
    )
    db = make_db(user)
    form_data = SimpleNamespace(
        username="teacher@example.com",
        password="123456",
    )

    with (
        patch(
            "app.api.v1.endpoints.auth.verify_password",
            return_value=True,
        ) as verify_password,
        patch(
            "app.api.v1.endpoints.auth.create_access_token",
            return_value="access-token",
        ) as create_access_token,
        patch(
            "app.api.v1.endpoints.auth.create_refresh_token",
            return_value="refresh-token",
        ) as create_refresh_token,
    ):
        response = await auth.login(form_data, db)

    assert response == {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "token_type": "bearer",
    }
    db.execute.assert_awaited_once()
    verify_password.assert_called_once_with("123456", "hashed-password")
    create_access_token.assert_called_once_with(subject=str(user_id))
    create_refresh_token.assert_called_once_with(subject=str(user_id))


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials():
    user = SimpleNamespace(
        id=uuid4(),
        email="teacher@example.com",
        hashed_password="hashed-password",
    )
    db = make_db(user)
    form_data = SimpleNamespace(
        username="teacher@example.com",
        password="wrong-password",
    )

    with patch("app.api.v1.endpoints.auth.verify_password", return_value=False):
        with pytest.raises(HTTPException) as context:
            await auth.login(form_data, db)

    assert context.value.status_code == 400
    assert context.value.detail == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_rejects_missing_user():
    db = make_db()
    form_data = SimpleNamespace(
        username="missing@example.com",
        password="123456",
    )

    with pytest.raises(HTTPException) as context:
        await auth.login(form_data, db)

    assert context.value.status_code == 400
    assert context.value.detail == "Incorrect email or password"


@pytest.mark.asyncio
async def test_register_creates_user_when_email_is_new():
    payload = UserRegister(
        email="new@example.com",
        password="123456",
        full_name="New User",
    )
    created_user = SimpleNamespace(
        id=uuid4(),
        email="new@example.com",
        full_name="New User",
        role="student",
    )
    db = make_db()

    with (
        patch(
            "app.api.v1.endpoints.auth.get_user_by_email",
            new=AsyncMock(return_value=None),
        ) as get_user_by_email,
        patch(
            "app.api.v1.endpoints.auth.create_user",
            new=AsyncMock(return_value=created_user),
        ) as create_user,
    ):
        response = await auth.register_user(payload, db)

    assert response is created_user
    get_user_by_email.assert_awaited_once_with(db, payload.email)
    create_user.assert_awaited_once_with(db, payload)


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email():
    payload = UserRegister(
        email="existing@example.com",
        password="123456",
    )
    existing_user = SimpleNamespace(email="existing@example.com")
    db = make_db()

    with patch(
        "app.api.v1.endpoints.auth.get_user_by_email",
        new=AsyncMock(return_value=existing_user),
    ):
        with pytest.raises(HTTPException) as context:
            await auth.register_user(payload, db)

    assert context.value.status_code == 400
    assert context.value.detail == "Email already registered."


@pytest.mark.asyncio
async def test_register_converts_create_user_value_error_to_bad_request():
    payload = UserRegister(
        email="new@example.com",
        password="123456",
    )
    db = make_db()

    with (
        patch(
            "app.api.v1.endpoints.auth.get_user_by_email",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.api.v1.endpoints.auth.create_user",
            new=AsyncMock(side_effect=ValueError("Invalid user data")),
        ),
    ):
        with pytest.raises(HTTPException) as context:
            await auth.register_user(payload, db)

    assert context.value.status_code == 400
    assert context.value.detail == "Invalid user data"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "decoded",
    [None, {"sub": "user-1", "type": "access"}],
)
async def test_refresh_rejects_invalid_refresh_token(decoded):
    with patch("app.api.v1.endpoints.auth.decode_token", return_value=decoded):
        with pytest.raises(HTTPException) as context:
            await auth.refresh_token("invalid-token")

    assert context.value.status_code == 401
    assert context.value.detail == "Invalid refresh token"


@pytest.mark.asyncio
async def test_refresh_missing_sub_claim_raises_key_error():
    with patch(
        "app.api.v1.endpoints.auth.decode_token",
        return_value={"type": "refresh"},
    ):
        with pytest.raises(KeyError):
            await auth.refresh_token("missing-sub-refresh-token")


@pytest.mark.asyncio
async def test_refresh_returns_new_tokens_for_valid_refresh_token():
    with (
        patch(
            "app.api.v1.endpoints.auth.decode_token",
            return_value={"sub": "user-1", "type": "refresh"},
        ),
        patch(
            "app.api.v1.endpoints.auth.create_access_token",
            return_value="new-access",
        ) as create_access_token,
        patch(
            "app.api.v1.endpoints.auth.create_refresh_token",
            return_value="new-refresh",
        ) as create_refresh_token,
    ):
        response = await auth.refresh_token("valid-refresh")

    assert response.access_token == "new-access"
    assert response.refresh_token == "new-refresh"
    create_access_token.assert_called_once_with("user-1")
    create_refresh_token.assert_called_once_with("user-1")


@pytest.mark.asyncio
async def test_me_returns_current_user():
    current_user = SimpleNamespace(
        id=uuid4(),
        email="teacher@example.com",
        full_name="Teacher",
        role="teacher",
    )

    response = await auth.read_users_me(current_user)

    assert response is current_user
