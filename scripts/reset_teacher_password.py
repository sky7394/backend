import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import User


TEACHER_EMAIL = "teacher@example.com"
TEACHER_PASSWORD = "123456"


def main() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEACHER_EMAIL).first()
        if user is None:
            raise RuntimeError(f"User not found: {TEACHER_EMAIL}")

        user.hashed_password = get_password_hash(TEACHER_PASSWORD)
        db.commit()
        print(f"Password reset successfully for {TEACHER_EMAIL}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
