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

def blue_bbox(image: Image.Image, box: tuple[int, int, int, int]):
    x0, y0, x1, y1 = box
    points = []
    for y in range(max(0, y0), min(image.height, y1)):
        for x in range(max(0, x0), min(image.width, x1)):
            r, g, b = image.getpixel((x, y))[:3]
            if b > r + 18 and b > g + 8 and b > 70:
                points.append((x, y))
    if not points:
        return None
    return min(x for x, _ in points), min(y for _, y in points), max(x for x, _ in points), max(y for _, y in points)


def main() -> None:
    menu = ROOT / "menu_buku"
    template = book_registry(menu)["book_buku_tulis_4"]
    base, layout = load_paper(template.template_id, ROOT / "assets" / "papers", menu)
    prefs = UserPreferences(
        telegram_user_id=1, book_style=template.template_id,
        handwriting_style="natural_student_upright_01", ink_color="blue",
        name="Faisal", npm="123456", class_name="SI-4A", attendance_number="07",
        show_identity=True, show_date=True, date_mode="custom", custom_date="13-10-2026",
    )
    final = GenerationService(ROOT / "assets").render(
        "Uji alignment Buku 4 dengan header perspektif.", prefs, seed=20261013
    ).pages[0].convert("RGB")
    out = ROOT / "outputs" / "book4_header_alignment"
    out.mkdir(parents=True, exist_ok=True)
    final.save(out / "book4_header_final.png", "PNG", optimize=True)

    left = layout.margin_left
    right = base.width - layout.margin_right
    mid = left + max(420, round((right - left) * 0.40))
    slopes = layout.baseline_slopes or ()

    def ruling(row: int, x: int) -> float:
        slope = slopes[row] if row < len(slopes) else 0.0
        return layout.baseline_positions[row] + slope * (x - left)

    def row_box(row: int, x0: int, x1: int) -> tuple[int, int, int, int]:
        anchor = (x0 + x1) / 2
        top = ruling(row, anchor)
        bottom = ruling(row + 1, anchor)
        return (x0, round(top - 5), x1, round(bottom + 5))

    fields = [
        ("Nama", left, 0, row_box(0, left - 20, mid - 10)),
        ("NPM", mid, 0, row_box(0, mid - 20, mid + 560)),
        ("Tanggal", right - 300, 0, row_box(0, right - 360, right + 10)),
        ("Kelas", left, 1, row_box(1, left - 20, mid - 10)),
        ("Absen", mid, 1, row_box(1, mid - 20, mid + 560)),
    ]
    overlay = base.convert("RGB")
    overlay.paste(final, mask=None)
    draw = ImageDraw.Draw(overlay, "RGBA")
    rows = []
    for name, x, row, box in fields:
        bbox = blue_bbox(final, box)
        if bbox:
            ink_bottom = bbox[3]
            ink_top = bbox[1]
            top_clearance = ink_top - ruling(row, x)
            clearance = ruling(row + 1, x) - ink_bottom
            status = "PASS" if top_clearance >= 8 and clearance >= 8 else "FAIL"
            draw.rectangle(bbox, outline=(0, 200, 255, 240), width=4)
        else:
            ink_top = -1
            top_clearance = -1
            ink_bottom = -1
            clearance = -1
            status = "FAIL"
        draw.line((left, ruling(row, left), right, ruling(row, right)), fill=(225, 40, 40, 230), width=3)
        draw.ellipse((x - 7, ruling(row, x) - 7, x + 7, ruling(row, x) + 7), fill=(255, 150, 0, 240))
        rows.append({
            "field": name, "header_row": row + 1, "field_x": x,
            "ruling_y_top": round(ruling(row, x), 2),
            "ruling_y_bottom": round(ruling(row + 1, x), 2),
            "ink_top": ink_top, "ink_bottom": ink_bottom,
            "top_clearance_px": round(top_clearance, 2),
            "bottom_clearance_px": round(clearance, 2), "status": status,
        })
    overlay.save(out / "book4_header_debug_overlay.png", "PNG", optimize=True)
    with (out / "book4_header_clearance.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    before = ROOT / "outputs" / "header_standardization" / "book_buku_tulis_4_natural_student_upright_01.png"
    if before.exists():
        previous = Image.open(before).convert("RGB")
        comparison = Image.new("RGB", (previous.width * 2, previous.height), "white")
        comparison.paste(previous, (0, 0)); comparison.paste(final, (previous.width, 0))
        comparison.save(out / "book4_header_before_after.png", "PNG", optimize=True)
    failed = [row for row in rows if row["status"] != "PASS"]
    print(f"fields={len(rows)} passed={len(rows)-len(failed)} failed={len(failed)}")
    for row in failed:
        print("FAIL", row)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
