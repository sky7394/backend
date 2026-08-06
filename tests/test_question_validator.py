import pytest

from app.schemas.exam import ExamGenerateRequest
from app.schemas.question import DifficultyLevel, QuestionType
from app.services.ai.exceptions import AIResponseValidationError
from app.services.ai.question_validator import normalize_questions


@pytest.fixture
def exam_request() -> ExamGenerateRequest:
    return ExamGenerateRequest(
        grade=7,
        subject="Science",
        num_questions=1,
        question_type=QuestionType.multiple_choice,
        difficulty=DifficultyLevel.medium,
        topic="Cells",
    )


def valid_question(**overrides):
    question = {
        "question_text": "What controls a cell?",
        "options": ["Nucleus", "Membrane"],
        "correct_answer": "Nucleus",
    }
    question.update(overrides)
    return {"questions": [question]}


def test_valid_question_uses_request_defaults(exam_request):
    questions = normalize_questions(valid_question(), exam_request)

    assert questions[0].question_text == "What controls a cell?"
    assert questions[0].question_type is QuestionType.multiple_choice
    assert questions[0].difficulty is DifficultyLevel.medium
    assert questions[0].grade == 7
    assert questions[0].subject == "Science"


@pytest.mark.parametrize("question_text", [None, "", "   "])
def test_missing_or_empty_statement_is_rejected(exam_request, question_text):
    with pytest.raises(AIResponseValidationError):
        normalize_questions(valid_question(question_text=question_text), exam_request)


@pytest.mark.parametrize("options", [None, "not-a-list", ["Valid", ""], ["Only one"]])
def test_invalid_multiple_choice_options_are_rejected(exam_request, options):
    with pytest.raises(AIResponseValidationError):
        normalize_questions(valid_question(options=options), exam_request)


def test_duplicate_options_are_rejected(exam_request):
    with pytest.raises(AIResponseValidationError):
        normalize_questions(valid_question(options=["Nucleus", " nucleus "]), exam_request)


def test_answer_not_present_in_options_is_rejected(exam_request):
    with pytest.raises(AIResponseValidationError):
        normalize_questions(valid_question(correct_answer="Cytoplasm"), exam_request)


@pytest.mark.parametrize(
    ("field", "value"),
    [("question_type", "short_answer"), ("difficulty", "impossible")],
)
def test_malformed_type_or_difficulty_is_rejected(exam_request, field, value):
    with pytest.raises(AIResponseValidationError):
        normalize_questions(valid_question(**{field: value}), exam_request)


@pytest.mark.parametrize("data", [None, [], {}, {"questions": []}, {"questions": ["bad"]}])
def test_structurally_invalid_ai_output_is_rejected(exam_request, data):
    with pytest.raises(AIResponseValidationError):
        normalize_questions(data, exam_request)


def test_descriptive_question_rejects_options(exam_request):
    exam_request.question_type = QuestionType.descriptive

    with pytest.raises(AIResponseValidationError):
        normalize_questions(valid_question(), exam_request)
