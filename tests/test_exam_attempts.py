from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints import exam_attempts
from app.schemas.exam_attempt import (
    AttemptAnswerUpsertRequest,
    ExamAttemptBulkSubmitRequest,
    ExamAttemptOut,
    ExamResultOut,
)
from app.services.exams import attempt_service


def make_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def make_db(*results):
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=list(results))
    db.scalar = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


def make_attempt(*, student_id, status="in_progress", answers=None):
    exam = SimpleNamespace(
        id=10,
        title="Physics",
        questions=[
            SimpleNamespace(id=1, correct_answer="A"),
            SimpleNamespace(id=2, correct_answer="B"),
        ],
    )
    return SimpleNamespace(
        id=uuid4(),
        exam_id=10,
        student_id=student_id,
        status=status,
        total_score=None,
        max_score=2.0,
        percentage=None,
        started_at=datetime.now(timezone.utc),
        submitted_at=None,
        graded_at=None,
        exam=exam,
        answers=answers or [],
    )


@pytest.mark.asyncio
async def test_start_attempt_creates_in_progress_attempt():
    student_id = uuid4()
    exam = SimpleNamespace(id=10, questions=[1, 2, 3])
    created = make_attempt(student_id=student_id)
    db = make_db(make_result(exam), make_result(created))
    db.add.side_effect = lambda attempt: setattr(attempt, "id", created.id)

    result = await attempt_service.start_attempt(db, 10, student_id)

    assert isinstance(result, ExamAttemptOut)
    assert result.id == created.id
    assert result.status == attempt_service.IN_PROGRESS
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_answer_rejects_attempt_owned_by_another_student():
    db = make_db(make_result(None))

    with pytest.raises(ValueError, match="Attempt not found"):
        await attempt_service.save_answer(db, uuid4(), uuid4(), 1, "A")


@pytest.mark.asyncio
async def test_submit_attempt_bulk_grades_answers_and_calculates_percentage():
    student_id = uuid4()
    attempt_id = uuid4()
    existing_answer = SimpleNamespace(
        id=uuid4(),
        attempt_id=attempt_id,
        question_id=1,
        submitted_answer="A",
        grading_status=attempt_service.PENDING,
        is_correct=None,
        awarded_score=None,
        feedback=None,
        graded_at=None,
    )
    attempt = make_attempt(student_id=student_id, answers=[existing_answer])
    submitted = make_attempt(student_id=student_id, answers=[existing_answer])
    submitted.id = attempt_id
    db = make_db(make_result(attempt), make_result(submitted))
    db.scalar.side_effect = [
        SimpleNamespace(id=2, correct_answer="B"),
    ]

    result = await attempt_service.submit_attempt(
        db,
        attempt_id,
        student_id,
        ExamAttemptBulkSubmitRequest(
            answers=[{"question_id": 2, "submitted_answer": "wrong"}]
        ),
    )

    assert isinstance(result, ExamResultOut)
    assert result.status == attempt_service.COMPLETED
    assert result.total_score == 1.0
    assert result.max_score == 2.0
    assert result.percentage == 50.0
    assert result.exam_title == "Physics"
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_attempt_rejects_completed_attempt_without_mutation():
    student_id = uuid4()
    answer = SimpleNamespace(
        id=uuid4(),
        attempt_id=uuid4(),
        question_id=1,
        submitted_answer="A",
        grading_status=attempt_service.CORRECT,
        is_correct=True,
        awarded_score=1.0,
        feedback="ok",
        graded_at=datetime.now(timezone.utc),
    )
    attempt = make_attempt(student_id=student_id, status=attempt_service.COMPLETED, answers=[answer])
    attempt.total_score = 1.0
    attempt.percentage = 50.0
    db = make_db(make_result(attempt))

    with pytest.raises(ValueError, match="Attempt is already completed"):
        await attempt_service.submit_attempt(db, attempt.id, student_id)

    assert attempt.status == attempt_service.COMPLETED
    assert attempt.total_score == 1.0
    assert attempt.percentage == 50.0
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_submit_attempt_rolls_back_when_question_belongs_to_another_exam():
    student_id = uuid4()
    attempt = make_attempt(student_id=student_id)
    db = make_db(make_result(attempt))
    db.scalar.return_value = None
    payload = ExamAttemptBulkSubmitRequest(
        answers=[{"question_id": 999, "submitted_answer": "A"}]
    )

    with pytest.raises(ValueError, match="Question does not belong to this exam"):
        await attempt_service.submit_attempt(db, attempt.id, student_id, payload)

    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


def test_exam_attempt_router_exposes_required_contract():
    routes = {
        (method, route.path)
        for route in exam_attempts.router.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }

    assert ("POST", "/exam-attempts/exams/{exam_id}/start") in routes
    assert ("PUT", "/exam-attempts/{attempt_id}/answers/{question_id}") in routes
    assert ("POST", "/exam-attempts/{attempt_id}/submit") in routes
    assert ("GET", "/exam-attempts/{attempt_id}") in routes
    assert ("GET", "/exam-attempts/") in routes


def test_bulk_submission_schema_validates_answer_items():
    payload = ExamAttemptBulkSubmitRequest(
        answers=[{"question_id": 1, "submitted_answer": "A"}]
    )
    assert payload.answers[0].question_id == 1
    assert AttemptAnswerUpsertRequest(submitted_answer="A").submitted_answer == "A"

@pytest.mark.asyncio
async def test_submit_attempt_rejects_already_completed_attempt():
    student_id = uuid4()
    attempt = make_attempt(student_id=student_id, status=attempt_service.COMPLETED)
    db = make_db(make_result(attempt))

    with pytest.raises(ValueError, match="Attempt is already completed"):
        await attempt_service.submit_attempt(db, attempt.id, student_id)

    db.commit.assert_not_awaited()
