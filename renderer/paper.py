from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from database.models import UserPreferences
from renderer.handwriting import load_font
from renderer.layout import LayoutConfig
from config.books import BookTemplate, book_registry, default_book_id


PAGE_SIZE = (2480, 3508)


@dataclass(frozen=True, slots=True)
class PaperDefinition:
    filename: str
    layout: LayoutConfig


PAPERS: dict[str, PaperDefinition] = {
    "lined": PaperDefinition("lined.png", LayoutConfig(line_spacing=104)),
    "grid": PaperDefinition("grid.png", LayoutConfig(line_spacing=100)),
    "plain": PaperDefinition("plain.png", LayoutConfig(line_spacing=94)),
    "folio": PaperDefinition("folio.png", LayoutConfig(margin_left=330, line_spacing=104)),
}


def load_paper(style: str, papers_dir: Path, menu_dir: Path | None = None) -> tuple[Image.Image, LayoutConfig]:
    if menu_dir is not None:
        registry = book_registry(menu_dir)
        template = registry.get(style)
        if template is not None:
            return _load_menu_template(template, menu_dir)
        if style.startswith("book_") or style in {"lined", "grid", "plain", "folio"}:
            style = default_book_id(menu_dir)
    if style.startswith("custom:"):
        safe_id = style.partition(":")[2]
        if not safe_id.isdigit():
            raise ValueError("ID template custom tidak valid.")
        path = papers_dir / "custom" / f"{safe_id}.png"
        definition = PaperDefinition(str(path), LayoutConfig())
    else:
        definition = PAPERS.get(style, PAPERS["lined"])
        path = papers_dir / definition.filename
    if not path.exists():
        raise FileNotFoundError(f"Template kertas '{style}' tidak ditemukan.")
    image = Image.open(path).convert("RGBA")
    if image.size != PAGE_SIZE:
        image = image.resize(PAGE_SIZE, Image.Resampling.LANCZOS)
    return image, definition.layout


