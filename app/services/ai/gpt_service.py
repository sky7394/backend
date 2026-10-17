import json
import logging
import re

import httpx
from openai import OpenAI

from app.core.config import settings
from app.schemas.exam import ExamGenerateRequest, ExamPreviewOut
from app.services.ai.exceptions import (
    AIProviderCommunicationError,
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIResponseParsingError,
)
from app.services.ai.prompt_builder import build_exam_prompt
from app.services.ai.question_validator import normalize_questions

logger = logging.getLogger(__name__)


def _close_http_client(http_client: httpx.Client | None) -> None:
    if http_client is None:
        return
    try:
        http_client.close()
    except Exception as exc:
        logger.warning(
            "GapGPT HTTP client close failed. type=%s",
            type(exc).__name__,
        )


def _clean_and_parse_json(raw: str) -> dict:
    if not isinstance(raw, str) or not raw.strip():
        raise AIResponseParsingError("AI response content is empty")

    cleaned = raw.strip()
    cleaned = cleaned.replace("\x60\x60\x60json", "").replace("\x60\x60\x60", "").strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if not match:
            raise AIResponseParsingError("AI response contains malformed JSON") from exc
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as nested_exc:
            raise AIResponseParsingError("AI response contains malformed JSON") from nested_exc

    if not isinstance(data, dict):
        raise AIResponseParsingError("AI response must contain a JSON object")

    return data


def generate_exam(request: ExamGenerateRequest) -> ExamPreviewOut:
    api_key = (settings.OPENAI_API_KEY or "").strip()
    base_url = (settings.OPENAI_BASE_URL or "").strip().rstrip("/")
    model = (settings.OPENAI_MODEL or "gpt-4o").strip()

    if base_url and not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"

    if not api_key or not base_url:
        raise AIProviderConfigurationError("AI provider is not configured")

    custom_http_client: httpx.Client | None = None

    try:
        try:
            custom_http_client = httpx.Client(
                timeout=httpx.Timeout(
                    timeout=90.0,
                    connect=20.0,
                    read=90.0,
                    write=30.0,
                ),
                trust_env=False,
            )

            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=custom_http_client,
            )
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            logger.error(
                "GapGPT client initialization failed. type=%s status=%s",
                type(exc).__name__,
                status_code,
            )
            raise AIProviderCommunicationError("AI provider request failed") from exc

        user_prompt = build_exam_prompt(request)
        system_prompt = (
            "You are an expert Iranian teacher. You MUST generate the exam "
            "questions strictly in JSON format matching the requested schema."
        )

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            logger.error(
                "GapGPT request failed. type=%s status=%s",
                type(exc).__name__,
                status_code,
            )
            raise AIProviderCommunicationError("AI provider request failed") from exc

        choices = getattr(response, "choices", None)
        if not isinstance(choices, (list, tuple)) or not choices:
            raise AIProviderResponseError("AI provider returned no choices")

        first_choice = choices[0]
        if first_choice is None:
            raise AIProviderResponseError("AI provider returned no choices")

        message = getattr(first_choice, "message", None)
        raw_text = getattr(message, "content", None)

        if isinstance(raw_text, list):
            text_parts: list[str] = []
            for part in raw_text:
                if isinstance(part, str):
                    fragment = part
                elif isinstance(part, dict):
                    fragment = part.get("text", "")
                else:
                    fragment = getattr(part, "text", "")
                if isinstance(fragment, str):
                    text_parts.append(fragment)
            raw_text = "".join(text_parts)

        if not isinstance(raw_text, str) or not raw_text.strip():
            raise AIProviderResponseError("AI provider returned no message content")

        data = _clean_and_parse_json(raw_text)
        questions = normalize_questions(data, request)

        return ExamPreviewOut(
            title=data.get("title") or data.get("exam_title") or "آزمون بدون عنوان",
            subject=request.subject,
            grade=request.grade,
            questions=questions,
        )
    finally:
        _close_http_client(custom_http_client)
