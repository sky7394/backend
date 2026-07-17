from datetime import datetime, timedelta, timezone
import unittest

from jose import jwt

from app.core import security
from app.core.config import settings


class SecurityTests(unittest.TestCase):
    def test_get_password_hash_hashes_plain_password(self):
        password = "correct-horse-battery-staple"

        hashed_password = security.get_password_hash(password)

        self.assertIsInstance(hashed_password, str)
        self.assertNotEqual(hashed_password, password)
        self.assertTrue(security.is_password_hash(hashed_password))
        self.assertTrue(security.verify_password(password, hashed_password))

    def test_get_password_hash_rejects_empty_password(self):
        with self.assertRaises(ValueError):
            security.get_password_hash("")

    def test_get_password_hash_rejects_passwords_longer_than_bcrypt_limit(self):
        with self.assertRaises(ValueError):
            security.get_password_hash("a" * 73)

    def test_get_password_hash_returns_existing_hash_unchanged(self):
        existing_hash = security.get_password_hash("already-hashed")

        self.assertEqual(security.get_password_hash(existing_hash), existing_hash)

    def test_hash_password_aliases_get_password_hash(self):
        password = "alias-password"

        hashed_password = security.hash_password(password)

        self.assertTrue(security.is_password_hash(hashed_password))
        self.assertTrue(security.verify_password(password, hashed_password))

    def test_verify_password_returns_true_for_matching_password(self):
        hashed_password = security.get_password_hash("secret-password")

        self.assertTrue(security.verify_password("secret-password", hashed_password))

    def test_verify_password_returns_false_for_non_matching_password(self):
        hashed_password = security.get_password_hash("secret-password")

        self.assertFalse(security.verify_password("wrong-password", hashed_password))

    def test_verify_password_returns_false_for_invalid_inputs(self):
        self.assertFalse(security.verify_password("", "hashed-password"))
        self.assertFalse(security.verify_password("password", ""))
        self.assertFalse(security.verify_password("password", "not-a-valid-bcrypt-hash"))

    def test_is_password_hash_identifies_bcrypt_hashes(self):
        hashed_password = security.get_password_hash("password")

        self.assertTrue(security.is_password_hash(hashed_password))
        self.assertFalse(security.is_password_hash("password"))
        self.assertFalse(security.is_password_hash("$2b$too-short"))
        self.assertFalse(security.is_password_hash(""))

    def test_create_access_token_contains_subject_and_expiration(self):
        token = security.create_access_token(subject="user-123", expires_delta=5)

        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        expires_at = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)

        self.assertEqual(decoded["sub"], "user-123")
        self.assertNotIn("type", decoded)
        self.assertIn("exp", decoded)
        self.assertGreater(expires_at, datetime.now(timezone.utc))
        self.assertLess(expires_at - datetime.now(timezone.utc), timedelta(minutes=6))

    def test_create_access_token_can_be_decoded_by_helper(self):
        token = security.create_access_token(subject="user-456", expires_delta=5)

        decoded = security.decode_token(token)

        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["sub"], "user-456")
        self.assertIn("exp", decoded)

    def test_create_refresh_token_contains_subject_expiration_and_type(self):
        token = security.create_refresh_token(subject="user-789")

        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        expires_at = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)

        self.assertEqual(decoded["sub"], "user-789")
        self.assertEqual(decoded["type"], "refresh")
        self.assertIn("exp", decoded)
        self.assertGreater(expires_at, datetime.now(timezone.utc))
        self.assertLess(expires_at - datetime.now(timezone.utc), timedelta(days=31))

    def test_create_access_token_expiration_matches_expected_window(self):
        before = datetime.now(timezone.utc)
        token = security.create_access_token(subject="user-window", expires_delta=0.1)
        after = datetime.now(timezone.utc)

        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        expires_at = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        expected_seconds = 0.1 * 60

        self.assertEqual(decoded["sub"], "user-window")
        self.assertGreaterEqual((expires_at - before).total_seconds(), expected_seconds - 2)
        self.assertLessEqual((expires_at - after).total_seconds(), expected_seconds + 2)

    def test_decode_token_returns_none_for_invalid_token(self):
        self.assertIsNone(security.decode_token("not-a-valid-token"))

    def test_decode_token_returns_none_for_token_signed_with_wrong_secret(self):
        token = jwt.encode({"sub": "user-123"}, "wrong-secret", algorithm=settings.ALGORITHM)

        self.assertIsNone(security.decode_token(token))

    def test_decode_token_returns_none_for_tampered_token(self):
        token = security.create_access_token(subject="user-123", expires_delta=5)
        tampered_token = token[:-1] + ("A" if token[-1] != "A" else "B")

        self.assertIsNone(security.decode_token(tampered_token))

    def test_create_refresh_token_round_trip_decodes_expected_payload(self):
        token = security.create_refresh_token(subject="user-refresh")

        decoded = security.decode_token(token)

        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["sub"], "user-refresh")
        self.assertEqual(decoded["type"], "refresh")
        self.assertIn("exp", decoded)


if __name__ == "__main__":
    unittest.main()
