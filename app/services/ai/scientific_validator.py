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


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = text.casefold()
    return any(term.casefold() in normalized for term in terms)


def _has_mass_distance_change(text: str) -> bool:
    normalized = text.casefold()

    mass_change = bool(
        re.search(
            r"(mass|جرم).{0,80}(double|twice|دو برابر|۲ برابر)",
            normalized,
        )
        or re.search(
            r"(double|twice|دو برابر|۲ برابر).{0,80}(mass|جرم)",
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
    Performs conservative, deterministic checks for known scientific traps.

    Unknown or generic questions are intentionally ignored. This validator
    must not replace a domain-aware reasoning system.
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

    is_gravity_question = (
        _contains_any(topic, _GRAVITY_TERMS)
        or _contains_any(text, _GRAVITY_TERMS)
    )

    if not is_gravity_question:
        return

    # F = G * m1 * m2 / r²:
    # doubling one mass and halving distance => 2 * 4 = 8 times.
    if _has_mass_distance_change(text):
        if _contains_any(text, _FOUR_TIMES_TERMS) and not _contains_any(
            text, _EIGHT_TIMES_TERMS
        ):
            raise ValueError(
                "Gravity scaling is scientifically incorrect: "
                "doubling one mass and halving the distance changes the force "
                "by a factor of eight."
            )

    # Conservative orbital wording check.
    orbital_text = (
        "orbit",
        "orbital",
        "مدار",
        "سرعت مماسی",
        "tangential velocity",
    )
    if _contains_any(text, orbital_text):
        incorrect_fall_claims = (
            "gravity does not act",
            "جاذبه作用 ندارد",
            "جاذبه نقشی ندارد",
            "سرعت مماسی مانع اثر جاذبه",
        )
        if _contains_any(text, incorrect_fall_claims):
            raise ValueError(
                "Orbital explanation incorrectly denies gravity's role."
            )
