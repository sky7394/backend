from unittest.mock import patch

from app.schemas import question as question_schemas
from app.services.ai.exceptions import AIResponseValidationError
from app.services.ai.scientific_validator import validate_scientific_content

from .exam_base_test import BaseExamE2ETest


class ScientificExamIntegrationTests(BaseExamE2ETest):
    @staticmethod
    def invalid_gravity_question() -> question_schemas.QuestionPreviewOut:
        return question_schemas.QuestionPreviewOut(
            question_text=(
                "جرم یکی از دو جسم را دو برابر و فاصله آنها را "
                "نصف می‌کنیم. نیروی گرانش چند برابر می‌شود؟"
            ),
            question_type=question_schemas.QuestionType.multiple_choice,
            difficulty=question_schemas.DifficultyLevel.medium,
            grade=10,
            subject="physics",
            topic="gravity",
            options=[
                "۲ برابر",
                "۴ برابر",
                "۶ برابر",
                "۸ برابر",
            ],
            correct_answer="۴ برابر",
            explanation=("جرم دو برابر و فاصله نصف شده است، پس نیرو ۴ برابر می‌شود."),
        )

    @staticmethod
    def valid_gravity_question() -> question_schemas.QuestionPreviewOut:
        return question_schemas.QuestionPreviewOut(
            question_text=(
                "جرم یکی از دو جسم را دو برابر و فاصله آنها را "
                "نصف می‌کنیم. نیروی گرانش چند برابر می‌شود؟"
            ),
            question_type=question_schemas.QuestionType.multiple_choice,
            difficulty=question_schemas.DifficultyLevel.medium,
            grade=10,
            subject="physics",
            topic="gravity",
            options=[
                "۲ برابر",
                "۴ برابر",
                "۶ برابر",
                "۸ برابر",
            ],
            correct_answer="۸ برابر",
            explanation=(
                "با دو برابر شدن یکی از جرم‌ها، نیروی گرانش ۲ برابر می‌شود. "
                "با نصف شدن فاصله، نیرو ۴ برابر می‌شود؛ "
                "بنابراین نیروی نهایی ۸ برابر خواهد شد."
            ),
        )

    @classmethod
    def valid_gravity_ai_output(cls) -> dict:
        question = cls.valid_gravity_question()

        return {
            "title": "آزمون فیزیک",
            "grade": 10,
            "subject": "physics",
            "questions": [question.model_dump()],
        }

    def test_scientific_validator_rejects_invalid_gravity_answer(self):
        question = self.invalid_gravity_question()

        with self.assertRaisesRegex(
            ValueError,
            "Gravity scaling is scientifically incorrect",
        ):
            validate_scientific_content(question)

    def test_scientific_validator_accepts_valid_gravity_answer(self):
        question = self.valid_gravity_question()

        validate_scientific_content(question)

    def test_preview_accepts_valid_gravity_output(self):
        client = self.build_client()

        with patch(
            "app.services.exams.exam_service.generate_exam_with_ai",
            return_value=self.valid_gravity_ai_output(),
        ):
            response = client.post(
                "/exam/preview",
                json=self.valid_payload(),
            )

        self.assertEqual(response.status_code, 200, response.text)

        body = response.json()

        self.assertIn("questions", body)
        self.assertEqual(len(body["questions"]), 1)
        self.assertEqual(
            body["questions"][0]["correct_answer"],
            "۸ برابر",
        )

    def test_preview_propagates_scientific_validation_failure_as_422(self):
        client = self.build_client()

        with patch(
            "app.services.exams.exam_service.generate_exam_with_ai",
            side_effect=AIResponseValidationError(
                "Generated question failed scientific validation"
            ),
        ):
            response = client.post(
                "/exam/preview",
                json=self.valid_payload(),
            )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"],
            "The generated exam data is invalid.",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
