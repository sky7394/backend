from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from jose import jwt
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import dependencies
from app.core.config import settings


def make_db(user=None, error=None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(
        return_value=result,
        side_effect=error,
    )
    return db


def make_token(payload, secret=None):
    return jwt.encode(
        payload,
        secret or settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def test_oauth2_scheme_token_url():
    assert dependencies.oauth2_scheme.model.flows.password.tokenUrl == "/api/v1/auth/login"


@pytest.mark.asyncio
async def test_get_current_user_returns_user_for_valid_token():
    user_id = str(uuid4())
    user = SimpleNamespace(
        id=user_id,
        email="teacher@example.com",
        role="teacher",
        is_active=True,
    )
    db = make_db(user)

    result = await dependencies.get_current_user(
        db=db,
        token=make_token({"sub": user_id}),
    )

    assert result is user
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token():
    db = make_db()

    with pytest.raises(HTTPException) as context:
        await dependencies.get_current_user(db=db, token="not-a-token")

    assert context.value.status_code == 401
    assert context.value.detail == "Could not validate credentials"
    assert context.value.headers == {"WWW-Authenticate": "Bearer"}
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_current_user_rejects_expired_token():
    db = make_db()

    with pytest.raises(HTTPException) as context:
        await dependencies.get_current_user(
            db=db,
            token=make_token({"sub": "user-1", "exp": 0}),
        )

    assert context.value.status_code == 401
    assert context.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [{"exp": 9999999999}, {"sub": "", "exp": 9999999999}],
)
async def test_get_current_user_rejects_missing_or_empty_subject(payload):
    db = make_db()

    with pytest.raises(HTTPException) as context:
        await dependencies.get_current_user(
            db=db,
            token=make_token(payload),
        )

    assert context.value.status_code == 401
    assert context.value.detail == "Could not validate credentials"
    assert context.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_get_current_user_propagates_db_lookup_failure():
    db = make_db(error=SQLAlchemyError("database unavailable"))

    with pytest.raises(SQLAlchemyError, match="database unavailable"):
        await dependencies.get_current_user(
            db=db,
            token=make_token({"sub": "user-1", "exp": 9999999999}),
        )


@pytest.mark.asyncio
async def test_get_current_user_rejects_token_for_wrong_signature():
    db = make_db()
    token = make_token({"sub": "user-1"}, secret="wrong-secret")

    with pytest.raises(HTTPException) as context:
        await dependencies.get_current_user(db=db, token=token)

    assert context.value.status_code == 401
    assert context.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_user():
    db = make_db()

    with pytest.raises(HTTPException) as context:
        await dependencies.get_current_user(
            db=db,
            token=make_token({"sub": "missing-user"}),
        )

    assert context.value.status_code == 401
    assert context.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_rejects_inactive_user():
    user = SimpleNamespace(
        id=str(uuid4()),
        email="teacher@example.com",
        role="teacher",
        is_active=False,
    )
    db = make_db(user)

    with pytest.raises(HTTPException) as context:
        await dependencies.get_current_user(
            db=db,
            token=make_token({"sub": user.id}),
        )

    assert context.value.status_code == 403
    assert context.value.detail == "Inactive user"


@pytest.mark.asyncio
async def test_role_checker_allows_configured_role():
    user = SimpleNamespace(role="teacher")
    checker = dependencies.RoleChecker(["teacher", "admin"])

    result = await checker(user)

    assert result is user


@pytest.mark.asyncio
async def test_role_checker_rejects_unconfigured_role():
    checker = dependencies.RoleChecker(["teacher", "admin"])

    with pytest.raises(HTTPException) as context:
        await checker(SimpleNamespace(role="student"))

    assert context.value.status_code == 403
    assert context.value.detail == "Operation not permitted for this role"
