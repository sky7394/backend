from pydantic import ValidationError

from app.schemas.generate import ExamGenerateRequest, QuestionOut
from app.services.ai.exceptions import AIResponseValidationError


def normalize_questions(data: dict, request: ExamGenerateRequest) -> list[QuestionOut]:
    question_type = str(request.question_type.value if hasattr(request.question_type, "value") else request.question_type)
    difficulty = str(request.difficulty.value if hasattr(request.difficulty, "value") else request.difficulty)
    raw_questions = data.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        raise AIResponseValidationError("Generated question data is unusable")

    questions = []

    for index, item in enumerate(raw_questions, start=1):
        if not isinstance(item, dict):
            raise AIResponseValidationError("Generated question data is unusable")

        options = item.get("options") or []
        if isinstance(options, dict):
            options = [value for value in options.values() if value is not None]
        if not isinstance(options, list):
            raise AIResponseValidationError("Generated question data is unusable")

        question_text = item.get("question_text") or item.get("text")
        correct_answer = item.get("correct_answer")
        if not isinstance(question_text, str) or not question_text.strip():
            raise AIResponseValidationError("Generated question data is unusable")
        if not isinstance(correct_answer, str) or not correct_answer.strip():
            raise AIResponseValidationError("Generated question data is unusable")

        try:
            questions.append(
                QuestionOut(
                    id=item.get("id", index),
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
            )
        except ValidationError as exc:
            raise AIResponseValidationError("Generated question data is invalid") from exc

    return questions
