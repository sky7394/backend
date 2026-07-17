import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import auth
from app.db.session import get_db


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


class AuthEndpointTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(auth.router, prefix="/api/v1/auth")
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def override_db(self, db):
        def get_test_db():
            yield db

        self.app.dependency_overrides[get_db] = get_test_db

    def test_login_accepts_form_data_and_returns_tokens(self):
        user_id = uuid4()
        user = SimpleNamespace(
            id=user_id,
            email="teacher@example.com",
            hashed_password="hashed-password",
            full_name="Teacher",
            role="teacher",
        )
        self.override_db(FakeDb(user=user))

        with (
            patch("app.api.v1.endpoints.auth.verify_password", return_value=True) as verify_password,
            patch("app.api.v1.endpoints.auth.create_access_token", return_value="access-token") as create_access_token,
            patch("app.api.v1.endpoints.auth.create_refresh_token", return_value="refresh-token") as create_refresh_token,
        ):
            response = self.client.post(
                "/api/v1/auth/login",
                data={
                    "username": "teacher@example.com",
                    "password": "123456",
                    "grant_type": "password",
                    "client_id": "",
                    "client_secret": "",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "token_type": "bearer",
            },
        )
        verify_password.assert_called_once_with("123456", "hashed-password")
        create_access_token.assert_called_once_with(subject=str(user_id))
        create_refresh_token.assert_called_once_with(subject=str(user_id))

    def test_login_rejects_invalid_credentials(self):
        user = SimpleNamespace(
            id=uuid4(),
            email="teacher@example.com",
            hashed_password="hashed-password",
        )
        self.override_db(FakeDb(user=user))

        with patch("app.api.v1.endpoints.auth.verify_password", return_value=False):
            response = self.client.post(
                "/api/v1/auth/login",
                data={"username": "teacher@example.com", "password": "wrong-password"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Incorrect email or password")

    def test_login_rejects_missing_user(self):
        self.override_db(FakeDb(user=None))

        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": "missing@example.com", "password": "123456"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Incorrect email or password")

    def test_register_creates_user_when_email_is_new(self):
        user_id = uuid4()
        created_user = SimpleNamespace(
            id=user_id,
            email="new@example.com",
            full_name="New User",
            role="student",
        )
        self.override_db(FakeDb())

        with (
            patch("app.api.v1.endpoints.auth.get_user_by_email", return_value=None) as get_user_by_email,
            patch("app.api.v1.endpoints.auth.create_user", return_value=created_user) as create_user,
        ):
            response = self.client.post(
                "/api/v1/auth/register",
                json={
                    "email": "new@example.com",
                    "password": "123456",
                    "full_name": "New User",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "new@example.com")
        self.assertEqual(response.json()["role"], "student")
        get_user_by_email.assert_called_once()
        create_user.assert_called_once()

    def test_register_rejects_duplicate_email(self):
        existing_user = SimpleNamespace(email="existing@example.com")
        self.override_db(FakeDb())

        with patch("app.api.v1.endpoints.auth.get_user_by_email", return_value=existing_user):
            response = self.client.post(
                "/api/v1/auth/register",
                json={"email": "existing@example.com", "password": "123456"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Email already registered.")

    def test_refresh_rejects_invalid_refresh_token(self):
        with patch("app.api.v1.endpoints.auth.decode_token", return_value=None):
            response = self.client.post(
                "/api/v1/auth/refresh",
                params={"refresh_token": "invalid-token"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid refresh token")

    def test_refresh_rejects_token_with_wrong_type(self):
        with patch("app.api.v1.endpoints.auth.decode_token", return_value={"sub": "user-1", "type": "access"}):
            response = self.client.post(
                "/api/v1/auth/refresh",
                params={"refresh_token": "access-token"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid refresh token")

    def test_refresh_missing_sub_claim_returns_server_error(self):
        app = FastAPI()
        app.include_router(auth.router, prefix="/api/v1/auth")
        client = TestClient(app, raise_server_exceptions=False)

        with patch("app.api.v1.endpoints.auth.decode_token", return_value={"type": "refresh"}):
            response = client.post(
                "/api/v1/auth/refresh",
                params={"refresh_token": "missing-sub-refresh-token"},
            )

        self.assertEqual(response.status_code, 500)

    def test_refresh_rejects_expired_refresh_token(self):
        with patch("app.api.v1.endpoints.auth.decode_token", return_value=None):
            response = self.client.post(
                "/api/v1/auth/refresh",
                params={"refresh_token": "expired-refresh-token"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid refresh token")

    def test_refresh_returns_new_tokens_for_valid_refresh_token(self):
        with (
            patch("app.api.v1.endpoints.auth.decode_token", return_value={"sub": "user-1", "type": "refresh"}),
            patch("app.api.v1.endpoints.auth.create_access_token", return_value="new-access") as create_access_token,
            patch("app.api.v1.endpoints.auth.create_refresh_token", return_value="new-refresh") as create_refresh_token,
        ):
            response = self.client.post(
                "/api/v1/auth/refresh",
                params={"refresh_token": "valid-refresh"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["access_token"], "new-access")
        self.assertEqual(response.json()["refresh_token"], "new-refresh")
        create_access_token.assert_called_once_with("user-1")
        create_refresh_token.assert_called_once_with("user-1")

    def test_me_returns_current_user(self):
        user_id = uuid4()
        current_user = SimpleNamespace(
            id=user_id,
            email="teacher@example.com",
            full_name="Teacher",
            role="teacher",
        )

        def get_test_current_user():
            return current_user

        self.app.dependency_overrides[auth.get_current_user] = get_test_current_user

        response = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(user_id))
        self.assertEqual(response.json()["email"], "teacher@example.com")


if __name__ == "__main__":
    unittest.main()
