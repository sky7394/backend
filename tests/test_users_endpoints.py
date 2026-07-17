import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

import app.schemas.user as user_schemas
from app.core import dependencies


if not hasattr(user_schemas, "UserResponse"):
    user_schemas.UserResponse = user_schemas.UserBase

users = importlib.import_module("app.api.v1.endpoints.users")


class FakeQuery:
    def __init__(self, user=None, error=None):
        self.user = user
        self.error = error

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        if self.error:
            raise self.error
        return self.user


class FakeDb:
    def __init__(self, user=None, error=None):
        self.user = user
        self.error = error

    def query(self, *_args, **_kwargs):
        if self.error and not isinstance(self.error, SQLAlchemyError):
            raise self.error
        return FakeQuery(user=self.user, error=self.error)


class UsersEndpointTests(unittest.TestCase):
    def build_client(self, *, current_user=None, current_user_error=None, db=None, raise_server_exceptions=True):
        app = FastAPI()
        app.include_router(users.router)

        if current_user_error is not None:
            def get_test_current_user():
                raise current_user_error

            app.dependency_overrides[users.get_current_user] = get_test_current_user
        elif current_user is not None:
            def get_test_current_user():
                return current_user

            app.dependency_overrides[users.get_current_user] = get_test_current_user
        elif db is not None:
            def get_test_db():
                yield db

            app.dependency_overrides[dependencies.get_db] = get_test_db

        return TestClient(app, raise_server_exceptions=raise_server_exceptions)

    def make_user(self, **overrides):
        values = {
            "id": uuid4(),
            "email": "teacher@example.com",
            "full_name": "Teacher User",
            "role": "teacher",
            "is_active": True,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_me_returns_authenticated_user_profile(self):
        current_user = self.make_user()
        client = self.build_client(current_user=current_user)

        with patch("app.api.v1.endpoints.users.get_profile", return_value=current_user) as get_profile:
            response = client.get("/users/me", headers={"Authorization": "Bearer token"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(current_user.id))
        self.assertEqual(response.json()["email"], "teacher@example.com")
        self.assertEqual(response.json()["full_name"], "Teacher User")
        self.assertEqual(response.json()["role"], "teacher")
        get_profile.assert_called_once_with(current_user)

    def test_me_without_authorization_header_is_unauthorized(self):
        client = self.build_client()

        response = client.get("/users/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Not authenticated")
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_me_with_invalid_token_is_unauthorized(self):
        client = self.build_client(
            current_user_error=HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        )

        response = client.get("/users/me", headers={"Authorization": "Bearer invalid-token"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_me_rejects_token_for_missing_user(self):
        client = self.build_client(
            current_user_error=HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        )

        response = client.get("/users/me", headers={"Authorization": "Bearer token-for-missing-user"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_me_with_real_dependency_and_fake_db_returns_user(self):
        current_user = self.make_user()
        client = self.build_client(db=FakeDb(user=current_user))

        with patch("app.core.dependencies.jwt.decode", return_value={"sub": str(current_user.id)}):
            response = client.get("/users/me", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(current_user.id))
        self.assertEqual(response.json()["email"], "teacher@example.com")

    def test_me_db_error_returns_server_error_when_dependency_raises(self):
        client = self.build_client(
            current_user_error=SQLAlchemyError("database unavailable"),
            raise_server_exceptions=False,
        )

        response = client.get("/users/me", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, 500)

    def test_me_response_validation_failure_returns_server_error(self):
        invalid_user = SimpleNamespace(
            id="not-a-uuid",
            email="not-an-email",
            full_name="Broken User",
            role="teacher",
        )
        client = self.build_client(current_user=invalid_user, raise_server_exceptions=False)

        response = client.get("/users/me", headers={"Authorization": "Bearer token"})

        self.assertEqual(response.status_code, 500)

    def test_profile_update_is_not_implemented_for_put(self):
        client = self.build_client(current_user=self.make_user())

        response = client.put("/users/me", json={"full_name": "Updated User"})

        self.assertEqual(response.status_code, 405)

    def test_profile_update_is_not_implemented_for_patch(self):
        client = self.build_client(current_user=self.make_user())

        response = client.patch("/users/me", json={"full_name": "Updated User"})

        self.assertEqual(response.status_code, 405)


if __name__ == "__main__":
    unittest.main()
