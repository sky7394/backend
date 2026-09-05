from __future__ import annotations

import re

from app.schemas.question import QuestionPreviewOut


_GRAVITY_TERMS = (
    "gravity",
    "gravitational",
    "جاذبه",
    "گرانش",
    "نیروی گرانشی",
)

_EIGHT_TIMES_TERMS = (
    "8 times",
    "eight times",
    "۸ برابر",
    "هشت برابر",
)

_FOUR_TIMES_TERMS = (
    "4 times",
    "four times",
    "۴ برابر",
    "چهار برابر",
)

_ORBITAL_TERMS = (
    "orbit",
    "orbital",
    "مدار",
    "سرعت مماسی",
    "tangential velocity",
)

_INCORRECT_ORBITAL_CLAIMS = (
    "gravity does not act",
    "no gravity",
    "جاذبه نقش ندارد",
    "جاذبه نقشی ندارد",
)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = text.casefold()
    return any(term.casefold() in normalized for term in terms)


def _has_mass_distance_change(text: str) -> bool:
    normalized = text.casefold()

    mass_change = bool(
        re.search(
            r"(mass|جرم).{0,80}(double|twice|دو\s*برابر|۲\s*برابر)",
            normalized,
        )
        or re.search(
            r"(double|twice|دو\s*برابر|۲\s*برابر).{0,80}(mass|جرم)",
            normalized,
        )
    )

    distance_change = bool(
        re.search(
            r"(distance|فاصله).{0,80}(half|halved|نصف|نیم)",
            normalized,
        )
        or re.search(
            r"(half|halved|نصف|نیم).{0,80}(distance|فاصله)",
            normalized,
        )
    )

    return mass_change and distance_change


def validate_scientific_content(question: QuestionPreviewOut) -> None:
    """
    Conservative deterministic checks for known scientific traps.

    This validator intentionally avoids rejecting generic questions and only
    handles a small set of high-confidence patterns.
    """
    topic = (question.topic or "").casefold()
    text = " ".join(
        part
        for part in (
            question.question_text,
            question.correct_answer,
            question.explanation or "",
        )
        if part
    )

    is_gravity_question = _contains_any(topic, _GRAVITY_TERMS) or _contains_any(
        text, _GRAVITY_TERMS
    )
    if not is_gravity_question:
        return

    # If the prompt explicitly describes doubling one mass and halving distance,
    # the correct force scaling is 8x, not 4x.
    if _has_mass_distance_change(text):
        if _contains_any(text, _FOUR_TIMES_TERMS) and not _contains_any(
            text,
            _EIGHT_TIMES_TERMS,
        ):
            raise ValueError(
                "Gravity scaling is scientifically incorrect: "
                "doubling one mass and halving the distance changes the force "
                "by a factor of eight."
            )

    # Orbital explanation guard: gravity is the centripetal force component.
    if _contains_any(text, _ORBITAL_TERMS) and _contains_any(
        text,
        _INCORRECT_ORBITAL_CLAIMS,
    ):
        raise ValueError("Orbital explanation incorrectly denies gravity's role.")
