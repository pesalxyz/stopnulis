from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class LayoutConfig:
    margin_left: int = 250
    margin_left_positions: tuple[int, ...] | None = None
    margin_right_positions: tuple[int, ...] | None = None
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
    bottom = page_height - config.margin_bottom
    pages: list[list[PositionedLine]] = [[]]
    y = config.margin_top
    page_line_index = 0

    def line_width(index: int) -> float:
        physical = config.baseline_start_index + index
        left = config.margin_left_positions[physical] if config.margin_left_positions and physical < len(config.margin_left_positions) else config.margin_left
        right = config.margin_right_positions[physical] if config.margin_right_positions and physical < len(config.margin_right_positions) else config.margin_right
        return max(1.0, page_width - left - right)

    def emit(line_text: str) -> None:
        nonlocal y, page_line_index
        physical_index = config.baseline_start_index + page_line_index
        if config.baseline_positions is not None and physical_index >= len(config.baseline_positions):
            pages.append([])
            y = config.margin_top
            page_line_index = 0
            physical_index = config.baseline_start_index
        if config.baseline_positions is not None and physical_index < len(config.baseline_positions):
            line_y = config.baseline_positions[physical_index] - config.baseline_offset
            if config.baseline_offsets is not None and physical_index < len(config.baseline_offsets):
                line_y += config.baseline_offset - config.baseline_offsets[physical_index]
        else:
            if y + config.line_spacing > bottom and pages[-1]:
                pages.append([])
                y = config.margin_top
                page_line_index = 0
                physical_index = config.baseline_start_index
            line_y = y
        x = config.margin_left_positions[physical_index] if config.margin_left_positions and physical_index < len(config.margin_left_positions) else config.margin_left
        slope = config.baseline_slope
        if config.baseline_slopes is not None and physical_index < len(config.baseline_slopes):
            slope = config.baseline_slopes[physical_index]
        pages[-1].append(PositionedLine(line_text, x, line_y, slope))
        y = line_y + config.line_spacing
        page_line_index += 1

    paragraphs = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for index, paragraph in enumerate(paragraphs):
        # Physical ruled templates have no spare baseline for an empty
        # paragraph separator. Keep paragraph breaks semantic without
        # consuming one of the photographed rows.
        if paragraph == "" and config.baseline_positions is not None:
            continue
        if paragraph == "":
            emit("")
        else:
            current = ""
            for word in paragraph.split():
                candidate = f"{current} {word}".strip()
                if current and measure(candidate) > line_width(page_line_index):
                    emit(current)
                    current = ""
                    candidate = word
                # Split only genuinely over-wide words; normal words remain
                # intact and are tested against the actual current line width.
                while measure(candidate) > line_width(page_line_index):
                    chunk = ""
                    for char in candidate:
                        trial = chunk + char
                        if chunk and measure(trial) > line_width(page_line_index):
                            break
                        chunk = trial
                    if not chunk:
                        chunk = candidate[:1]
                    emit(chunk)
                    candidate = candidate[len(chunk):]
                    if not candidate:
                        break
                if candidate:
                    current = candidate
            if current:
                emit(current)
        if index < len(paragraphs) - 1 and paragraph:
            # Stable content-based imperfection avoids geometrically identical paragraph gaps.
            gap_jitter = 0
            if config.paragraph_spacing:
                signature = sum((position + 1) * ord(char) for position, char in enumerate(paragraph[:80]))
                gap_jitter = (signature + index * 17) % 13 - 6
            y += config.paragraph_spacing + gap_jitter
    return pages
