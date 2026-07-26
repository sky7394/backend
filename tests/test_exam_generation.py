import json
import unittest
from asyncio import run
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import exams
from app.db.session import get_db
from app.schemas import exam as exam_schemas
from app.schemas import generate as compatibility_schemas
from app.schemas import question as question_schemas
from app.services.ai.exceptions import (
    AIProviderCommunicationError,
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIResponseParsingError,
    AIResponseValidationError,
)
from app.services.ai.gemini_service import _clean_and_parse_json, generate_exam
from app.services.exams.exam_service import finalize_exam, preview_exam


class SchemaCanonicalTests(unittest.TestCase):
    def test_question_schemas_canonical(self):
        self.assertEqual(question_schemas.QuestionType.multiple_choice.value, "multiple_choice")
        self.assertEqual(question_schemas.DifficultyLevel.medium.value, "medium")

    def test_compatibility_layer_exports_canonical_schemas(self):
        schema_names = (
            "QuestionType",
            "DifficultyLevel",
            "ExamGenerateRequest",
        )
        for name in schema_names:
            with self.subTest(schema=name):
                if hasattr(compatibility_schemas, name):
                    canonical = getattr(exam_schemas, name, None) or getattr(
                        question_schemas, name, None
                    )
                    if canonical:
                        self.assertIs(getattr(compatibility_schemas, name), canonical)


class GeminiServiceTests(unittest.TestCase):
    def setUp(self):
        self.request = exam_schemas.ExamGenerateRequest(
            grade=7,
            subject="Science",
            num_questions=1,
            question_type=question_schemas.QuestionType.multiple_choice,
            difficulty=question_schemas.DifficultyLevel.medium,
            topic="Cells",
        )
        self.exam_data = {
            "title": "Cell Biology",
            "questions": [
                {
                    "question_text": "What controls a cell?",
                    "question_type": "multiple_choice",
                    "difficulty": "medium",
                    "grade": 7,
                    "subject": "Science",
                    "topic": "Cells",
                    "options": ["Nucleus", "Membrane"],
                    "correct_answer": "Nucleus",
                    "explanation": "The nucleus contains genetic material.",
                }
            ],
        }

    def make_response(self, content):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                )
            ]
        )

    def generate_with_response(self, response):
        with (
            patch("app.services.ai.gemini_service.settings.GEMINI_API_KEY", "test-key"),
            patch(
                "app.services.ai.gemini_service.settings.GEMINI_BASE_URL",
                "https://provider.test/v1",
            ),
            patch("app.services.ai.gemini_service.settings.GEMINI_MODEL", "test-model"),
            patch("app.services.ai.gemini_service.OpenAI") as openai_client,
        ):
            openai_client.return_value.chat.completions.create.return_value = response
            return generate_exam(self.request)

    def test_empty_provider_choices_raise_response_error(self):
        with self.assertRaises(AIProviderResponseError):
            self.generate_with_response(SimpleNamespace(choices=[]))

    def test_missing_or_blank_message_content_raises_response_error(self):
        for content in (None, "", "   "):
            with self.subTest(content=content):
                with self.assertRaises(AIProviderResponseError):
                    self.generate_with_response(self.make_response(content))

    def test_malformed_json_raises_parsing_error(self):
        with self.assertRaises(AIResponseParsingError):
            _clean_and_parse_json('{"title": "Broken", "questions": [}')

    def test_top_level_json_array_raises_parsing_error(self):
        with self.assertRaises(AIResponseParsingError):
            _clean_and_parse_json('[{"title": "Not an exam object"}]')

    def test_valid_fenced_json_is_parsed(self):
        raw = f"```json\n{json.dumps(self.exam_data)}\n```"
        self.assertEqual(_clean_and_parse_json(raw), self.exam_data)

    def test_provider_sdk_failure_is_converted_to_safe_domain_error(self):
        with (
            patch("app.services.ai.gemini_service.settings.GEMINI_API_KEY", "test-key"),
            patch(
                "app.services.ai.gemini_service.settings.GEMINI_BASE_URL",
                "https://provider.test/v1",
            ),
            patch("app.services.ai.gemini_service.settings.GEMINI_MODEL", "test-model"),
            patch("app.services.ai.gemini_service.OpenAI") as openai_client,
        ):
            openai_client.return_value.chat.completions.create.side_effect = RuntimeError(
                "provider-secret-token"
            )

            with self.assertRaises(AIProviderCommunicationError) as context:
                generate_exam(self.request)

        self.assertNotIn("provider-secret-token", str(context.exception))

    def test_unusable_question_data_raises_validation_error(self):
        response = self.make_response(json.dumps({"title": "Broken", "questions": []}))
        with self.assertRaises(AIResponseValidationError):
            self.generate_with_response(response)


class ExamEndpointTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(exams.router)

        async def get_test_db():
            yield AsyncMock()

        app.dependency_overrides[get_db] = get_test_db
        self.client = TestClient(app)
        self.payload = {
            "grade": 7,
            "subject": "Science",
            "num_questions": 1,
            "question_type": "multiple_choice",
            "difficulty": "medium",
            "topic": "Cells",
        }
        self.preview_exam_data = exam_schemas.ExamPreviewOut(
            title="Cell Biology",
            grade=7,
            subject="Science",
            questions=[
                question_schemas.QuestionPreviewOut(
                    question_text="What controls a cell?",
                    question_type=question_schemas.QuestionType.multiple_choice,
                    difficulty=question_schemas.DifficultyLevel.medium,
                    grade=7,
                    subject="Science",
                    topic="Cells",
                    options=["Nucleus", "Membrane"],
                    correct_answer="Nucleus",
                )
            ],
        )
        self.finalized_exam_data = exam_schemas.ExamFinalizeOut(
            title="Cell Biology",
            grade=7,
            subject="Science",
            questions=[
                question_schemas.QuestionFinalizeOut(
                    id=1,
                    question_text="What controls a cell?",
                    question_type=question_schemas.QuestionType.multiple_choice,
                    difficulty=question_schemas.DifficultyLevel.medium,
                    grade=7,
                    subject="Science",
                    topic="Cells",
                    options=["Nucleus", "Membrane"],
                    correct_answer="Nucleus",
                )
            ],
        )

    def test_preview_endpoint_success(self):
        with patch(
            "app.api.v1.endpoints.exams.preview_exam",
            new=AsyncMock(return_value=self.preview_exam_data),
        ) as mock_preview:
            response = self.client.post("/exam/preview", json=self.payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.preview_exam_data.model_dump(mode="json"))
        mock_preview.assert_awaited_once()

    def test_finalize_endpoint_success(self):
        with patch(
            "app.api.v1.endpoints.exams.finalize_exam",
            new=AsyncMock(return_value=self.finalized_exam_data),
        ) as mock_finalize:
            response = self.client.post("/exam/finalize", json=self.payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.finalized_exam_data.model_dump(mode="json"))
        mock_finalize.assert_awaited_once()

    def test_known_ai_failures_return_safe_status_codes(self):
        cases = (
            (AIProviderConfigurationError("api-key-secret"), 503),
            (AIResponseParsingError("raw-provider-response"), 502),
            (AIProviderResponseError("raw-provider-response"), 502),
            (AIProviderCommunicationError("provider-secret-token"), 502),
            (AIResponseValidationError("invalid-internal-data"), 422),
        )

        for error, expected_status in cases:
            with self.subTest(error=type(error).__name__):
                with patch(
                    "app.api.v1.endpoints.exams.preview_exam",
                    new=AsyncMock(side_effect=error),
                ):
                    response = self.client.post("/exam/preview", json=self.payload)

                self.assertEqual(response.status_code, expected_status)
                response_text = response.text
                self.assertNotIn(str(error), response_text)
                self.assertNotIn("secret", response_text.lower())
                self.assertNotIn("raw-provider-response", response_text)

    def test_unexpected_failure_preview_returns_generic_500(self):
        with patch(
            "app.api.v1.endpoints.exams.preview_exam",
            new=AsyncMock(side_effect=RuntimeError("internal-error")),
        ):
            response = self.client.post("/exam/preview", json=self.payload)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Unable to generate the exam preview."})

    def test_unexpected_failure_finalize_returns_generic_500(self):
        with patch(
            "app.api.v1.endpoints.exams.finalize_exam",
            new=AsyncMock(side_effect=RuntimeError("internal-error")),
        ):
            response = self.client.post("/exam/finalize", json=self.payload)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Unable to finalize the exam."})


class ExamServiceTests(unittest.TestCase):
    def setUp(self):
        self.request = exam_schemas.ExamGenerateRequest(grade=7, subject="Science")
        self.ai_raw_output = exam_schemas.ExamPreviewOut(
            title="Science Exam",
            grade=7,
            subject="Science",
            questions=[
                question_schemas.QuestionPreviewOut(
                    question_text="What is an atom?",
                    question_type=question_schemas.QuestionType.multiple_choice,
                    difficulty=question_schemas.DifficultyLevel.medium,
                    grade=7,
                    subject="Science",
                    options=["A particle", "A planet"],
                    correct_answer="A particle",
                )
            ],
        )

    def test_preview_generates_and_validates_without_saving(self):
        with (
            patch(
                "app.services.exams.exam_service.generate_exam_with_ai",
                return_value=self.ai_raw_output,
            ) as generate_exam_with_ai,
            patch("app.services.exams.exam_service.create_exam") as create_exam,
        ):
            result = run(preview_exam(self.request))

        generate_exam_with_ai.assert_called_once_with(self.request)
        create_exam.assert_not_called()
        self.assertEqual(result.title, "Science Exam")

    def test_finalize_generates_saves_and_returns_finalized_exam(self):
        finalized_exam = exam_schemas.ExamFinalizeOut(
            title="Saved Science Exam",
            grade=7,
            subject="Science",
            questions=[
                question_schemas.QuestionFinalizeOut(
                    id=10,
                    question_text="What is an atom?",
                    question_type=question_schemas.QuestionType.multiple_choice,
                    difficulty=question_schemas.DifficultyLevel.medium,
                    grade=7,
                    subject="Science",
                    options=["A particle", "A planet"],
                    correct_answer="A particle",
                )
            ],
        )

        with (
            patch(
                "app.services.exams.exam_service.generate_exam_with_ai",
                return_value=self.ai_raw_output,
            ) as generate_exam_with_ai,
            patch(
                "app.services.exams.exam_service.create_exam",
                new=AsyncMock(return_value=finalized_exam),
            ) as create_exam,
        ):
            db = AsyncMock()
            result = run(finalize_exam(self.request, db))

        generate_exam_with_ai.assert_called_once_with(self.request)
        create_exam.assert_awaited_once()
        self.assertIs(create_exam.await_args.args[0], db)
        self.assertEqual(result.title, "Saved Science Exam")

    def test_preview_validation_failure_raises_ai_validation_error(self):
        with patch(
            "app.services.exams.exam_service.generate_exam_with_ai",
            return_value={"title": "Invalid format missing questions"},
        ):
            with self.assertRaises(AIResponseValidationError):
                run(preview_exam(self.request))


if __name__ == "__main__":
    unittest.main()
