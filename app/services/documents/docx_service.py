import io
import logging
from typing import Any, Dict

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_TABLE_DIRECTION, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

from app.services.documents.document_content import (
    header_rows, normalize_questions, question_body_and_options, resolve_header,
)
from app.services.documents.math_rendering import render_math, split_math

logger = logging.getLogger(__name__)

# فونت رسمی استاندارد مدارس ایران
DEFAULT_FONT_NAME = "B Nazanin"

# اگر متن سؤال و گزینه‌ها در مجموع از این کوتاه‌تر بود، جدول سؤال قابل شکستن بین دو صفحه نیست
_COMPACT_LIMIT = 1000
# گزینه‌های کوتاه‌تر از این حد در دو ستون قرار می‌گیرند؛ بلندها تک‌ستونی می‌مانند
_OPTION_COLUMN_MAX_LEN = 60


def _set_run_font(run, font_name: str = DEFAULT_FONT_NAME, size_pt: float = None, bold: bool = False, color_rgb: RGBColor = None) -> None:
    """تنظیم فونت فارسی استاندارد (Complex Script و Latin) برای یک Run."""
    run.font.name = font_name
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    if bold:
        run.bold = True
    if color_rgb:
        run.font.color.rgb = color_rgb

    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:cs"), font_name)


def _set_paragraph_rtl(paragraph) -> None:
    """تنظیم جهت پاراگراف به راست‌به‌چپ (RTL) و فاصله خطوط مناسب."""
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph.paragraph_format.line_spacing = 1.15
    pPr = paragraph._element.get_or_add_pPr()
    bidi = pPr.find(qn("w:bidi"))
    if bidi is None:
        bidi = OxmlElement("w:bidi")
        pPr.append(bidi)
    bidi.set(qn("w:val"), "1")


