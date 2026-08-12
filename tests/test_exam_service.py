from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.schemas.exam import ExamFinalizeOut, ExamGenerateRequest, ExamPreviewOut
from app.services.ai.exceptions import AIResponseValidationError
from app.services.exams import exam_service


@pytest.fixture
def sample_generate_request():
    return ExamGenerateRequest(
        grade=10,
        subject="physics",
        num_questions=1,
        question_type="multiple_choice",
        difficulty="medium",
        topic="gravity",
    )


@pytest.fixture
def mock_ai_raw_response():
    return {
        "title": "Physics Exam",
        "grade": 10,
        "subject": "physics",
        "questions": [
            {
                "question_text": "What is gravity?",
                "question_type": "multiple_choice",
                "difficulty": "medium",
                "grade": 10,
                "subject": "physics",
                "topic": "gravity",
                "options": ["A force", "A chemical", "A particle", "Nothing"],
                "correct_answer": "A force",
                "explanation": "Gravity is the attractive force between masses.",
            }
        ],
    }


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


@pytest.mark.asyncio
async def test_preview_exam_service_success(
    sample_generate_request, mock_ai_raw_response
):
    with patch(
        "app.services.exams.exam_service.run_in_threadpool",
        new=AsyncMock(return_value=mock_ai_raw_response),
    ) as mock_thread:
        result = await exam_service.preview_exam(sample_generate_request)

    assert isinstance(result, ExamPreviewOut)
    assert result.title == "Physics Exam"
    assert len(result.questions) == 1
    assert result.questions[0].question_text == "What is gravity?"
    mock_thread.assert_awaited_once_with(
        exam_service.generate_exam_with_ai, sample_generate_request
    )


@pytest.mark.asyncio
async def test_preview_exam_validation_failure(sample_generate_request):
    invalid_ai_response = {
        "title": "Invalid Exam",
        "questions": [],  # Missing fields like grade and subject
    }

    with patch(
        "app.services.exams.exam_service.run_in_threadpool",
        new=AsyncMock(return_value=invalid_ai_response),
    ):
        with pytest.raises(AIResponseValidationError) as exc_info:
            await exam_service.preview_exam(sample_generate_request)

    assert "Generated exam preview data is invalid" in str(exc_info.value)


@pytest.mark.asyncio
async def test_finalize_exam_service_success(
    sample_generate_request, mock_ai_raw_response, mock_db
):
    finalized_data = ExamFinalizeOut(
        title="Physics Exam",
        grade=10,
        subject="physics",
        questions=[
            {
                "id": 42,
                "question_text": "What is gravity?",
                "question_type": "multiple_choice",
                "difficulty": "medium",
                "grade": 10,
                "subject": "physics",
                "topic": "gravity",
                "options": ["A force", "A chemical", "A particle", "Nothing"],
                "correct_answer": "A force",
                "explanation": "Gravity is the attractive force between masses.",
            }
        ],
    )

    with patch(
        "app.services.exams.exam_service.run_in_threadpool",
        new=AsyncMock(return_value=mock_ai_raw_response),
    ), patch(
        "app.services.exams.exam_service.create_exam",
        new=AsyncMock(return_value=finalized_data),
    ) as mock_create_exam:

        result = await exam_service.finalize_exam(sample_generate_request, mock_db)

    assert isinstance(result, ExamFinalizeOut)
    assert result.questions[0].id == 42
    mock_create_exam.assert_awaited_once()


@pytest.mark.asyncio
async def test_finalize_exam_validation_failure_on_storage_output(
    sample_generate_request, mock_ai_raw_response, mock_db
):
    # If the database returns invalid schemas, validate_finalized_exam must raise validation error
    invalid_saved_exam = {
        "title": "Corrupted Saved Exam",
        "questions": [],  # Invalid fields
    }

    with patch(
        "app.services.exams.exam_service.run_in_threadpool",
        new=AsyncMock(return_value=mock_ai_raw_response),
    ), patch(
        "app.services.exams.exam_service.create_exam",
        new=AsyncMock(return_value=invalid_saved_exam),
    ):
        with pytest.raises(AIResponseValidationError) as exc_info:
            await exam_service.finalize_exam(sample_generate_request, mock_db)

    assert "Generated finalized exam data is invalid" in str(exc_info.value)
