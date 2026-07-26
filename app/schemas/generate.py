from app.schemas.question import QuestionType, DifficultyLevel
from app.schemas.exam import ExamGenerateRequest

# اگر سایر بخش‌های پروژه (مانند تست‌های قدیمی‌تر) به کلاس‌های خروجی 
# مثل ExamOut و QuestionOut از این فایل نیاز دارند، آن‌ها را نیز به عنوان alias تعریف می‌کنیم:
from app.schemas.exam import ExamFinalizeOut as ExamOut
from app.schemas.question import QuestionFinalizeOut as QuestionOut

__all__ = [
    "QuestionType",
    "DifficultyLevel",
    "ExamGenerateRequest",
    "QuestionOut",
    "ExamOut"
]
