from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:  # Optional text-shaping dependencies.
    arabic_reshaper = None
    get_display = None


def _find_font() -> Path | None:
    path = Path(__file__).resolve().parents[2] / "fonts" / "Vazir.ttf"
    return path if path.is_file() else None


def _shape_text(value: Any, unicode_font: bool) -> str:
    text = "" if value is None else str(value)
    if not unicode_font:
        return text.encode("ascii", errors="ignore").decode("ascii") or "Text"
    if arabic_reshaper is not None and get_display is not None:
        return get_display(arabic_reshaper.reshape(text))
    return text


class ExamPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=20)
        font = _find_font()
        if font is not None:
            self.add_font("Vazir", fname=str(font))
            self.font_name = "Vazir"
            self.is_unicode_font = True
        else:
            self.font_name = "Helvetica"
            self.is_unicode_font = False
        self.alias_nb_pages()

    @property
    def content_width(self) -> float:
        return max(1.0, self.w - self.l_margin - self.r_margin)

    def header(self) -> None:
        self.set_font(self.font_name, size=10)
        text = _shape_text("GapCode - سامانه آزمون", self.is_unicode_font)
        self.cell(self.content_width, 8, text, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font(self.font_name, size=8)
        self.cell(self.content_width, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def _write(pdf: ExamPDF, value: Any, height: float, size: int) -> None:
    pdf.set_font(pdf.font_name, size=size)
    pdf.multi_cell(
        w=pdf.content_width,
        h=height,
        text=_shape_text(value, pdf.is_unicode_font),
        align="R" if pdf.is_unicode_font else "L",
        wrapmode="CHAR",
    )


def build_exam_pdf(
    questions: list[dict[str, Any]],
    title: str = "آزمون",
    with_answers: bool = False,
) -> ExamPDF:
    pdf = ExamPDF()
    pdf.add_page()
    _write(pdf, title, 10, 16)
    pdf.ln(5)
    for index, item in enumerate(questions, 1):
        question = item.get("question", item.get("text", ""))
        _write(pdf, f"{index}. {question}", 8, 12)
        for option_index, option in enumerate(item.get("options") or [], 1):
            _write(pdf, f"{option_index}) {option}", 6, 10)
        if with_answers and item.get("answer") is not None:
            _write(pdf, f"Answer: {item['answer']}", 6, 10)
        pdf.ln(4)
    return pdf


def generate_exam_pdf_bytes(
    questions: list[dict[str, Any]],
    title: str = "آزمون",
    with_answers: bool = False,
) -> bytes:
    output = build_exam_pdf(questions, title, with_answers).output()
    return output if isinstance(output, bytes) else bytes(output)


def create_exam_pdf(
    questions: list[dict[str, Any]],
    title: str = "آزمون",
    with_answers: bool = False,
) -> str:
    descriptor, path = tempfile.mkstemp(prefix="gapcode_exam_", suffix=".pdf")
    os.close(descriptor)
    Path(path).write_bytes(generate_exam_pdf_bytes(questions, title, with_answers))
    return path
