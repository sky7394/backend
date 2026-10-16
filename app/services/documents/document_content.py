"""Shared, non-mutating input normalization for PDF and Word exports."""
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from app.services.documents.exam_models import ExamHeaderConfig, NormalizedQuestion

BLANK = "........................"
OPTION_LABELS = ("الف", "ب", "ج", "د")


def _value(item: Any, *names: str, default=None):
    for name in names:
        value = item.get(name) if isinstance(item, Mapping) else getattr(item, name, None)
        if value is not None:
            return value
    return default


def normalize_questions(raw_questions) -> list[NormalizedQuestion]:
    questions = []
    for number, raw in enumerate(raw_questions, 1):
        if isinstance(raw, NormalizedQuestion):
            questions.append(raw.model_copy(deep=True))
            continue
        options = [
            str(_value(option, "text", default=option))
            for option in (_value(raw, "options", default=[]) or [])
        ]
        answer = _value(raw, "correct_answer", "answer")
        index = _value(raw, "correct_option_index")
        if answer is None and isinstance(index, int) and 0 <= index < len(options):
            answer = options[index]
        questions.append(NormalizedQuestion(
            number=number,
            question_text=str(_value(raw, "question_text", "question", "text", default="")),
            options=options,
            answer=str(answer) if answer is not None else None,
            points=_value(raw, "score", "points"),
            explanation=_value(raw, "explanation"),
            section=_value(raw, "section"),
            formula=_value(raw, "formula"),
            answer_lines=_value(raw, "answer_lines", default=3),
        ))
    return questions


def resolve_header(exam_data, title="آزمون کتبی", explicit=None) -> ExamHeaderConfig:
    if explicit is not None:
        return explicit.model_copy(deep=True)
    data = exam_data if isinstance(exam_data, Mapping) else {}
    values = {
        key: data[key] for key in ExamHeaderConfig.model_fields
        if key in data and data[key] is not None
    }
    values.setdefault("course_name", data.get("subject") or data.get("title") or title)
    grade = data.get("grade") or data.get("grade_level")
    major = data.get("major")
    if grade or major:
        values.setdefault("grade_field", " / ".join(str(v) for v in (grade, major) if v))
    if "exam_duration" not in values and data.get("duration_minutes") is not None:
        values["exam_duration"] = f"{data['duration_minutes']} دقیقه"
    nested = data.get("header_config")
    if isinstance(nested, BaseModel):
        nested = nested.model_dump(exclude_unset=True)
    if nested:
        values.update({key: value for key, value in nested.items() if value is not None})
    return ExamHeaderConfig.model_validate(values)


def header_rows(config: ExamHeaderConfig) -> list[tuple[str, str]]:
    """Logical RTL order: first cell is the right cell in each row."""
    return [
        (f"نام مدرسه/آموزشگاه: {config.school_name}", f"نام درس: {config.course_name}"),
        (f"پایه و رشته: {config.grade_field or BLANK}", f"نام طراح: {config.teacher_name or BLANK}"),
        (f"تاریخ آزمون: {config.exam_date or BLANK}", f"مدت آزمون: {config.exam_duration or BLANK}"),
        (f"نام و نام خانوادگی: {config.student_name or BLANK}",
         f"شماره داوطلبی: {config.candidate_number or BLANK}"),
        (f"کلاس: {config.class_name or BLANK}", f"نوبت آزمون: {config.exam_term or BLANK}"),
        (f"نمره به عدد: {BLANK}", f"نمره به حروف: {BLANK}"),
        (f"امضای مصحح: {BLANK}", ""),
    ]


def option_label(index: int) -> str:
    return OPTION_LABELS[index] if index < len(OPTION_LABELS) else str(index + 1)


def question_parts(question: NormalizedQuestion) -> list[tuple[str, str]]:
    parts = [("text", question.question_text)]
    if question.formula:
        parts.append(("math", question.formula))
    parts.extend(("text", f"{option_label(i)}) {option}") for i, option in enumerate(question.options))
    if not question.options:
        parts.extend(("line", "") for _ in range(question.answer_lines))
    return parts


def question_body_and_options(question: NormalizedQuestion) -> tuple[list[tuple[str, str]], list[tuple[str, str]] | None]:
    """Split a question into body parts and labeled options.

    Returns (body_parts, options) where options is a list of
    (label, text) tuples, or None when the question has no options.
    """
    body: list[tuple[str, str]] = [("text", question.question_text)]
    if question.formula:
        body.append(("math", question.formula))
    if not question.options:
        return body, None
    options = [(option_label(i), option) for i, option in enumerate(question.options)]
    return body, options
