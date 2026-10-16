from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status

from app.api.v1.endpoints import exams

MODULE = "app.api.v1.endpoints.exams"

# Minimal valid payload matching ExamPreviewOut / ExamFinalizeOut schemas
PREVIEW_DATA = {
    "title": "Physics exam",
    "grade": "10",
    "subject": "Physics",
    "questions": [],
}

FINAL_DATA = {
    "title": "Physics exam",
    "grade": "10",
    "subject": "Physics",
    "questions": [],
}


class ModelDumpExam:
    def model_dump(self):
        return {"title": "Model dump exam", "questions": []}


class DictExam:
    def dict(self):
        return {"title": "Dict exam", "questions": []}


class ToDictExam:
    def to_dict(self):
        return {"title": "To dict exam", "questions": []}


@pytest.fixture
def mock_request():
    return MagicMock(name="exam_request")


@pytest.fixture
def db():
    return AsyncMock(name="db")


# ==============================================================================
# 1. Direct Unit Tests for Helper Functions (Lines 31 - 86)
# ==============================================================================

def test_map_ai_exception_validation_and_value_error():
    exc1 = exams.AIResponseValidationError("invalid")
    res1 = exams.map_ai_exception_to_http(exc1)
    assert res1.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert res1.detail == "The generated exam data is invalid."

    exc2 = ValueError("value error")
    res2 = exams.map_ai_exception_to_http(exc2)
    assert res2.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert res2.detail == "The generated exam data is invalid."


def test_map_ai_exception_configuration_error():
    exc = exams.AIProviderConfigurationError("config")
    res = exams.map_ai_exception_to_http(exc)
    assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert res.detail == "AI exam generation is temporarily unavailable."


def test_map_ai_exception_parsing_error():
    exc = exams.AIResponseParsingError("parse")
    res = exams.map_ai_exception_to_http(exc)
    assert res.status_code == status.HTTP_502_BAD_GATEWAY
    assert res.detail == "The AI provider returned an invalid response."


def test_map_ai_exception_communication_and_response_error():
    exc1 = exams.AIProviderCommunicationError("comm")
    res1 = exams.map_ai_exception_to_http(exc1)
    assert res1.status_code == status.HTTP_502_BAD_GATEWAY
    assert res1.detail == "The AI provider could not generate an exam."

    exc2 = exams.AIProviderResponseError("resp")
    res2 = exams.map_ai_exception_to_http(exc2)
    assert res2.status_code == status.HTTP_502_BAD_GATEWAY
    assert res2.detail == "The AI provider could not generate an exam."


def test_map_ai_exception_generic_fallback():
    exc = RuntimeError("unknown issue")
    res = exams.map_ai_exception_to_http(exc)
    assert res.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert res.detail == "Internal server error"


def test_coerce_preview_result_non_dict():
    dummy = object()
    result = exams._coerce_preview_result(dummy)
    assert result is dummy


def test_coerce_preview_result_invalid_dict_raises():
    with pytest.raises(HTTPException) as caught:
        exams._coerce_preview_result({"invalid_key": 123})
    assert caught.value.status_code == 500
    assert caught.value.detail == "Unable to generate the exam preview."


def test_coerce_finalize_result_non_dict():
    dummy = object()
    result = exams._coerce_finalize_result(dummy)
    assert result is dummy


def test_coerce_finalize_result_invalid_dict_raises():
    with pytest.raises(HTTPException) as caught:
        exams._coerce_finalize_result({"invalid_key": 123})
    assert caught.value.status_code == 500
    assert caught.value.detail == "Unable to finalize the exam."


# ==============================================================================
# 2. Preview Endpoint Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_preview_success(mock_request):
    dummy_out = exams.ExamPreviewOut(
        title="Physics exam",
        grade="10",
        subject="Physics",
        questions=[]
    )
    with patch(f"{MODULE}.preview_exam", new=AsyncMock(return_value=dummy_out)):
        result = await exams.preview_exam_endpoint(mock_request)
    assert result == dummy_out


@pytest.mark.asyncio
async def test_preview_reraises_http_exception(mock_request):
    original = HTTPException(status_code=409, detail="Conflict")
    with patch(f"{MODULE}.preview_exam", new=AsyncMock(side_effect=original)):
        with pytest.raises(HTTPException) as caught:
            await exams.preview_exam_endpoint(mock_request)
    assert caught.value is original


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,expected_status",
    [
        (exams.AIProviderConfigurationError("conf"), 503),
        (exams.AIProviderCommunicationError("comm"), 502),
        (exams.AIProviderResponseError("resp"), 502),
        (exams.AIResponseParsingError("parse"), 502),
        (exams.AIResponseValidationError("val"), 422),
        (ValueError("val_err"), 422),
    ],
)
async def test_preview_maps_known_errors(mock_request, error, expected_status):
    with patch(f"{MODULE}.preview_exam", new=AsyncMock(side_effect=error)):
        with pytest.raises(HTTPException) as caught:
            await exams.preview_exam_endpoint(mock_request)
    assert caught.value.status_code == expected_status


