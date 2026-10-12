"""Isolated visual calibration for Buku 3 body handwriting scale.

This script deliberately does not modify the production layout. Each variant
uses the same template geometry, ruling slopes, margins, seed, and identity
header; only the body glyph size and its matching measurement are changed.
"""
from __future__ import annotations

import csv
import sys
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.books import book_registry
from config.settings import HANDWRITING_STYLES, INK_COLORS
from database.models import UserPreferences
from renderer.layout import paginate_text
from renderer.multiglyph import MultiGlyphHandwritingRenderer
from renderer.paper import add_header, load_paper


SEED = 20261013
SCALES = (1.00, 0.95, 0.90, 0.88)
TEXT = (
    "Latar Belakang\n\n"
    "Penelitian merupakan salah satu aspek penting dalam Tridharma Perguruan Tinggi. "
    "Mahasiswa perlu menyusun gagasan secara rapi, efisien, dan mudah dipahami.\n"
    "Dalam pengembangan perangkat lunak, kebutuhan pengguna, alur data, serta keamanan "
    "informasi harus diperhatikan dengan teliti.\n\n"
    "    1. github   vscode\n"
    "    2. laravel\n"
    "    3. dokumentasi-dan-pengujian-yang-berkelanjutan\n\n"
    "Konsistensi membantu pembaca mengikuti penjelasan dari awal sampai akhir. "
    "Catatan yang lengkap membuat setiap langkah dapat diperiksa kembali, termasuk "
    "kata-dengan-tanda-baca, angka 123456, dan kalimat yang mendekati batas kanan."
)


def prefs() -> UserPreferences:
    return UserPreferences(
        1, book_style="book_buku_tulis_3", handwriting_style="natural_student_upright_01",
        ink_color="blue", show_identity=True, name="Faisal", npm="123456",
        class_name="TI-A", attendance_number="07", show_date=True,
        date_mode="custom", custom_date="13-10-2026",
    )


def fit_ruling(base: Image.Image, expected: int, x0: int, x1: int) -> tuple[float, float]:
    rgb = base.convert("RGB")
    points: list[tuple[float, float]] = []
    for x in range(x0, x1, 20):
        end = min(x + 20, x1)
        candidates = []
        for y in range(max(0, expected - 12), min(rgb.height, expected + 13)):
            darkness = sum(sum(rgb.getpixel((xx, y))) for xx in range(x, end))
            candidates.append((darkness, y))
        points.append((x + (end - x) / 2, min(candidates)[1]))
    n = len(points); sx = sum(x for x, _ in points); sy = sum(y for _, y in points)
    sxx = sum(x * x for x, _ in points); sxy = sum(x * y for x, y in points)
    den = n * sxx - sx * sx
    slope = (n * sxy - sx * sy) / den if den else 0.0
    return slope, (sy - slope * sx) / n


def ink_bbox(layer: Image.Image, box: tuple[int, int, int, int]):
    x0, y0, x1, y1 = box
    points = [(x, y) for y in range(max(0, y0), min(layer.height, y1))
              for x in range(max(0, x0), min(layer.width, x1))
              if layer.getpixel((x, y))[3] >= 24]
    if not points:
        return None
    return min(x for x, _ in points), min(y for _, y in points), max(x for x, _ in points), max(y for _, y in points)


def make_writer(root: Path, layout, relative: float, seed: int):
    style = HANDWRITING_STYLES["natural_student_upright_01"]
    return MultiGlyphHandwritingRenderer(
        root / "assets" / "handwriting" / style["asset_style"],
        round(54 * layout.handwriting_scale * relative),
        INK_COLORS["blue"], seed, style["variation_level"], style["slant_factor"],
        style["rotation_jitter"], style["advance_factor"],
    )


def render_variant(base, layout, relative: float, output: Path):
    p = prefs()
    pages = paginate_text(TEXT, base.width, base.height, layout, make_writer(ROOT, layout, relative, SEED).measure)
    body_writer = make_writer(ROOT, layout, relative, SEED)
    header_writer = make_writer(ROOT, layout, 1.0, SEED + 991)
    page = base.copy()
    text_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    line_boxes = []
    for line in pages[0]:
        line_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        body_writer.render_line(line_layer, line.text, line.x, line.y, baseline_slope=line.baseline_slope)
        page.alpha_composite(line_layer)
        text_layer.alpha_composite(line_layer)
        line_boxes.append(line_layer.getchannel("A").getbbox())
    add_header(page, p, p.custom_date, None, layout, header_writer)
    final_path = output / f"book3_scale_{round(relative * 100):02d}.png"
    page.convert("RGB").save(final_path, optimize=True)

    x0, x1 = 570, base.width - layout.margin_right
    rows = []
    overlay = page.convert("RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")
    previous = None
    occupied = [line for line in pages[0] if line.text.strip()]
    for index, expected in enumerate(layout.baseline_positions or (), 1):
        slope, intercept = fit_ruling(base, expected, x0, x1)
        origin = expected - (layout.baseline_offsets[index - 1] if layout.baseline_offsets else layout.baseline_offset)
        box = line_boxes[index - 1] if index <= len(line_boxes) else None
        if box:
            left, top, right, bottom = box
            pixels = [(x, y) for y in range(top, bottom + 1) for x in range(left, right + 1)
                      if text_layer.getpixel((x, y))[3] >= 24]
            lower = min(slope * x + intercept - y for x, y in pixels)
            upper = min((y - (previous[0] * x + previous[1]) for x, y in pixels), default=999.0) if previous else 999.0
            collision = sum(1 for x, y in pixels if slope * x + intercept - y < 2.0 or (previous and y - (previous[0] * x + previous[1]) < 2.0))
            height = bottom - top + 1
            horizontal_overflow = int(left < x0 or right > x1)
            clipped = int(left <= 0 or top <= 0 or right >= text_layer.width - 1 or bottom >= text_layer.height - 1)
            status = "PASS" if lower >= 2 and upper >= 2 and collision == 0 and not horizontal_overflow and not clipped else "FAIL"
            draw.rectangle(box, outline=(0, 120, 255, 220), width=3)
        else:
            left = top = right = bottom = -1; lower = upper = -1.0; collision = -1; height = 0; horizontal_overflow = 0; clipped = 0; status = "EMPTY"
        draw.line((x0, slope * x0 + intercept, x1, slope * x1 + intercept), fill=(225, 40, 40, 220), width=3)
        draw.line((x0, origin, x1, origin), fill=(35, 220, 80, 210), width=2)
        draw.line((x0, slope * x0 + intercept - 8, x1, slope * x1 + intercept - 8), fill=(245, 205, 40, 170), width=2)
        rows.append({"line_index": index, "ruling_y_left": round(slope * x0 + intercept, 2), "ruling_y_right": round(slope * x1 + intercept, 2), "baseline_y": origin, "ink_top": top, "ink_bottom": bottom, "ink_height": height, "minimum_clearance": round(min(lower, upper), 2), "collision_pixels": collision, "horizontal_overflow": horizontal_overflow, "clipped_glyph": clipped, "status": status})
        previous = (slope, intercept)
    overlay.save(output / f"book3_scale_{round(relative * 100):02d}_debug.png", optimize=True)
    return page.convert("RGB"), rows, len(pages), sum(len(line.text) for line in occupied) / max(1, len(occupied)), len(occupied)


