from types import SimpleNamespace

import pytest

from app.schemas.exam import ExamGenerateRequest
from app.schemas.question import (
    DifficultyLevel,
    QuestionPreviewOut,
    QuestionType,
)
from app.services.ai.exceptions import (
    AIProviderCommunicationError,
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIResponseParsingError,
)
from app.services.ai.gpt_service import _clean_and_parse_json, generate_exam
from app.services.ai.scientific_validator import validate_scientific_content


def _request():
    return ExamGenerateRequest(
        grade=10,
        subject="Physics",
        num_questions=1,
        question_type="multiple_choice",
        difficulty="medium",
        topic="gravity",
    )


def _response(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _generate_with_response(monkeypatch, response=None, error=None):
    monkeypatch.setattr(
        "app.services.ai.gpt_service.settings.OPENAI_API_KEY",
        "test-key",
    )
    monkeypatch.setattr(
        "app.services.ai.gpt_service.settings.OPENAI_BASE_URL",
        "https://provider.test/v1",
    )

    def create_completion(**kwargs):
        if error is not None:
            raise error
        return response

    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create_completion)
        )
    )
    monkeypatch.setattr(
        "app.services.ai.gpt_service.OpenAI",
        lambda **kwargs: client,
    )
    monkeypatch.setattr(
        "app.services.ai.gpt_service.normalize_questions",
        lambda data, request: [],
    )

    return generate_exam(_request())


def test_clean_and_parse_json_rejects_empty_and_non_string():
    for value in ("", "  ", None):
        with pytest.raises(AIResponseParsingError, match="empty"):
            _clean_and_parse_json(value)


def test_clean_and_parse_json_rejects_invalid_json_inside_wrapper():
    with pytest.raises(AIResponseParsingError, match="malformed JSON"):
        _clean_and_parse_json("prefix {not valid json} suffix")


def test_clean_and_parse_json_rejects_non_object_json():
    with pytest.raises(AIResponseParsingError, match="JSON object"):
        _clean_and_parse_json('["not", "an object"]')


def test_generate_exam_wraps_provider_exception(monkeypatch):
    with pytest.raises(AIProviderCommunicationError, match="request failed"):
        _generate_with_response(
            monkeypatch,
            error=RuntimeError("simulated network failure"),
        )


def test_generate_exam_rejects_empty_choices(monkeypatch):
    with pytest.raises(AIProviderResponseError, match="no choices"):
        _generate_with_response(
            monkeypatch,
            response=SimpleNamespace(choices=[]),
        )


@pytest.mark.parametrize("content", ["", None])
def test_generate_exam_rejects_empty_content(monkeypatch, content):
    with pytest.raises(AIProviderResponseError, match="no message content"):
        _generate_with_response(
            monkeypatch,
            response=_response(content),
        )


def test_generate_exam_handles_list_content(monkeypatch):
    response = _response(
        [
            {"text": '{"title": "Physics exam",'},
            {"text": '"questions": []}'},
        ]
    )

    result = _generate_with_response(monkeypatch, response=response)

    assert result.title == "Physics exam"
    assert result.questions == []


def test_generate_exam_rejects_missing_configuration(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai.gpt_service.settings.OPENAI_API_KEY",
        "",
    )
    monkeypatch.setattr(
        "app.services.ai.gpt_service.settings.OPENAI_BASE_URL",
        "https://provider.test/v1",
    )

    with pytest.raises(AIProviderConfigurationError, match="not configured"):
        generate_exam(_request())


def test_orbital_explanation_cannot_deny_gravity():
    question = QuestionPreviewOut(
        question_text="ماهواره چگونه در مدار زمین حرکت می‌کند؟",
        question_type=QuestionType.multiple_choice,
        difficulty=DifficultyLevel.medium,
        grade=10,
        subject="Physics",
        topic="orbit",
        options=["Gravity", "Friction"],
        correct_answer="Gravity does not act on the satellite.",
        explanation="There is no gravity in orbit.",
    )

    with pytest.raises(
        ValueError,
        match="Orbital explanation incorrectly denies gravity's role",
    ):
        validate_scientific_content(question)
