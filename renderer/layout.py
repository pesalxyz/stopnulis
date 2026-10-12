from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class LayoutConfig:
    margin_left: int = 250
    margin_left_positions: tuple[int, ...] | None = None
    margin_right: int = 180
    margin_top: int = 500
    margin_bottom: int = 220
    line_spacing: int = 92
    paragraph_spacing: int = 46
    baseline_positions: tuple[int, ...] | None = None
    baseline_start_index: int = 0
    baseline_slopes: tuple[float, ...] | None = None
    baseline_offset: int = 64
    handwriting_scale: float = 1.0
    header_top: int = 120
    baseline_slope: float = 0.0
    baseline_offsets: tuple[int, ...] | None = None
    header_outside_lines: bool = False
    header_margin_left: int | None = None
    header_margin_right: int | None = None
    header_horizontal: bool = False
    body_scale_adjust: float = 1.0
    header_field_scales: tuple[float, ...] | None = None
    # Per-template header scale.  This keeps legacy paper templates stable
    # while allowing photographed books to use the active body glyph scale.
    header_scale_override: float | None = None


@dataclass(frozen=True, slots=True)
class PositionedLine:
    text: str
    x: int
    y: int
    baseline_slope: float = 0.0


def wrap_paragraph(paragraph: str, max_width: float, measure: Callable[[str], float]) -> list[str]:
    """Wrap a paragraph by words, splitting individual overlong words safely."""
    if not paragraph:
        return [""]
    words = paragraph.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if measure(candidate) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        if measure(word) <= max_width:
            current = word
            continue
        chunk = ""
        for char in word:
            if chunk and measure(chunk + char) > max_width:
                lines.append(chunk)
                chunk = char
            else:
                chunk += char
        current = chunk
    if current:
        lines.append(current)
    return lines or [""]


def paginate_text(
    text: str,
    page_width: int,
    page_height: int,
    config: LayoutConfig,
    measure: Callable[[str], float],
) -> list[list[PositionedLine]]:
    effective_left = max((config.margin_left_positions or (config.margin_left,)))
    max_width = page_width - effective_left - config.margin_right
    bottom = page_height - config.margin_bottom
    pages: list[list[PositionedLine]] = [[]]
    y = config.margin_top
    page_line_index = 0

    paragraphs = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for index, paragraph in enumerate(paragraphs):
        # Physical ruled templates have no spare baseline for an empty
        # paragraph separator. Keep paragraph breaks semantic without
        # consuming one of the photographed rows.
        if paragraph == "" and config.baseline_positions is not None:
            continue
        wrapped = wrap_paragraph(paragraph, max_width, measure)
        if paragraph == "":
            wrapped = [""]
        for line in wrapped:
            physical_index = config.baseline_start_index + page_line_index
            if config.baseline_positions is not None and physical_index >= len(config.baseline_positions):
                pages.append([])
                y = config.margin_top
                page_line_index = 0
                physical_index = config.baseline_start_index
            if config.baseline_positions is not None and physical_index < len(config.baseline_positions):
                y = config.baseline_positions[physical_index] - config.baseline_offset
                if config.baseline_offsets is not None and physical_index < len(config.baseline_offsets):
                    y += config.baseline_offset - config.baseline_offsets[physical_index]
            elif y + config.line_spacing > bottom:
                pages.append([])
                y = config.margin_top
                page_line_index = 0
            x = config.margin_left
            if config.margin_left_positions is not None and physical_index < len(config.margin_left_positions):
                x = config.margin_left_positions[physical_index]
            slope = config.baseline_slope
            if config.baseline_slopes is not None and physical_index < len(config.baseline_slopes):
                slope = config.baseline_slopes[physical_index]
            pages[-1].append(PositionedLine(line, x, y, slope))
            y += config.line_spacing
            page_line_index += 1
        if index < len(paragraphs) - 1 and paragraph:
            # Stable content-based imperfection avoids geometrically identical paragraph gaps.
            gap_jitter = 0
            if config.paragraph_spacing:
                signature = sum((position + 1) * ord(char) for position, char in enumerate(paragraph[:80]))
                gap_jitter = (signature + index * 17) % 13 - 6
            y += config.paragraph_spacing + gap_jitter
    return pages
