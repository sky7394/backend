from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.schemas.exam import ExamPreviewOut
from app.schemas.question import (
    DifficultyLevel,
    QuestionPreviewOut,
    QuestionType,
)
from app.services.exams.exam_storage import create_exam


def make_exam_payload() -> ExamPreviewOut:
    return ExamPreviewOut(
        title="Atomic Science Exam",
        grade=7,
        subject="Science",
        questions=[
            QuestionPreviewOut(
                question_text="What controls a cell?",
                question_type=QuestionType.multiple_choice,
                difficulty=DifficultyLevel.medium,
                grade=7,
                subject="Science",
                topic="Cells",
                options=["Nucleus", "Membrane"],
                correct_answer="Nucleus",
            )
        ],
    )


def assign_database_ids(exam):
    exam.id = 1
    for index, question in enumerate(exam.questions, start=1):
        question.id = index
        question.exam_id = exam.id


def make_db(*, flush_effect=None, commit_effect=None):
    db = SimpleNamespace()
    db.add = lambda exam: setattr(db, "added_exam", exam)
    db.flush = AsyncMock(side_effect=flush_effect)
    db.commit = AsyncMock(side_effect=commit_effect)
    db.rollback = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_question_creation_failure_rolls_back_whole_finalize_write():
    db = make_db(flush_effect=RuntimeError("question insert failed"))

    with pytest.raises(RuntimeError, match="question insert failed"):
        await create_exam(db, make_exam_payload())

    assert db.added_exam.title == "Atomic Science Exam"
    assert len(db.added_exam.questions) == 1
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_validation_failure_does_not_start_a_transaction():
    db = make_db()

    with pytest.raises(ValidationError):
        await create_exam(db, {"title": "Missing required fields"})

    assert not hasattr(db, "added_exam")
    db.flush.assert_not_awaited()
    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_unexpected_commit_failure_rolls_back_flushed_exam_and_questions():
    db = make_db(commit_effect=RuntimeError("commit failed"))
    db.flush.side_effect = lambda: assign_database_ids(db.added_exam)

    with pytest.raises(RuntimeError, match="commit failed"):
        await create_exam(db, make_exam_payload())

    db.flush.assert_awaited_once()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_success_flushes_ids_then_commits_exam_and_questions_together():
    db = make_db()
    db.flush.side_effect = lambda: assign_database_ids(db.added_exam)

    saved_exam = await create_exam(db, make_exam_payload())

    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()
    assert saved_exam.title == "Atomic Science Exam"
    assert saved_exam.questions[0].id == 1
    assert db.added_exam.questions_count == 1
