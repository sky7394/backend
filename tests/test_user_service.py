import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from app.models.user import Subscription, User
from app.schemas.user import UserRegister
from app.services.users import user_service


class FakeQuery:
    def __init__(self, result):
        self.result = result
        self.filter_args = None
        self.filter_kwargs = None

    def filter(self, *args, **kwargs):
        self.filter_args = args
        self.filter_kwargs = kwargs
        return self

    def first(self):
        return self.result


class FakeDbSession:
    def __init__(self, query_result=None):
        self.query_result = query_result
        self.query_model = None
        self.query_instance = None
        self.added = []
        self.flush_called = False
        self.commit_called = False
        self.refreshed = []

    def query(self, model):
        self.query_model = model
        self.query_instance = FakeQuery(self.query_result)
        return self.query_instance

    def add(self, instance):
        self.added.append(instance)

    def flush(self):
        self.flush_called = True

    def commit(self):
        self.commit_called = True

    def refresh(self, instance):
        self.refreshed.append(instance)


class UserServiceTests(unittest.TestCase):
    def test_get_profile_returns_given_user(self):
        user = SimpleNamespace(email="teacher@example.com")

        self.assertIs(user_service.get_profile(user), user)

    def test_get_user_by_email_returns_matching_user(self):
        existing_user = SimpleNamespace(email="teacher@example.com")
        db = FakeDbSession(query_result=existing_user)

        result = user_service.get_user_by_email(db, "teacher@example.com")

        self.assertIs(result, existing_user)
        self.assertIs(db.query_model, User)
        self.assertIsNotNone(db.query_instance.filter_args)

    def test_get_user_by_email_returns_none_for_missing_user(self):
        db = FakeDbSession(query_result=None)

        result = user_service.get_user_by_email(db, "missing@example.com")

        self.assertIsNone(result)
        self.assertIs(db.query_model, User)

    def test_create_user_hashes_password_and_persists_user_and_subscription(self):
        db = FakeDbSession()
        payload = UserRegister(email="new@example.com", password="plain-password", full_name="New User")

        with patch("app.services.users.user_service.get_password_hash", return_value="hashed-password") as get_password_hash:
            created_user = user_service.create_user(db, payload)

        self.assertIsInstance(created_user, User)
        self.assertIsInstance(created_user.id, UUID)
        self.assertEqual(created_user.email, "new@example.com")
        self.assertEqual(created_user.hashed_password, "hashed-password")
        self.assertNotEqual(created_user.hashed_password, "plain-password")
        self.assertEqual(created_user.full_name, "New User")
        self.assertEqual(created_user.role, "student")
        get_password_hash.assert_called_once_with("plain-password")

        self.assertEqual(len(db.added), 2)
        self.assertIs(db.added[0], created_user)
        self.assertIsInstance(db.added[1], Subscription)
        self.assertEqual(db.added[1].user_id, created_user.id)
        self.assertEqual(db.added[1].plan_name, "free")
        self.assertEqual(db.added[1].credits, 5)
        self.assertEqual(db.added[1].status, "active")
        self.assertTrue(db.flush_called)
        self.assertTrue(db.commit_called)
        self.assertEqual(db.refreshed, [created_user])

    def test_create_user_accepts_missing_full_name(self):
        db = FakeDbSession()
        payload = UserRegister(email="new@example.com", password="plain-password")

        with patch("app.services.users.user_service.get_password_hash", return_value="hashed-password"):
            created_user = user_service.create_user(db, payload)

        self.assertIsNone(created_user.full_name)
        self.assertEqual(created_user.role, "student")

    def test_duplicate_email_handling_is_lookup_responsibility_before_create(self):
        existing_user = SimpleNamespace(email="existing@example.com")
        db = FakeDbSession(query_result=existing_user)

        result = user_service.get_user_by_email(db, "existing@example.com")

        self.assertIs(result, existing_user)
        self.assertEqual(db.added, [])
        self.assertFalse(db.commit_called)


if __name__ == "__main__":
    unittest.main()
