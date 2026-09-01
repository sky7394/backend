import asyncio
from unittest.mock import AsyncMock, patch
import pytest

from app.schemas import exam as exam_schemas
from app.schemas import question as question_schemas
from app.services.exams.exam_service import finalize_exam, preview_exam, validate_preview_exam
from app.services.ai.exceptions import AIResponseValidationError


def run_inline(func, *args, **kwargs):
    return func(*args, **kwargs)


def run(coro):
    return asyncio.run(coro)


class TestExamService:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self):
        self.request = exam_schemas.ExamGenerateRequest(
            title="Science Exam",
            grade=7,
            subject="Science",
            difficulty="medium",
            question_types=["multiple_choice"],
            number_of_questions=1,
            extra_instructions="Cover basic atom structure.",
        )
        self.ai_raw_output = {
            "title": "Science Exam",
            "grade": 7,
            "subject": "Science",
            "questions": [
                {
                    "question_text": "What is an atom?",
                    "question_type": "multiple_choice",
                    "difficulty": "medium",
                    "grade": 7,
                    "subject": "Science",
                    "options": ["A particle", "A planet"],
                    "correct_answer": "A particle",
                }
            ],
        }

    def test_validate_preview_exam_success(self):
        preview = validate_preview_exam(self.ai_raw_output)
        assert isinstance(preview, exam_schemas.ExamPreviewOut)
        assert preview.title == "Science Exam"
        assert len(preview.questions) == 1
        assert preview.questions[0].question_text == "What is an atom?"

    def test_validate_preview_exam_raises_validation_error_on_invalid_data(self):
        invalid_output = {"title": "Invalid"}
        with pytest.raises(AIResponseValidationError):
            validate_preview_exam(invalid_output)

    def test_preview_exam_service_returns_preview_exam_out(self):
        with (
            patch(
                "app.services.exams.exam_service.generate_exam_with_ai",
                return_value=self.ai_raw_output,
            ) as generate_exam_with_ai,
            patch(
                "app.services.exams.exam_service.run_in_threadpool",
                new=AsyncMock(side_effect=run_inline),
            ),
        ):
            result = run(preview_exam(self.request))

        generate_exam_with_ai.assert_called_once_with(self.request)
        assert isinstance(result, exam_schemas.ExamPreviewOut)
        assert result.title == "Science Exam"
        assert len(result.questions) == 1

    def test_finalize_generates_saves_and_returns_finalized_exam(self):
        finalized_exam = exam_schemas.ExamFinalizeOut(
            id=1,
            title="Saved Science Exam",
            grade=7,
            subject="Science",
            questions=[
                question_schemas.QuestionFinalizeOut(
                    id=10,
                    question_text="What is an atom?",
                    question_type=question_schemas.QuestionType.multiple_choice,
                    difficulty=question_schemas.DifficultyLevel.medium,
                    grade=7,
                    subject="Science",
                    options=["A particle", "A planet"],
                    correct_answer="A particle",
                )
            ],
        )

        with (
            patch(
                "app.services.exams.exam_service.generate_exam_with_ai",
                return_value=self.ai_raw_output,
            ) as generate_exam_with_ai,
            patch(
                "app.services.exams.exam_service.run_in_threadpool",
                new=AsyncMock(side_effect=run_inline),
            ),
            patch(
                "app.services.exams.exam_service.create_exam",
                new=AsyncMock(return_value=finalized_exam),
            ) as create_exam,
        ):
            db = AsyncMock()
            result = run(finalize_exam(self.request, db))

        generate_exam_with_ai.assert_called_once_with(self.request)
        create_exam.assert_awaited_once()

        called_db = (
            create_exam.await_args.args[0]
            if create_exam.await_args.args
            else create_exam.await_args.kwargs.get("db")
        )
        assert called_db is db
        assert result.title == "Saved Science Exam"
        assert len(result.questions) == 1
        assert result.questions[0].id == 10
