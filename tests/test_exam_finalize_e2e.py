import unittest
from unittest.mock import AsyncMock, patch

from app.api.v1.endpoints import exams
from .exam_base_test import BaseExamE2ETest


class ExamFinalizeE2ETests(BaseExamE2ETest):
    def finalized_response(self):
        return {
            "title": "Physics Exam",
            "grade": 10,
            "subject": "physics",
            "questions": [
                {
                    "id": 1,
                    "question_text": "What is gravity?",
                    "question_type": "multiple_choice",
                    "difficulty": "medium",
                    "grade": 10,
                    "subject": "physics",
                    "topic": "gravity",
                    "options": [
                        "A force",
                        "A particle",
                        "A wave",
                        "Nothing",
                    ],
                    "correct_answer": "A force",
                    "explanation": (
                        "Gravity is the attractive force between masses."
                    ),
                }
            ],
        }

    def test_finalize_returns_200_with_valid_response(self):
        client = self.build_client()

        with patch(
            "app.api.v1.endpoints.exams.finalize_exam",
            new=AsyncMock(return_value=self.finalized_response()),
        ) as mock_finalize:
            response = client.post(
                "/exam/finalize",
                json=self.valid_payload(),
            )

        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["title"], "Physics Exam")
        self.assertEqual(body["grade"], 10)
        self.assertEqual(body["questions"][0]["id"], 1)

        mock_finalize.assert_awaited_once()

    def test_finalize_rejects_forbidden_role(self):
        client = self.build_client(role_allowed=False)

        response = client.post(
            "/exam/finalize",
            json=self.valid_payload(),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "Not enough permissions",
        )

    def test_finalize_request_validation_returns_422(self):
        client = self.build_client()

        invalid_payload = self.valid_payload()
        invalid_payload.pop("grade")

        response = client.post(
            "/exam/finalize",
            json=invalid_payload,
        )

        self.assertEqual(response.status_code, 422)

    def test_finalize_response_validation_failure_returns_500(self):
        client = self.build_client(
            raise_server_exceptions=False,
        )

        invalid_finalized_response = {
            "title": "Broken Exam",
            "grade": 10,
            "subject": "physics",
            "questions": [
                {
                    "question_text": "Missing id field",
                    "question_type": "multiple_choice",
                    "difficulty": "medium",
                    "grade": 10,
                    "subject": "physics",
                    "topic": "gravity",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "explanation": "Broken response payload",
                }
            ],
        }

        with patch(
            "app.api.v1.endpoints.exams.finalize_exam",
            new=AsyncMock(
                return_value=invalid_finalized_response,
            ),
        ):
            response = client.post(
                "/exam/finalize",
                json=self.valid_payload(),
            )

        self.assertEqual(response.status_code, 500)

    def test_finalize_maps_service_validation_error_to_422(self):
        client = self.build_client()

        with patch(
            "app.api.v1.endpoints.exams.finalize_exam",
            new=AsyncMock(
                side_effect=exams.AIResponseValidationError(
                    "invalid exam",
                ),
            ),
        ):
            response = client.post(
                "/exam/finalize",
                json=self.valid_payload(),
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "The generated exam data is invalid.",
        )


if __name__ == "__main__":
    unittest.main()
