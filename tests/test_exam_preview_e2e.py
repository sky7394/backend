import unittest
from unittest.mock import AsyncMock, patch
from app.api.v1.endpoints import exams
from .exam_base_test import BaseExamE2ETest


class ExamPreviewE2ETests(BaseExamE2ETest):
    def preview_response(self):
        return {
            "title": "Physics Exam Preview",
            "grade": 10,
            "subject": "physics",
            "questions": [
                {
                    "question_text": "What is gravity?",
                    "question_type": "multiple_choice",
                    "difficulty": "medium",
                    "grade": 10,
                    "subject": "physics",
                    "topic": "gravity",
                    "options": ["A force", "A particle", "A wave", "Nothing"],
                    "correct_answer": "A force",
                    "explanation": "Gravity is the attractive force between masses.",
                }
            ],
        }

    def test_preview_returns_200_with_valid_response(self):
        client = self.build_client()
        with patch(
            "app.api.v1.endpoints.exams.preview_exam",
            new=AsyncMock(return_value=self.preview_response()),
        ) as mock_preview:
            response = client.post("/exam/preview", json=self.valid_payload())

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["title"], "Physics Exam Preview")
        self.assertNotIn("id", body["questions"][0])
        mock_preview.assert_awaited_once()

    def test_preview_rejects_forbidden_role(self):
        client = self.build_client(role_allowed=False)
        response = client.post("/exam/preview", json=self.valid_payload())
        self.assertEqual(response.status_code, 403)

    def test_preview_request_validation_returns_422(self):
        client = self.build_client()
        invalid_payload = self.valid_payload()
        invalid_payload.pop("grade")
        response = client.post("/exam/preview", json=invalid_payload)
        self.assertEqual(response.status_code, 422)

    def test_preview_response_validation_failure_returns_500(self):
        client = self.build_client(raise_server_exceptions=False)
        invalid_preview_response = {
            "title": "Broken Exam Preview",
            "grade": 10,
            "subject": "physics",
            "questions": [
                {
                    "question_text": "Invalid schema data",
                    "question_type": "multiple_choice",
                    "difficulty": "medium",
                    "grade": 10,
                    "subject": "physics",
                    "topic": "gravity",
                    "options": "Not a list of options",
                    "correct_answer": "A",
                    "explanation": "Broken response payload",
                }
            ],
        }
        with patch(
            "app.api.v1.endpoints.exams.preview_exam",
            new=AsyncMock(return_value=invalid_preview_response),
        ):
            response = client.post("/exam/preview", json=self.valid_payload())
        self.assertEqual(response.status_code, 500)

    def test_preview_maps_ai_validation_error_to_422(self):
        client = self.build_client()
        with patch(
            "app.api.v1.endpoints.exams.preview_exam",
            new=AsyncMock(side_effect=exams.AIResponseValidationError("invalid exam")),
        ):
            response = client.post("/exam/preview", json=self.valid_payload())
        self.assertEqual(response.status_code, 422)

    def test_preview_maps_configuration_error_to_503(self):
        client = self.build_client()
        with patch(
            "app.api.v1.endpoints.exams.preview_exam",
            new=AsyncMock(side_effect=exams.AIProviderConfigurationError("Config issues")),
        ):
            response = client.post("/exam/preview", json=self.valid_payload())
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
