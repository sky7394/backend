from typing import List
from fpdf import FPDF
from app.services.documents.exam_models import ExamHeaderConfig, NormalizedQuestion
from app.services.documents.text_direction import fix_text_bidi, sanitize_ascii


def _safe_text(pdf: FPDF, text: str) -> str:
    is_unicode = getattr(pdf, "is_unicode_font", True)
    if not is_unicode or getattr(pdf, "font_family", "").lower() in ["helvetica", "courier", "times"]:
        return sanitize_ascii(text)
    return fix_text_bidi(text)


def render_questions_table(
    pdf: FPDF,
    questions: List[NormalizedQuestion],
    config: ExamHeaderConfig,
    font_name: str = "Vazirmatn"
):
    actual_font = getattr(pdf, "font_name", font_name)
    if not getattr(pdf, "is_unicode_font", True):
        actual_font = "Helvetica"

    page_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_no = 12.0
    col_pts = 16.0
    col_q = page_width - col_no - col_pts

    def draw_header():
        pdf.set_font(actual_font, style="B", size=10)
        pdf.cell(col_pts, 8, _safe_text(pdf, "بارم"), border=1, align="C")
        pdf.cell(col_q, 8, _safe_text(pdf, "شرح سؤال"), border=1, align="C")
        pdf.cell(col_no, 8, _safe_text(pdf, "ردیف"), border=1, align="C")
        pdf.ln()
        pdf.set_font(actual_font, size=9)

    # اتصال هدر به رویداد ساخت صفحه جدید در FPDF
    original_header = getattr(pdf, "header", None)
    def auto_table_header():
        if original_header:
            original_header()
        draw_header()
    pdf.header = auto_table_header

    draw_header()

    for q in questions:
        q_text = f"{q.question_text}"
        if q.options:
            opts_str = "  |  ".join(f"({i+1}) {opt}" for i, opt in enumerate(q.options))
            q_text += f"\n{opts_str}"
        if q.answer:
            q_text += f"\nپاسخ: {q.answer}"

        safe_q = _safe_text(pdf, q_text)
        pts_str = str(q.points) if q.points is not None else ""

        # رندر ردیف به نحوی که در شکست‌های چند صفحه‌ای هدر در بالای هر صفحه قرار گیرد
        y_start = pdf.get_y()
        x_start = pdf.l_margin

        # سلول بارم (سمت چپ)
        pdf.cell(col_pts, 8, pts_str, border=1, align="C")

        # شرح سؤال (وسط)
        pdf.set_xy(x_start + col_pts, y_start)
        pdf.multi_cell(col_q, 6, safe_q, border=1, align="R")
        end_y = pdf.get_y()

        # ردیف (سمت راست فیزیکی در RTL)
        actual_h = max(8.0, end_y - y_start)
        pdf.set_xy(x_start + col_pts + col_q, y_start)
        pdf.cell(col_no, actual_h, str(q.number), border=1, align="C")
        pdf.set_xy(x_start, end_y)

    # پاکسازی رویداد هدر پس از اتمام جدول
    pdf.header = original_header or (lambda: None)


def render_answer_sheet(pdf: FPDF, questions: List[NormalizedQuestion], font_name: str = "Vazirmatn") -> None:
    actual_font = getattr(pdf, "font_name", font_name)
    if not getattr(pdf, "is_unicode_font", True):
        actual_font = "Helvetica"

    # غیرفعال کردن هدر جدول در صفحه پاسخنامه
    pdf.header = lambda: None
    pdf.add_page()
    pdf.set_font(actual_font, style="B", size=12)

    from fpdf.enums import XPos, YPos
    pdf.cell(
        pdf.epw,
        10,
        _safe_text(pdf, "ANSWER_SECRET - کلید و پاسخ‌نامه تشریحی آزمون"),
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(5)

    pdf.set_font(actual_font, size=10)
    for q in questions:
        ans_text = f"سؤال {q.number}: {q.answer or 'بدون پاسخ ثبت‌شده'}"
        pdf.cell(
            pdf.epw,
            8,
            _safe_text(pdf, ans_text),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
