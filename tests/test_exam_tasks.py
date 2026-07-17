import unittest
from unittest.mock import patch

from app.schemas.question import ExamOut, QuestionOut
from app.tasks.exam_tasks import generate_exam_task


class ExamTaskTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "grade": 7,
            "subject": "Science",
            "num_questions": 1,
            "question_type": "multiple_choice",
            "difficulty": "medium",
            "topic": "Cells",
        }
        self.generated_exam = ExamOut(
            title="Cell Biology",
            grade=7,
            subject="Science",
            questions=[
                QuestionOut(
                    id=1,
                    question_text="What controls a cell?",
                    question_type="multiple_choice",
                    difficulty="medium",
                    grade=7,
                    subject="Science",
                    topic="Cells",
                    options=["Nucleus", "Membrane"],
                    correct_answer="Nucleus",
                    explanation="The nucleus contains the cell's genetic material.",
                )
            ],
        )

    def test_success_returns_serialized_generated_exam_without_broker(self):
        with patch(
            "app.tasks.exam_tasks.generate_exam_with_ai",
            return_value=self.generated_exam,
        ) as generate_exam_with_ai:
            result = generate_exam_task.run(self.payload)

        self.assertEqual(result, self.generated_exam.model_dump())

    def test_payload_is_mapped_to_exam_generate_request(self):
        with patch(
            "app.tasks.exam_tasks.generate_exam_with_ai",
            return_value=self.generated_exam,
        ) as generate_exam_with_ai:
            generate_exam_task.run(self.payload)

        request = generate_exam_with_ai.call_args.args[0]
        self.assertEqual(request.model_dump(), self.payload)

    def test_api_timeout_is_propagated(self):
        timeout = TimeoutError("AI service timed out")

        with patch(
            "app.tasks.exam_tasks.generate_exam_with_ai",
            side_effect=timeout,
        ):
            with self.assertRaises(TimeoutError) as context:
                generate_exam_task.run(self.payload)

        self.assertIs(context.exception, timeout)

    def test_ai_error_is_propagated(self):
        ai_error = RuntimeError("AI service unavailable")

        with patch(
            "app.tasks.exam_tasks.generate_exam_with_ai",
            side_effect=ai_error,
        ):
            with self.assertRaises(RuntimeError) as context:
                generate_exam_task.run(self.payload)

        self.assertIs(context.exception, ai_error)


if __name__ == "__main__":
    unittest.main()
