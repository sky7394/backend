"""
تست‌های جامع app/services/exams/attempt_service.py
پوشش: توابع کمکی نرمال‌سازی، start_attempt، get_attempt، save_answer،
submit_attempt، get_attempt_result، list_student_results و سناریوهای خطا.

الگوی Mock مطابق با سایر تست‌های پروژه:
- db_session: یک MagicMock(spec=AsyncSession)
- execute یک Result همگام می‌دهد؛ رکوردها داده‌های واقعی و کامل دارند.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.exam_attempt import ExamAttemptBulkSubmitRequest

from app.services.exams.attempt_service import (
    IN_PROGRESS,
    COMPLETED,
    answers_are_equal,
    normalize_answer,
    start_attempt,
    get_attempt,
    save_answer,
    submit_attempt,
    get_attempt_result,
    list_student_results,
    get_exam_results,
)

def _single_result(item) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    return result

@pytest.fixture
def db_session():
    """یک AsyncSession مقلد برای تزریق به توابع سرویس"""
    return MagicMock(spec=AsyncSession)


def _fake_uuid() -> UUID:
    return uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _attempt(*, student_id=None, status=IN_PROGRESS):
    return SimpleNamespace(
        id=_fake_uuid(), exam_id=1, student_id=student_id or _fake_uuid(),
        status=status, started_at=_now(), submitted_at=None, graded_at=None,
        total_score=None, max_score=1.0, percentage=None, answers=[],
        exam=SimpleNamespace(
            id=1, title="آزمون", questions=[SimpleNamespace(id=10, correct_answer="جواب درست")],
        ),
    )


# =====================================================================
# ۱. توابع کمکی نرمال‌سازی فارسی (normalize_answer / answers_are_equal)
# =====================================================================

def test_normalize_answer_none_returns_empty():
    assert normalize_answer(None) == ""


def test_normalize_answer_arabic_characters_to_persian():
    """حروف عربی ي/ك به معادل فارسی ی/ک تبدیل می‌شوند"""
    assert normalize_answer("يكي") == "یکی"
    assert normalize_answer("كبير") == "کبیر"


def test_normalize_answer_half_space_zwnj():
    """نیم‌فاصله (ZWNJ) به فاصله عادی تبدیل می‌شود"""
    assert normalize_answer("می‌رود") == "می رود"


def test_normalize_answer_persian_alef_preserved():
    """حرف «آ» در ابتدای کلمه حفظ می‌شود"""
    assert normalize_answer("آزمون") == "آزمون"


def test_normalize_answer_combined_and_extra_whitespace():
    """ترکیب تبدیل کاراکترها و حذف فاصله‌های اضافه"""
    assert normalize_answer("  علي‌رضا  ") == "علی رضا"


def test_answers_are_equal_true_on_normalized_equality():
    assert answers_are_equal("علي", "علی") is True


def test_answers_are_equal_false_on_different_inputs():
    assert answers_are_equal("غلط", "درست") is False


def test_answers_are_equal_empty_both_true():
    assert answers_are_equal("", "") is True


def test_answers_are_equal_one_empty_false():
    assert answers_are_equal("", "پاسخ") is False


# =====================================================================
# ۲. start_attempt
# =====================================================================

@pytest.mark.asyncio
async def test_start_attempt_exam_not_found_raises_valueerror(db_session):
    """آزمون وجود نداشته باشد -> ValueError با پیام Exam not found"""
    db_session.execute = AsyncMock(return_value=_single_result(None))

    with pytest.raises(ValueError, match="Exam not found"):
        await start_attempt(db_session, exam_id=9999, student_id=_fake_uuid())


@pytest.mark.asyncio
async def test_start_attempt_success_returns_in_progress(db_session):
    """ایجاد موفق تلاش که در وضعیت IN_PROGRESS بازگردانده می‌شود"""
    student_id = _fake_uuid()
    instance = _attempt(student_id=student_id)
    fresh_exam = instance.exam
    attempt_id = instance.id
    started_at = instance.started_at
    db_session.execute = AsyncMock(side_effect=[
        _single_result(fresh_exam), _single_result(instance),
    ])

    def assign_generated_fields(attempt):
        attempt.id = attempt_id
        attempt.started_at = started_at

    db_session.add.side_effect = assign_generated_fields
    result = await start_attempt(db_session, exam_id=1, student_id=student_id)
    instance = db_session.add.call_args.args[0]

    assert result.id == attempt_id
    assert result.status == IN_PROGRESS
    assert result.started_at == started_at
    db_session.add.assert_called_once_with(instance)
    db_session.commit.assert_awaited_once()
    db_session.refresh.assert_awaited()


# =====================================================================
# ۳. get_attempt
# =====================================================================

@pytest.mark.asyncio
async def test_get_attempt_not_found(db_session):
    """تلاش یافت نشود -> ValueError"""
    db_session.execute = AsyncMock(return_value=_single_result(None))

    with pytest.raises(ValueError):
        await get_attempt(db_session, attempt_id=_fake_uuid())


@pytest.mark.asyncio
async def test_get_attempt_success(db_session):
    student_id = _fake_uuid()
    attempt = _attempt(student_id=student_id)
    db_session.execute = AsyncMock(return_value=_single_result(attempt))

    result = await get_attempt(db_session, attempt_id=attempt.id)

    assert result.id == attempt.id


# =====================================================================
# ۴. save_answer
# =====================================================================

@pytest.mark.asyncio
async def test_save_answer_attempt_not_found(db_session):
    """تلاش‌ غیرموجود -> ValueError"""
    db_session.execute = AsyncMock(return_value=_single_result(None))

    with pytest.raises(ValueError):
        await save_answer(db_session, attempt_id=_fake_uuid(), question_id=1, answer_text="پاسخ")


@pytest.mark.asyncio
async def test_save_answer_success(db_session):
    """ثبت پاسخ و ذخیره در دیتابیس"""
    attempt = _attempt()
    db_session.execute = AsyncMock(return_value=_single_result(attempt))
    db_session.scalar = AsyncMock(return_value=SimpleNamespace(id=5, exam_id=1))
    result = await save_answer(
        db_session, attempt_id=attempt.id, question_id=5, answer_text="پاسخ ۵",
    )
    ans = db_session.add.call_args.args[0]

    assert result.id == ans.id
    db_session.add.assert_called_once_with(ans)
    db_session.commit.assert_awaited_once()
    db_session.refresh.assert_awaited()


# =====================================================================
# ۵. submit_attempt (نمره‌دهی دسته‌جمعی)
# =====================================================================

@pytest.mark.asyncio
async def test_submit_attempt_attempt_not_found(db_session):
    db_session.execute = AsyncMock(return_value=_single_result(None))

    with pytest.raises(ValueError):
        await submit_attempt(
            db_session,
            attempt_id=_fake_uuid(),
            student_id=_fake_uuid(),
            bulk=MagicMock(answers=[]),
        )


@pytest.mark.asyncio
async def test_submit_attempt_409_when_not_in_progress(db_session):
    """تلاش از قبل نهایی شده باشد -> ValueError"""
    finished = _attempt(status=COMPLETED)
    db_session.execute = AsyncMock(return_value=_single_result(finished))

    request = MagicMock(answers=[])

    with pytest.raises(ValueError):
        await submit_attempt(db_session, attempt_id=finished.id, student_id=finished.student_id, bulk=request)


@pytest.mark.asyncio
async def test_submit_attempt_success_bulk_grading(db_session):
    """نمره‌دهی دسته‌جمعی پاسخ‌ها و تغییر وضعیت به COMPLETED"""
    attempt = _attempt()
    db_session.execute = AsyncMock(return_value=_single_result(attempt))

    request = ExamAttemptBulkSubmitRequest(
        answers=[{"question_id": 10, "submitted_answer": "جواب درست"}],
    )

    with patch(
        "app.services.exams.attempt_service.bulk_grading",
        new=AsyncMock(return_value={"answered": 1, "correct": 1, "total": 1}),
    ):
        await submit_attempt(
            db_session, attempt_id=attempt.id, student_id=attempt.student_id, bulk=request
        )

    assert attempt.status == COMPLETED
    db_session.commit.assert_awaited()


# =====================================================================
# ۶. get_attempt_result
# =====================================================================

@pytest.mark.asyncio
async def test_get_attempt_result_not_found(db_session):
    db_session.execute = AsyncMock(return_value=_single_result(None))

    with pytest.raises(ValueError):
        await get_attempt_result(db_session, attempt_id=_fake_uuid(), student_id=_fake_uuid())


@pytest.mark.asyncio
async def test_get_attempt_result_success(db_session):
    attempt = _attempt(status=COMPLETED)
    attempt.total_score = 80
    attempt.percentage = 80.0
    db_session.execute = AsyncMock(return_value=_single_result(attempt))

    result = await get_attempt_result(db_session, attempt_id=attempt.id, student_id=attempt.student_id)
    assert result is not None


# =====================================================================
# ۷. list_student_results / get_exam_results
# =====================================================================

def _make_scalar_result(items):
    return MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=items))))


@pytest.mark.asyncio
async def test_list_student_results_returns_items(db_session):
    """بازگرداندن نتایج دانش‌آموز به صورت لیست"""
    result_1 = _attempt(status=COMPLETED)
    result_2 = _attempt(status=COMPLETED)
    db_session.execute = AsyncMock(return_value=_make_scalar_result([result_1, result_2]))

    results = await list_student_results(db_session, student_id=_fake_uuid(), exam_id=1)

    assert len(results) == 2


@pytest.mark.asyncio
async def test_list_student_results_empty(db_session):
    db_session.execute = AsyncMock(return_value=_make_scalar_result([]))

    results = await list_student_results(db_session, student_id=_fake_uuid())

    assert results == []


def test_get_exam_results_is_alias_of_list_student_results():
    """get_exam_results همان list_student_results است"""
    assert get_exam_results is list_student_results
