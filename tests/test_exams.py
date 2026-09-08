from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Response
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


@pytest.mark.asyncio
async def test_download_exam_pdf_endpoint_success(mock_db: MagicMock):
    fake_exam = {
        "id": 1,
        "title": "آزمون فیزیک - گرانش",
        "questions": [
            {
                "question_text": "شتاب گرانش زمین چقدر است؟",
                "options": ["9.8", "10", "5", "1"],
                "correct_answer": "9.8",
            }
        ],
    }
    fake_pdf_bytes = b"%PDF-1.4 Fake PDF Content"

    with patch(
        "app.api.v1.endpoints.exams.get_exam_by_id",
        new=AsyncMock(return_value=fake_exam),
    ) as mock_get_exam, patch(
        "app.api.v1.endpoints.exams.generate_exam_pdf_bytes",
        return_value=fake_pdf_bytes,
    ) as mock_gen_pdf:
        response = await exams.download_exam_pdf_endpoint(
            exam_id=1,
            db=mock_db,
            current_user=MagicMock(),
        )

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.media_type == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="exam_1.pdf"'
    assert response.body == fake_pdf_bytes

    mock_get_exam.assert_awaited_once_with(mock_db, 1)
    mock_gen_pdf.assert_called_once_with(fake_exam)


@pytest.mark.asyncio
async def test_download_exam_pdf_endpoint_not_found(mock_db: MagicMock):
    with patch(
        "app.api.v1.endpoints.exams.get_exam_by_id",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(HTTPException) as context:
            await exams.download_exam_pdf_endpoint(
                exam_id=999,
                db=mock_db,
                current_user=MagicMock(),
            )

    assert context.value.status_code == 404
    assert context.value.detail == "Exam not found"


@pytest.mark.asyncio
async def test_download_exam_pdf_endpoint_pdf_generation_error(mock_db: MagicMock):
    fake_exam = {"id": 1, "title": "آزمون فیزیک"}

    with patch(
        "app.api.v1.endpoints.exams.get_exam_by_id",
        new=AsyncMock(return_value=fake_exam),
    ), patch(
        "app.api.v1.endpoints.exams.generate_exam_pdf_bytes",
        side_effect=RuntimeError("PDF engine failure"),
    ):
        with pytest.raises(HTTPException) as context:
            await exams.download_exam_pdf_endpoint(
                exam_id=1,
                db=mock_db,
                current_user=MagicMock(),
            )

    assert context.value.status_code == 500
    assert context.value.detail == "Unable to generate the exam PDF."


@pytest.mark.asyncio
async def test_download_exam_docx_endpoint_success(mock_db: MagicMock):
    fake_exam = {
        "id": 1,
        "title": "آزمون فیزیک - گرانش",
        "questions": [
            {
                "question_text": "شتاب گرانش زمین چقدر است؟",
                "options": ["9.8", "10", "5", "1"],
                "correct_answer": "9.8",
            }
        ],
    }
    fake_docx_bytes = b"Fake DOCX Content"

    with patch(
        "app.api.v1.endpoints.exams.get_exam_by_id",
        new_callable=AsyncMock,
        return_value=fake_exam,
    ) as mock_get_exam, patch(
        "app.services.documents.docx_service.generate_exam_docx_bytes",
        return_value=fake_docx_bytes,
    ) as mock_gen_docx:
        response = await exams.download_exam_docx_endpoint(
            exam_id=1,
            db=mock_db,
            current_user=MagicMock(),
        )

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert (
        response.media_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert 'attachment; filename="exam_1.docx"' in response.headers["content-disposition"]
    assert response.body == fake_docx_bytes

    mock_get_exam.assert_awaited_once_with(mock_db, 1)
    mock_gen_docx.assert_called_once_with(fake_exam)


@pytest.mark.asyncio
async def test_download_exam_docx_endpoint_not_found(mock_db: MagicMock):
    with patch(
        "app.api.v1.endpoints.exams.get_exam_by_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(HTTPException) as context:
            await exams.download_exam_docx_endpoint(
                exam_id=999,
                db=mock_db,
                current_user=MagicMock(),
            )

    assert context.value.status_code == 404
    assert context.value.detail == "Exam not found"


@pytest.mark.asyncio
async def test_download_exam_docx_endpoint_generation_error(mock_db: MagicMock):
    fake_exam = {"id": 1, "title": "آزمون فیزیک"}

    with patch(
        "app.api.v1.endpoints.exams.get_exam_by_id",
        new_callable=AsyncMock,
        return_value=fake_exam,
    ), patch(
        "app.services.documents.docx_service.generate_exam_docx_bytes",
        side_effect=RuntimeError("DOCX engine failure"),
    ):
        with pytest.raises(HTTPException) as context:
            await exams.download_exam_docx_endpoint(
                exam_id=1,
                db=mock_db,
                current_user=MagicMock(),
            )

    assert context.value.status_code == 500
    assert context.value.detail == "Unable to generate the exam Word document."
