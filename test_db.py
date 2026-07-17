import sys
import os

# اضافه کردن مسیر پروژه به sys.path تا ایمپورت‌ها کار کنند
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    from app.core.security import get_password_hash, verify_password
    print("[✅] Imports successful!")
except ImportError as e:
    print(f"[❌] Import failed: {e}")
    sys.exit(1)

# پسورد تستی
test_password = "123456"

print(f"\n--- TESTING PASSWORD FUNCTIONS ---")
print(f"Original Password: {test_password}")

# ۱. ساخت هش با متد پروژه
hashed_pw = get_password_hash(test_password)
print(f"Generated Hash   : {hashed_pw}")

# ۲. تست صحت وریفای با پسورد درست
verify_correct = verify_password(test_password, hashed_pw)
print(f"Verify Correct PW: {verify_correct} (Should be True)")

# ۳. تست صحت وریفای با پسورد غلط
verify_wrong = verify_password("wrongpassword", hashed_pw)
print(f"Verify Wrong PW  : {verify_wrong} (Should be False)")

print(f"----------------------------------\n")

if verify_correct is True and verify_wrong is False:
    print("[🎉] The security functions work perfectly on their own!")
else:
    print("[🚨] Something is wrong with the functions!")
