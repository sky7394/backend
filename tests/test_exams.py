from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints import exams
from app.schemas.exam import ExamGenerateRequest
from app.services.ai.exceptions import (
    AIProviderCommunicationError,
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIResponseParsingError,
    AIResponseValidationError,
)


@pytest.fixture
def valid_request_payload() -> ExamGenerateRequest:
    return ExamGenerateRequest(
        grade=10,
        subject="physics",
        num_questions=2,
        question_type="multiple_choice",
        difficulty="medium",
        topic="gravity",
    )


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock(spec=AsyncSession)


@pytest.mark.asyncio
async def test_preview_exam_endpoint_success(
    valid_request_payload: ExamGenerateRequest,
):
    expected_output = {
        "title": "Physics Exam",
        "grade": 10,
        "subject": "physics",
        "questions": [],
    }

    with patch(
        "app.api.v1.endpoints.exams.preview_exam",
        new=AsyncMock(return_value=expected_output),
    ) as mock_preview:
        response = await exams.preview_exam_endpoint(valid_request_payload)

    assert response.model_dump(mode="json") == expected_output
    mock_preview.assert_awaited_once_with(valid_request_payload)


@pytest.mark.asyncio
async def test_finalize_exam_endpoint_success(
    valid_request_payload: ExamGenerateRequest,
    mock_db: MagicMock,
):
    expected_output = {
        "title": "Physics Exam",
        "grade": 10,
        "subject": "physics",
        "questions": [
            {
                "id": 1,
                "question_text": "gravity test",
                "question_type": "multiple_choice",
                "difficulty": "medium",
                "grade": 10,
                "subject": "physics",
                "correct_answer": "A force",
            }
        ],
    }

    with patch(
        "app.api.v1.endpoints.exams.finalize_exam",
        new=AsyncMock(return_value=expected_output),
    ) as mock_finalize:
        response = await exams.finalize_exam_endpoint(
            valid_request_payload,
            mock_db,
        )

    assert response.model_dump(mode="json", exclude_none=True) == expected_output
    mock_finalize.assert_awaited_once_with(
        valid_request_payload,
        mock_db,
    )


@pytest.mark.asyncio
async def test_preview_exam_maps_configuration_error(
    valid_request_payload: ExamGenerateRequest,
):
    with patch(
        "app.api.v1.endpoints.exams.preview_exam",
        new=AsyncMock(
            side_effect=AIProviderConfigurationError("Config issue"),
        ),
    ):
        with pytest.raises(HTTPException) as context:
            await exams.preview_exam_endpoint(valid_request_payload)

    assert context.value.status_code == 503
    assert context.value.detail == "AI exam generation is temporarily unavailable."


@pytest.mark.asyncio
async def test_preview_exam_maps_parsing_error(
    valid_request_payload: ExamGenerateRequest,
):
    with patch(
        "app.api.v1.endpoints.exams.preview_exam",
        new=AsyncMock(
            side_effect=AIResponseParsingError("Failed to parse JSON"),
        ),
    ):
        with pytest.raises(HTTPException) as context:
            await exams.preview_exam_endpoint(valid_request_payload)

    assert context.value.status_code == 502
    assert context.value.detail == "The AI provider returned an invalid response."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception_cls",
    [
        AIProviderCommunicationError,
        AIProviderResponseError,
    ],
)
async def test_preview_exam_maps_communication_or_response_errors(
    valid_request_payload: ExamGenerateRequest,
    exception_cls: type[Exception],
):
    with patch(
        "app.api.v1.endpoints.exams.preview_exam",
        new=AsyncMock(
            side_effect=exception_cls("Network/Provider issue"),
        ),
    ):
        with pytest.raises(HTTPException) as context:
            await exams.preview_exam_endpoint(valid_request_payload)

    assert context.value.status_code == 502
    assert context.value.detail == "The AI provider could not generate an exam."


@pytest.mark.asyncio
async def test_preview_exam_maps_validation_error(
    valid_request_payload: ExamGenerateRequest,
):
    with patch(
        "app.api.v1.endpoints.exams.preview_exam",
        new=AsyncMock(
            side_effect=AIResponseValidationError("Validation failed"),
        ),
    ):
        with pytest.raises(HTTPException) as context:
            await exams.preview_exam_endpoint(valid_request_payload)

    assert context.value.status_code == 422
    assert context.value.detail == "The generated exam data is invalid."


@pytest.mark.asyncio
async def test_finalize_exam_unexpected_error_returns_500(
    valid_request_payload: ExamGenerateRequest,
    mock_db: MagicMock,
):
    with patch(
        "app.api.v1.endpoints.exams.finalize_exam",
        new=AsyncMock(
            side_effect=RuntimeError("Unexpected system failure"),
        ),
    ):
        with pytest.raises(HTTPException) as context:
            await exams.finalize_exam_endpoint(
                valid_request_payload,
                mock_db,
            )

    assert context.value.status_code == 500
    assert context.value.detail == "Unable to finalize the exam."
