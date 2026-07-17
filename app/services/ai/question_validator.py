from app.schemas.question import ExamGenerateRequest, QuestionOut


def normalize_questions(data: dict, request: ExamGenerateRequest) -> list[QuestionOut]:
    question_type = str(request.question_type.value if hasattr(request.question_type, "value") else request.question_type)
    difficulty = str(request.difficulty.value if hasattr(request.difficulty, "value") else request.difficulty)
    questions = []

    for index, item in enumerate(data.get("questions", []), start=1):
        options = item.get("options") or []
        if isinstance(options, dict):
            options = [value for value in options.values() if value is not None]

        questions.append(
            QuestionOut(
                id=item.get("id", index),
                question_text=item.get("question_text") or item.get("text") or "",
                question_type=item.get("question_type", question_type),
                difficulty=item.get("difficulty", difficulty),
                grade=item.get("grade", request.grade),
                subject=item.get("subject", request.subject),
                topic=item.get("topic", request.topic),
                options=options,
                correct_answer=item.get("correct_answer"),
                explanation=item.get("explanation"),
            )
        )

    return questions
