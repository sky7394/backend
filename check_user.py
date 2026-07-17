import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import User

email_to_fix = "teacher@example.com"
new_password_plain = "123456"

try:
    db = SessionLocal()
    user = db.query(User).filter(User.email == email_to_fix).first()

    if not user:
        print(f"[❌] User with email {email_to_fix} not found!")
    else:
        print(f"[?] Current password in DB: {user.hashed_password}")
        new_hash = get_password_hash(new_password_plain)
        user.hashed_password = new_hash
        db.commit()

        print(f"[✅] Password updated successfully for {email_to_fix}")
        print(f"[✅] New Hash: {new_hash}")

except Exception as e:
    print(f"[🚨] Error: {e}")
finally:
    if "db" in locals():
        db.close()
