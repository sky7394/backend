import pytest
from app.services.documents.exam_models import ExamHeaderConfig, ExamHeaderStyle, ExamLayoutType, NormalizedQuestion
from app.services.documents.text_direction import fix_text_bidi, sanitize_ascii, contains_farsi
from app.services.documents.exam_header import render_exam_header
from app.services.documents.exam_questions import render_questions_table
from app.services.documents.pdf_service import ExamPDF, build_exam_pdf, create_exam_pdf, generate_exam_pdf_bytes


def test_text_direction_functions():
    assert contains_farsi("سلام") is True
    assert contains_farsi("Hello") is False
    
    assert sanitize_ascii("سلام دنیا Hello") == "Hello"
    assert sanitize_ascii("123 Test") == "123 Test"
    
    fixed = fix_text_bidi("تست ۱۲۳")
    assert isinstance(fixed, str)


def test_render_exam_header_styles():
    pdf = ExamPDF()
    pdf.add_page()
    
    for style in [ExamHeaderStyle.SCHOOL, ExamHeaderStyle.OFFICIAL]:
        config = ExamHeaderConfig(
            school_name="مدرسه نمونه",
            course_name="فیزیک ۱",
            exam_date="1403/08/10",
            duration_minutes=90,
            header_style=style,
        )
        render_exam_header(pdf, config, font_name="Helvetica")


def test_render_questions_table_branches():
    pdf = ExamPDF()
    pdf.add_page()
    
    config1 = ExamHeaderConfig(
        course_name="ریاضی",
        layout_type=ExamLayoutType.GENERAL,
    )
    
    questions = [
        NormalizedQuestion(
            number=1,
            question_text="سوال چهارگزینه‌ای اول",
            options=["الف", "ب", "ج", "د"],
            points=2.0,
            section="بخش اول",
        ),
        NormalizedQuestion(
            number=2,
            question_text="سوال تشریحی دوم با فرمول",
            options=[],
            points=3.0,
            formula="E = mc^2",
        ),
    ]
    
    render_questions_table(pdf, questions, config1, font_name="Helvetica")
    
    # Check STEM layout branch
    config2 = ExamHeaderConfig(
        course_name="ریاضی",
        layout_type=ExamLayoutType.STEM,
    )
    render_questions_table(pdf, questions, config2, font_name="Helvetica")


def test_pdf_generation_full_cycle():
    data = {
        "questions": [
            {"question": "سوال تستی", "options": ["۱", "۲"], "points": 1, "answer": "۱"}
        ]
    }
    header = ExamHeaderConfig(course_name="شیمی")
    pdf_bytes = generate_exam_pdf_bytes(data, header_config=header, with_answers=True)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0

    temp_path = create_exam_pdf(data, header_config=header, with_answers=False)
    assert temp_path.endswith(".pdf")
