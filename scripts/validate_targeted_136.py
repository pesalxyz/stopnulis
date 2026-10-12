from __future__ import annotations

import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.models import UserPreferences
from renderer.paper import load_paper
from services.generation_service import GenerationService

TEXT = "Mahasiswa belajar merancang sistem yang rapi, efisien, dan mudah digunakan. Catatan ini menguji ukuran header."
BOOKS = ("book_buku_tulis_1", "book_buku_tulis_3", "book_buku_tulis_6")
STYLES = ("natural_student_upright_01", "natural_student")


def prefs(book: str, style: str) -> UserPreferences:
    return UserPreferences(1, book_style=book, handwriting_style=style,
        ink_color="blue", show_identity=True, name="Faisal", npm="123456",
        class_name="SI-4A", attendance_number="07", show_date=True,
        date_mode="custom", custom_date="13-10-2026")


def ink_bbox(layer: Image.Image) -> tuple[int, int, int, int] | None:
    return layer.getchannel("A").getbbox()


def main() -> int:
    out = ROOT / "outputs" / "targeted_136"
    out.mkdir(parents=True, exist_ok=True)
    service = GenerationService(ROOT / "assets")
    rows: list[dict[str, object]] = []
    for book in BOOKS:
        for style in STYLES:
            p = prefs(book, style)
            result = service.render(TEXT, p, seed=20261013)
            final = result.pages[0].convert("RGB")
            text_layer = service.render(TEXT, p, seed=20261013, text_only=True).pages[0].convert("RGBA")
            stem = f"{book}_{style}"
            final.save(out / f"{stem}.png", optimize=True)
            base, layout = load_paper(book, ROOT / "assets" / "papers", ROOT / "menu_buku")
            debug = base.convert("RGBA")
            debug.alpha_composite(text_layer)
            draw = ImageDraw.Draw(debug, "RGBA")
            if layout.baseline_positions:
                for i, y in enumerate(layout.baseline_positions, 1):
                    draw.line((layout.margin_left, y, final.width - layout.margin_right, y), fill=(225, 30, 30, 150), width=2)
                    draw.text((layout.margin_left + 4, y - layout.baseline_offset - 24), str(i), fill=(225, 30, 30, 220))
            bbox = ink_bbox(text_layer)
            if bbox:
                draw.rectangle(bbox, outline=(255, 120, 0, 230), width=3)
            debug.save(out / f"{stem}_debug.png", optimize=True)
            rows.append({"book": book, "style": style, "pages": len(result.pages),
                         "ink_left": bbox[0] if bbox else -1, "ink_top": bbox[1] if bbox else -1,
                         "ink_right": bbox[2] if bbox else -1, "ink_bottom": bbox[3] if bbox else -1,
                         "body_scale_adjust": layout.body_scale_adjust,
                         "header_scale_override": layout.header_scale_override,
                         "header_field_scales": layout.header_field_scales or ""})
    with (out / "targeted_136_measurements.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (out / "targeted_136_report.md").write_text(
        "# Targeted Buku 1/3/6 validation\n\n"
        "All renders use seed `20261013`, blue ink, and the same identity/test text. "
        "Debug images overlay the text-only alpha mask and physical baselines.\n\n"
        "- Buku 1/Buku 6 body adjustment: 1.08\n"
        "- Buku 3 field scales (Nama, NPM, Kelas, Absen, Tanggal): 1.00, 0.86, 1.00, 0.86, 0.86\n"
        "- Folio/HVS remain on their legacy 0.80 header scale.\n")
    print(f"validated={len(rows)} outputs={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
