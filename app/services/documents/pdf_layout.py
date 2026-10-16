"""Measured PDF content blocks shared by questions and the answer sheet."""
from dataclasses import dataclass
from io import BytesIO

from fpdf import FPDF

from app.services.documents.math_rendering import MathImage, render_math, split_math
from app.services.documents.text_direction import fix_text_bidi, sanitize_ascii


def safe_text(pdf: FPDF, text: str) -> str:
    return fix_text_bidi(text) if getattr(pdf, "is_unicode_font", True) else sanitize_ascii(text)


@dataclass
class Block:
    kind: str
    text: str = ""
    height: float = 5.5
    image: MathImage | None = None
    width: float = 0


def text_lines(pdf: FPDF, text: str, width: float) -> list[str]:
    # Wrap in logical order first, then apply bidi per line. Shaping the whole
    # paragraph before wrapping reverses the order of long Persian paragraphs.
    logical = str(text) if getattr(pdf, "is_unicode_font", True) else sanitize_ascii(text)
    return pdf.multi_cell(width, 5.5, logical, dry_run=True, output="LINES")


def content_blocks(pdf: FPDF, parts, width: float) -> list[Block]:
    blocks = []
    for kind, value in parts:
        segments = split_math(value) if kind == "text" else [(kind, value)]
        for segment_kind, segment in segments:
            if segment_kind == "math":
                image = render_math(segment)
                w, h = image.fitted(width)
                max_height = pdf.h - pdf.t_margin - pdf.b_margin - 24
                if h > max_height:
                    w *= max_height / h
                    h = max_height
                blocks.append(Block("math", height=h + 3, image=image, width=w))
            elif segment_kind == "line":
                blocks.append(Block("line", height=8))
            elif segment.strip():
                blocks.extend(Block("text", text=line) for line in text_lines(pdf, segment, width))
    return blocks or [Block("text")]


def draw_block(pdf: FPDF, block: Block, x: float, y: float, width: float):
    pdf.set_xy(x, y)
    if block.kind == "math":
        pdf.image(BytesIO(block.image.data), x=x + (width - block.width) / 2,
                  y=y + 1, w=block.width, h=block.height - 3)
    elif block.kind == "line":
        pdf.set_draw_color(190)
        pdf.line(x, y + block.height - 2, x + width, y + block.height - 2)
        pdf.set_draw_color(0)
    else:
        pdf.cell(width, block.height, safe_text(pdf, block.text), align="R")


def draw_flow(pdf: FPDF, parts, width: float | None = None):
    width = width or pdf.epw
    for block in content_blocks(pdf, parts, width):
        if pdf.get_y() + block.height > pdf.h - pdf.b_margin:
            pdf.add_page()
        y = pdf.get_y()
        draw_block(pdf, block, pdf.l_margin, y, width)
        pdf.set_xy(pdf.l_margin, y + block.height)
