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


def valid_question(**overrides) -> dict:
    question = {
        "question_text": "What controls a cell?",
        "options": ["Nucleus", "Membrane"],
        "correct_answer": "Nucleus",
    }
    question.update(overrides)
    return {"questions": [question]}


def test_valid_question_uses_request_defaults(exam_request):
    questions = normalize_questions(valid_question(), exam_request)

    question = questions[0]

    assert question.question_text == "What controls a cell?"
    assert question.question_type is QuestionType.multiple_choice
    assert question.difficulty is DifficultyLevel.medium
    assert question.grade == 7
    assert question.subject == "Science"
    assert question.topic == "Cells"
    assert question.options == ["Nucleus", "Membrane"]
    assert question.correct_answer == "Nucleus"


def test_question_explicit_values_override_request_defaults(exam_request):
    data = valid_question(
        question_type="multiple_choice",
        difficulty="hard",
        grade=10,
        subject="Physics",
        topic="Gravity",
        explanation="The nucleus controls the cell.",
    )

    questions = normalize_questions(data, exam_request)
    question = questions[0]

    assert question.question_type is QuestionType.multiple_choice
    assert question.difficulty is DifficultyLevel.hard
    assert question.grade == 10
    assert question.subject == "Physics"
    assert question.topic == "Gravity"
    assert question.explanation == "The nucleus controls the cell."


@pytest.mark.parametrize("question_text", [None, "", "   "])
def test_missing_or_empty_question_text_is_rejected(
    exam_request,
    question_text,
):
    data = valid_question(question_text=question_text)

    with pytest.raises(AIResponseValidationError):
        normalize_questions(data, exam_request)


@pytest.mark.parametrize(
    "correct_answer",
    [None, "", "   "],
)
def test_missing_or_empty_correct_answer_is_rejected(
    exam_request,
    correct_answer,
):
    data = valid_question(correct_answer=correct_answer)

    with pytest.raises(AIResponseValidationError):
        normalize_questions(data, exam_request)


@pytest.mark.parametrize(
    "options",
    [
        None,
        "not-a-list",
        [],
        ["Valid", ""],
        ["Valid", "   "],
        ["Only one"],
        [None, "Valid"],
        ["Valid", 123],
    ],
)
def test_invalid_multiple_choice_options_are_rejected(
    exam_request,
    options,
):
    data = valid_question(options=options)

    with pytest.raises(AIResponseValidationError):
        normalize_questions(data, exam_request)


def test_duplicate_options_are_rejected_case_insensitively(
    exam_request,
):
    data = valid_question(options=["Nucleus", " nucleus "])

    with pytest.raises(AIResponseValidationError):
        normalize_questions(data, exam_request)


def test_answer_not_present_in_options_is_rejected(exam_request):
    data = valid_question(correct_answer="Cytoplasm")

    with pytest.raises(AIResponseValidationError):
        normalize_questions(data, exam_request)


def test_whitespace_is_removed_from_question_fields(exam_request):
    data = valid_question(
        question_text="  What controls a cell?  ",
        options=["  Nucleus  ", " Membrane "],
        correct_answer="  Nucleus  ",
    )

    questions = normalize_questions(data, exam_request)
    question = questions[0]

    assert question.question_text == "What controls a cell?"
    assert question.options == ["Nucleus", "Membrane"]
    assert question.correct_answer == "Nucleus"


def test_dictionary_options_are_normalized_to_a_list(exam_request):
    data = valid_question(
        options={
            "a": "Nucleus",
            "b": "Membrane",
        },
    )

    questions = normalize_questions(data, exam_request)

    assert questions[0].options == ["Nucleus", "Membrane"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("question_type", "short_answer"),
        ("difficulty", "impossible"),
    ],
)
def test_malformed_type_or_difficulty_is_rejected(
    exam_request,
    field,
    value,
):
    data = valid_question(**{field: value})

    with pytest.raises(AIResponseValidationError):
        normalize_questions(data, exam_request)


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        {},
        {"questions": None},
        {"questions": []},
        {"questions": ["bad"]},
        {"questions": [None]},
    ],
)
def test_structurally_invalid_ai_output_is_rejected(
    exam_request,
    data,
):
    with pytest.raises(AIResponseValidationError):
        normalize_questions(data, exam_request)


def test_descriptive_question_without_options_is_accepted(exam_request):
    exam_request.question_type = QuestionType.descriptive

    data = valid_question(
        question_type="descriptive",
        options=[],
        correct_answer="The nucleus controls the cell.",
    )

    questions = normalize_questions(data, exam_request)

    assert len(questions) == 1
    assert questions[0].question_type is QuestionType.descriptive
    assert questions[0].options == []
    assert questions[0].correct_answer == "The nucleus controls the cell."


