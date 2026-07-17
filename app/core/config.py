import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "GapCode AI SaaS"
    ALGORITHM: str = "HS256"

    def __init__(self) -> None:
        self.DATABASE_URL = self._get_required_env("DATABASE_URL")
        self.JWT_SECRET = self._get_required_env("JWT_SECRET", fallback="SECRET_KEY")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = self._get_int_env(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            default=43200,
        )

        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "llama-3.3-70b-versatile")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.GEMINI_BASE_URL = os.getenv(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.SMS_PROVIDER = os.getenv("SMS_PROVIDER", "mock")
        self.SMS_API_KEY = os.getenv("SMS_API_KEY", "")
        self.SMS_SENDER = os.getenv("SMS_SENDER", "")
        self.OTP_EXPIRE_MINUTES = self._get_int_env("OTP_EXPIRE_MINUTES", default=2)
        self.PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "zarinpal")
        self.ZARINPAL_MERCHANT_ID = os.getenv("ZARINPAL_MERCHANT_ID", "")
        self.PAYMENT_CALLBACK_URL = os.getenv("PAYMENT_CALLBACK_URL", "")
        self.DEFAULT_SUBSCRIPTION_DAYS = self._get_int_env(
            "DEFAULT_SUBSCRIPTION_DAYS",
            default=30,
        )
        self.GENERATED_PDF_DIR = os.getenv("GENERATED_PDF_DIR", "generated_pdfs")
        self.FONT_PATH = os.getenv("FONT_PATH", "fonts/Vazir.ttf")

    @property
    def APP_NAME(self) -> str:
        return self.PROJECT_NAME

    @property
    def SECRET_KEY(self) -> str:
        return self.JWT_SECRET

    @staticmethod
    def _get_required_env(name: str, fallback: str | None = None) -> str:
        value = os.getenv(name)
        if value:
            return value

        if fallback:
            fallback_value = os.getenv(fallback)
            if fallback_value:
                return fallback_value

        fallback_message = f" or {fallback}" if fallback else ""
        raise RuntimeError(f"Missing required environment variable: {name}{fallback_message}")

    @staticmethod
    def _get_int_env(name: str, default: int) -> int:
        value = os.getenv(name)
        if value is None or value == "":
            return default

        try:
            return int(value)
        except ValueError as exc:
            raise RuntimeError(f"Environment variable {name} must be an integer") from exc


settings = Settings()
