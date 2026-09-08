import os
from app.services.documents.pdf_service import (
    build_exam_pdf,
    create_exam_pdf,
    generate_exam_pdf_bytes,
)


def test_build_exam_pdf_instance():
    questions = [
        {
            "question": "قانون اول نیوتن چیست؟",
            "options": ["لختی", "شتاب", "گرانش", "اصطکاک"],
            "answer": "لختی",
        },
        {
            "question": "یکای نیرو در SI چیست؟",
            "options": ["ژول", "نیوتون", "وات", "پاسکال"],
            "answer": "نیوتون",
        },
    ]
    pdf = build_exam_pdf(questions, title="آزمون فیزیک دهم", with_answers=True)
    assert pdf is not None
    assert pdf.page_no() >= 1


def test_generate_exam_pdf_bytes():
    questions = [
        {
            "question": "پایتون چیست؟",
            "options": ["زبان برنامه‌نویسی", "سیستم عامل", "پایگاه داده"],
            "answer": "زبان برنامه‌نویسی",
        }
    ]
    pdf_bytes = generate_exam_pdf_bytes(questions, title="آزمون پایتون", with_answers=False)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    # PDF files start with %PDF header magic bytes
    assert pdf_bytes.startswith(b"%PDF")


def test_create_exam_pdf_file():
    questions = [
        {
            "question": "تست ایجاد فایل",
            "options": ["گزینه ۱", "گزینه ۲"],
            "answer": "گزینه ۱",
        }
    ]
    filepath = create_exam_pdf(questions, title="آزمون فایل")
    assert os.path.exists(filepath)
    assert filepath.endswith(".pdf")
    # Clean up generated file after test
    try:
        os.remove(filepath)
    except OSError:
        pass
def test_pdf_has_valid_header():
    pdf_bytes = generate_exam_pdf_bytes(
        [
            {
                "question": "آزمون صحت PDF",
                "options": ["بله", "خیر"],
                "answer": "بله",
            }
        ],
        title="تست PDF",
    )

    assert pdf_bytes.startswith(b"%PDF")
