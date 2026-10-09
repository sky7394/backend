import re
from typing import Optional

try:
    import arabic_reshaper
except ImportError:
    arabic_reshaper = None

try:
    from bidi.algorithm import get_display
except ImportError:
    get_display = None


def contains_farsi(text: Optional[str]) -> bool:
    if not text:
        return False
    return bool(re.search(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]", str(text)))


def contains_persian_arabic(text: Optional[str]) -> bool:
    return contains_farsi(text)


def sanitize_ascii(text: Optional[str]) -> str:
    if not text:
        return ""
    clean = re.sub(r"[^\x00-\x7F]+", "", str(text)).strip()
    return clean if clean else "Text"


def fix_text_bidi(text: Optional[str], unicode_font: Optional[bool] = None) -> str:
    if not text:
        return ""
    s_text = str(text)

    # اگر مستقیماً مشخص شده یونیکد نیست یا هیچ کاراکتر فارسی ندارد
    if unicode_font is False:
        return sanitize_ascii(s_text)

    if not contains_farsi(s_text):
        return s_text

    # در صورتی که کتابخانه‌های bidi و reshaper موجود باشند
    if arabic_reshaper and get_display:
        try:
            reshaped = arabic_reshaper.reshape(s_text)
            return get_display(reshaped)
        except Exception:
            return s_text
    return s_text
