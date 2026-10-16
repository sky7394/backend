from typing import List, Optional
from pydantic import BaseModel, Field, field_serializer
from app.services.documents.exam_models import ExamHeaderConfig

class QuestionExportSchema(BaseModel):
    question_text: str = Field(..., description="متن سوال")
    score: Optional[float] = Field(1.0, description="بارم یا نمره سوال")
    options: List[str] = Field(default_factory=list, description="گزینه‌ها (برای سوالات تستی)")
    correct_answer: Optional[str] = Field(None, description="پاسخ صحیح")
    explanation: Optional[str] = Field(None, description="توضیح یا پاسخ تشریحی")
    formula: Optional[str] = Field(None, max_length=2000, description="فرمول متنی یا LaTeX ساده")
    answer_lines: int = Field(3, ge=0, le=20, description="تعداد خطوط جای پاسخ تشریحی")

class ExamExportRequestSchema(BaseModel):
    title: str = Field(..., description="عنوان آزمون")
    grade: Optional[str] = Field(None, description="پایه تحصیلی")
    subject: Optional[str] = Field(None, description="درس")
    header_config: Optional[ExamHeaderConfig] = None
    include_answers: bool = Field(True, description="آیا پاسخ‌نامه در انتهای فایل درج شود؟")
    questions: List[QuestionExportSchema] = Field(..., description="لیست سوالات آزمون")

    @field_serializer("header_config")
    def serialize_header(self, header):
        # Preserve explicit overrides so omitted course/grade values still come
        # from the existing subject/grade fields after the endpoint model_dump.
        return header.model_dump(exclude_unset=True) if header is not None else None
