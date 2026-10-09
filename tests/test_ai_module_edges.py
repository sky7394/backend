"""Tests for the small AI package modules: ai_client, gemini_service,
exam_generator and prompt_builder."""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.ai import ai_client, gemini_service
from app.services.ai.ai_client import generate_questions
from app.services.ai.exam_generator import generate_exam_with_ai
from app.services.ai.prompt_builder import build_exam_prompt


# ---------------------------------------------------------------------------
# ai_client.generate_questions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_generate_questions_returns_valid_json_payload():
    raw = await generate_questions(topic="جاذبه", grade="دهم", count=3)
    payload = json.loads(raw)

    assert len(payload["questions"]) == 3

    for i, q in enumerate(payload["questions"], start=1):
        assert q["question"] == f"سوال {i} از مبحث جاذبه برای پایه دهم چیست؟"
        assert q["options"] == ["گزینه 1", "گزینه 2", "گزینه 3", "گزینه 4"]
        assert q["answer"] == "گزینه 1"


@pytest.mark.asyncio
async def test_generate_questions_count_zero_returns_empty_list():
    payload = json.loads(await generate_questions("فیزیک", "یازدهم", 0))
    assert payload == {"questions": []}


@pytest.mark.asyncio
async def test_generate_questions_output_is_not_ascii_escaped():
    raw = await generate_questions("مکانیک", "دوازدهم", 1)
    assert "سوال" in raw


# ---------------------------------------------------------------------------
# gemini_service (compatibility layer)
# ---------------------------------------------------------------------------
def test_gemini_service_reexports_gpt_service_functions():
    from app.services.ai import gpt_service

    assert gemini_service.generate_exam is gpt_service.generate_exam
    assert gemini_service._clean_and_parse_json is gpt_service._clean_and_parse_json
    assert set(gemini_service.__all__) == {"_clean_and_parse_json", "generate_exam"}


# ---------------------------------------------------------------------------
# exam_generator.generate_exam_with_ai
# ---------------------------------------------------------------------------
def test_generate_exam_with_ai_delegates_to_gpt_service():
    request = object()
    sentinel = SimpleNamespace(title="پیش‌نمایش")

    with patch(
        "app.services.ai.exam_generator.generate_exam", return_value=sentinel
    ) as mock_generate:
        result = generate_exam_with_ai(request)

    mock_generate.assert_called_once_with(request)
    assert result is sentinel


# ---------------------------------------------------------------------------
# prompt_builder.build_exam_prompt
# ---------------------------------------------------------------------------
def _make_request(**overrides):
    defaults = {
        "subject": "فیزیک",
        "topic": "جاذبه و اینرسی",
        "grade": "دهم",
        "num_questions": 5,
        "question_type": "multiple_choice",
        "difficulty": "medium",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_prompt_with_plain_string_values():
    prompt = build_exam_prompt(_make_request())

    assert "درس فیزیک" in prompt
    assert "تعداد سوالات: 5" in prompt
    assert "موضوع: جاذبه و اینرسی" in prompt
    assert '"question_type": "multiple_choice"' in prompt
    assert '"difficulty": "medium"' in prompt


def test_build_prompt_falls_back_to_subject_when_topic_empty():
    prompt = build_exam_prompt(_make_request(topic=""))

    assert "موضوع: فیزیک" in prompt


def test_build_prompt_unwraps_enum_values():
    request = _make_request(
        question_type=SimpleNamespace(value="true_false"),
        difficulty=SimpleNamespace(value="hard"),
    )
    prompt = build_exam_prompt(request)

    assert '"question_type": "true_false"' in prompt
    assert '"difficulty": "hard"' in prompt


def test_build_prompt_uses_default_labels_for_unknown_types():
    prompt = build_exam_prompt(_make_request(question_type="unknown_type", difficulty="unknown_diff"))

    assert "نوع سوال: چهارگزینه‌ای" in prompt
    assert "سطح دشواری: متوسط" in prompt
