import importlib
import sys
import types
from unittest.mock import patch

import app.services.documents.pdf_service as pdf_service


def test_find_font_missing():
    """When Vazir.ttf does not exist, _find_font returns None."""
    with patch(
        "app.services.documents.pdf_service.Path.is_file",
        return_value=False,
    ):
        assert pdf_service._find_font() is None


def test_exam_pdf_no_font():
    """ExamPDF falls back to Helvetica when no Unicode font is available."""
    with patch(
        "app.services.documents.pdf_service._find_font",
        return_value=None,
    ):
        pdf = pdf_service.ExamPDF()

        assert pdf.font_name == "Helvetica"
        assert pdf.is_unicode_font is False

        # FPDF invokes header-related page initialization here.
        pdf.add_page()


def test_shape_text_ascii():
    """Non-Unicode mode removes non-ASCII characters and applies fallback text."""
    assert pdf_service._shape_text("سلام", unicode_font=False) == "Text"


def test_shape_text_without_optional_dependencies():
    """Unicode mode returns the original text when shaping dependencies are absent."""
    with (
        patch.object(pdf_service, "arabic_reshaper", None),
        patch.object(pdf_service, "get_display", None),
    ):
        assert pdf_service._shape_text("سلام", unicode_font=True) == "سلام"


def test_optional_dependencies_import_path():
    """
    Cover the successful `from bidi.algorithm import get_display` path.

    Fake modules keep this test independent of whether the optional packages
    are installed in the test environment.
    """
    fake_reshaper = types.ModuleType("arabic_reshaper")
    fake_reshaper.reshape = lambda value: value

    fake_bidi = types.ModuleType("bidi")
    fake_bidi.__path__ = []

    fake_algorithm = types.ModuleType("bidi.algorithm")
    fake_algorithm.get_display = lambda value: value

    fake_bidi.algorithm = fake_algorithm

    fake_modules = {
        "arabic_reshaper": fake_reshaper,
        "bidi": fake_bidi,
        "bidi.algorithm": fake_algorithm,
    }

    try:
        with patch.dict(sys.modules, fake_modules):
            importlib.reload(pdf_service)

            assert pdf_service.arabic_reshaper is fake_reshaper
            assert pdf_service.get_display is fake_algorithm.get_display
            assert pdf_service._shape_text("سلام", unicode_font=True) == "سلام"
    finally:
        # Restore the module's normal import state for the remaining test suite.
        importlib.reload(pdf_service)
