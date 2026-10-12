from __future__ import annotations

import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.books import book_registry
from database.models import UserPreferences
from renderer.paper import add_header, load_paper
from services.generation_service import GenerationService


def label_font(size: int = 24):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def darkest_column(image: Image.Image, expected: int, y0: int, y1: int, radius: int = 35) -> int:
    rgb = image.convert("RGB")
    scores = []
    for x in range(max(0, expected - radius), min(image.width, expected + radius + 1)):
        score = sum(sum(rgb.getpixel((x, y))) for y in range(max(0, y0), min(image.height, y1)))
        scores.append((score, x))
    return min(scores)[1]


def ruling_y(image: Image.Image, expected: int, x0: int, x1: int) -> int:
    rgb = image.convert("RGB")
    scores = []
    for y in range(max(0, expected - 12), min(image.height, expected + 13)):
        score = sum(sum(rgb.getpixel((x, y))) for x in range(x0, x1, 4))
        scores.append((score, y))
    return min(scores)[1]


def alpha_bbox(layer: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int, int] | None:
    x0, y0, x1, y1 = box
    points = [
        (x, y)
        for y in range(max(0, y0), min(layer.height, y1))
        for x in range(max(0, x0), min(layer.width, x1))
        if layer.getpixel((x, y))[3] >= 20
    ]
    if not points:
        return None
    return min(x for x, _ in points), min(y for _, y in points), max(x for x, _ in points), max(y for _, y in points)


def make_preferences() -> UserPreferences:
    return UserPreferences(
        telegram_user_id=1,
        book_style="book_buku_tulis_1",
        handwriting_style="natural_student_upright_01",
        ink_color="blue",
        name="Faisal",
        npm="123456",
        class_name="SI-4A",
        attendance_number="07",
        show_identity=True,
        show_date=True,
        date_mode="custom",
        custom_date="12-10-2026",
    )


