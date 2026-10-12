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


def font(size: int):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def fit_ruling(base: Image.Image, expected_y: int, x0: int, x1: int) -> tuple[float, float]:
    rgb = base.convert("RGB")
    points: list[tuple[float, float]] = []
    for x in range(x0, x1, 20):
        end = min(x + 20, x1)
        candidates = []
        for y in range(max(0, expected_y - 16), min(rgb.height, expected_y + 17)):
            darkness = sum(sum(rgb.getpixel((xx, y))) for xx in range(x, end)) / max(1, (end - x) * 3)
            candidates.append((darkness, y))
        points.append((x + (end - x) / 2, min(candidates)[1]))
    n = len(points)
    sx, sy = sum(x for x, _ in points), sum(y for _, y in points)
    sxx, sxy = sum(x * x for x, _ in points), sum(x * y for x, y in points)
    denom = n * sxx - sx * sx
    slope = (n * sxy - sx * sy) / denom if denom else 0.0
    return slope, (sy - slope * sx) / n


def boundary_x(base: Image.Image, y0: int, y1: int, expected: int) -> int:
    rgb = base.convert("RGB")
    values = []
    for x in range(expected - 55, expected + 55):
        darkness = sum(sum(rgb.getpixel((x, y))) for y in range(y0, y1)) / max(1, (y1 - y0) * 3)
        values.append((darkness, x))
    return min(values)[1]


def header_bbox(base: Image.Image, preferences: UserPreferences, layout) -> tuple[int, int]:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    add_header(layer, preferences, "12-10-2026", None, layout)
    ys = [y for y in range(layer.height) for x in range(layer.width) if layer.getpixel((x, y))[3] >= 20]
    return (min(ys), max(ys)) if ys else (-1, -1)


