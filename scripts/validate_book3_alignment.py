from __future__ import annotations

import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.books import book_registry
from database.models import UserPreferences
from renderer.paper import load_paper
from services.generation_service import GenerationService


def font(size: int):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def fit_local_ruling(base: Image.Image, expected_y: int, x0: int, x1: int) -> tuple[float, float]:
    """Fit y=a*x+b to the photographed ruling near one expected row."""
    rgb = base.convert("RGB")
    points: list[tuple[float, float]] = []
    for x in range(x0, x1, 20):
        end = min(x + 20, x1)
        candidates: list[tuple[float, int]] = []
        for y in range(max(0, expected_y - 12), min(rgb.height, expected_y + 13)):
            darkness = sum(sum(rgb.getpixel((xx, y))) for xx in range(x, end)) / max(1, (end - x) * 3)
            candidates.append((darkness, y))
        points.append((x + (end - x) / 2, min(candidates)[1]))
    n = len(points)
    sx = sum(x for x, _ in points)
    sy = sum(y for _, y in points)
    sxx = sum(x * x for x, _ in points)
    sxy = sum(x * y for x, y in points)
    denom = n * sxx - sx * sx
    a = (n * sxy - sx * sy) / denom if denom else 0.0
    return a, (sy - a * sx) / n


def detect_left_boundary(base: Image.Image, y0: int, y1: int, expected_x: int = 621) -> int:
    """Find the photographed vertical divider at this row's local height."""
    rgb = base.convert("RGB")
    values: list[tuple[float, int]] = []
    for x in range(expected_x - 55, expected_x + 55):
        darkness = sum(sum(rgb.getpixel((x, y))) for y in range(y0, y1)) / max(1, (y1 - y0) * 3)
        values.append((darkness, x))
    return min(values)[1]


def main() -> None:
    menu_dir = ROOT / "menu_buku"
    template = book_registry(menu_dir)["book_buku_tulis_3"]
    base, layout = load_paper(template.template_id, ROOT / "assets" / "papers", menu_dir)
    if layout.baseline_positions is None or len(layout.baseline_positions) != 31:
        raise AssertionError("Buku 3 wajib memiliki tepat 31 baseline fisik")

    lines = [f"Baris {index:02d} tulisan uji" for index in range(1, 32)]
    preferences = UserPreferences(
        telegram_user_id=1, book_style=template.template_id,
        handwriting_style="natural_student_upright_01", ink_color="blue",
        show_identity=False, show_date=False,
    )
    service = GenerationService(ROOT / "assets")
    result = service.render("\n".join(lines), preferences, seed=20261012)
    text_layer = service.render("\n".join(lines), preferences, seed=20261012, text_only=True).pages[0].convert("RGBA")
    image = result.pages[0].convert("RGB")
    output_dir = ROOT / "outputs" / "book3_alignment"
    output_dir.mkdir(parents=True, exist_ok=True)
    image.save(output_dir / "book_buku_tulis_3_exact31.png", "PNG", optimize=True)

    debug = base.convert("RGB")
    draw = ImageDraw.Draw(debug, "RGBA")
    rows: list[dict[str, object]] = []
    x0, x1 = 570, debug.width - layout.margin_right
    render_origins = [
        ruling - (layout.baseline_offsets[index] if layout.baseline_offsets else layout.baseline_offset)
        for index, ruling in enumerate(layout.baseline_positions)
    ]
    for index, expected_ruling in enumerate(layout.baseline_positions, start=1):
        slope, intercept = fit_local_ruling(base, expected_ruling, x0, x1)
        text_origin = render_origins[index - 1]
        left_boundary = detect_left_boundary(base, text_origin + 8, text_origin + 55)
        # The glyph alpha has a stable visual offset below the renderer origin.
        # Keep this slot window tight; midpoint bands would include the tail of
        # the preceding row when the photographed ruling is only ~68 px apart.
        band_top = max(0, text_origin + 8)
        band_bottom = min(text_layer.height, text_origin + 66)
        pixels: list[tuple[int, int]] = []
        for y in range(band_top, band_bottom):
            for x in range(x0, x1):
                if text_layer.getpixel((x, y))[3] >= 20:
                    pixels.append((x, y))
        if pixels:
            left = min(x for x, _ in pixels)
            right = max(x for x, _ in pixels)
            top = min(y for _, y in pixels)
            bottom = max(y for _, y in pixels)
            min_clearance = min(slope * x + intercept - y for x, y in pixels)
            left_clearance = left - left_boundary
            status = "PASS" if min_clearance >= 2.0 and left_clearance >= 8 else "FAIL"
            draw.rectangle((left, top, right, bottom), outline=(0, 180, 255, 220), width=3)
        else:
            left = right = top = bottom = -1
            min_clearance = -1.0
            status = "FAIL"
        draw.line((x0, slope * x0 + intercept, x1, slope * x1 + intercept), fill=(225, 40, 40, 220), width=3)
        draw.line((left_boundary, band_top, left_boundary, band_bottom), fill=(255, 150, 0, 230), width=3)
        draw.line((x0, text_origin, x1, text_origin), fill=(50, 220, 80, 180), width=2)
        draw.text((x0 + 8, round(text_origin - 30)), f"L{index:02d}", font=font(24), fill=(220, 30, 30, 255))
        rows.append({
            "line_index": index,
            "left_boundary_x": left_boundary,
            "actual_ink_left_x": left if pixels else -1,
            "left_clearance_px": round(left - left_boundary, 2) if pixels else -1,
            "ruling_y_left": round(slope * x0 + intercept, 2),
            "ruling_y_right": round(slope * x1 + intercept, 2),
            "baseline_y": text_origin,
            "text_top": top,
            "text_bottom": bottom,
            "clearance_px": round(min_clearance, 2),
            "status": status,
        })

    debug.save(output_dir / "book_buku_tulis_3_debug_31_lines.png", "PNG", optimize=True)
    with (output_dir / "book_buku_tulis_3_calibration.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for name, start, end in (("01_10", 1, 10), ("11_20", 11, 20), ("21_31", 21, 31)):
        top = max(0, round(layout.baseline_positions[start - 1] - 150))
        bottom = min(image.height, round(layout.baseline_positions[end - 1] + 150))
        image.crop((0, top, image.width, bottom)).save(output_dir / f"book_buku_tulis_3_closeup_{name}.png", "PNG", optimize=True)

    failed = [row for row in rows if row["status"] != "PASS"]
    print(f"slots={len(rows)} failed={len(failed)}")
    for row in rows:
        print(row)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
