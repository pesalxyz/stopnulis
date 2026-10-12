"""Isolated body-scale calibration for the Folio 1 template."""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import HANDWRITING_STYLES, INK_COLORS
from database.models import UserPreferences
from renderer.layout import paginate_text
from renderer.multiglyph import MultiGlyphHandwritingRenderer
from renderer.paper import add_header, load_paper


SEED = 20261013
SCALES = (1.00, 0.95, 0.90, 0.88)
TEXT = (
    "Catatan Penelitian\n\n"
    "Mahasiswa belajar merancang sistem yang rapi, efisien, dan mudah digunakan. "
    "Dalam pengembangan perangkat lunak, kebutuhan pengguna, alur data, serta "
    "keamanan informasi perlu diperhatikan dengan teliti.\n"
    "Konsistensi membantu pembaca mengikuti penjelasan dari awal sampai akhir; "
    "angka 123456 dan tanda baca tetap menjadi bagian dari catatan.\n\n"
    "    1. github   vscode\n"
    "    2. laravel\n"
    "    3. dokumentasi-dan-pengujian-yang-berkelanjutan\n\n"
    "Setiap proses perlu diuji secara bertahap. Catatan yang lengkap membantu "
    "menemukan kesalahan, memperbaiki langkah kerja, dan menjaga hasil tetap "
    "dapat diandalkan. Kerja sama dan ketelitian membuat laporan menjadi lebih baik.\n"
    "Kalimat panjang ini sengaja mendekati batas kanan untuk memeriksa wrapping "
    "dan memastikan tidak ada tulisan keluar dari area Folio.\n\n"
    "Kesimpulan penelitian harus ditulis secara jelas agar dapat dibaca kembali "
    "pada halaman berikutnya tanpa kehilangan struktur paragraf. "
) * 2


def prefs() -> UserPreferences:
    return UserPreferences(
        1, book_style="book_kertas_folio_1", handwriting_style="natural_student_upright_01",
        ink_color="blue", show_identity=True, name="Faisal", npm="123456",
        class_name="TI-A", attendance_number="07", show_date=True,
        date_mode="custom", custom_date="13-10-2026",
    )


def fit_ruling(base: Image.Image, expected: int, x0: int, x1: int) -> tuple[float, float]:
    rgb = base.convert("RGB")
    points = []
    for x in range(x0, x1, 24):
        end = min(x + 24, x1)
        candidates = []
        for y in range(max(0, expected - 18), min(rgb.height, expected + 19)):
            darkness = sum(sum(rgb.getpixel((xx, y))) for xx in range(x, end))
            candidates.append((darkness, y))
        points.append((x + (end - x) / 2, min(candidates)[1]))
    n = len(points); sx = sum(x for x, _ in points); sy = sum(y for _, y in points)
    sxx = sum(x * x for x, _ in points); sxy = sum(x * y for x, y in points)
    den = n * sxx - sx * sx
    slope = (n * sxy - sx * sy) / den if den else 0.0
    return slope, (sy - slope * sx) / n


def make_writer(layout, relative: float, seed: int):
    style = HANDWRITING_STYLES["natural_student_upright_01"]
    return MultiGlyphHandwritingRenderer(
        ROOT / "assets" / "handwriting" / style["asset_style"],
        round(54 * layout.handwriting_scale * relative),
        INK_COLORS["blue"], seed, style["variation_level"], style["slant_factor"],
        style["rotation_jitter"], style["advance_factor"],
    )


