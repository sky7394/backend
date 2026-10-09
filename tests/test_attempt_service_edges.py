from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.db.models import AttemptAnswer
from app.services.exams.attempt_service import (
    INCORRECT,
    PENDING,
    IN_PROGRESS,
    _upsert_answer,
    bulk_grading,
    get_attempt,
    save_answer,
    start_attempt,
)


# ==========================================
# 1. تست‌های خطایابی و Rollback در دیتابیس
# ==========================================

@pytest.mark.asyncio
async def test_start_attempt_rolls_back_on_commit_error():
    """پوشش خطوط 115-117: اطمینان از Rollback شدن تراکنش هنگام خطای دیتابیس در start_attempt."""
    db = AsyncMock()
    db.add = MagicMock()
    fake_exam = SimpleNamespace(id=1, questions=[SimpleNamespace(id=10)])
    result = MagicMock()
    result.scalar_one_or_none.return_value = fake_exam
    db.execute.return_value = result
    db.commit.side_effect = RuntimeError("Database connection dropped")

    with pytest.raises(RuntimeError, match="Database connection dropped"):
        await start_attempt(db=db, exam_id=1, student_id=uuid4())

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_answer_rolls_back_on_commit_error():
    """اطمینان از Rollback شدن تراکنش هنگام خطای دیتابیس در save_answer."""
    attempt_id = uuid4()
    student_id = uuid4()
    fake_attempt = SimpleNamespace(
        id=attempt_id,
        student_id=student_id,
        status=IN_PROGRESS,
        exam_id=1,
        answers=[],
    )
    fake_answer = SimpleNamespace(id=uuid4())

    db = AsyncMock()
    db.commit.side_effect = RuntimeError("Failed to commit answer")

    with patch("app.services.exams.attempt_service._load_attempt", return_value=fake_attempt), \
         patch("app.services.exams.attempt_service._upsert_answer", return_value=fake_answer):
        
        with pytest.raises(RuntimeError, match="Failed to commit answer"):
            await save_answer(
                db=db,
                attempt_id=attempt_id,
                student_id=student_id,
                question_id=10,
                submitted_answer="A",
            )

    db.rollback.assert_awaited_once()


# ==========================================
# 2. تست‌های اعتبارسنجی ورودی‌ها در save_answer
# ==========================================

@pytest.mark.asyncio
async def test_save_answer_raises_on_conflicting_answer_values():
    """پوشش خط 178: بررسی تناقض بین submitted_answer و answer_text."""
    with pytest.raises(ValueError, match="Conflicting answer values"):
        await save_answer(
            db=None,
            attempt_id=uuid4(),
            question_id=1,
            submitted_answer="Option A",
            answer_text="Option B",
        )


@pytest.mark.asyncio
async def test_save_answer_raises_when_question_or_answer_missing():
    """پوشش خط 180: بررسی عدم ارسال question_id یا submitted_answer."""
    with pytest.raises(ValueError, match="question_id and submitted_answer are required"):
        await save_answer(
            db=None,
            attempt_id=uuid4(),
            question_id=None,
            submitted_answer=None,
        )


@pytest.mark.asyncio
async def test_save_answer_raises_when_attempt_not_in_progress():
    """بررسی عدم امکان ویرایش آزمونی که وضعیت آن IN_PROGRESS نیست."""
    attempt_id = uuid4()
    fake_attempt = SimpleNamespace(id=attempt_id, status="COMPLETED")

    with patch("app.services.exams.attempt_service._load_attempt", return_value=fake_attempt):
        with pytest.raises(ValueError, match="This attempt is no longer editable"):
            await save_answer(
                db=AsyncMock(),
                attempt_id=attempt_id,
                question_id=1,
                submitted_answer="A",
            )


# ==========================================
# 3. تست‌های _upsert_answer
# ==========================================

