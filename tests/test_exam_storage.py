from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExamModel
from app.schemas.exam import ExamPreviewOut
from app.services.exams import exam_storage


@pytest.fixture
def mock_db_session() -> MagicMock:
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def sample_preview_payload():
    return ExamPreviewOut(
        title="Math Exam",
        grade=8,
        subject="mathematics",
        questions=[
            {
                "question_text": "2 + 2 = ?",
                "question_type": "multiple_choice",
                "difficulty": "easy",
                "grade": 8,
                "subject": "mathematics",
                "topic": "addition",
                "options": ["3", "4", "5", "6"],
                "correct_answer": "4",
                "explanation": "Basic addition.",
            }
        ],
    )


@pytest.mark.asyncio
async def test_create_exam_storage_success(mock_db_session, sample_preview_payload):
    payload_dict = sample_preview_payload.model_dump()
    payload_dict["description"] = "Mock Description"

    def assign_database_ids(exam: ExamModel) -> None:
        exam.id = 1
        for question_id, question in enumerate(exam.questions, start=100):
            question.id = question_id

    mock_db_session.add.side_effect = assign_database_ids

    result = await exam_storage.create_exam(mock_db_session, payload_dict)

    assert result.title == "Math Exam"
    assert result.grade == 8
    assert len(result.questions) == 1
    assert result.questions[0].id == 100
    assert result.questions[0].question_text == "2 + 2 = ?"

    mock_db_session.add.assert_called_once()
    mock_db_session.flush.assert_awaited_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.rollback.assert_not_called()



@pytest.mark.asyncio
async def test_create_exam_storage_database_exception_rolls_back(
    mock_db_session, sample_preview_payload
):
    # Force flush to raise error to trigger rollback block
    mock_db_session.flush.side_effect = RuntimeError("DB connection lost")

    with pytest.raises(RuntimeError) as exc_info:
        await exam_storage.create_exam(mock_db_session, sample_preview_payload)

    assert "DB connection lost" in str(exc_info.value)
    mock_db_session.rollback.assert_awaited_once()
    mock_db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_exam_by_id_found(mock_db_session):
    # Mocking SQLAlchemy execution result
    mock_exam = ExamModel(
        id=101,
        title="Physics 101",
        grade=11,
        subject="physics",
        questions=[],
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_exam
    mock_db_session.execute.return_value = mock_result

    result = await exam_storage.get_exam_by_id(mock_db_session, 101)

    assert result is not None
    assert result.title == "Physics 101"
    assert result.grade == 11
    mock_db_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_exam_by_id_not_found(mock_db_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    result = await exam_storage.get_exam_by_id(mock_db_session, 999)

    assert result is None


@pytest.mark.asyncio
async def test_list_exams_returns_serialized_list(mock_db_session):
    mock_exam1 = ExamModel(id=1, title="Exam A", grade=10, subject="sub", questions=[])
    mock_exam2 = ExamModel(id=2, title="Exam B", grade=12, subject="sub", questions=[])

    mock_result = MagicMock()
    mock_result.scalars().unique().all.return_value = [mock_exam1, mock_exam2]
    mock_db_session.execute.return_value = mock_result

    result = await exam_storage.list_exams(mock_db_session, skip=0, limit=10)

    assert len(result) == 2
    assert result[0].title == "Exam A"
    assert result[1].title == "Exam B"


@pytest.mark.asyncio
async def test_delete_exam_success(mock_db_session):
    mock_exam = ExamModel(id=10, title="To Delete", grade=10, subject="sub", questions=[])
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_exam
    mock_db_session.execute.return_value = mock_result

    status = await exam_storage.delete_exam(mock_db_session, 10)

    assert status is True
    mock_db_session.delete.assert_awaited_once_with(mock_exam)
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_delete_exam_not_found(mock_db_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    status = await exam_storage.delete_exam(mock_db_session, 999)

    assert status is False
    mock_db_session.delete.assert_not_called()
    mock_db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_exam_database_exception_rolls_back(mock_db_session):
    mock_exam = ExamModel(id=10, title="To Delete", grade=10, subject="sub", questions=[])
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_exam
    mock_db_session.execute.return_value = mock_result

    mock_db_session.delete.side_effect = RuntimeError("Delete blocked")

    with pytest.raises(RuntimeError) as exc_info:
        await exam_storage.delete_exam(mock_db_session, 10)

    assert "Delete blocked" in str(exc_info.value)
    mock_db_session.rollback.assert_awaited_once()