def render_variant(base, layout, relative: float, output: Path):
    p = prefs()
    measure_writer = make_writer(layout, relative, SEED)
    pages = paginate_text(TEXT, base.width, base.height, layout, measure_writer.measure)
    body_writer = make_writer(layout, relative, SEED)
    header_writer = make_writer(layout, 1.0, SEED + 991)
    page = base.copy()
    text_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    line_boxes = []
    for line in pages[0]:
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        body_writer.render_line(layer, line.text, line.x, line.y, baseline_slope=line.baseline_slope)
        page.alpha_composite(layer); text_layer.alpha_composite(layer)
        line_boxes.append(layer.getchannel("A").getbbox())
    add_header(page, p, p.custom_date, None, layout, header_writer)
    page.convert("RGB").save(output / f"folio1_scale_{round(relative * 100):02d}.png", optimize=True)

    x0, x1 = layout.margin_left, base.width - layout.margin_right
    overlay = page.convert("RGBA"); draw = ImageDraw.Draw(overlay, "RGBA")
    rows = []; previous = None
    for index, expected in enumerate(layout.baseline_positions or (), 1):
        slope, intercept = fit_ruling(base, expected, x0, x1)
        offset = layout.baseline_offsets[index - 1] if layout.baseline_offsets else layout.baseline_offset
        origin = expected - offset
        box = line_boxes[index - 1] if index <= len(line_boxes) else None
        if box:
            left, top, right, bottom = box
            pixels = [(x, y) for y in range(top, bottom + 1) for x in range(left, right + 1)
                      if text_layer.getpixel((x, y))[3] >= 24]
            clearances = [slope * x + intercept - y for x, y in pixels]
            upper_clearances = [y - (previous[0] * x + previous[1]) for x, y in pixels] if previous else [999.0]
            lower = min(clearances)
            upper = min(upper_clearances)
            # Count only the actual alpha pixels that enter either ruling's
            # 2px tolerance band; do not multiply one bad minimum by the full
            # glyph area.
            collisions = sum(1 for value in clearances if value < 2.0)
            if previous:
                collisions += sum(1 for value in upper_clearances if value < 2.0)
            height = bottom - top + 1
            overflow = int(left < x0 or right > x1)
            clipped = int(left <= 0 or top <= 0 or right >= text_layer.width - 1 or bottom >= text_layer.height - 1)
            status = "PASS" if min(lower, upper) >= 2.0 and collisions == 0 and not overflow and not clipped else "FAIL"
            draw.rectangle(box, outline=(0, 120, 255, 220), width=3)
        else:
            left = top = right = bottom = -1; lower = upper = -1.0; collisions = 0; height = 0; overflow = clipped = 0; status = "EMPTY"
        draw.line((x0, slope * x0 + intercept, x1, slope * x1 + intercept), fill=(225, 40, 40, 220), width=3)
        draw.line((x0, origin, x1, origin), fill=(35, 220, 80, 210), width=2)
        draw.line((x0, slope * x0 + intercept - 8, x1, slope * x1 + intercept - 8), fill=(245, 205, 40, 170), width=2)
        rows.append({"line_index": index, "ink_height": height, "minimum_clearance": round(min(lower, upper), 2), "collision_pixels": collisions, "horizontal_overflow": overflow, "clipped_glyph": clipped, "status": status})
        previous = (slope, intercept)
    overlay.save(output / f"folio1_scale_{round(relative * 100):02d}_debug.png", optimize=True)
    occupied = [line for line in pages[0] if line.text.strip()]
    avg_chars = sum(len(line.text) for line in occupied) / max(1, len(occupied))
    return page.convert("RGB"), rows, len(pages), avg_chars, len(occupied)


def main() -> None:
    output = ROOT / "outputs" / "folio1_scale_calibration"; output.mkdir(parents=True, exist_ok=True)
    base, layout = load_paper("book_kertas_folio_1", ROOT / "assets" / "papers", ROOT / "menu_buku")
    # Keep this historical experiment anchored to the original production
    # baseline even after Variant D is enabled in config/books.py.
    layout = replace(layout, handwriting_scale=layout.handwriting_scale / 0.88)
    results = []; variants = []
    for relative in SCALES:
        image, rows, pages, avg_chars, occupied = render_variant(base, layout, relative, output)
        variants.append(image.resize((620, 877), Image.Resampling.LANCZOS))
        valid = [row for row in rows if row["status"] != "EMPTY"]
        results.append({"scale": f"{relative:.2f}", "font_size": round(54 * layout.handwriting_scale * relative), "avg": round(avg_chars, 2), "occupied": occupied, "pages": pages, "max_height": max((r["ink_height"] for r in valid), default=0), "min_clearance": min((r["minimum_clearance"] for r in valid), default=-1), "collisions": sum(r["collision_pixels"] for r in valid), "overflow": sum(r["horizontal_overflow"] for r in valid), "clipped": sum(r["clipped_glyph"] for r in valid)})
    comparison = Image.new("RGB", (1240, 1794), "white"); draw = ImageDraw.Draw(comparison)
    for i, image in enumerate(variants):
        x, y = (i % 2) * 620, (i // 2) * 897
        comparison.paste(image, (x, y + 20)); draw.text((x + 12, y + 2), f"Variant {chr(65+i)} — {int(SCALES[i]*100)}%", fill=(20, 20, 20))
    comparison.save(output / "folio1_comparison.png", optimize=True)
    report = ["# Folio 1 handwriting scale calibration", "", "Eksperimen terisolasi; konfigurasi produksi Folio 1 tidak diubah.", "", "Template: `book_kertas_folio_1` (`kertas_folio_1.png`)", "Style: `natural_student_upright_01`", f"Production body font size: `{round(54 * layout.handwriting_scale)}` px", f"Ruling lines: `{len(layout.baseline_positions or ())}`", f"Pagination pages for test content: `{results[0]['pages']}`", f"Baseline offsets: `{layout.baseline_offsets}`", f"Horizontal margins: left `{layout.margin_left}`, right `{layout.margin_right}`", "", "## Results", "", "| scale | font px | avg chars/line | occupied lines | max glyph h | min clearance | collisions | overflow | clipped | pages |", "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in results:
        report.append(f"| {r['scale']} | {r['font_size']} | {r['avg']} | {r['occupied']} | {r['max_height']} | {r['min_clearance']} | {r['collisions']} | {r['overflow']} | {r['clipped']} | {r['pages']} |")
    report += ["", "Visual comparison is limited to the first page; pagination count is measured from the same test content.", "No scale is applied to production by this experiment.", "", "Debug overlays: `folio1_scale_100_debug.png`, `folio1_scale_95_debug.png`, `folio1_scale_90_debug.png`, `folio1_scale_88_debug.png`."]
    (output / "folio1_calibration_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"output={output} variants={len(results)} pages={[r['pages'] for r in results]}")


if __name__ == "__main__":
    main()
