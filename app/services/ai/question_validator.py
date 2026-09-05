from app.services.ai.scientific_validator import validate_scientific_content
from pydantic import ValidationError

from app.schemas.exam import ExamGenerateRequest
from app.schemas.question import QuestionPreviewOut
from app.services.ai.exceptions import AIResponseValidationError


def normalize_questions(
    data: dict,
    request: ExamGenerateRequest,
) -> list[QuestionPreviewOut]:
    if not isinstance(data, dict):
        raise AIResponseValidationError("Generated question data is unusable")

    question_type = str(
        request.question_type.value
        if hasattr(request.question_type, "value")
        else request.question_type
    )
    difficulty = str(
        request.difficulty.value if hasattr(request.difficulty, "value") else request.difficulty
    )
    raw_questions = data.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        raise AIResponseValidationError("Generated question data is unusable")

    questions = []

    for item in raw_questions:
        if not isinstance(item, dict):
            raise AIResponseValidationError("Generated question data is unusable")

        options = item.get("options") or []
        if isinstance(options, dict):
            options = [value for value in options.values() if value is not None]
        if not isinstance(options, list):
            raise AIResponseValidationError("Generated question data is unusable")
        if any(not isinstance(option, str) or not option.strip() for option in options):
            raise AIResponseValidationError("Generated question data is unusable")
        options = [option.strip() for option in options]
        if len({option.casefold() for option in options}) != len(options):
            raise AIResponseValidationError("Generated question data is unusable")

        question_text = item.get("question_text") or item.get("text")
        correct_answer = item.get("correct_answer")
        if not isinstance(question_text, str) or not question_text.strip():
            raise AIResponseValidationError("Generated question data is unusable")
        if not isinstance(correct_answer, str) or not correct_answer.strip():
            raise AIResponseValidationError("Generated question data is unusable")

        try:
            question = QuestionPreviewOut(
                question_text=question_text.strip(),
                question_type=item.get("question_type", question_type),
                difficulty=item.get("difficulty", difficulty),
                grade=item.get("grade", request.grade),
                subject=item.get("subject", request.subject),
                topic=item.get("topic", request.topic),
                options=options,
                correct_answer=correct_answer.strip(),
                explanation=item.get("explanation"),
            )
        except ValidationError as exc:
            raise AIResponseValidationError("Generated question data is invalid") from exc

        if question.question_type.value == "multiple_choice":
            if len(options) < 2 or question.correct_answer not in options:
                raise AIResponseValidationError("Generated question data is unusable")
        elif question.question_type.value == "true_false":
            if len(options) != 2 or question.correct_answer not in options:
                raise AIResponseValidationError("Generated question data is unusable")
        elif options:
            raise AIResponseValidationError("Generated question data is unusable")
        try:
            validate_scientific_content(question)
        except ValueError as exc:
            raise AIResponseValidationError(
                "Generated question failed scientific validation"
            ) from exc

        questions.append(question)

    return questions
