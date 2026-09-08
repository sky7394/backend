import io
import logging
from typing import Any, Dict

import docx
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

logger = logging.getLogger(__name__)


def _set_paragraph_rtl(paragraph) -> None:
    """تنظیم جهت پاراگراف به راست‌به‌چپ (RTL)."""
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pPr = paragraph._element.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    pPr.append(bidi)


def _set_cell_rtl(cell) -> None:
    """تنظیم جهت سلول جدول به راست‌به‌چپ."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    tcMar.set(qn("w:w"), "100")
    tcMar.set(qn("w:type"), "dxa")
    tcPr.append(tcMar)


def build_exam_docx(exam_data: Dict[str, Any]) -> Document:
    """ساخت سند Word (Document) به صورت Stateless از روی داده‌های آزمون."""
    doc = Document()

    # تنظیم حاشیه‌های صفحه (1 اینچ از هر طرف)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # 1. سربرگ آزمون (جدول مشخصات)
    title = exam_data.get("title", "آزمون آنلاین")
    grade = exam_data.get("grade") or exam_data.get("grade_level", "")
    subject = exam_data.get("subject", "")

    header_table = doc.add_table(rows=2, cols=2)
    header_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header_table.autofit = False

    # سلول‌های سربرگ
    cell_top_right = header_table.cell(0, 1)
    cell_top_left = header_table.cell(0, 0)
    cell_bot_right = header_table.cell(1, 1)
    cell_bot_left = header_table.cell(1, 0)

    p1 = cell_top_right.paragraphs[0]
    p1.text = f"عنوان آزمون: {title}"
    _set_paragraph_rtl(p1)

    p2 = cell_top_left.paragraphs[0]
    p2.text = f"نام و نام خانوادگی: ...................."
    _set_paragraph_rtl(p2)

    p3 = cell_bot_right.paragraphs[0]
    p3.text = f"مقطع: {grade} | درس: {subject}"
    _set_paragraph_rtl(p3)

    p4 = cell_bot_left.paragraphs[0]
    p4.text = f"تاریخ: .................... | زمان: ........ دقیقه"
    _set_paragraph_rtl(p4)

    # خط جداکننده
    divider = doc.add_paragraph()
    _set_paragraph_rtl(divider)
    divider_run = divider.add_run("―" * 55)
    divider_run.font.color.rgb = RGBColor(120, 120, 120)

    # 2. لیست سوالات
    questions = exam_data.get("questions", [])

    for idx, q in enumerate(questions, 1):
        q_text = q.get("question_text") or q.get("text", "")
        p_q = doc.add_paragraph()
        _set_paragraph_rtl(p_q)

        run_num = p_q.add_run(f"سوال {idx}: ")
        run_num.bold = True
        run_num.font.color.rgb = RGBColor(20, 40, 100)

        run_text = p_q.add_run(q_text)
        run_text.font.size = Pt(11)

        options = q.get("options", [])
        if options:
            for opt_idx, opt in enumerate(options, 1):
                p_opt = doc.add_paragraph()
                _set_paragraph_rtl(p_opt)
                p_opt.paragraph_format.right_indent = Inches(0.3)

                opt_labels = ["الف", "ب", "ج", "د"]
                label = opt_labels[opt_idx - 1] if opt_idx <= len(opt_labels) else str(opt_idx)

                opt_text = opt.get("text", opt) if isinstance(opt, dict) else str(opt)
                run_opt = p_opt.add_run(f"{label}) {opt_text}")
                run_opt.font.size = Pt(10.5)

        # فاصله بین سوالات
        doc.add_paragraph()

    return doc


def generate_exam_docx_bytes(exam_data: Dict[str, Any]) -> bytes:
    """تولید بایت‌های فایل Word به صورت در-حافظه (Stateless)."""
    doc = build_exam_docx(exam_data)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
