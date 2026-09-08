import asyncio
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import AttemptAnswer, ExamModel, QuestionModel, User
from app.schemas.exam_attempt import ExamAttemptBulkSubmitRequest
from app.services.exams import attempt_service as service


async def check(expire_on_commit):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=expire_on_commit)
        student_id = uuid4()
        async with sessions() as db:
            db.add(User(id=student_id, email="student@example.com", hashed_password="unused"))
            db.add(ExamModel(id=1, title="Physics", grade=10, subject="Physics"))
            for question_id, correct in [(1, "A"), (2, "B")]:
                db.add(QuestionModel(
                    id=question_id, exam_id=1, question_text="Question",
                    question_type="text", difficulty="easy", grade=10,
                    subject="Physics", correct_answer=correct,
                ))
            await db.commit()
            attempt = await service.start_attempt(db, 1, student_id)
            answer = await service.save_answer(db, attempt.id, student_id, 1, "wrong")
            updated = await service.save_answer(db, attempt.id, student_id, 1, "A")
            assert answer.id == updated.id
            assert updated.grading_status == "pending"
            try:
                await service.get_attempt(db, attempt.id, uuid4())
            except ValueError as exc:
                assert str(exc) == "Attempt not found"
            else:
                raise AssertionError("Ownership was not enforced")
            invalid = ExamAttemptBulkSubmitRequest(answers=[
                {"question_id": 1, "submitted_answer": "wrong"},
                {"question_id": 999, "submitted_answer": "invalid"},
            ])
            try:
                await service.submit_attempt(db, attempt.id, student_id, invalid)
            except ValueError as exc:
                assert str(exc) == "Question does not belong to this exam"
            else:
                raise AssertionError("Invalid question was accepted")
            persisted = await service.get_attempt(db, attempt.id, student_id)
            assert persisted.status == "in_progress"
            assert persisted.answers[0].submitted_answer == "A"
            result = await service.submit_attempt(
                db, attempt.id, student_id,
                ExamAttemptBulkSubmitRequest(answers=[
                    {"question_id": 2, "submitted_answer": "wrong"},
                ]),
            )
            assert (result.total_score, result.max_score, result.percentage) == (1, 2, 50)
            assert [a.grading_status for a in result.answers] == ["correct", "incorrect"]
        async with sessions() as db:
            loaded = await service.get_attempt_result(db, attempt.id, student_id)
            assert loaded.status == "completed" and loaded.percentage == 50
            assert len(loaded.answers) == 2
            assert len(await service.list_student_results(db, student_id, 1)) == 1
            assert await service.list_student_results(db, uuid4()) == []
            assert len((await db.execute(select(AttemptAnswer))).scalars().all()) == 2
            try:
                await service.submit_attempt(db, attempt.id, student_id)
            except ValueError as exc:
                assert str(exc) == "Attempt is already completed"
            else:
                raise AssertionError("Completed attempt was submitted again")
        print(f"SQLite lifecycle, ownership, upsert, rollback, persisted grading: PASS (expire_on_commit={expire_on_commit})")
    finally:
        await engine.dispose()


async def main():
    await check(False)
    await check(True)


asyncio.run(main())
