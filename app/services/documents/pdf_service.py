from fpdf import FPDF
import os
import uuid

from app.core.config import settings


def create_exam_pdf(questions):
    os.makedirs(settings.GENERATED_PDF_DIR, exist_ok=True)

    filename = f"{uuid.uuid4()}.pdf"
    filepath = os.path.join(settings.GENERATED_PDF_DIR, filename)

    pdf = FPDF()
    pdf.add_page()

    font_path = settings.FONT_PATH
    if not os.path.isabs(font_path):
        font_path = os.path.join(os.getcwd(), font_path)

    pdf.add_font("Vazir", "", font_path)
    pdf.set_font("Vazir", size=14)

    pdf.cell(0,10,"آزمون", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    for i,q in enumerate(questions,1):

        pdf.multi_cell(0,10,f"{i}) {q['question']}")

        for idx,opt in enumerate(q["options"],1):
            pdf.cell(0,8,f"{idx}) {opt}", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(3)

    pdf.output(filepath)

    return filepath
