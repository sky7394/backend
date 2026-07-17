from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt, JWTError

from app.core.config import settings


def is_password_hash(value: str) -> bool:
    if not value:
        return False
    return value.startswith(("$2a$", "$2b$", "$2y$")) and len(value) == 60


def get_password_hash(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")

    if is_password_hash(password):
        return password

    if len(password.encode("utf-8")) > 72:
        raise ValueError("password cannot be longer than 72 bytes, truncate manually if necessary (e.g. my_password[:72])")

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def hash_password(password: str) -> str:
    return get_password_hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False

    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    subject: str,
    expires_delta: Optional[int] = None,
) -> str:
    if expires_delta is None:
        expires_delta = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_delta)
    payload = {"sub": subject, "exp": expire}

    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return decoded
    except JWTError:
        return None
