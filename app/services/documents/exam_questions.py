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

    pdf.set_font(actual_font, size=10)
    page_width = pdf.w - pdf.l_margin - pdf.r_margin

    col_no = 12.0
    col_pts = 16.0
    col_q = page_width - col_no - col_pts

    # Table Header
    pdf.set_font(actual_font, style="B", size=10)
    pdf.cell(col_no, 8, _safe_text(pdf, "ردیف"), border=1, align="C")
    pdf.cell(col_q, 8, _safe_text(pdf, "شرح سؤال"), border=1, align="C")
    pdf.cell(col_pts, 8, _safe_text(pdf, "بارم"), border=1, align="C")
    pdf.ln()

    pdf.set_font(actual_font, size=9)
    for q in questions:
        q_text = f"{q.question_text}"
        if q.options:
            opts_str = "  |  ".join(f"({i+1}) {opt}" for i, opt in enumerate(q.options))
            q_text += f"\n{opts_str}"
        if q.answer:
            q_text += f"\nپاسخ: {q.answer}"

        safe_q = _safe_text(pdf, q_text)
        pts_str = str(q.points) if q.points is not None else ""
        
        # محاسبه ارتفاع تقریبی
        line_count = max(1, safe_q.count("\n") + 1)
        row_height = max(8.0, line_count * 5.0)

        x_start = pdf.get_x()
        y_start = pdf.get_y()

        pdf.cell(col_no, row_height, str(q.number), border=1, align="C")
        pdf.set_xy(x_start + col_no, y_start)
        pdf.multi_cell(col_q, 5, safe_q, border=1, align="R")
        end_y = pdf.get_y()
        actual_h = max(row_height, end_y - y_start)

        pdf.set_xy(x_start + col_no + col_q, y_start)
        pdf.cell(col_pts, actual_h, pts_str, border=1, align="C")
        pdf.set_xy(x_start, max(end_y, y_start + actual_h))