def main() -> None:
    menu_dir = ROOT / "menu_buku"
    template = book_registry(menu_dir)["book_buku_tulis_1"]
    base, layout = load_paper(template.template_id, ROOT / "assets" / "papers", menu_dir)
    prefs = make_preferences()
    service = GenerationService(ROOT / "assets")
    # One deterministic line per physical rule makes every row measurable.
    text = "\n".join(f"Baris {i:02d} tulisan uji" for i in range(1, len(layout.baseline_positions or ())))
    final = service.render(text, prefs, seed=20261012).pages[0].convert("RGB")
    ink_layer = service.render(text, prefs, seed=20261012, text_only=True).pages[0].convert("RGBA")
    out = ROOT / "outputs" / "book1_alignment"
    out.mkdir(parents=True, exist_ok=True)
    final.save(out / "book1_final.png", "PNG", optimize=True)
    # Keep a convenient root-level artifact for the bot's normal output folder.
    final.save(ROOT / "outputs" / "book1_final.png", "PNG", optimize=True)

    header_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    add_header(header_layer, prefs, "12-10-2026", None, layout)
    header_box = alpha_bbox(header_layer, (0, 0, base.width, max(0, layout.baseline_positions[0] - 2)))
    first_rule = ruling_y(base, layout.baseline_positions[0], layout.margin_left, base.width - layout.margin_right)

    expected_divider = layout.margin_left - 10
    divider_x = darkest_column(base, expected_divider, layout.baseline_positions[0], layout.baseline_positions[-1] + 60)
    rows: list[dict[str, object]] = []
    debug = base.convert("RGB")
    draw = ImageDraw.Draw(debug, "RGBA")
    x0, x1 = layout.margin_left - 20, base.width - layout.margin_right
    for index, baseline in enumerate(layout.baseline_positions or (), start=1):
        origin = baseline - layout.baseline_offset
        bbox = alpha_bbox(ink_layer, (0, max(0, origin - 8), base.width, min(base.height, origin + 82)))
        actual_rule = ruling_y(base, baseline, max(0, divider_x + 15), x1)
        if bbox:
            left, top, right, bottom = bbox
            clearance = left - divider_x
            vertical_clearance = actual_rule - bottom
            status = "PASS" if clearance >= 8 and vertical_clearance >= 2 and right <= x1 else "FAIL"
            draw.rectangle(bbox, outline=(0, 180, 255, 230), width=3)
        else:
            left = top = right = bottom = -1
            clearance = vertical_clearance = -1
            # The probe uses semantic newlines, so paragraph spacing can push
            # the final physical row onto page two. An unused row is not a
            # collision; rows with actual glyph pixels are the rows assessed.
            status = "SKIP"
        draw.line((divider_x, max(0, origin - 10), divider_x, min(base.height, origin + 82)), fill=(255, 145, 0, 230), width=3)
        draw.line((max(0, divider_x + 10), actual_rule, x1, actual_rule), fill=(225, 40, 40, 210), width=3)
        draw.text((max(0, divider_x + 18), max(0, origin - 28)), f"L{index:02d}", font=label_font(), fill=(220, 30, 30, 255))
        rows.append({
            "line_index": index,
            "ruling_y": actual_rule,
            "baseline_y": baseline,
            "ink_left": left,
            "ink_top": top,
            "ink_right": right,
            "ink_bottom": bottom,
            "left_boundary_x": divider_x,
            "left_clearance_px": round(clearance, 2),
            "vertical_clearance_px": round(vertical_clearance, 2),
            "status": status,
        })

    if header_box:
        draw.rectangle(header_box, outline=(140, 0, 220, 230), width=4)
        header_bottom = header_box[3]
    else:
        header_bottom = -1
    draw.line((0, first_rule, base.width, first_rule), fill=(0, 200, 80, 220), width=3)
    draw.text((30, max(10, first_rule - 34)), "first physical rule", font=label_font(22), fill=(0, 140, 60, 255))
    debug.save(out / "book1_debug_overlay.png", "PNG", optimize=True)
    with (out / "book1_calibration.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    before_path = ROOT / "outputs" / "book1_before.png"
    if before_path.exists():
        before = Image.open(before_path).convert("RGB")
        comparison = Image.new("RGB", (before.width * 2, before.height), "white")
        comparison.paste(before, (0, 0))
        comparison.paste(final, (before.width, 0))
        comparison.save(out / "book1_before_after.png", "PNG", optimize=True)

    # Close-ups support visual review of the first, middle, and last rules.
    baselines = list(layout.baseline_positions or ())
    for name, start, end in (("top", 0, 9), ("middle", 10, 19), ("bottom", 20, len(baselines))):
        if start < len(baselines):
            top = max(0, baselines[start] - 150)
            bottom = min(final.height, baselines[min(end, len(baselines)) - 1] + 150)
            final.crop((0, top, final.width, bottom)).save(out / f"book1_{name}.png", "PNG", optimize=True)

    failed = [row for row in rows if row["status"] == "FAIL"]
    report = out / "book1_validation_report.md"
    report.write_text(
        "# Buku 1 validation\n\n"
        f"- physical lines measured: **{len(rows)}**\n"
        f"- detected left divider: **x={divider_x}px**\n"
        f"- target ink clearance: **8 px minimum**\n"
        f"- observed ink clearance: **{min(row['left_clearance_px'] for row in rows if row['status'] == 'PASS'):.1f} px minimum**\n"
        f"- header bbox: **{header_box}**; first rule y={first_rule}; header/body separation={first_rule - header_bottom}px\n"
        f"- failed rows: **{len(failed)}** (unused rows: {sum(row['status'] == 'SKIP' for row in rows)})\n\n"
        "The body baseline positions and line spacing are sourced from the existing Buku 1 physical rule grid.\n"
        "The debug overlay uses actual text-only alpha pixels, not font metrics.\n",
        encoding="utf-8",
    )
    print(f"lines={len(rows)} divider_x={divider_x} header_bbox={header_box} first_rule={first_rule} failed={len(failed)}")
    for row in failed:
        print("FAIL", row)
    if failed or not header_box or header_bottom >= first_rule:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