def _load_menu_template(template: BookTemplate, menu_dir: Path) -> tuple[Image.Image, LayoutConfig]:
    path = menu_dir / template.filename
    if not path.exists():
        raise FileNotFoundError(f"Template buku '{template.filename}' tidak ditemukan.")
    with Image.open(path) as source:
        # Keep the original image intact; photographed surroundings remain part of
        # the source background. Only proportional fitting to the A4 canvas occurs.
        image = source.convert("RGB")
        scale = min(PAGE_SIZE[0] / image.width, PAGE_SIZE[1] / image.height)
        size = (round(image.width * scale), round(image.height * scale))
        resized = image.resize(size, Image.Resampling.LANCZOS)
    offset_x = (PAGE_SIZE[0] - resized.width) // 2
    offset_y = (PAGE_SIZE[1] - resized.height) // 2
    canvas = Image.new("RGBA", PAGE_SIZE, (248, 247, 240, 255))
    canvas.paste(resized, (offset_x, offset_y))
    left_x = round(offset_x + template.source_left * scale)
    right_x = round(offset_x + template.source_right * scale)
    margin_right = max(120, PAGE_SIZE[0] - right_x)
    scale_factor = template.handwriting_scale
    if template.filename == "kertas_hvs.jpg":
        # HVS is an unruled photographed sheet.  Establish a virtual grid in
        # the physical paper polygon instead of using the full image bounds.
        # Source corners measured from the sheet edges: (89,101), (639,102),
        # (637,879), (85,878). Margins are 2.5 cm left, 2 cm right/top/bottom.
        top_left = (round(offset_x + 89 * scale), round(offset_y + 101 * scale))
        top_right = (round(offset_x + 639 * scale), round(offset_y + 102 * scale))
        bottom_left = (round(offset_x + 85 * scale), round(offset_y + 878 * scale))
        bottom_right = (round(offset_x + 637 * scale), round(offset_y + 879 * scale))
        cm_x = (top_right[0] - top_left[0]) / 21.0
        cm_y = (bottom_left[1] - top_left[1]) / 29.7
        # Body margins are intentionally narrower than the previous 2.5 cm
        # setting: approximately 6.5% of the physical sheet width on both
        # sides. Header coordinates remain unchanged below.
        left_margin = 0.065 * (top_right[0] - top_left[0])
        right_margin = 0.065 * (top_right[0] - top_left[0])
        top_margin = 2.0 * cm_y; bottom_margin = 2.0 * cm_y
        count = 28
        first_y = top_left[1] + top_margin + 90
        pitch = 76
        baselines = tuple(round(first_y + index * pitch) for index in range(count))
        left_positions = tuple(round(top_left[0] + left_margin + (bottom_left[0] - top_left[0]) * index / (count - 1)) for index in range(count))
        safe_right = round(top_right[0] - right_margin)
        slope = (top_right[1] - top_left[1]) / max(1, top_right[0] - top_left[0])
        layout = LayoutConfig(
            margin_left=left_positions[0], margin_left_positions=left_positions,
            margin_right=max(120, PAGE_SIZE[0] - safe_right),
            margin_top=baselines[0] - 64, margin_bottom=round(bottom_margin),
            line_spacing=pitch, paragraph_spacing=round(pitch * 0.5),
            baseline_positions=baselines, baseline_offset=64,
            baseline_slopes=tuple(slope for _ in baselines),
            handwriting_scale=scale_factor,
            header_top=max(80, top_left[1] + 20),
            header_outside_lines=True,
            header_margin_left=521,
            header_margin_right=503,
            header_horizontal=True,
            header_scale_override=0.80,
        )
        return canvas, layout
    if template.filename == "buku_tulis_1.jpg" and template.source_baselines is not None:
        # The photographed checkbox divider is at source x≈110. Keep the
        # writing origin 10 px to its right in output coordinates while
        # leaving the calibrated baselines and line spacing untouched.
        baselines = tuple(round(offset_y + value * scale) for value in template.source_baselines)
        divider_x = round(offset_x + 110 * scale)
        body_left = divider_x + 10
        layout = LayoutConfig(
            margin_left=body_left,
            margin_left_positions=tuple(body_left for _ in baselines),
            margin_right=margin_right,
            margin_top=max(0, baselines[0] - round(64 * scale_factor)),
            margin_bottom=max(180, PAGE_SIZE[1] - baselines[-1] - round(70 * scale_factor)),
            line_spacing=round((baselines[1] - baselines[0]) * scale_factor),
            paragraph_spacing=round(46 * scale_factor),
            baseline_positions=baselines,
            baseline_offset=round(74 * scale_factor),
            handwriting_scale=scale_factor,
            header_top=max(80, round(offset_y + (template.source_header_bottom - 50) * scale)),
            header_outside_lines=True,
            header_margin_left=round(offset_x + 145 * scale),
            header_margin_right=margin_right,
            header_horizontal=True,
            body_scale_adjust=1.08,
        )
        return canvas, layout
    if template.source_baselines is None:
        layout = LayoutConfig(
            margin_left=left_x,
            margin_right=margin_right,
            margin_top=round(offset_y + template.source_header_bottom * scale + 170 * scale),
            margin_bottom=max(180, PAGE_SIZE[1] - round(offset_y + image.height * scale) + 220),
            line_spacing=round(104 * scale_factor),
            paragraph_spacing=0 if template.filename == "kertas_folio_1.png" else round(46 * scale_factor),
            baseline_positions=None,
            baseline_offset=round(64 * scale_factor),
            handwriting_scale=scale_factor,
            header_top=max(80, round(offset_y + (template.source_header_bottom - 50) * scale)),
        )
    else:
        baselines = tuple(round(offset_y + value * scale) for value in template.source_baselines)
        header_top = max(0, round(offset_y + (template.source_header_bottom - 50) * scale))
        # The photographed Buku 3 sheet starts below a large surrounding
        # background band. Keep the standardized header on the sheet itself,
        # while leaving the calibrated body baselines untouched.
        if template.filename == "buku_tulis_3.jpg":
            header_top = max(0, baselines[0] - 245)
        if template.filename == "buku_tulis_6.jpg":
            # Keep both identity rows above the first physical ruling.  The
            # header is positioned from the measured first line rather than a
            # page-global offset, leaving the body grid untouched.
            header_top = max(80, baselines[0] - 285)
        if template.filename == "kertas_folio_1.png":
            header_top = max(0, baselines[0] - 185)
        layout = LayoutConfig(
            margin_left=left_x,
            margin_right=margin_right,
            margin_top=max(0, baselines[0] - round(64 * scale_factor)),
            margin_bottom=max(180, PAGE_SIZE[1] - baselines[-1] - round(70 * scale_factor)),
            line_spacing=round((baselines[1] - baselines[0]) * scale_factor) if len(baselines) > 1 else 100,
            paragraph_spacing=0 if template.filename == "kertas_folio_1.png" else round(46 * scale_factor),
            baseline_positions=baselines,
            baseline_start_index=4 if template.filename == "buku_tulis_4.jpg" else 0,
            # The multi-glyph writer's draw origin sits above its visual baseline.
            # Keep the ink just above each photographed rule instead of centered on it.
            baseline_offset=round((82 if template.filename == "buku_tulis_4.jpg" else (75 if template.filename == "kertas_folio_1.png" else 74)) * scale_factor),
            handwriting_scale=scale_factor,
            header_top=max(80, header_top),
            # Follow the small local fall of the photographed ruling without
            # altering glyph geometry or introducing a global diagonal skew.
            baseline_slope=-0.004 if template.filename == "buku_tulis_3.jpg" else 0.0,
            baseline_offsets=(
                # Keep every glyph visibly above its corresponding physical rule.
                (75, *([75] * 30))
                if template.filename == "buku_tulis_3.jpg" else (
                    # Per-line Folio calibration in output pixels.  The
                    # photographed sheet bows slightly, so a single offset
                    # produces a 2--25 px clearance drift.
                    (57, 58, 60, 60, 61, 62, 63, 64, 64, 64,
                     66, 66, 67, 67, 68, 68, 68, 69, 69, 70,
                     70, 70, 70, 70, 70, 69, 69, 68, 66, 65,
                     63, 62, 59, 58, 55, 53, 51, 48)
                    if template.filename == "kertas_folio_1.png" else None
                )
            ),
            baseline_slopes=(
                (0.01350, 0.01535, 0.01460, 0.01416, 0.01320, 0.01242,
                 0.01224, 0.01169, 0.01147, 0.00863, 0.00628, 0.00921,
                 0.00941, 0.00856, 0.00780, 0.00691, 0.00601, 0.00506,
                 0.00414, 0.00354, 0.00305, 0.00338, 0.00426, 0.00552,
                 0.00659, 0.00740, 0.00784, 0.00629, 0.00593, 0.00656,
                 0.00784)
                if template.filename == "buku_tulis_4.jpg" else (
                    (-0.00120, -0.00017, -0.00057, -0.00234, -0.00267,
                     -0.00353, -0.00308, -0.00468, -0.00459, -0.00505,
                     -0.00486, -0.00493, -0.00521, -0.00503, -0.00522,
                     -0.00474, -0.00473, -0.00503, -0.00555, -0.00510,
                     -0.00579, -0.00563, -0.00563, -0.00615, -0.00588,
                     -0.00651, -0.00507, -0.00535, -0.00475, -0.00392)
                    if template.filename == "buku_tulis_6.jpg" else (
                        (-0.00483, -0.00375, -0.00314, -0.00148, -0.00020,
                         0.00027, 0.00247, 0.00049, 0.00204, 0.00257,
                         0.00310, 0.00488, 0.00244, 0.00364, 0.00259,
                         0.00076, 0.00196, 0.00190, 0.00208, 0.00359,
                         0.00151, 0.00513, 0.00249, 0.00218, 0.00516,
                         0.00233, 0.00268, 0.00332, 0.00102, 0.00147,
                         -0.00069, -0.00454, -0.00639, -0.00790, -0.01103,
                         -0.01172, -0.00997, -0.00745)
                        if template.filename == "kertas_folio_1.png" else None
                    )
                )
            ),
            margin_left_positions=(
                # Local vertical-boundary x plus a 10 px origin margin. The
                # photographed boundary drifts right down the page.
                (621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631,
                 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642,
                 643, 644, 645, 646, 647, 648, 649, 650, 651)
                if template.filename == "buku_tulis_3.jpg" else None
            ),
            # All photographed templates use the same two-row identity layout;
            # only their measured anchors/margins differ.
            header_outside_lines=True,
            header_horizontal=True,
            body_scale_adjust=1.08 if template.filename == "buku_tulis_6.jpg" else 1.0,
            header_field_scales=(1.0, 0.86, 1.0, 0.86, 0.86) if template.filename == "buku_tulis_3.jpg" else None,
            header_scale_override=0.80 if template.filename == "kertas_folio_1.png" else 1.0,
        )
    return canvas, layout


