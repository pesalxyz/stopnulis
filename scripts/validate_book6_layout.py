from __future__ import annotations

import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.models import UserPreferences
from renderer.paper import add_header, load_paper
from services.generation_service import GenerationService


def fit_ruling(base: Image.Image, expected: int, x0: int, x1: int) -> tuple[float, float]:
    rgb = base.convert("RGB")
    points = []
    for x in range(x0, x1, 20):
        end = min(x + 20, x1)
        candidates = []
        for y in range(max(0, expected - 18), min(rgb.height, expected + 19)):
            score = sum(sum(rgb.getpixel((xx, y))) for xx in range(x, end))
            candidates.append((score, y))
        points.append((x + (end - x) / 2, min(candidates)[1]))
    n = len(points)
    sx = sum(x for x, _ in points); sy = sum(y for _, y in points)
    sxx = sum(x * x for x, _ in points); sxy = sum(x * y for x, y in points)
    den = n * sxx - sx * sx
    slope = (n * sxy - sx * sy) / den if den else 0.0
    return slope, (sy - slope * sx) / n


def ink_bbox(layer: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int, int] | None:
    x0, y0, x1, y1 = box
    pts = [(x, y) for y in range(max(0, y0), min(layer.height, y1))
           for x in range(max(0, x0), min(layer.width, x1))
           if layer.getpixel((x, y))[3] >= 24]
    if not pts:
        return None
    return min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)


def boundary_x(base: Image.Image, y0: int, y1: int, expected: int) -> int:
    rgb = base.convert("RGB")
    values = []
    for x in range(expected - 70, expected + 40):
        score = sum(sum(rgb.getpixel((x, y))) for y in range(max(0, y0), min(base.height, y1)))
        values.append((score, x))
    return min(values)[1]


def prefs() -> UserPreferences:
    return UserPreferences(1, book_style="book_buku_tulis_6",
        handwriting_style="natural_student_upright_01", ink_color="blue",
        show_identity=True, name="Faisal", npm="123456", class_name="TI-A",
        attendance_number="07", show_date=True, date_mode="custom", custom_date="12-10-2026")


def main() -> int:
    out = ROOT / "outputs" / "book6_alignment"
    out.mkdir(parents=True, exist_ok=True)
    p = prefs(); service = GenerationService(ROOT / "assets")
    base, layout = load_paper(p.book_style, ROOT / "assets" / "papers", ROOT / "menu_buku")
    n = len(layout.baseline_positions or ())
    numbered = "\n".join(f"Baris {i:02d} tulisan uji" for i in range(1, n + 1))
    final = service.render(numbered, p, seed=20261012).pages[0].convert("RGB")
    text_layer = service.render(numbered, p, seed=20261012, text_only=True).pages[0].convert("RGBA")
    final.save(out / "book6_final.png", optimize=True)

    x0, x1 = layout.margin_left, base.width - layout.margin_right
    rows = []
    debug = base.convert("RGBA")
    debug.alpha_composite(text_layer)
    draw = ImageDraw.Draw(debug, "RGBA")
    for i, ruling in enumerate(layout.baseline_positions or (), 1):
        slope, intercept = fit_ruling(base, ruling, x0, x1)
        origin = ruling - layout.baseline_offset
        bbox = ink_bbox(text_layer, (x0 - 10, origin - 8, x1 + 10, origin + 70))
        if bbox:
            left, top, right, bottom = bbox
            # compare every glyph pixel to the local fitted rule at its x
            clearance = min(slope * x + intercept - y for y in range(top, bottom + 1)
                            for x in range(left, right + 1)
                            if text_layer.getpixel((x, y))[3] >= 24)
            local_boundary = boundary_x(base, origin + 8, origin + 68, x0 - 20)
            left_clearance = left - local_boundary
            right_clearance = x1 - right
            status = "PASS" if clearance >= 2 and left_clearance >= 8 and right_clearance >= 8 else "FAIL"
            draw.rectangle(bbox, outline=(0, 180, 255, 220), width=3)
        else:
            left = top = right = bottom = -1; clearance = left_clearance = right_clearance = -1; status = "FAIL"
        y_left, y_right = slope * x0 + intercept, slope * x1 + intercept
        draw.line((x0, y_left, x1, y_right), fill=(225, 40, 40, 230), width=3)
        draw.text((x0 + 8, origin - 35), f"L{i:02d}", fill=(220, 30, 30, 255))
        local_boundary = boundary_x(base, origin + 8, origin + 68, x0 - 20)
        rows.append({"line_index": i, "physical_line_index": i,
                     "ruling_y_left": round(y_left, 2), "ruling_y_right": round(y_right, 2),
                     "baseline_y_left": round(y_left - layout.baseline_offset, 2),
                     "baseline_y_right": round(y_right - layout.baseline_offset, 2),
                     "ink_left": left, "ink_top": top, "ink_right": right, "ink_bottom": bottom,
                     "vertical_clearance_px": round(clearance, 2),
                     "left_boundary_x": local_boundary, "left_clearance_px": left_clearance, "right_clearance_px": right_clearance,
                     "status": status})
    debug.save(out / "book6_debug_overlay.png", optimize=True)
    with (out / "book6_calibration.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    header = Image.new("RGBA", base.size, (0, 0, 0, 0)); add_header(header, p, "12-10-2026", None, layout)
    hb = ink_bbox(header, (0, 0, base.width, layout.baseline_positions[0]))
    header_check = base.convert("RGB"); hd = ImageDraw.Draw(header_check, "RGBA")
    if hb: hd.rectangle(hb, outline=(255, 120, 0, 240), width=4)
    first = layout.baseline_positions[0]
    hd.line((x0, first, x1, first), fill=(225, 40, 40, 230), width=4)
    header_check.save(out / "book6_header_validation.png", optimize=True)
    header_bottom = hb[3] if hb else -1

    paragraph = ("Mahasiswa belajar merancang sistem yang rapi, efisien, dan mudah digunakan. "
                 "Dalam pengembangan perangkat lunak, kita perlu memperhatikan kebutuhan pengguna, "
                 "alur data, serta keamanan informasi. Konsistensi menjadi bagian penting dalam setiap tugas.\n") * 5
    full = service.render(paragraph, p, seed=20261012).pages[0].convert("RGB")
    full.save(out / "book6_fullwidth_test.png", optimize=True)
    # Close-up bands for human visual inspection.
    for name, a, b in (("top", 0, 10), ("middle", 10, 20), ("bottom", 20, 30)):
        final.crop((0, max(0, (layout.baseline_positions[a] - 170)), final.width,
                    min(final.height, layout.baseline_positions[b - 1] + 170))).save(out / f"book6_{name}_closeup.png", optimize=True)
    before = base.convert("RGB").resize((1240, 1754)); after = final.resize((1240, 1754))
    comparison = Image.new("RGB", (2480, 1754), "white"); comparison.paste(before, (0, 0)); comparison.paste(after, (1240, 0)); comparison.save(out / "book6_before_after.png", optimize=True)
    failed = [r for r in rows if r["status"] != "PASS"]
    print(f"physical_lines={n} header_bbox={hb} header_bottom={header_bottom} first_ruling={first} failed={len(failed)}")
    if failed:
        for row in failed: print("FAIL", row)
    return 1 if n != 30 or failed or (hb and header_bottom >= first - 8) else 0


if __name__ == "__main__":
    raise SystemExit(main())
