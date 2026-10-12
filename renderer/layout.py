from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


TAB_SIZE = 4


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


def _wrap_hard_line(line: str, max_width: float, measure: Callable[[str], float]) -> list[str]:
    """Soft-wrap one user-supplied line without normalising its whitespace.

    Newlines are handled by the caller, so this function never joins hard
    lines.  Spaces are kept in the returned chunks (including indentation and
    repeated spaces); a whitespace-only line remains one empty writable slot.
    """
    if line == "" or not line.strip():
        return [line]
    chunks: list[str] = []
    remaining = line
    while remaining:
        if measure(remaining) <= max_width:
            chunks.append(remaining)
            break
        # Find the last whitespace boundary that still leaves content on the
        # next line. Keep the boundary whitespace in the current chunk so no
        # source spaces disappear from the internal representation.
        # Consume whitespace and words as segments. This keeps repeated spaces
        # intact while avoiding an O(n²) character-by-character scan for long
        # Telegram messages.
        segments: list[str] = []
        start = 0
        mode = remaining[0].isspace()
        for index, char in enumerate(remaining[1:], 1):
            if char.isspace() != mode:
                segments.append(remaining[start:index])
                start, mode = index, char.isspace()
        segments.append(remaining[start:])
        current = ""
        consumed = 0
        for seg_index, segment in enumerate(segments):
            candidate = current + segment
            if not current and measure(segment) > max_width:
                low, high = 1, len(segment)
                while low < high:
                    middle = (low + high + 1) // 2
                    if measure(segment[:middle]) <= max_width:
                        low = middle
                    else:
                        high = middle - 1
                cut = max(1, low)
                chunks.append(segment[:cut])
                remaining = segment[cut:] + "".join(segments[seg_index + 1:])
                break
            if not current or measure(candidate) <= max_width:
                current = candidate
                consumed += len(segment)
                continue
            chunks.append(current)
            remaining = remaining[consumed:]
            break
        else:
            chunks.append(current)
            break
    return chunks or [""]


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

    # Normalise only the newline encoding. Every resulting list item is a
    # hard line supplied by the user; empty and whitespace-only lines consume
    # a writable slot instead of being filtered or converted to paragraph gap.
    hard_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for hard_line in hard_lines:
        # Tabs are horizontal whitespace, not glyphs. Expand them at a stable
        # four-column tab stop so indentation remains deterministic across
        # handwriting styles and page sizes.
        hard_line = hard_line.expandtabs(TAB_SIZE)
        wrapped = _wrap_hard_line(hard_line, line_width(page_line_index), measure)
        for line_text in wrapped:
            emit(line_text)
    return pages