def main() -> None:
    output = ROOT / "outputs" / "book3_scale_calibration"
    output.mkdir(parents=True, exist_ok=True)
    base, layout = load_paper("book_buku_tulis_3", ROOT / "assets" / "papers", ROOT / "menu_buku")
    # Keep the experiment anchored to the original 100% production baseline
    # even after Variant D becomes the live configuration.
    layout = replace(layout, handwriting_scale=layout.handwriting_scale / 0.88)
    results = []
    variants = []
    for relative in SCALES:
        image, rows, page_count, avg_chars, occupied = render_variant(base, layout, relative, output)
        variants.append(image.resize((620, 877), Image.Resampling.LANCZOS))
        valid = [r for r in rows if r["status"] != "EMPTY"]
        results.append({"scale": f"{relative:.2f}", "font_size": round(54 * layout.handwriting_scale * relative), "average_characters_per_line": round(avg_chars, 2), "occupied_lines": occupied, "pages": page_count, "max_glyph_height": max((r["ink_height"] for r in valid), default=0), "minimum_vertical_clearance": min((r["minimum_clearance"] for r in valid), default=-1), "glyph_ruling_collisions": sum(max(0, r["collision_pixels"]) for r in valid), "horizontal_overflows": sum(r["horizontal_overflow"] for r in valid), "clipped_glyphs": sum(r["clipped_glyph"] for r in valid)})
    comparison = Image.new("RGB", (1240, 1794), "white")
    draw = ImageDraw.Draw(comparison)
    for i, image in enumerate(variants):
        x, y = (i % 2) * 620, (i // 2) * 897
        comparison.paste(image, (x, y + 20)); draw.text((x + 12, y + 2), f"Variant {chr(65+i)} — {int(SCALES[i]*100)}%", fill=(20, 20, 20))
    comparison.save(output / "book3_comparison.png", optimize=True)
    report = ["# Buku 3 handwriting scale calibration", "", "Eksperimen terisolasi; konfigurasi produksi tidak diubah.", "", f"Template: `book_buku_tulis_3` (`buku_tulis_3.jpg`)", f"Style: `natural_student_upright_01`", f"Production body font size: `{round(54 * layout.handwriting_scale)}` px", f"Ruling lines: `{len(layout.baseline_positions or ())}`", f"Line spacing: `{layout.line_spacing}` px", f"Baseline offset: `{layout.baseline_offset}` px", f"Horizontal margins: left `{layout.margin_left}`, right `{layout.margin_right}`", "", "## Results", "", "| scale | font px | avg chars/line | occupied lines | max glyph h | min clearance | collisions | overflow | clipped |", "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in results:
        report.append(f"| {r['scale']} | {r['font_size']} | {r['average_characters_per_line']} | {r['occupied_lines']} | {r['max_glyph_height']} | {r['minimum_vertical_clearance']} | {r['glyph_ruling_collisions']} | {r['horizontal_overflows']} | {r['clipped_glyphs']} |")
    report += ["", "## Visual observations", "", "- **100%:** largest glyphs; most crowded vertically and least spare horizontal capacity.", "- **95%:** slightly more compact, but the visual difference from production is subtle.", "- **90%:** clearer spare capacity and shorter glyphs while remaining readable.", "- **88%:** most compact and highest line capacity; compare against 90% for preferred handwriting presence.", "", "The strict clearance audit is reported above; this experiment does not silently change baseline offsets or declare a collision variant production-ready.", "", "Debug overlays: `book3_scale_100_debug.png`, `book3_scale_95_debug.png`, `book3_scale_90_debug.png`, `book3_scale_88_debug.png`."]
    (output / "book3_calibration_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"output={output} variants={len(results)} pages={[r['pages'] for r in results]}")


if __name__ == "__main__":
    main()