def _set_cell_rtl(cell) -> None:
    """تنظیم جهت سلول جدول به راست‌به‌چپ با پدینگ استاندارد."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = tcPr.find(qn("w:tcMar"))
    if tcMar is None:
        tcMar = OxmlElement("w:tcMar")
        tcPr.append(tcMar)
    for side in ("top", "bottom"):
        margin = tcMar.find(qn(f"w:{side}"))
        if margin is None:
            margin = OxmlElement(f"w:{side}")
            tcMar.append(margin)
        margin.set(qn("w:w"), "120")
        margin.set(qn("w:type"), "dxa")
    for side in ("left", "right"):
        margin = tcMar.find(qn(f"w:{side}"))
        if margin is None:
            margin = OxmlElement(f"w:{side}")
            tcMar.append(margin)
        margin.set(qn("w:w"), "140")
        margin.set(qn("w:type"), "dxa")
    for paragraph in cell.paragraphs:
        _set_paragraph_rtl(paragraph)


def _add_content(paragraph, text, *, math=False, bold=False, size_pt=11):
    _set_paragraph_rtl(paragraph)
    segments = [("math", text)] if math else split_math(text)
    for kind, value in segments:
        run = paragraph.add_run()
        if kind == "math":
            image = render_math(value)
            width, height = image.fitted(125)
            run.add_picture(io.BytesIO(image.data), width=Mm(width), height=Mm(height))
            run.font.rtl = False
            run._r.xpath(".//wp:docPr")[0].set("descr", value)
        else:
            run.text = value
            _set_run_font(run, font_name=DEFAULT_FONT_NAME, size_pt=size_pt, bold=bold)



def _clear_table_borders(table):
    tblPr = table._tbl.tblPr
    tblBorders = tblPr.first_child_found_in("w:tblBorders")
    if tblBorders is None:
        tblBorders = OxmlElement('w:tblBorders')
        tblPr.append(tblBorders)
    for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'none')
        tblBorders.append(border)


def _rtl_table(doc, labels, widths):
    table = doc.add_table(rows=1, cols=len(labels))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.table_direction = WD_TABLE_DIRECTION.RTL
    table.autofit = False
    for column, width in zip(table.columns, widths):
        column.width = Mm(width)
    row = table.rows[0]
    row._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for cell, label, width in zip(row.cells, labels, widths):
        cell.width = Mm(width)
        _set_cell_rtl(cell)
        _add_content(cell.paragraphs[0], label, bold=True, size_pt=11)
    return table


def _add_options_grid(body_cell, options, body_width_mm: float) -> None:
    """رندر گزینه‌ها داخل سلول بدنه؛ دو ستونه اگر کوتاه باشند، وگرنه تک‌ستونی."""
    two_columns = (
        len(options) in (2, 4)
        and all(len(text) <= _OPTION_COLUMN_MAX_LEN for _, text in options)
    )
    if two_columns:
        columns, rows = 2, len(options) // 2
    else:
        columns, rows = 1, len(options)
    grid = body_cell.add_table(rows=rows, cols=columns)
    _clear_table_borders(grid)
    grid.alignment = WD_TABLE_ALIGNMENT.CENTER
    grid.table_direction = WD_TABLE_DIRECTION.RTL
    grid.autofit = False
    column_width = body_width_mm / columns
    for column in grid.columns:
        column.width = Mm(column_width)
    placed = 0
    for row in grid.rows:
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for cell in row.cells:
            cell.width = Mm(column_width)
            _set_cell_rtl(cell)
            if placed < len(options):
                label, text = options[placed]
                placed += 1
                paragraph = cell.paragraphs[0]
                _add_content(paragraph, f"{label}) ", bold=True, size_pt=11)
                segments = split_math(text)
                for kind, value in segments:
                    if kind == "math":
                        _add_content(paragraph, value, math=True, size_pt=11)
                    else:
                        _add_content(paragraph, value, size_pt=11)
            else:
                # سلول خالی در حالت تعداد فرد؛ کادر حفظ شود
                _add_content(cell.paragraphs[0], "", size_pt=11)


def build_exam_docx(exam_data: Dict[str, Any], include_answers: bool = False) -> Document:
    """Build an A4 exam with logical RTL columns, B Nazanin font, and 2-column options."""
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = DEFAULT_FONT_NAME
    normal.font.size = Pt(11)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.15
    normal_rpr = normal.element.get_or_add_rPr()
    fonts = normal_rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        normal_rpr.append(fonts)
    for attribute in ("ascii", "hAnsi", "cs"):
        fonts.set(qn(f"w:{attribute}"), DEFAULT_FONT_NAME)
    for section in doc.sections:
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.top_margin = section.bottom_margin = Mm(15)
        section.left_margin = section.right_margin = Mm(15)

    config = resolve_header(exam_data)
    title = doc.add_paragraph()
    _add_content(title, exam_data.get("title") or config.course_name, bold=True, size_pt=13)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.keep_with_next = True
    title.paragraph_format.space_after = Pt(6)

    header = doc.add_table(rows=0, cols=2)
    header.style = "Table Grid"
    header.table_direction = WD_TABLE_DIRECTION.RTL
    header.alignment = WD_TABLE_ALIGNMENT.CENTER
    for right, left in header_rows(config):
        row = header.add_row()
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for cell, text in zip(row.cells, (right, left)):
            _set_cell_rtl(cell)
            paragraph = cell.paragraphs[0]
            _add_content(paragraph, text, size_pt=10)
            paragraph.paragraph_format.keep_with_next = True
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    questions = normalize_questions(exam_data.get("questions") or [])
    widths = (14, 144, 22)
    table = _rtl_table(doc, ("ردیف", "شرح سؤال", "بارم"), widths)
    for question in questions:
        row = table.add_row()
        if len(question.question_text) + sum(map(len, question.options)) < _COMPACT_LIMIT:
            row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for cell, width in zip(row.cells, widths):
            cell.width = Mm(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            _set_cell_rtl(cell)
        number, body, points = row.cells
        _add_content(number.paragraphs[0], str(question.number), size_pt=11)
        if question.points is not None:
            _add_content(points.paragraphs[0], f"[{question.points:g} نمره]", size_pt=10)
        body_parts, options = question_body_and_options(question)
        if question.section:
            body_parts.insert(0, ("text", question.section))
        for index, (kind, value) in enumerate(body_parts):
            paragraph = body.paragraphs[0] if index == 0 else body.add_paragraph()
            if kind == "line":
                _set_paragraph_rtl(paragraph)
                paragraph.paragraph_format.space_after = Pt(8)
                borders = OxmlElement("w:pBdr")
                bottom = OxmlElement("w:bottom")
                bottom.set(qn("w:val"), "single")
                bottom.set(qn("w:sz"), "2")
                bottom.set(qn("w:color"), "BBBBBB")
                borders.append(bottom)
                paragraph._p.get_or_add_pPr().append(borders)
            else:
                _add_content(paragraph, value, math=kind == "math", size_pt=11)
                borders = OxmlElement("w:pBdr")
                bottom = OxmlElement("w:bottom")
                bottom.set(qn("w:val"), "single")
                bottom.set(qn("w:sz"), "2")
                bottom.set(qn("w:color"), "BBBBBB")
                borders.append(bottom)
                paragraph._p.get_or_add_pPr().append(borders)
        if options:
            _add_options_grid(body, options, body_width_mm=144.0)
        elif not question.options:
            # سؤالات تشریحی بدون گزینه: خطوط پاسخ از body_parts می‌آیند (kind=line)

            pass

    if include_answers and questions:
        doc.add_page_break()
        heading = doc.add_paragraph()
        _add_content(heading, "کلید و پاسخ‌نامه تشریحی آزمون", bold=True, size_pt=13)
        heading.paragraph_format.keep_with_next = True
        heading.paragraph_format.space_after = Pt(8)
        answers = _rtl_table(doc, ("ردیف", "پاسخ صحیح / توضیح"), (14, 166))
        for question in questions:
            row = answers.add_row()
            for cell, width in zip(row.cells, (14, 166)):
                cell.width = Mm(width)
                _set_cell_rtl(cell)
            _add_content(row.cells[0].paragraphs[0], str(question.number), size_pt=11)
            paragraph = row.cells[1].paragraphs[0]
            _add_content(paragraph, f"پاسخ صحیح: {question.answer or 'مشخص نشده'}", bold=True, size_pt=11)
            if question.explanation:
                paragraph.paragraph_format.keep_with_next = True
                _add_content(row.cells[1].add_paragraph(), f"توضیح: {question.explanation}", size_pt=10.5)
    return doc


def generate_exam_docx_bytes(exam_data: Dict[str, Any], include_answers: bool = False) -> bytes:
    """Serialize a Word document in memory."""
    doc = build_exam_docx(exam_data, include_answers=include_answers)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
