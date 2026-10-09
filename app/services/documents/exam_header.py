from fpdf import FPDF
from app.services.documents.exam_models import ExamHeaderConfig, ExamLayoutType, ExamHeaderStyle
from app.services.documents.text_direction import fix_text_bidi, sanitize_ascii


def _safe_text(pdf: FPDF, text: str) -> str:
    is_unicode = getattr(pdf, "is_unicode_font", True)
    if not is_unicode or getattr(pdf, "font_family", "").lower() in ["helvetica", "courier", "times"]:
        return sanitize_ascii(text)
    return fix_text_bidi(text)


def _render_official_header(pdf: FPDF, config: ExamHeaderConfig, page_width: float, font_name: str):
    pdf.set_font(font_name, size=10)
    pdf.set_xy(10, 10)
    col_w = (page_width - 20) / 3

    # راست: مشخصات مدرسه و آزمون
    right_lines = [
        f"جمهوری اسلامی ایران",
        f"نام آموزشگاه: {config.school_name}",
        f"پایه و رشته: {config.grade_field or '-'}",
        f"نوبت: {config.exam_term or '-'}"
    ]
    x_r, y_r = 10, 10
    for line in right_lines:
        pdf.set_xy(x_r, y_r)
        pdf.cell(col_w, 5, _safe_text(pdf, line), align="R")
        y_r += 5

    # وسط: عنوان آزمون و نام درس
    pdf.set_font(font_name, style="B", size=12)
    pdf.set_xy(10 + col_w, 12)
    pdf.cell(col_w, 7, _safe_text(pdf, "سؤالات آزمون"), align="C")
    pdf.set_xy(10 + col_w, 20)
    pdf.cell(col_w, 7, _safe_text(pdf, f"درس: {config.course_name}"), align="C")

    # چپ: تاریخ و زمان
    pdf.set_font(font_name, size=10)
    left_lines = [
        f"تاریخ: {config.exam_date or '-'}",
        f"مدت پاسخگویی: {config.exam_duration or '-'}",
        f"نام دبیر: {config.teacher_name or '-'}"
    ]
    x_l, y_l = 10 + 2 * col_w, 10
    for line in left_lines:
        pdf.set_xy(x_l, y_l)
        pdf.cell(col_w, 5, _safe_text(pdf, line), align="L")
        y_l += 5

    pdf.line(10, 35, page_width - 10, 35)
    pdf.set_y(38)


def _render_school_header(pdf: FPDF, config: ExamHeaderConfig, page_width: float, font_name: str):
    pdf.set_font(font_name, style="B", size=14)
    pdf.set_xy(10, 10)
    col_w = page_width - 20
    pdf.cell(col_w, 6, _safe_text(pdf, config.school_name), align="C")

    pdf.set_font(font_name, size=11)
    pdf.ln(7)
    pdf.cell(col_w, 6, _safe_text(pdf, f"آزمون درس: {config.course_name}"), align="C")

    pdf.ln(7)
    pdf.set_font(font_name, size=9)
    sub_col = col_w / 3
    pdf.cell(sub_col, 5, _safe_text(pdf, f"نوبت: {config.exam_term or '-'}"), align="C")
    pdf.cell(sub_col, 5, _safe_text(pdf, f"تاریخ: {config.exam_date or '-'}"), align="C")
    pdf.cell(sub_col, 5, _safe_text(pdf, f"مدت: {config.exam_duration or '-'}"), align="C")

    pdf.ln(7)
    pdf.line(10, pdf.get_y(), page_width - 10, pdf.get_y())
    pdf.ln(3)


def render_exam_header(pdf: FPDF, config: ExamHeaderConfig, font_name: str = "Vazirmatn"):
    page_width = pdf.w
    # در صورتی که فونت فعال هلوتیکا باشد
    actual_font = getattr(pdf, "font_name", font_name)
    if not getattr(pdf, "is_unicode_font", True):
        actual_font = "Helvetica"

    if config.header_style == ExamHeaderStyle.OFFICIAL:
        _render_official_header(pdf, config, page_width, actual_font)
    else:
        _render_school_header(pdf, config, page_width, actual_font)