@pytest.mark.asyncio
async def test_upsert_answer_raises_when_question_not_found():
    """بررسی پرتاب خطا وقتی سوال متعلق به آزمون نباشد."""
    attempt = SimpleNamespace(id=uuid4(), exam_id=99, answers=[])
    db = AsyncMock()
    db.scalar.return_value = None

    with pytest.raises(ValueError, match="Question does not belong to this exam"):
        await _upsert_answer(
            db=db,
            attempt=attempt,
            question_id=404,
            submitted_answer="any",
        )


@pytest.mark.asyncio
async def test_upsert_answer_creates_new_record():
    """بررسی ایجاد رکورد جدید در صورتی که پاسخی قبلاً ثبت نشده باشد."""
    attempt_id = uuid4()
    exam_id = 1
    attempt = SimpleNamespace(id=attempt_id, exam_id=exam_id, answers=[])
    fake_question = SimpleNamespace(id=10, exam_id=exam_id)

    db = AsyncMock()
    db.add = MagicMock()
    db.scalar.return_value = fake_question

    answer = await _upsert_answer(
        db=db,
        attempt=attempt,
        question_id=10,
        submitted_answer="Option C",
    )

    assert isinstance(answer, AttemptAnswer)
    assert answer.submitted_answer == "Option C"
    assert answer.grading_status == PENDING
    assert answer in attempt.answers
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_answer_updates_existing_record():
    """بررسی بازنویسی و ریست شدن فیلدهای تصحیح در صورت ثبت مجدد پاسخ."""
    attempt_id = uuid4()
    exam_id = 1
    existing_answer = AttemptAnswer(
        id=uuid4(),
        attempt_id=attempt_id,
        question_id=10,
        submitted_answer="Old Answer",
        grading_status="CORRECT",
        is_correct=True,
        awarded_score=1.0,
        feedback="Old Feedback",
        graded_at=None,
    )
    attempt = SimpleNamespace(id=attempt_id, exam_id=exam_id, answers=[existing_answer])
    fake_question = SimpleNamespace(id=10, exam_id=exam_id)

    db = AsyncMock()
    db.scalar.return_value = fake_question

    answer = await _upsert_answer(
        db=db,
        attempt=attempt,
        question_id=10,
        submitted_answer="New Answer",
    )

    assert answer is existing_answer
    assert answer.submitted_answer == "New Answer"
    assert answer.grading_status == PENDING
    assert answer.is_correct is None
    assert answer.awarded_score is None


# ==========================================
# 4. تست‌های bulk_grading
# ==========================================

@pytest.mark.asyncio
async def test_bulk_grading_with_payload_and_mixed_answers():
    """تست تصحیح گروهی با ارسال آبجکت bulk و بررسی پاسخ‌های درست و نادرست."""
    exam_id = 1
    attempt_id = uuid4()
    q1 = SimpleNamespace(id=101, correct_answer="Alpha")
    q2 = SimpleNamespace(id=102, correct_answer="Beta")

    attempt = SimpleNamespace(
        id=attempt_id,
        exam_id=exam_id,
        answers=[],
        exam=SimpleNamespace(questions=[q1, q2]),
    )

    bulk_items = [
        SimpleNamespace(question_id=101, submitted_answer="Alpha"),
        SimpleNamespace(question_id=102, submitted_answer="Gamma"),
    ]
    bulk_request = SimpleNamespace(answers=bulk_items)

    db = AsyncMock()
    db.add = MagicMock()
    # شبیه‌سازی پیدا شدن سوالات در دیتابیس
    db.scalar.side_effect = [
        SimpleNamespace(id=101, exam_id=exam_id),
        SimpleNamespace(id=102, exam_id=exam_id),
    ]

    result = await bulk_grading(db=db, attempt=attempt, bulk=bulk_request)

    assert result == {"answered": 2, "correct": 1, "total": 2}
    assert attempt.answers[0].is_correct is True
    assert attempt.answers[0].feedback == "پاسخ صحیح است."
    assert attempt.answers[1].is_correct is False
    assert attempt.answers[1].feedback == "پاسخ صحیح نیست."
    db.flush.assert_awaited_once()