@pytest.mark.asyncio
async def test_preview_unexpected_error_returns_500(mock_request):
    with patch(
        f"{MODULE}.preview_exam",
        new=AsyncMock(side_effect=RuntimeError("unexpected")),
    ):
        with pytest.raises(HTTPException) as caught:
            await exams.preview_exam_endpoint(mock_request)

    assert caught.value.status_code == 500
    assert caught.value.detail == "Unable to generate the exam preview."


# ==============================================================================
# 3. Finalize Endpoint Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_finalize_success(mock_request, db):
    dummy_out = exams.ExamFinalizeOut(
        title="Physics exam",
        grade="10",
        subject="Physics",
        questions=[]
    )
    with patch(f"{MODULE}.finalize_exam", new=AsyncMock(return_value=dummy_out)):
        result = await exams.finalize_exam_endpoint(mock_request, db)
    assert result == dummy_out


@pytest.mark.asyncio
async def test_finalize_reraises_http_exception(mock_request, db):
    original = HTTPException(status_code=400, detail="Bad request")
    with patch(f"{MODULE}.finalize_exam", new=AsyncMock(side_effect=original)):
        with pytest.raises(HTTPException) as caught:
            await exams.finalize_exam_endpoint(mock_request, db)
    assert caught.value is original


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,expected_status",
    [
        (exams.AIProviderConfigurationError("conf"), 503),
        (exams.AIProviderCommunicationError("comm"), 502),
        (exams.AIProviderResponseError("resp"), 502),
        (exams.AIResponseParsingError("parse"), 502),
        (exams.AIResponseValidationError("val"), 422),
        (ValueError("val_err"), 422),
    ],
)
async def test_finalize_maps_known_errors(mock_request, db, error, expected_status):
    with patch(f"{MODULE}.finalize_exam", new=AsyncMock(side_effect=error)):
        with pytest.raises(HTTPException) as caught:
            await exams.finalize_exam_endpoint(mock_request, db)
    assert caught.value.status_code == expected_status


@pytest.mark.asyncio
async def test_finalize_unexpected_error_returns_500(mock_request, db):
    with patch(
        f"{MODULE}.finalize_exam",
        new=AsyncMock(side_effect=RuntimeError("unexpected")),
    ):
        with pytest.raises(HTTPException) as caught:
            await exams.finalize_exam_endpoint(mock_request, db)

    assert caught.value.status_code == 500
    assert caught.value.detail == "Unable to finalize the exam."


# ==============================================================================
# 4. Get & List Endpoints Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_get_exam_success(db):
    expected = MagicMock()
    with patch(f"{MODULE}.get_exam_by_id", new=AsyncMock(return_value=expected)) as get_exam:
        result = await exams.get_exam_endpoint(7, db)

    assert result is expected
    get_exam.assert_awaited_once_with(db, 7)


