from app.prompts.exam_prompts import DIFFICULTY_LABELS, QUESTION_TYPE_LABELS
from app.schemas.question import ExamGenerateRequest


def build_exam_prompt(request: ExamGenerateRequest) -> str:
    question_type = str(request.question_type.value if hasattr(request.question_type, "value") else request.question_type)
    difficulty = str(request.difficulty.value if hasattr(request.difficulty, "value") else request.difficulty)
    question_type_label = QUESTION_TYPE_LABELS.get(question_type, "چهارگزینه‌ای")
    difficulty_label = DIFFICULTY_LABELS.get(difficulty, "متوسط")
    topic = request.topic or request.subject

    return f"""تو یک استاد متخصص در درس {request.subject} هستی.
یک آزمون با مشخصات زیر بساز:

- تعداد سوالات: {request.num_questions}
- نوع سوال: {question_type_label}
- سطح دشواری: {difficulty_label}
- پایه تحصیلی: {request.grade}
- موضوع: {topic}

خروجی را دقیقاً به صورت JSON با ساختار زیر بده:

{{
  "title": "عنوان آزمون",
  "subject": "{request.subject}",
  "grade": {request.grade},
  "questions": [
    {{
      "id": 1,
      "question_text": "متن سوال",
      "question_type": "{question_type}",
      "difficulty": "{difficulty}",
      "grade": {request.grade},
      "subject": "{request.subject}",
      "topic": "{topic}",
      "options": ["گزینه ۱", "گزینه ۲", "گزینه ۳", "گزینه ۴"],
      "correct_answer": "گزینه صحیح",
      "explanation": "توضیح پاسخ"
    }}
  ]
}}

- اگر نوع سوال درست/غلط است، options فقط ["درست", "غلط"] باشد
- اگر نوع سوال تشریحی یا پاسخ کوتاه است، options خالی [] باشد
- همه فیلدها را پر کن
- فقط JSON برگردان، بدون توضیح اضافی"""
