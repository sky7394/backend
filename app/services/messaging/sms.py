from app.core.config import settings


def send_sms(mobile: str, message: str):
    if settings.SMS_PROVIDER == "mock":
        print(f"[MOCK SMS] To: {mobile} | Message: {message}")
        return True

    # اینجا بعداً اتصال واقعی به سرویس پیامک ایران اضافه می‌شود
    return True
