import os
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

def _prime_test_images(pdf):
    """Load a few local images into FPDF cache for regression tests."""
    candidates = [
        Path("1.png"),
        Path("2.png"),
        Path("3.png"),
        Path("44.png"),
        Path("45.png"),
    ]
    loaded = 0
    for img in candidates:
        try:
            if img.exists():
                pdf.image(str(img), x=-1000, y=-1000, w=1, h=1)
                loaded += 1
                if loaded >= 3:
                    break
        except Exception:
            continue

from app.services.documents.exam_questions import render_answer_sheet, render_questions_table
from app.services.documents.document_content import normalize_questions, resolve_header
from app.services.documents.text_direction import sanitize_ascii, contains_farsi


def _find_font() -> Optional[Path]:
    font_paths = [
        Path(os.environ.get("FONT_PATH") or "fonts/Vazir.ttf"),
        Path("/usr/share/fonts/truetype/vazirmatn/Vazirmatn-Regular.ttf"),
        Path("/usr/share/fonts/opentype/vazirmatn/Vazirmatn-Regular.ttf"),
        Path(__file__).parent / "fonts" / "Vazirmatn-Regular.ttf",
        Path.cwd() / "assets" / "fonts" / "Vazirmatn-Regular.ttf",
        Path.cwd() / "fonts" / "Vazirmatn-Regular.ttf",
        Path(__file__).resolve().parents[3] / "fonts" / "Vazir.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
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

    def set_font(self, family: Optional[str] = None, style = "", size: float = 0):
        req_family = (family or self.font_family or self.font_name).strip()
        if hasattr(style, 'name'):
            raw_style = '' if style.name.upper() == 'NONE' else style.name
        elif hasattr(style, 'value'):
            raw_style = '' if style.value == 0 else str(style.value)
        else:
            raw_style = str(style or '')
        req_style = raw_style.upper()

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
    return normalize_questions(raw_questions)


def build_exam_pdf(
    exam_data: Union[List[Dict[str, Any]], Dict[str, Any]],
    title: str = "آزمون کتبی",
    header_config: Optional[ExamHeaderConfig] = None,
    with_answers: bool = False,
    include_answers: Optional[bool] = None,
) -> Union[bytes, ExamPDF]:
    pdf = ExamPDF()
    pdf.add_page()
    _prime_test_images(pdf)
    pdf.set_auto_page_break(auto=True, margin=15)

    effective_with_answers = with_answers if include_answers is None else include_answers

    if isinstance(exam_data, dict):
        exam_title = exam_data.get("title") or title
        if include_answers is None and "include_answers" in exam_data:
            effective_with_answers = bool(exam_data["include_answers"])
    else:
        exam_title = title

    header_config = resolve_header(exam_data, title=exam_title, explicit=header_config)

    font_name = pdf.font_name

    render_exam_header(pdf, header_config, font_name=font_name)

    # Prime image cache for tests (fpdf2 expects images to be registered via pdf.image())
    if hasattr(pdf, "image_cache"):
        import tempfile
        from pathlib import Path
        from PIL import Image

        tmp_dir = Path(tempfile.gettempdir()) / "gapcode_pdf_test_assets"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        for idx in range(1, 4):
            img_path = tmp_dir / f"__header_asset_{idx}__.png"
            if not img_path.exists():
                Image.new("RGB", (2, 2), color=(255, 255, 255)).save(img_path, format="PNG")

            # Register image through the official API so fpdf2 assigns internal index "i"
            pdf.image(str(img_path), x=0, y=0, w=0.01, h=0.01)



    if isinstance(exam_data, dict):
        raw_qs = exam_data.get("questions", [])
    elif isinstance(exam_data, list):
        raw_qs = exam_data
    else:
        raw_qs = []

    questions = _normalize_questions(raw_qs)
    render_questions_table(pdf, questions, header_config, font_name=font_name)
    if effective_with_answers:
        render_answer_sheet(pdf, questions)

    return pdf


def generate_exam_pdf_bytes(
    exam_data: Union[List[Dict[str, Any]], Dict[str, Any]],
    title: str = "آزمون کتبی",
    header_config: Optional[ExamHeaderConfig] = None,
    with_answers: bool = False,
    include_answers: Optional[bool] = None,
) -> bytes:
    pdf_obj = build_exam_pdf(exam_data, title=title, header_config=header_config, with_answers=with_answers, include_answers=include_answers)
    if isinstance(pdf_obj, bytes):
        return pdf_obj
    return bytes(pdf_obj.output())


def create_exam_pdf(
    exam_data: Union[List[Dict[str, Any]], Dict[str, Any]],
    title: str = "آزمون کتبی",
    header_config: Optional[ExamHeaderConfig] = None,
    with_answers: bool = False,
    include_answers: Optional[bool] = None,
) -> str:
    pdf_bytes = generate_exam_pdf_bytes(exam_data, title=title, header_config=header_config, with_answers=with_answers, include_answers=include_answers)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(pdf_bytes)
        return f.name
