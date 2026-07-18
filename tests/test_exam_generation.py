import json
import unittest
from asyncio import run
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import exams
from app.schemas import exam as legacy_exam_schemas
from app.schemas import generate as generation_schemas
from app.schemas import question as legacy_question_schemas
from app.services.ai.exceptions import (
    AIProviderCommunicationError,
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIResponseParsingError,
    AIResponseValidationError,
)
from app.services.ai.gemini_service import _clean_and_parse_json, generate_exam
from app.services.exams.exam_service import generate_exam as generate_and_save_exam


class GenerationSchemaTests(unittest.TestCase):
    def test_generation_schemas_have_one_canonical_implementation(self):
        schema_names = (
            "QuestionType",
            "DifficultyLevel",
            "ExamGenerateRequest",
            "QuestionOut",
            "ExamOut",
        )

        for schema_name in schema_names:
            with self.subTest(schema=schema_name):
                canonical = getattr(generation_schemas, schema_name)
                self.assertIs(getattr(legacy_question_schemas, schema_name), canonical)
                self.assertIs(getattr(legacy_exam_schemas, schema_name), canonical)
                self.assertEqual(canonical.__module__, "app.schemas.generate")


class GeminiServiceTests(unittest.TestCase):
    def setUp(self):
        self.request = generation_schemas.ExamGenerateRequest(
            grade=7,
            subject="Science",
            num_questions=1,
            question_type="multiple_choice",
            difficulty="medium",
            topic="Cells",
        )
        self.exam_data = {
            "title": "Cell Biology",
            "questions": [
                {
                    "id": 1,
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
            patch("app.services.ai.gemini_service.settings.GEMINI_BASE_URL", "https://provider.test/v1"),
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
            patch("app.services.ai.gemini_service.settings.GEMINI_BASE_URL", "https://provider.test/v1"),
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
        self.client = TestClient(app)
        self.payload = {
            "grade": 7,
            "subject": "Science",
            "num_questions": 1,
            "question_type": "multiple_choice",
            "difficulty": "medium",
            "topic": "Cells",
        }

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
                    "app.api.v1.endpoints.exams.generate_exam",
                    new=AsyncMock(side_effect=error),
                ):
                    response = self.client.post("/exam/generate", json=self.payload)

                self.assertEqual(response.status_code, expected_status)
                response_text = response.text
                self.assertNotIn(str(error), response_text)
                self.assertNotIn("secret", response_text.lower())
                self.assertNotIn("raw-provider-response", response_text)

    def test_unexpected_failure_returns_generic_500(self):
        with patch(
            "app.api.v1.endpoints.exams.generate_exam",
            new=AsyncMock(side_effect=RuntimeError("internal-path-and-secret")),
        ):
            response = self.client.post("/exam/generate", json=self.payload)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Unable to generate the exam."})
        self.assertNotIn("internal-path-and-secret", response.text)


class ExamServiceTests(unittest.TestCase):
    def test_generate_exam_preserves_generate_save_return_workflow(self):
        request = generation_schemas.ExamGenerateRequest(grade=7, subject="Science")
        generated_exam = generation_schemas.ExamOut(
            title="Science Exam",
            grade=7,
            subject="Science",
            questions=[
                generation_schemas.QuestionOut(
                    id=1,
                    question_text="What is an atom?",
                    question_type="multiple_choice",
                    difficulty="medium",
                    grade=7,
                    subject="Science",
                    options=["A particle", "A planet"],
                    correct_answer="A particle",
                )
            ],
        )
        saved_exam = generated_exam.model_copy(update={"title": "Saved Science Exam"})

        with (
            patch(
                "app.services.exams.exam_service.generate_exam_with_ai",
                return_value=generated_exam,
            ) as generate_exam_with_ai,
            patch(
                "app.services.exams.exam_service.save_generated_exam",
                return_value=saved_exam,
            ) as save_generated_exam,
        ):
            result = run(generate_and_save_exam(request))

        generate_exam_with_ai.assert_called_once_with(request)
        save_generated_exam.assert_called_once_with(generated_exam)
        self.assertIs(result, saved_exam)


if __name__ == "__main__":
    unittest.main()