@pytest.mark.asyncio
async def test_get_exam_not_found(db):
    with patch(f"{MODULE}.get_exam_by_id", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as caught:
            await exams.get_exam_endpoint(404, db)

    assert caught.value.status_code == 404
    assert caught.value.detail == "Exam not found"


@pytest.mark.asyncio
async def test_list_exams(db):
    expected = [MagicMock(), MagicMock()]
    with patch(f"{MODULE}.list_exams", new=AsyncMock(return_value=expected)) as service:
        result = await exams.list_exams_endpoint(db, skip=10, limit=25)

    assert result == expected
    service.assert_awaited_once_with(db, skip=10, limit=25)


# ==============================================================================
# 5. PDF & DOCX Export Endpoints Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_pdf_not_found(db):
    with patch(f"{MODULE}.get_exam_by_id", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as caught:
            await exams.download_exam_pdf_endpoint(404, include_answers=True, db=db)

    assert caught.value.status_code == 404
    assert caught.value.detail == "Exam not found"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exam_obj", "expected"),
    [
        (ModelDumpExam(), {"title": "Model dump exam", "questions": []}),
        (DictExam(), {"title": "Dict exam", "questions": []}),
        (ToDictExam(), {"title": "To dict exam", "questions": []}),
        (
            {"title": "Dictionary exam", "questions": []},
            {"title": "Dictionary exam", "questions": []},
        ),
        (
            SimpleNamespace(title="ORM exam", questions=["q1"]),
            {"title": "ORM exam", "questions": ["q1"]},
        ),
        (object(), {"title": "آزمون", "questions": []}),
    ],
)
async def test_pdf_success_for_all_exam_shapes(db, exam_obj, expected):
    pdf_bytes = b"%PDF-1.4 test"

    with (
        patch(f"{MODULE}.get_exam_by_id", new=AsyncMock(return_value=exam_obj)),
        patch(f"{MODULE}.generate_exam_pdf_bytes", return_value=pdf_bytes) as generate,
    ):
        response = await exams.download_exam_pdf_endpoint(12, include_answers=True, db=db)

    assert response.status_code == 200
    assert response.body == pdf_bytes
    assert response.media_type == "application/pdf"
    assert response.headers["content-disposition"].startswith('attachment; filename="exam_12.pdf"')
    generate.assert_called_once_with(expected, include_answers=True)


@pytest.mark.asyncio
async def test_pdf_generation_error_returns_500(db):
    with (
        patch(f"{MODULE}.get_exam_by_id", new=AsyncMock(return_value={"title": "Exam", "questions": []})),
        patch(f"{MODULE}.generate_exam_pdf_bytes", side_effect=RuntimeError("PDF failed")),
    ):
        with pytest.raises(HTTPException) as caught:
            await exams.download_exam_pdf_endpoint(3, include_answers=True, db=db)

    assert caught.value.status_code == 500
    assert caught.value.detail == "Unable to generate the exam PDF."


@pytest.mark.asyncio
async def test_docx_not_found(db):
    with patch(f"{MODULE}.get_exam_by_id", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as caught:
            await exams.download_exam_docx_endpoint(404, include_answers=True, db=db)

    assert caught.value.status_code == 404
    assert caught.value.detail == "Exam not found"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exam_obj", "expected"),
    [
        (ModelDumpExam(), {"title": "Model dump exam", "questions": []}),
        (DictExam(), {"title": "Dict exam", "questions": []}),
        (ToDictExam(), {"title": "To dict exam", "questions": []}),
        (
            {"title": "Dictionary exam", "questions": []},
            {"title": "Dictionary exam", "questions": []},
        ),
        (
            SimpleNamespace(title="ORM exam", questions=["q1"]),
            {"title": "ORM exam", "questions": ["q1"]},
        ),
        (object(), {"title": "آزمون", "questions": []}),
    ],
)
async def test_docx_success_for_all_exam_shapes(db, exam_obj, expected):
    docx_bytes = b"PK mock docx"

    with (
        patch(f"{MODULE}.get_exam_by_id", new=AsyncMock(return_value=exam_obj)),
        patch(f"{MODULE}.generate_exam_docx_bytes", return_value=docx_bytes) as generate,
    ):
        response = await exams.download_exam_docx_endpoint(18, include_answers=True, db=db)

    assert response.status_code == 200
    assert response.body == docx_bytes
    assert response.media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert response.headers["content-disposition"].startswith('attachment; filename="exam_18.docx"')
    generate.assert_called_once_with(expected, include_answers=True)


@pytest.mark.asyncio
async def test_docx_missing_library_returns_500(db):
    exam_data = {"title": "Exam", "questions": []}

    with (
        patch(f"{MODULE}.get_exam_by_id", new=AsyncMock(return_value=exam_data)),
        patch(f"{MODULE}.generate_exam_docx_bytes", side_effect=ModuleNotFoundError("python-docx")),
    ):
        with pytest.raises(HTTPException) as caught:
            await exams.download_exam_docx_endpoint(5, include_answers=True, db=db)

    assert caught.value.status_code == 500
    assert caught.value.detail == "DOCX generation library is missing on server."


@pytest.mark.asyncio
async def test_docx_generation_error_returns_500(db):
    exam_data = {"title": "Exam", "questions": []}

    with (
        patch(f"{MODULE}.get_exam_by_id", new=AsyncMock(return_value=exam_data)),
        patch(f"{MODULE}.generate_exam_docx_bytes", side_effect=RuntimeError("DOCX failed")),
    ):
        with pytest.raises(HTTPException) as caught:
            await exams.download_exam_docx_endpoint(6, include_answers=True, db=db)

    assert caught.value.status_code == 500
    assert caught.value.detail == "Unable to generate the exam Word document."
