import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from fpdf import FPDF

try:
    import arabic_reshaper
except ImportError:
    arabic_reshaper = None

try:
    from bidi.algorithm import get_display
except ImportError:
    get_display = None

from app.services.documents.exam_header import render_exam_header
from app.services.documents.exam_models import ExamHeaderConfig, NormalizedQuestion
from app.services.documents.exam_questions import render_questions_table
from app.services.documents.text_direction import fix_text_bidi, sanitize_ascii, contains_farsi


def _find_font() -> Optional[Path]:
    font_paths = [
        Path("/usr/share/fonts/truetype/vazirmatn/Vazirmatn-Regular.ttf"),
        Path("/usr/share/fonts/opentype/vazirmatn/Vazirmatn-Regular.ttf"),
        Path(__file__).parent / "fonts" / "Vazirmatn-Regular.ttf",
        Path.cwd() / "assets" / "fonts" / "Vazirmatn-Regular.ttf",
        Path.cwd() / "fonts" / "Vazirmatn-Regular.ttf",
    ]
    for p in font_paths:
        if p.is_file():
            return p
    return None


def _shape_text(text: Optional[str], unicode_font: bool = True) -> str:
    if not text:
        return ""
    if not unicode_font:
        return sanitize_ascii(text)
    if not contains_farsi(text):
        return str(text)
    if arabic_reshaper and get_display:
        try:
            return get_display(arabic_reshaper.reshape(str(text)))
        except Exception:
            return str(text)
    return str(text)


class ExamPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_unicode_font = False
        self.font_name = "Helvetica"
        self._setup_fonts()

    def _setup_fonts(self):
        font_path = _find_font()
        if font_path and font_path.is_file():
            try:
                self.add_font("Vazirmatn", "", str(font_path))
                self.add_font("Vazirmatn", "B", str(font_path))
                self.is_unicode_font = True
                self.font_name = "Vazirmatn"
            except Exception:
                self.is_unicode_font = False
                self.font_name = "Helvetica"
        else:
            self.is_unicode_font = False
            self.font_name = "Helvetica"

    def set_font(self, family: Optional[str] = None, style: str = "", size: float = 0):
        req_family = (family or self.font_family or self.font_name).strip()
        req_style = style.upper()

        if self.is_unicode_font and req_family.lower() == "vazirmatn":
            fontkey = f"vazirmatn{req_style}"
            if fontkey not in self.fonts:
                req_style = ""
            super().set_font("Vazirmatn", style=req_style, size=size)
        elif not self.is_unicode_font:
            super().set_font("Helvetica", style=req_style, size=size)
        else:
            try:
                super().set_font(family=family, style=style, size=size)
            except Exception:
                super().set_font("Helvetica", style=style, size=size)


def _normalize_questions(raw_questions: List[Any]) -> List[NormalizedQuestion]:
    norm_list = []
    for idx, q in enumerate(raw_questions, start=1):
        if isinstance(q, NormalizedQuestion):
            norm_list.append(q)
        elif isinstance(q, dict):
            norm_list.append(
                NormalizedQuestion(
                    number=idx,
                    question_text=q.get("question") or q.get("question_text", ""),
                    options=q.get("options", []),
                    answer=q.get("answer"),
                    points=q.get("points"),
                    section=q.get("section"),
                    formula=q.get("formula"),
                )
            )
        else:
            norm_list.append(
                NormalizedQuestion(
                    number=idx,
                    question_text=getattr(q, "question_text", getattr(q, "question", str(q))),
                    options=getattr(q, "options", []),
                    answer=getattr(q, "answer", None),
                    points=getattr(q, "points", None),
                    section=getattr(q, "section", None),
                    formula=getattr(q, "formula", None),
                )
            )
    return norm_list


def build_exam_pdf(
    exam_data: Union[List[Dict[str, Any]], Dict[str, Any]],
    title: str = "آزمون کتبی",
    header_config: Optional[ExamHeaderConfig] = None,
    with_answers: bool = False,
) -> Union[bytes, ExamPDF]:
    pdf = ExamPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    if header_config is None:
        header_config = ExamHeaderConfig(course_name=title)

    font_name = pdf.font_name

    try:
        render_exam_header(pdf, header_config, font_name=font_name)
    except TypeError:
        render_exam_header(pdf, header_config)

    if isinstance(exam_data, dict):
        raw_qs = exam_data.get("questions", [])
    elif isinstance(exam_data, list):
        raw_qs = exam_data
    else:
        raw_qs = []

    questions = _normalize_questions(raw_qs)
    if not with_answers:
        for q in questions:
            q.answer = None

    try:
        render_questions_table(pdf, questions, header_config, font_name=font_name)
    except TypeError:
        render_questions_table(pdf, questions, header_config)

    return pdf


def generate_exam_pdf_bytes(
    exam_data: Union[List[Dict[str, Any]], Dict[str, Any]],
    title: str = "آزمون کتبی",
    header_config: Optional[ExamHeaderConfig] = None,
    with_answers: bool = False,
) -> bytes:
    pdf_obj = build_exam_pdf(exam_data, title=title, header_config=header_config, with_answers=with_answers)
    if isinstance(pdf_obj, bytes):
        return pdf_obj
    return bytes(pdf_obj.output())


def create_exam_pdf(
    exam_data: Union[List[Dict[str, Any]], Dict[str, Any]],
    title: str = "آزمون کتبی",
    header_config: Optional[ExamHeaderConfig] = None,
    with_answers: bool = False,
) -> str:
    pdf_bytes = generate_exam_pdf_bytes(exam_data, title=title, header_config=header_config, with_answers=with_answers)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(pdf_bytes)
        return f.name
