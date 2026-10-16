from fpdf import FPDF

from app.services.documents.document_content import header_rows
from app.services.documents.exam_models import ExamHeaderConfig, ExamHeaderStyle
from app.services.documents.pdf_layout import safe_text, text_lines


def render_exam_header(pdf: FPDF, config: ExamHeaderConfig, font_name: str = "Vazirmatn"):
    actual_font = getattr(pdf, "font_name", font_name)
    pdf.set_font(actual_font, style="B", size=12)
    title = "سؤالات آزمون" if config.header_style == ExamHeaderStyle.OFFICIAL else config.school_name
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 7, safe_text(pdf, title), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(actual_font, size=9)
    width = pdf.epw / 2
    for right, left in header_rows(config):
        cells = [text_lines(pdf, value, width - 4) if value else [] for value in (left, right)]
        height = max(8, max(len(lines) for lines in cells) * 5.5 + 3)
        if pdf.get_y() + height > pdf.h - pdf.b_margin:
            pdf.add_page()
        y = pdf.get_y()
        for index, lines in enumerate(cells):
            x = pdf.l_margin + index * width
            pdf.rect(x, y, width, height)
            for line_number, line in enumerate(lines):
                pdf.set_xy(x + 2, y + 1.5 + line_number * 5.5)
                pdf.cell(width - 4, 5.5, safe_text(pdf, line), align="R")
        pdf.set_xy(pdf.l_margin, y + height)
    pdf.ln(4)
