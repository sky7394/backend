import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.schemas.exam import ExamFinalizeOut, ExamGenerateRequest, ExamPreviewOut
from app.services.ai.exceptions import AIResponseValidationError
from app.services.exams.exam_service import (
    finalize_exam,
    preview_exam,
    validate_finalized_exam,
    validate_preview_exam,
)


def _minimal_preview_payload(title: str = "آزمون فیزیک") -> dict:
    return {
        "title": title,
        "grade": 10,
        "subject": "فیزیک",
        "questions": [],
    }


def _minimal_finalized_payload(exam_id, title: str = "آزمون فیزیک") -> dict:
    return {
        "exam_id": exam_id,
        "title": title,
        "grade": 10,
        "subject": "فیزیک",
        "questions": [],
    }


def test_validate_preview_exam_success():
    valid_data = _minimal_preview_payload("فیزیک")
    result = validate_preview_exam(valid_data)
    assert isinstance(result, ExamPreviewOut)
    assert result.title == "فیزیک"
    assert result.grade == 10
    assert result.subject == "فیزیک"


def test_validate_preview_exam_validation_error():
    invalid_data = {"title": 12345, "questions": "not-a-list"}
    with pytest.raises(AIResponseValidationError) as exc_info:
        validate_preview_exam(invalid_data)
    assert "Generated exam preview data is invalid" in str(exc_info.value)


def test_validate_finalized_exam_success():
    exam_id = uuid4()
    valid_data = _minimal_finalized_payload(exam_id, "مکانیک")
    result = validate_finalized_exam(valid_data)
    assert isinstance(result, ExamFinalizeOut)
    assert result.title == "مکانیک"
    assert result.grade == 10
    assert result.subject == "فیزیک"


def test_validate_finalized_exam_validation_error():
    invalid_data = {"title": None, "grade": "invalid"}
    with pytest.raises(AIResponseValidationError) as exc_info:
        validate_finalized_exam(invalid_data)
    assert "Generated finalized exam data is invalid" in str(exc_info.value)


@pytest.mark.asyncio
async def test_preview_exam_success():
    request = ExamGenerateRequest(
        topic="موتورهای درون‌سوز",
        grade=11,
        subject="مکانیک خودرو",
        number_of_questions=5,
    )
    mock_ai_output = _minimal_preview_payload("موتورهای درون‌سوز")

    with patch(
        "app.services.exams.exam_service.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_threadpool:
        mock_threadpool.return_value = mock_ai_output

        result = await preview_exam(request)

        assert isinstance(result, ExamPreviewOut)
        assert result.title == "موتورهای درون‌سوز"
        mock_threadpool.assert_called_once()


@pytest.mark.asyncio
async def test_finalize_exam_with_authenticated_user():
    user_id = uuid4()
    exam_id = uuid4()

    mock_user = MagicMock()
    mock_user.id = user_id

    mock_db = AsyncMock()
    request = ExamGenerateRequest(
        topic="سیستم تعلیق",
        grade=11,
        subject="مکانیک خودرو",
        number_of_questions=3,
    )

    mock_ai_output = _minimal_preview_payload("سیستم تعلیق")
    mock_saved_exam = _minimal_finalized_payload(exam_id, "سیستم تعلیق")

    with patch(
        "app.services.exams.exam_service.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_threadpool, patch(
        "app.services.exams.exam_service.create_exam",
        new_callable=AsyncMock,
    ) as mock_create_exam:
        mock_threadpool.return_value = mock_ai_output
        mock_create_exam.return_value = mock_saved_exam

        result = await finalize_exam(request=request, db=mock_db, current_user=mock_user)

        assert isinstance(result, ExamFinalizeOut)
        assert result.title == "سیستم تعلیق"

        mock_threadpool.assert_called_once()
        mock_create_exam.assert_called_once()
        _, kwargs = mock_create_exam.call_args
        assert kwargs["created_by_user_id"] == user_id


@pytest.mark.asyncio
async def test_finalize_exam_without_user():
    exam_id = uuid4()

    mock_db = AsyncMock()
    request = ExamGenerateRequest(
        topic="شاسی خودرو",
        grade=11,
        subject="مکانیک خودرو",
        number_of_questions=2,
    )

    mock_ai_output = _minimal_preview_payload("شاسی خودرو")
    mock_saved_exam = _minimal_finalized_payload(exam_id, "شاسی خودرو")

    with patch(
        "app.services.exams.exam_service.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_threadpool, patch(
        "app.services.exams.exam_service.create_exam",
        new_callable=AsyncMock,
    ) as mock_create_exam:
        mock_threadpool.return_value = mock_ai_output
        mock_create_exam.return_value = mock_saved_exam

        result = await finalize_exam(request=request, db=mock_db, current_user=None)

        assert isinstance(result, ExamFinalizeOut)
        assert result.title == "شاسی خودرو"

        mock_threadpool.assert_called_once()
        mock_create_exam.assert_called_once()
        _, kwargs = mock_create_exam.call_args
        assert kwargs["created_by_user_id"] is None
