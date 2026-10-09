import pytest
import json
from unittest.mock import MagicMock, patch

from app.services.ai.gpt_service import generate_exam, _clean_and_parse_json
from app.services.ai.exceptions import (
    AIProviderConfigurationError,
    AIProviderCommunicationError,
    AIResponseParsingError,
)
from app.schemas.exam import ExamGenerateRequest

# --- تست‌های بخش Parser ---
def test_clean_and_parse_json_valid():
    raw = '{"key": "value"}'
    assert _clean_and_parse_json(raw) == {"key": "value"}

def test_clean_and_parse_json_with_markdown():
    raw = '```json\n{"key": "value"}\n```'

    assert _clean_and_parse_json(raw) == {"key": "value"}

def test_clean_and_parse_json_invalid_format():
    with pytest.raises(AIResponseParsingError):
        _clean_and_parse_json("invalid json")

# --- تست‌های اصلی سرویس ---

@patch("app.services.ai.gpt_service.settings")
@patch("app.services.ai.gpt_service.OpenAI")
@patch("app.services.ai.gpt_service.build_exam_prompt")
@patch("app.services.ai.gpt_service.normalize_questions")
def test_generate_exam_success(mock_norm, mock_prompt, mock_openai, mock_settings):
    # تنظیمات Mock
    mock_settings.OPENAI_API_KEY = "test_key"
    mock_settings.OPENAI_BASE_URL = "https://api.test.com"
    mock_settings.OPENAI_MODEL = "gpt-4o"
    
    # تنظیم کلاینت جعلی
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    # تنظیم پاسخ جعلی OpenAI
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"title": "Test Exam", "questions": []}'))]
    mock_client.chat.completions.create.return_value = mock_response
    
    mock_prompt.return_value = "Prompt text"
    mock_norm.return_value = []

    # استفاده از امضای صحیح کلاس ExamGenerateRequest
    request = ExamGenerateRequest(grade=10, subject="Math")
    
    result = generate_exam(request)
    
    assert result.title == "Test Exam"
    mock_client.chat.completions.create.assert_called_once()

@patch("app.services.ai.gpt_service.settings")
def test_generate_exam_config_error(mock_settings):
    mock_settings.OPENAI_API_KEY = "" # تنظیم بدون کلید برای ایجاد خطا
    request = ExamGenerateRequest(grade=10, subject="Math")
    
    with pytest.raises(AIProviderConfigurationError):
        generate_exam(request)

@patch("app.services.ai.gpt_service.settings")
@patch("app.services.ai.gpt_service.OpenAI")
@patch("app.services.ai.gpt_service.build_exam_prompt")
def test_generate_exam_api_exception(mock_prompt, mock_openai, mock_settings):
    mock_settings.OPENAI_API_KEY = "test_key"
    mock_settings.OPENAI_BASE_URL = "https://api.test.com"
    
    # شبیه‌سازی خطا در اتصال
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.side_effect = Exception("API Connection Failed")
    
    request = ExamGenerateRequest(grade=10, subject="Math")
    
    with pytest.raises(AIProviderCommunicationError):
        generate_exam(request)