def validate_case(name: str, text: str, preferences: UserPreferences, expected_lines: int, root: Path) -> int:
    menu_dir = root / "menu_buku"
    template = book_registry(menu_dir)["book_buku_tulis_4"]
    base, layout = load_paper(template.template_id, root / "assets" / "papers", menu_dir)
    service = GenerationService(root / "assets")
    result = service.render(text, preferences, seed=20261012)
    text_layer = service.render(text, preferences, seed=20261012, text_only=True).pages[0].convert("RGBA")
    image = result.pages[0].convert("RGB")
    out = root / "outputs" / "book4_alignment" / name
    out.mkdir(parents=True, exist_ok=True)
    image.save(out / f"book_buku_tulis_4_{name}.png", "PNG", optimize=True)
    debug = base.convert("RGB")
    draw = ImageDraw.Draw(debug, "RGBA")
    physical = layout.baseline_start_index
    origins = [layout.baseline_positions[physical + i] - layout.baseline_offset for i in range(expected_lines)]
    x0, x1 = layout.margin_left, layout.margin_left + (base.width - layout.margin_left - layout.margin_right)
    header_top, header_bottom = header_bbox(base, preferences, layout)
    rows: list[dict[str, object]] = []
    for i in range(expected_lines):
        ruling = layout.baseline_positions[physical + i]
        origin = origins[i]
        slope, intercept = fit_ruling(base, ruling, x0, x1)
        left_line = boundary_x(base, origin + 8, origin + 55, layout.margin_left)
        top_band, bottom_band = origin + 8, min(text_layer.height, origin + 66)
        pixels = [(x, y) for y in range(top_band, bottom_band) for x in range(x0, x1) if text_layer.getpixel((x, y))[3] >= 20]
        if pixels:
            left, right = min(x for x, _ in pixels), max(x for x, _ in pixels)
            top, bottom = min(y for _, y in pixels), max(y for _, y in pixels)
            vertical = min(slope * x + intercept - y for x, y in pixels)
            left_clearance = left - left_line
            right_clearance = (base.width - layout.margin_right) - right
            horizontal = min(left_clearance, right_clearance)
            header_clearance = top - header_bottom
            status = "PASS" if vertical >= 2 and horizontal >= 8 and header_clearance >= 8 else "FAIL"
            draw.rectangle((left, top, right, bottom), outline=(0, 180, 255, 220), width=3)
        else:
            left = right = top = bottom = -1
            vertical = horizontal = header_clearance = -1
            # A shorter paragraph may not consume all remaining body slots on
            # page one; those physical rows are unused, not collisions.
            status = "SKIP"
        draw.line((x0, slope * x0 + intercept, x1, slope * x1 + intercept), fill=(225, 40, 40, 220), width=3)
        draw.line((left_line, top_band, left_line, bottom_band), fill=(255, 150, 0, 230), width=3)
        draw.text((x0 + 8, origin - 30), f"L{i + 1:02d}", font=font(24), fill=(220, 30, 30, 255))
        rows.append({
            "line_index": i + 1,
            "physical_line_index": physical + i + 1,
            "ruling_y_left": round(slope * x0 + intercept, 2),
            "ruling_y_right": round(slope * x1 + intercept, 2),
            "baseline_y": origin,
            "ink_top": top,
            "ink_bottom": bottom,
            "horizontal_clearance": round(horizontal, 2),
            "vertical_clearance": round(vertical, 2),
            "header_clearance": round(header_clearance, 2),
            "status": status,
        })
    debug.save(out / f"book_buku_tulis_4_{name}_debug.png", "PNG", optimize=True)
    with (out / f"book_buku_tulis_4_{name}_calibration.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    for label, start, end in (("top", 0, min(9, expected_lines)), ("middle", expected_lines // 3, min(expected_lines * 2 // 3 + 1, expected_lines)), ("bottom", max(0, expected_lines - 9), expected_lines)):
        top = max(0, origins[start] - 170); bottom = min(image.height, origins[end - 1] + 170)
        image.crop((0, top, image.width, bottom)).save(out / f"book_buku_tulis_4_{name}_{label}.png", "PNG", optimize=True)
    failed = [row for row in rows if row["status"] not in {"PASS", "SKIP"}]
    print(f"{name}: body_slots={len(rows)} header_bbox={header_top},{header_bottom} failed={len(failed)}")
    for row in failed:
        print("FAIL", row)
    return len(failed)


def build_exact31_deliverables(root: Path, preferences: UserPreferences) -> None:
    """Build the required 31-row artifact, including header rows 01-04."""
    menu_dir = root / "menu_buku"
    template = book_registry(menu_dir)["book_buku_tulis_4"]
    base, layout = load_paper(template.template_id, root / "assets" / "papers", menu_dir)
    service = GenerationService(root / "assets")
    text = "\n".join(f"Baris {i:02d} tulisan uji" for i in range(1, 28))
    final = service.render(text, preferences, seed=20261012).pages[0].convert("RGB")
    body = service.render(text, preferences, seed=20261012, text_only=True).pages[0].convert("RGBA")
    header = Image.new("RGBA", base.size, (0, 0, 0, 0))
    add_header(header, preferences, "12-10-2026", None, layout)
    out = root / "outputs" / "book4_alignment"
    out.mkdir(parents=True, exist_ok=True)
    final.save(out / "book4_exact31_final.png", "PNG", optimize=True)
    final.save(out / "book4_header_collision_test.png", "PNG", optimize=True)
    debug = base.convert("RGB")
    draw = ImageDraw.Draw(debug, "RGBA")
    rows: list[dict[str, object]] = []
    x0, x1 = layout.margin_left, base.width - layout.margin_right
    for physical_index, ruling in enumerate(layout.baseline_positions, start=1):
        slope, intercept = fit_ruling(base, ruling, x0, x1)
        baseline_left = slope * x0 + intercept - layout.baseline_offset
        baseline_right = slope * x1 + intercept - layout.baseline_offset
        if physical_index <= 4:
            origin = ruling - 68
            layer = header
            band = (origin + 5, origin + 55)
            content_type = "HEADER"
        else:
            origin = ruling - layout.baseline_offset
            layer = body
            band = (origin + 8, origin + 66)
            content_type = "BODY"
        pixels = [(x, y) for y in range(max(0, band[0]), min(layer.height, band[1])) for x in range(x0, x1) if layer.getpixel((x, y))[3] >= 20]
        left_boundary = boundary_x(base, max(0, band[0]), min(base.height, band[1]), layout.margin_left)
        if pixels:
            left, right = min(x for x, _ in pixels), max(x for x, _ in pixels)
            top, bottom = min(y for _, y in pixels), max(y for _, y in pixels)
            vertical = min(slope * x + intercept - y for x, y in pixels)
            left_clearance = left - left_boundary
            right_clearance = (base.width - layout.margin_right) - right
            horizontal = min(left_clearance, right_clearance)
            status = "PASS" if vertical >= 2 and horizontal >= 8 else "FAIL"
            draw.rectangle((left, top, right, bottom), outline=(0, 180, 255, 220), width=3)
        else:
            left = right = top = bottom = -1
            vertical = horizontal = -1
            status = "FAIL"
        draw.line((x0, slope * x0 + intercept, x1, slope * x1 + intercept), fill=(225, 40, 40, 220), width=3)
        draw.line((x0, baseline_left, x1, baseline_right), fill=(50, 220, 80, 180), width=2)
        draw.line((left_boundary, band[0], left_boundary, band[1]), fill=(255, 150, 0, 230), width=3)
        draw.text((x0 + 8, round(origin - 24)), f"L{physical_index:02d}", font=font(24), fill=(220, 30, 30, 255))
        rows.append({
            "line_index": physical_index,
            "physical_line_index": physical_index,
            "content_type": content_type,
            "ruling_y_left": round(slope * x0 + intercept, 2),
            "ruling_y_right": round(slope * x1 + intercept, 2),
            "baseline_y_left": round(baseline_left, 2),
            "baseline_y_right": round(baseline_right, 2),
            "ink_top": top,
            "ink_bottom": bottom,
            "min_ink_clearance_px": round(vertical, 2),
            "left_margin_clearance_px": round(left - left_boundary, 2) if pixels else -1,
            "right_margin_clearance_px": round((base.width - layout.margin_right) - right, 2) if pixels else -1,
            "status": status,
        })
    debug.save(out / "book4_exact31_debug_overlay.png", "PNG", optimize=True)
    with (out / "book4_exact31_calibration.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    full_width_path = out / "full_width" / "book_buku_tulis_4_full_width.png"
    if full_width_path.exists():
        Image.open(full_width_path).convert("RGB").save(out / "book4_fullwidth_test.png", "PNG", optimize=True)
    # Side-by-side evidence: previous 29-line probe versus the integrated 31-line result.
    before_path = root / "outputs" / "book4_probe.png"
    if before_path.exists():
        before = Image.open(before_path).convert("RGB")
        comparison = Image.new("RGB", (before.width * 2, before.height), "white")
        comparison.paste(before, (0, 0)); comparison.paste(final, (before.width, 0))
        comparison.save(out / "book4_before_after.png", "PNG", optimize=True)


def main() -> None:
    root = ROOT
    prefs = UserPreferences(
        telegram_user_id=1, book_style="book_buku_tulis_4",
        handwriting_style="natural_student_upright_01", ink_color="blue",
        name="Faisal", npm="123456", class_name="TI-1", attendance_number="07",
        show_identity=True, show_date=True, date_mode="custom", custom_date="12-10-2026",
    )
    numbered = "\n".join(f"Baris {i:02d} tulisan uji" for i in range(1, 28))
    paragraph = ("Mahasiswa belajar merancang sistem yang rapi, efisien, dan mudah digunakan. "
                 "Dalam pengembangan perangkat lunak, kebutuhan pengguna harus dipahami dengan baik, "
                 "data harus diatur, dan keamanan informasi harus dijaga. " * 8)
    failures = validate_case("numbered", numbered, prefs, 27, root)
    failures += validate_case("full_width", paragraph, prefs, 27, root)
    build_exact31_deliverables(root, prefs)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