def test_descriptive_question_with_options_is_rejected(exam_request):
    data = valid_question(
        question_type="descriptive",
        options=["Nucleus", "Membrane"],
    )

    with pytest.raises(AIResponseValidationError):
        normalize_questions(data, exam_request)


def test_true_false_question_requires_two_options(exam_request):
    exam_request.question_type = QuestionType.true_false

    data = valid_question(
        question_type="true_false",
        options=["True", "False"],
        correct_answer="True",
    )

    questions = normalize_questions(data, exam_request)

    assert len(questions) == 1
    assert questions[0].question_type is QuestionType.true_false
    assert questions[0].options == ["True", "False"]


@pytest.mark.parametrize(
    "options",
    [
        [],
        ["True"],
        ["True", "False", "Maybe"],
    ],
)
def test_true_false_question_with_invalid_options_is_rejected(
    exam_request,
    options,
):
    data = valid_question(
        question_type="true_false",
        options=options,
        correct_answer="True",
    )

    with pytest.raises(AIResponseValidationError):
        normalize_questions(data, exam_request)


def test_true_false_answer_must_be_in_options(exam_request):
    data = valid_question(
        question_type="true_false",
        options=["True", "False"],
        correct_answer="Maybe",
    )

    with pytest.raises(AIResponseValidationError):
        normalize_questions(data, exam_request)


def test_generic_non_gravity_question_is_not_blocked_by_scientific_validation(
    exam_request,
):
    data = valid_question(
        question_text="What is the function of the nucleus?",
        correct_answer="Nucleus",
        explanation="The nucleus contains genetic material.",
    )

    questions = normalize_questions(data, exam_request)

    assert len(questions) == 1
    assert questions[0].correct_answer == "Nucleus"


def test_incorrect_gravity_scaling_is_rejected(exam_request):
    exam_request.subject = "Physics"
    exam_request.topic = "Gravity"

    data = valid_question(
        question_text=(
            "If one mass doubles and the distance between the objects "
            "is halved, how does the gravitational force change?"
        ),
        options=["4 times", "8 times"],
        correct_answer="4 times",
        explanation=("The gravitational force becomes 4 times greater."),
    )

    with pytest.raises(AIResponseValidationError):
        normalize_questions(data, exam_request)


def test_correct_gravity_scaling_is_accepted(exam_request):
    exam_request.subject = "Physics"
    exam_request.topic = "Gravity"

    data = valid_question(
        question_text=(
            "If one mass doubles and the distance between the objects "
            "is halved, how does the gravitational force change?"
        ),
        options=["4 times", "8 times"],
        correct_answer="8 times",
        explanation=(
            "Doubling the mass multiplies the force by 2 and halving "
            "the distance multiplies it by 4, so the result is 8 times."
        ),
    )

    questions = normalize_questions(data, exam_request)

    assert len(questions) == 1
    assert questions[0].correct_answer == "8 times"


def test_correct_persian_gravity_scaling_is_accepted(exam_request):
    exam_request.subject = "فیزیک"
    exam_request.topic = "گرانش"

    data = valid_question(
        question_text=(
            "اگر جرم یکی از اجسام دو برابر و فاصله بین آن‌ها نصف شود، نیروی گرانشی چند برابر می‌شود؟"
        ),
        options=["۴ برابر", "۸ برابر"],
        correct_answer="۸ برابر",
        explanation=(
            "دو برابر شدن جرم ضریب ۲ و نصف شدن فاصله ضریب ۴ ایجاد می‌کند؛ "
            "بنابراین نیرو ۸ برابر می‌شود."
        ),
    )

    questions = normalize_questions(data, exam_request)

    assert len(questions) == 1
    assert questions[0].correct_answer == "۸ برابر"


def test_incorrect_persian_gravity_scaling_is_rejected(exam_request):
    exam_request.subject = "فیزیک"
    exam_request.topic = "گرانش"

    data = valid_question(
        question_text=(
            "اگر جرم یکی از اجسام دو برابر و فاصله بین آن‌ها نصف شود، نیروی گرانشی چند برابر می‌شود؟"
        ),
        options=["۴ برابر", "۸ برابر"],
        correct_answer="۴ برابر",
        explanation="نیروی گرانشی ۴ برابر می‌شود.",
    )

    with pytest.raises(AIResponseValidationError):
        normalize_questions(data, exam_request)
