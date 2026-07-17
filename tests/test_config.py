import importlib
import os
import unittest
from unittest.mock import patch


BASE_ENV = {
    "DATABASE_URL": "postgresql://user:pass@localhost:5432/app_db",
    "JWT_SECRET": "jwt-secret",
}


class ConfigTests(unittest.TestCase):
    def load_config(self, env):
        with patch("dotenv.load_dotenv", return_value=False), patch.dict(os.environ, env, clear=True):
            import app.core.config as config

            return importlib.reload(config)

    def tearDown(self):
        import app.core.config as config

        importlib.reload(config)

    def test_settings_load_required_environment_variables(self):
        config = self.load_config(BASE_ENV)

        self.assertEqual(config.settings.DATABASE_URL, BASE_ENV["DATABASE_URL"])
        self.assertEqual(config.settings.JWT_SECRET, "jwt-secret")
        self.assertEqual(config.settings.SECRET_KEY, "jwt-secret")

    def test_secret_key_fallback_is_used_when_jwt_secret_missing(self):
        env = {
            "DATABASE_URL": BASE_ENV["DATABASE_URL"],
            "SECRET_KEY": "fallback-secret",
        }

        config = self.load_config(env)

        self.assertEqual(config.settings.JWT_SECRET, "fallback-secret")
        self.assertEqual(config.settings.SECRET_KEY, "fallback-secret")

    def test_jwt_secret_takes_precedence_over_secret_key_fallback(self):
        env = {
            "DATABASE_URL": BASE_ENV["DATABASE_URL"],
            "JWT_SECRET": "primary-secret",
            "SECRET_KEY": "fallback-secret",
        }

        config = self.load_config(env)

        self.assertEqual(config.settings.JWT_SECRET, "primary-secret")
        self.assertEqual(config.settings.SECRET_KEY, "primary-secret")

    def test_missing_database_url_raises_runtime_error(self):
        with self.assertRaisesRegex(RuntimeError, "Missing required environment variable: DATABASE_URL"):
            self.load_config({"JWT_SECRET": "jwt-secret"})

    def test_missing_jwt_secret_and_secret_key_raises_runtime_error(self):
        with self.assertRaisesRegex(RuntimeError, "Missing required environment variable: JWT_SECRET or SECRET_KEY"):
            self.load_config({"DATABASE_URL": BASE_ENV["DATABASE_URL"]})

    def test_defaults_are_used_for_optional_settings(self):
        config = self.load_config(BASE_ENV)

        self.assertEqual(config.settings.APP_NAME, "GapCode AI SaaS")
        self.assertEqual(config.settings.ALGORITHM, "HS256")
        self.assertEqual(config.settings.ACCESS_TOKEN_EXPIRE_MINUTES, 43200)
        self.assertEqual(config.settings.REDIS_URL, "redis://localhost:6379/0")
        self.assertEqual(config.settings.OPENAI_API_KEY, "")
        self.assertEqual(config.settings.OPENAI_BASE_URL, "https://api.groq.com/openai/v1")
        self.assertEqual(config.settings.OPENAI_MODEL, "llama-3.3-70b-versatile")
        self.assertEqual(config.settings.GEMINI_API_KEY, "")
        self.assertEqual(
            config.settings.GEMINI_BASE_URL,
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self.assertEqual(config.settings.GEMINI_MODEL, "gemini-2.0-flash-exp")
        self.assertEqual(config.settings.SMS_PROVIDER, "mock")
        self.assertEqual(config.settings.SMS_API_KEY, "")
        self.assertEqual(config.settings.SMS_SENDER, "")
        self.assertEqual(config.settings.OTP_EXPIRE_MINUTES, 2)
        self.assertEqual(config.settings.PAYMENT_PROVIDER, "zarinpal")
        self.assertEqual(config.settings.ZARINPAL_MERCHANT_ID, "")
        self.assertEqual(config.settings.PAYMENT_CALLBACK_URL, "")
        self.assertEqual(config.settings.DEFAULT_SUBSCRIPTION_DAYS, 30)
        self.assertEqual(config.settings.GENERATED_PDF_DIR, "generated_pdfs")
        self.assertEqual(config.settings.FONT_PATH, "fonts/Vazir.ttf")

    def test_custom_optional_settings_override_defaults(self):
        env = BASE_ENV | {
            "REDIS_URL": "redis://redis:6379/1",
            "OPENAI_API_KEY": "openai-key",
            "OPENAI_BASE_URL": "https://example.test/openai",
            "OPENAI_MODEL": "test-openai-model",
            "GEMINI_API_KEY": "gemini-key",
            "GEMINI_BASE_URL": "https://example.test/gemini",
            "GEMINI_MODEL": "test-gemini-model",
            "SMS_PROVIDER": "twilio",
            "SMS_API_KEY": "sms-key",
            "SMS_SENDER": "sender",
            "PAYMENT_PROVIDER": "mockpay",
            "ZARINPAL_MERCHANT_ID": "merchant-id",
            "PAYMENT_CALLBACK_URL": "https://example.test/callback",
            "GENERATED_PDF_DIR": "/tmp/pdfs",
            "FONT_PATH": "/tmp/font.ttf",
        }

        config = self.load_config(env)

        self.assertEqual(config.settings.REDIS_URL, "redis://redis:6379/1")
        self.assertEqual(config.settings.OPENAI_API_KEY, "openai-key")
        self.assertEqual(config.settings.OPENAI_BASE_URL, "https://example.test/openai")
        self.assertEqual(config.settings.OPENAI_MODEL, "test-openai-model")
        self.assertEqual(config.settings.GEMINI_API_KEY, "gemini-key")
        self.assertEqual(config.settings.GEMINI_BASE_URL, "https://example.test/gemini")
        self.assertEqual(config.settings.GEMINI_MODEL, "test-gemini-model")
        self.assertEqual(config.settings.SMS_PROVIDER, "twilio")
        self.assertEqual(config.settings.SMS_API_KEY, "sms-key")
        self.assertEqual(config.settings.SMS_SENDER, "sender")
        self.assertEqual(config.settings.PAYMENT_PROVIDER, "mockpay")
        self.assertEqual(config.settings.ZARINPAL_MERCHANT_ID, "merchant-id")
        self.assertEqual(config.settings.PAYMENT_CALLBACK_URL, "https://example.test/callback")
        self.assertEqual(config.settings.GENERATED_PDF_DIR, "/tmp/pdfs")
        self.assertEqual(config.settings.FONT_PATH, "/tmp/font.ttf")

    def test_integer_environment_values_are_parsed(self):
        env = BASE_ENV | {
            "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
            "OTP_EXPIRE_MINUTES": "4",
            "DEFAULT_SUBSCRIPTION_DAYS": "45",
        }

        config = self.load_config(env)

        self.assertEqual(config.settings.ACCESS_TOKEN_EXPIRE_MINUTES, 15)
        self.assertEqual(config.settings.OTP_EXPIRE_MINUTES, 4)
        self.assertEqual(config.settings.DEFAULT_SUBSCRIPTION_DAYS, 45)

    def test_empty_integer_environment_values_use_defaults(self):
        env = BASE_ENV | {
            "ACCESS_TOKEN_EXPIRE_MINUTES": "",
            "OTP_EXPIRE_MINUTES": "",
            "DEFAULT_SUBSCRIPTION_DAYS": "",
        }

        config = self.load_config(env)

        self.assertEqual(config.settings.ACCESS_TOKEN_EXPIRE_MINUTES, 43200)
        self.assertEqual(config.settings.OTP_EXPIRE_MINUTES, 2)
        self.assertEqual(config.settings.DEFAULT_SUBSCRIPTION_DAYS, 30)

    def test_invalid_access_token_expire_minutes_raises_runtime_error(self):
        env = BASE_ENV | {"ACCESS_TOKEN_EXPIRE_MINUTES": "not-an-int"}

        with self.assertRaisesRegex(RuntimeError, "ACCESS_TOKEN_EXPIRE_MINUTES must be an integer"):
            self.load_config(env)

    def test_invalid_otp_expire_minutes_raises_runtime_error(self):
        env = BASE_ENV | {"OTP_EXPIRE_MINUTES": "not-an-int"}

        with self.assertRaisesRegex(RuntimeError, "OTP_EXPIRE_MINUTES must be an integer"):
            self.load_config(env)

    def test_invalid_default_subscription_days_raises_runtime_error(self):
        env = BASE_ENV | {"DEFAULT_SUBSCRIPTION_DAYS": "not-an-int"}

        with self.assertRaisesRegex(RuntimeError, "DEFAULT_SUBSCRIPTION_DAYS must be an integer"):
            self.load_config(env)

    def test_project_name_class_default_is_not_overridden_by_app_name_env(self):
        env = BASE_ENV | {"APP_NAME": "Custom App"}

        config = self.load_config(env)

        self.assertEqual(config.settings.PROJECT_NAME, "GapCode AI SaaS")
        self.assertEqual(config.settings.APP_NAME, "GapCode AI SaaS")

    def test_no_boolean_settings_are_currently_parsed(self):
        env = BASE_ENV | {"DEBUG": "true"}

        config = self.load_config(env)

        self.assertFalse(hasattr(config.settings, "DEBUG"))


if __name__ == "__main__":
    unittest.main()
