"""Unit tests for AI Exam Generation Service."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# اسکیماها
try:
    from app.schemas.exam import (
        DifficultyLevel,
        ExamGenerateRequest,
        QuestionType,
    )
except ImportError:
    from app.schemas.generate import (
        DifficultyLevel,
        ExamGenerateRequest,
        QuestionType,
    )

# استثناهای اختصاصی پروژه
from app.services.ai.exceptions import (
    AIProviderCommunicationError,
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIResponseParsingError,
)

# نکته کلیدی: ماژول را import می‌کنیم، نه خود تابع را!
# این‌طوری patch روی exam_service.generate_exam_with_ai اثر می‌کند.
from app.services.exams import exam_service


# ---------------------------------------------------------------------------
# Fixtures & Dummy Data
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_generate_request() -> ExamGenerateRequest:
    return ExamGenerateRequest(
        grade=10,
        subject="فیزیک",
        num_questions=2,
        question_type=QuestionType.MULTIPLE_CHOICE if hasattr(QuestionType, "MULTIPLE_CHOICE") else "multiple_choice",
        difficulty=DifficultyLevel.MEDIUM if hasattr(DifficultyLevel, "MEDIUM") else "medium",
        topic="فصل اول: فیزیک و اندازه‌گیری",
    )


@pytest.fixture
def mock_preview_out() -> MagicMock:
    """A MagicMock mimicking ExamPreviewOut, resistant to schema changes."""
    preview = MagicMock()
    preview.title = "آزمون فیزیک دهم"
    preview.questions = [
        MagicMock(question_text="یکای اصلی جرم در SI کدام است؟", correct_answer="کیلوگرم"),
        MagicMock(question_text="کدام کمیت فرعی است؟", correct_answer="سرعت"),
    ]
    return preview


# ---------------------------------------------------------------------------
# Unit Tests for AI Exam Generation Logic
# ---------------------------------------------------------------------------

class TestAIExamGeneration:
    def test_generate_exam_success(
        self, sample_generate_request: ExamGenerateRequest, mock_preview_out: MagicMock
    ):
        with patch.object(
            exam_service, "generate_exam_with_ai", return_value=mock_preview_out
        ) as mock_gen:
            result = exam_service.generate_exam_with_ai(sample_generate_request)

            assert result is not None
            assert result.title == "آزمون فیزیک دهم"
            assert len(result.questions) == 2
            assert result.questions[0].correct_answer == "کیلوگرم"
            mock_gen.assert_called_once_with(sample_generate_request)

    def test_generate_exam_parsing_error(
        self, sample_generate_request: ExamGenerateRequest
    ):
        with patch.object(
            exam_service,
            "generate_exam_with_ai",
            side_effect=AIResponseParsingError("Failed to parse AI output"),
        ):
            with pytest.raises(AIResponseParsingError):
                exam_service.generate_exam_with_ai(sample_generate_request)

    def test_generate_exam_communication_error(
        self, sample_generate_request: ExamGenerateRequest
    ):
        with patch.object(
            exam_service,
            "generate_exam_with_ai",
            side_effect=AIProviderCommunicationError("Network timeout / Rate limit"),
        ):
            with pytest.raises(AIProviderCommunicationError):
                exam_service.generate_exam_with_ai(sample_generate_request)

    def test_generate_exam_config_error(
        self, sample_generate_request: ExamGenerateRequest
    ):
        with patch.object(
            exam_service,
            "generate_exam_with_ai",
            side_effect=AIProviderConfigurationError("Gemini API key is missing"),
        ):
            with pytest.raises(AIProviderConfigurationError):
                exam_service.generate_exam_with_ai(sample_generate_request)

    def test_generate_exam_provider_response_error(
        self, sample_generate_request: ExamGenerateRequest
    ):
        with patch.object(
            exam_service,
            "generate_exam_with_ai",
            side_effect=AIProviderResponseError("Malformed provider response"),
        ):
            with pytest.raises(AIProviderResponseError):
                exam_service.generate_exam_with_ai(sample_generate_request)
