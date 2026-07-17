import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from jose import jwt
from sqlalchemy.exc import SQLAlchemyError

from app.core import dependencies
from app.core.config import settings


class FakeQuery:
    def __init__(self, user):
        self.user = user

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.user


class FakeDb:
    def __init__(self, user=None):
        self.user = user

    def query(self, *_args, **_kwargs):
        return FakeQuery(self.user)


class FailingDb:
    def query(self, *_args, **_kwargs):
        raise SQLAlchemyError("database unavailable")


class DependenciesTests(unittest.TestCase):
    def make_token(self, payload, secret=None):
        return jwt.encode(payload, secret or settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def test_oauth2_scheme_token_url(self):
        self.assertEqual(dependencies.oauth2_scheme.model.flows.password.tokenUrl, "/api/v1/auth/login")

    def test_get_current_user_returns_user_for_valid_token(self):
        user_id = str(uuid4())
        user = SimpleNamespace(id=user_id, email="teacher@example.com", role="teacher", is_active=True)
        token = self.make_token({"sub": user_id})

        result = dependencies.get_current_user(db=FakeDb(user=user), token=token)

        self.assertIs(result, user)

    def test_get_current_user_rejects_invalid_token(self):
        with self.assertRaises(HTTPException) as context:
            dependencies.get_current_user(db=FakeDb(), token="not-a-token")

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Could not validate credentials")
        self.assertEqual(context.exception.headers, {"WWW-Authenticate": "Bearer"})

    def test_get_current_user_rejects_expired_token(self):
        token = self.make_token({"sub": "user-1", "exp": 0})

        with self.assertRaises(HTTPException) as context:
            dependencies.get_current_user(db=FakeDb(), token=token)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Could not validate credentials")

    def test_get_current_user_rejects_token_missing_sub_claim(self):
        token = self.make_token({"exp": 9999999999})

        with self.assertRaises(HTTPException) as context:
            dependencies.get_current_user(db=FakeDb(), token=token)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Could not validate credentials")
        self.assertEqual(context.exception.headers, {"WWW-Authenticate": "Bearer"})

    def test_get_current_user_rejects_empty_sub_claim(self):
        token = self.make_token({"sub": "", "exp": 9999999999})

        with self.assertRaises(HTTPException) as context:
            dependencies.get_current_user(db=FakeDb(user=None), token=token)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Could not validate credentials")
        self.assertEqual(context.exception.headers, {"WWW-Authenticate": "Bearer"})

    def test_get_current_user_propagates_db_lookup_failure(self):
        token = self.make_token({"sub": "user-1", "exp": 9999999999})

        with self.assertRaises(SQLAlchemyError):
            dependencies.get_current_user(db=FailingDb(), token=token)

    def test_get_current_user_rejects_token_for_wrong_signature(self):
        token = self.make_token({"sub": "user-1"}, secret="wrong-secret")

        with self.assertRaises(HTTPException) as context:
            dependencies.get_current_user(db=FakeDb(), token=token)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Could not validate credentials")

    def test_get_current_user_rejects_missing_user(self):
        token = self.make_token({"sub": "missing-user"})

        with self.assertRaises(HTTPException) as context:
            dependencies.get_current_user(db=FakeDb(user=None), token=token)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Could not validate credentials")

    def test_get_current_user_passes_string_subject_through_to_db_lookup(self):
        user_id = str(uuid4())
        user = SimpleNamespace(id=user_id, email="teacher@example.com", role="teacher", is_active=True)
        token = self.make_token({"sub": user_id})
        db = FakeDb(user=user)

        with patch.object(db, "query", wraps=db.query) as query_mock:
            result = dependencies.get_current_user(db=db, token=token)

        self.assertIs(result, user)
        query_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
