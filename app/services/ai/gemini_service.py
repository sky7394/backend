import json
import re
from openai import OpenAI

from app.core.config import settings
from app.schemas.question import ExamGenerateRequest, ExamOut
from app.services.ai.prompt_builder import build_exam_prompt
from app.services.ai.question_validator import normalize_questions


def _clean_and_parse_json(raw: str) -> dict:
    lines = raw.strip().split("\n")
    if lines and lines[0].startswith("``"):
        lines = lines[1:]
    if lines and lines[-1].startswith("``"):
        lines = lines[:-1]
    raw = "\n".join(lines).strip()
    
    start = raw.find('{')
    if start == -1:
        raise ValueError("No JSON object found in LLM response")
    raw = raw[start:]
    try: 
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    raw = raw.rstrip()
    raw = re.sub(r",\s*$", "", raw)
    brace_count = raw.count('{') - raw.count('}')
    if brace_count > 0:
        raw += '}' * brace_count
    bracket_count = raw.count('[') - raw.count(']')
    if bracket_count > 0:
        raw += ']' * bracket_count
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from LLM: {e}")


def generate_exam(request: ExamGenerateRequest) -> ExamOut:
    client = OpenAI(
        api_key=settings.GEMINI_API_KEY or settings.OPENAI_API_KEY,
        base_url=settings.GEMINI_BASE_URL,
    )

    response = client.chat.completions.create(
        model=settings.GEMINI_MODEL,
        messages=[{"role": "user", "content": build_exam_prompt(request)}],
    )
    
    raw_text = response.choices[0].message.content
    data = _clean_and_parse_json(raw_text)
    
    questions = normalize_questions(data, request)
    
    return ExamOut(
        title=data.get("title", "آزمون بدون عنوان"),
        subject=request.subject,
        grade=request.grade,
        questions=questions
    )
