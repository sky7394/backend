"""Render a bounded MathText subset as one LTR image in either document format.

No TeX subprocess, external file loading, or HTML evaluation is involved.
Unsupported expressions remain visible as literal text, with a logged warning.
"""
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
import logging
import re
from threading import RLock

import matplotlib
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import math_to_image
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)
_LOCK = RLock()
DPI = 240
_DELIMITED = re.compile(
    r"\$\$(.+?)\$\$|\\\[(.+?)\\\]|\\\((.+?)\\\)|(?<![\\$])\$(?!\$)(.+?)(?<!\\)\$(?!\$)",
    re.DOTALL,
)
_PLAIN_EQUATION = re.compile(
    r"[A-Za-zΑ-ω][A-Za-z0-9_{}^]*\s*=\s*[A-Za-z0-9Α-ω+*/\\^_{}().−×÷= -]+"
    r"|\\[A-Za-z]+(?:\s*\{(?:[^{}]|\{[^{}]*\})*\}){0,2}"
)


@dataclass(frozen=True)
class MathImage:
    data: bytes
    width_mm: float
    height_mm: float

    def fitted(self, max_width: float) -> tuple[float, float]:
        scale = min(1.0, max_width / self.width_mm)
        return self.width_mm * scale, self.height_mm * scale


def _plain_parts(text: str):
    cursor = 0
    for match in _PLAIN_EQUATION.finditer(text):
        if match.start() > cursor:
            yield "text", text[cursor:match.start()]
        yield "math", match.group().strip()
        cursor = match.end()
    if cursor < len(text):
        yield "text", text[cursor:]


def split_math(text: str) -> list[tuple[str, str]]:
    """Recognize $...$, $$...$$, \\( ... \\), \\[ ... \\], and plain equations."""
    parts = []
    cursor = 0
    for match in _DELIMITED.finditer(str(text)):
        parts.extend(_plain_parts(text[cursor:match.start()]))
        parts.append(("math", next(group for group in match.groups() if group is not None)))
        cursor = match.end()
    parts.extend(_plain_parts(text[cursor:]))
    return parts


@lru_cache(maxsize=128)
def render_math(expression: str) -> MathImage:
    expression = expression.strip()
    delimited = _DELIMITED.fullmatch(expression)
    if delimited:
        expression = next(group for group in delimited.groups() if group is not None)
    if not expression or len(expression) > 2000:
        raise ValueError("Math expressions must contain between 1 and 2000 characters")
    normalized = expression.replace(r"\dfrac", r"\frac").replace(r"\tfrac", r"\frac")
    normalized = normalized.replace(r"\displaystyle", "").replace("−", "-")
    buffer = BytesIO()
    with _LOCK, matplotlib.rc_context({"text.usetex": False, "mathtext.fontset": "dejavusans"}):
        try:
            math_to_image(
                f"${normalized}$", buffer, prop=FontProperties(size=12),
                dpi=DPI, format="png", color="black",
            )
        except ValueError:
            logger.warning("Unsupported math syntax; rendering the literal expression")
            font_path = str(matplotlib.get_data_path()) + "/fonts/ttf/DejaVuSans.ttf"
            font = ImageFont.truetype(font_path, 40)
            literal = " ".join(expression.splitlines())
            bounds = font.getbbox(literal)
            image = Image.new("RGB", (max(1, bounds[2] - bounds[0]) + 12,
                                      max(1, bounds[3] - bounds[1]) + 12), "white")
            ImageDraw.Draw(image).text((6 - bounds[0], 6 - bounds[1]), literal, font=font, fill="black")
            buffer = BytesIO()
            image.save(buffer, format="PNG")
    data = buffer.getvalue()
    with Image.open(BytesIO(data)) as image:
        width, height = image.size
    return MathImage(data, width * 25.4 / DPI, height * 25.4 / DPI)
