import unittest
from unittest.mock import patch

from app.schemas.exam import ExamFinalizeOut as ExamOut
from app.schemas.question import QuestionFinalizeOut as QuestionOut
from app.tasks.exam_tasks import generate_exam_task


class ExamTaskTests(unittest.TestCase):
    def setUp(self):
        # تغییر فیلدهای grade به مقادیر عددی برای همگامی با ساختار جدید Pydantic
        self.payload = {
            "title": "فیزیک یازدهم",
            "grade": 11,
            "subject": "فیزیک",
            "description": "سوالات فصل اول فیزیک",
            "questions_count": 2,
            "questions": [
                {
                    "question_text": "قانون کولن چیست؟",
                    "question_type": "descriptive",
                    "difficulty": "easy",
                    "options": [],
                    "correct_answer": "نیروی بین دو بار الکتریکی...",
                    "grade": 11,
                    "subject": "فیزیک",
                },
                {
                    "question_text": "فرمول شتاب متوسط کدام است؟",
                    "question_type": "multiple_choice",
                    "difficulty": "medium",
                    "options": ["a=v/t", "a=F/m", "a=dx/dt", "همه موارد"],
                    "correct_answer": "a=v/t",
                    "grade": 11,
                    "subject": "فیزیک",
                },
            ],
        }

        self.generated_exam = ExamOut(
            id=123,
            title="فیزیک یازدهم",
            grade=11,
            subject="فیزیک",
            description="سوالات فصل اول فیزیک",
            questions=[
                QuestionOut(
                    id=1,
                    question_text="قانون کولن چیست؟",
                    question_type="descriptive",
                    difficulty="easy",
                    options=[],
                    correct_answer="نیروی بین دو بار الکتریکی...",
                    grade=11,
                    subject="فیزیک",
                ),
                QuestionOut(
                    id=2,
                    question_text="فرمول شتاب متوسط کدام است؟",
                    question_type="multiple_choice",
                    difficulty="medium",
                    options=["a=v/t", "a=F/m", "a=dx/dt", "همه موارد"],
                    correct_answer="a=v/t",
                    grade=11,
                    subject="فیزیک",
                ),
            ],
        )

    def test_success_returns_serialized_generated_exam_without_broker(self):
        with patch(
            "app.tasks.exam_tasks.generate_exam_with_ai",
            return_value=self.generated_exam,
        ):
            result = generate_exam_task.run(self.payload)
            self.assertEqual(result["title"], "فیزیک یازدهم")
            self.assertEqual(len(result["questions"]), 2)

    def test_payload_is_mapped_to_exam_generate_request(self):
        with patch(
            "app.tasks.exam_tasks.generate_exam_with_ai",
            return_value=self.generated_exam,
        ) as generate_exam_with_ai:
            generate_exam_task.run(self.payload)
            generate_exam_with_ai.assert_called_once()

    def test_api_timeout_is_propagated(self):
        timeout = TimeoutError("AI service timed out")

        with patch(
            "app.tasks.exam_tasks.generate_exam_with_ai",
            side_effect=timeout,
        ):
            with self.assertRaises(TimeoutError):
                generate_exam_task.run(self.payload)

    def test_ai_error_is_propagated(self):
        ai_error = RuntimeError("AI service unavailable")

        with patch(
            "app.tasks.exam_tasks.generate_exam_with_ai",
            side_effect=ai_error,
        ):
            with self.assertRaises(RuntimeError):
                generate_exam_task.run(self.payload)