def _draw_handwriting_header_field(
    image: Image.Image,
    text: str,
    x: int,
    y: int,
    handwriting_renderer,
    scale: float = 0.80,
    max_width: int | None = None,
    right_anchor: int | None = None,
    vertical_bounds: tuple[float, float] | None = None,
    normalize_reference: bool = False,
) -> tuple[int, int, int, int] | None:
    """Render a header field with the active handwriting renderer at 80%."""
    if not text or handwriting_renderer is None:
        return None
    scratch = Image.new("RGBA", (max(500, image.width // 2), 180), (0, 0, 0, 0))
    handwriting_renderer.render_line(scratch, text, 18, 18, optimized=False)
    alpha = scratch.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return None
    patch = scratch.crop((max(0, bbox[0] - 8), max(0, bbox[1] - 8), min(scratch.width, bbox[2] + 8), min(scratch.height, bbox[3] + 8)))
    if normalize_reference:
        scale *= 54.0 / max(1.0, float(getattr(handwriting_renderer, "font_size", 54.0)))
    if max_width is not None:
        scale = min(scale, max(0.60, max_width / max(1, patch.width)))
    patch = patch.resize((max(1, round(patch.width * scale)), max(1, round(patch.height * scale))), Image.Resampling.LANCZOS)
    paste_x = right_anchor - patch.width if right_anchor is not None else x
    if vertical_bounds is not None:
        top, bottom = vertical_bounds
        paste_y = round((top + bottom - patch.height) / 2)
    else:
        paste_y = y
    image.alpha_composite(patch, (paste_x, paste_y))
    return (paste_x, paste_y, paste_x + patch.width, paste_y + patch.height)


def add_header(
    image: Image.Image,
    preferences: UserPreferences,
    date_text: str | None,
    font_path: Path | None = None,
    layout: LayoutConfig | None = None,
    handwriting_renderer=None,
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    font = load_font(font_path, 42)
    small = load_font(font_path, 36)
    ink = (45, 52, 70, 235)
    if layout and layout.header_outside_lines and layout.header_horizontal and layout.baseline_positions:
        # Shared Buku 6-style two-row identity layout. Coordinates remain
        # template-specific through each layout's measured anchors/margins.
        first = layout.baseline_positions[layout.baseline_start_index]
        top = layout.header_top if layout.header_top else max(70, first - 220)
        left = layout.header_margin_left or layout.margin_left
        right_edge = image.width - (layout.header_margin_right or layout.margin_right)
        mid = left + max(420, round((right_edge - left) * 0.40))
        row_gap = 48
        if layout.baseline_start_index == 4:
            # Buku 4 is frozen: preserve its established two-row geometry.
            slopes = layout.baseline_slopes or ()

            def ruling(row: int, x: int) -> float:
                slope = slopes[row] if row < len(slopes) else 0.0
                return layout.baseline_positions[row] + slope * (x - layout.margin_left)

            row_gap = None
            header_scale = layout.header_scale_override if layout.header_scale_override is not None else 1.0
            legacy_book4 = False
        else:
            ruling = None
            # Covered templates use the exact active body renderer scale.
            # Buku 4 takes the same path with its own physical row geometry;
            # this value is intentionally not a shared 0.80 shrink factor.
            header_scale = 1.0
            legacy_book4 = False
        fields = []
        if preferences.show_identity:
            fields = [
                (f"Nama: {preferences.name or ''}", left, 0, 0),
                (f"NPM: {preferences.npm or ''}", mid, 0, 1),
                (f"Kelas: {preferences.class_name or ''}", left, 1, 2),
                (f"Absen: {preferences.attendance_number or ''}", mid, 1, 3),
            ]
        for text, x, row, field_index in fields:
            if ruling and not legacy_book4:
                top_y = ruling(row, x)
                bottom_y = ruling(row + 1, x)
                bounds = (top_y + 8, bottom_y - 8)
                y = round((bounds[0] + bounds[1]) / 2)
            else:
                bounds = None
                y = top + (row_gap or 48) * row
            if handwriting_renderer is not None:
                field_scale = header_scale
                if layout.header_field_scales and field_index < len(layout.header_field_scales):
                    field_scale *= layout.header_field_scales[field_index]
                _draw_handwriting_header_field(
                    image, text, x, y, handwriting_renderer, scale=field_scale,
                    max_width=(max(160, mid - x - 24) if x == left else max(160, right_edge - x)) if ruling else None,
                    vertical_bounds=bounds,
                    normalize_reference=bool(ruling),
                )
            elif text.split(": ", 1)[1]:
                draw.text((x, y), text, font=small, fill=ink)
        if date_text:
            text = f"Tanggal: {date_text}"
            if handwriting_renderer is not None:
                date_scale = header_scale
                if layout.header_field_scales and len(layout.header_field_scales) > 4:
                    date_scale *= layout.header_field_scales[4]
                _draw_handwriting_header_field(
                    image, text, right_edge, round(top), handwriting_renderer, scale=date_scale,
                    max_width=max(160, right_edge - mid - 24) if ruling else None,
                    right_anchor=right_edge,
                    vertical_bounds=(ruling(0, right_edge) + 8, ruling(1, right_edge) - 8) if ruling and not legacy_book4 else None,
                    normalize_reference=bool(ruling),
                )
            else:
                width = draw.textlength(text, font=small)
                draw.text((right_edge - width, top), text, font=small, fill=ink)
        return
    y = layout.header_top if layout else 120
    left = layout.margin_left if layout else 250
    right = layout.margin_right if layout else 180
    if preferences.show_identity:
        fields = [
            ("Nama", preferences.name), ("NPM", preferences.npm),
            ("Kelas", preferences.class_name), ("Absen", preferences.attendance_number),
        ]
        for label, value in fields:
            if value:
                draw.text((left, y), f"{label}: {value}", font=small, fill=ink)
                y += 55
    if date_text:
        text = f"Tanggal: {date_text}"
        width = draw.textlength(text, font=font)
        draw.text((image.width - right - width, layout.header_top if layout else 120), text, font=font, fill=ink)
