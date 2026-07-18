import json
import re

from openai import OpenAI

from app.core.config import settings
from app.schemas.generate import ExamGenerateRequest, ExamOut
from app.services.ai.exceptions import (
    AIProviderCommunicationError,
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIResponseParsingError,
)
from app.services.ai.prompt_builder import build_exam_prompt
from app.services.ai.question_validator import normalize_questions


def _clean_and_parse_json(raw: str) -> dict:
    if not isinstance(raw, str) or not raw.strip():
        raise AIResponseParsingError("AI response content is empty")

    cleaned = raw.strip()
    fenced_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        cleaned = fenced_match.group(1).strip()

    object_start = cleaned.find("{")
    array_start = cleaned.find("[")
    starts = [position for position in (object_start, array_start) if position >= 0]
    if not starts:
        raise AIResponseParsingError("AI response does not contain JSON")

    candidate = cleaned[min(starts):]
    decoder = json.JSONDecoder()
    try:
        data, _ = decoder.raw_decode(candidate)
    except json.JSONDecodeError:
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            data, _ = decoder.raw_decode(candidate)
        except json.JSONDecodeError as exc:
            raise AIResponseParsingError("AI response contains malformed JSON") from exc

    if not isinstance(data, dict):
        raise AIResponseParsingError("AI response JSON must be an object")

    return data


def generate_exam(request: ExamGenerateRequest) -> ExamOut:
    api_key = settings.GEMINI_API_KEY or settings.OPENAI_API_KEY
    if not api_key or not settings.GEMINI_BASE_URL or not settings.GEMINI_MODEL:
        raise AIProviderConfigurationError("AI provider is not configured")

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=settings.GEMINI_BASE_URL,
        )
        response = client.chat.completions.create(
            model=settings.GEMINI_MODEL,
            messages=[{"role": "user", "content": build_exam_prompt(request)}],
        )
    except Exception as exc:
        raise AIProviderCommunicationError("AI provider request failed") from exc

    choices = getattr(response, "choices", None)
    if not isinstance(choices, (list, tuple)) or not choices:
        raise AIProviderResponseError("AI provider returned no choices")

    message = getattr(choices[0], "message", None)
    raw_text = getattr(message, "content", None)
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise AIProviderResponseError("AI provider returned no message content")

    data = _clean_and_parse_json(raw_text)
    questions = normalize_questions(data, request)

    return ExamOut(
        title=data.get("title", "آزمون بدون عنوان"),
        subject=request.subject,
        grade=request.grade,
        questions=questions,
    )
