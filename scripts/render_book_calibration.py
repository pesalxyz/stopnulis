from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.books import discover_book_templates
from database.models import UserPreferences
from renderer.paper import load_paper
from services.generation_service import GenerationService


LONG_TEXT = (
    "Mahasiswa belajar merancang sistem yang rapi, efisien, dan mudah digunakan. Dalam pengembangan perangkat lunak, kita perlu memperhatikan kebutuhan pengguna, alur data, serta keamanan informasi.\n\n"
    "Konsistensi menjadi bagian penting dalam setiap tugas. Dengan latihan yang teratur, tulisan tetap terbaca dan nyaman dilihat. Struktur informasi harus jelas agar pembaca mudah mengikuti penjelasan dari awal sampai akhir.\n\n"
    "Setiap proses perlu diuji secara bertahap. Catatan yang lengkap membantu mahasiswa menemukan kesalahan, memperbaiki langkah kerja, dan menjaga hasil tetap dapat diandalkan. Kerja sama dan ketelitian membuat laporan menjadi lebih baik."
)


def _font(size: int):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def main() -> None:
    menu_dir = ROOT / "menu_buku"
    debug_dir = ROOT / "outputs" / "book_calibration_debug"
    output_dir = ROOT / "outputs" / "book_templates_calibrated"
    debug_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    service = GenerationService(ROOT / "assets")
    rendered: list[tuple[str, Image.Image]] = []
    for template in discover_book_templates(menu_dir):
        base, layout = load_paper(template.template_id, ROOT / "assets" / "papers", menu_dir)
        debug = base.convert("RGB")
        draw = ImageDraw.Draw(debug, "RGBA")
        baselines = layout.baseline_positions or tuple(layout.margin_top + layout.baseline_offset + i * layout.line_spacing for i in range(24))
        for index, baseline in enumerate(baselines):
            draw.line((layout.margin_left, baseline, debug.width - layout.margin_right, baseline), fill=(220, 40, 40, 155), width=3)
            if index in {0, 4, 9, len(baselines) - 1}:
                draw.text((layout.margin_left + 8, baseline - 32), f"L{index + 1}", font=_font(24), fill=(190, 30, 30, 230))
        draw.line((layout.margin_left, 0, layout.margin_left, debug.height), fill=(30, 175, 70, 220), width=5)
        draw.line((debug.width - layout.margin_right, 0, debug.width - layout.margin_right, debug.height), fill=(30, 175, 70, 220), width=5)
        draw.rectangle((0, 0, debug.width, max(0, layout.margin_top + layout.baseline_offset - 12)), outline=(240, 150, 25, 230), width=6)
        debug.save(debug_dir / f"{template.template_id}.png", "PNG", optimize=True)

        preferences = UserPreferences(
            telegram_user_id=1,
            book_style=template.template_id,
            handwriting_style="natural_student_upright_01",
            ink_color="blue",
            show_identity=True,
            name="Faisal",
            npm="123456",
            class_name="SI-4A",
            attendance_number="07",
            show_date=True,
            date_mode="custom",
            custom_date="07-10-2026",
        )
        result = service.render(LONG_TEXT, preferences, seed=20261007)
        image = result.pages[0].convert("RGB")
        image.save(output_dir / f"{template.template_id}.png", "PNG", optimize=True)
        rendered.append((f"{template.template_id} · {template.label}", image))
        print(f"{template.template_id}: lines={len(baselines)} left={layout.margin_left} right={image.width - layout.margin_right} first={baselines[0]} spacing={layout.line_spacing} scale={layout.handwriting_scale}")

    scale = 0.30
    thumb = (round(rendered[0][1].width * scale), round(rendered[0][1].height * scale))
    cols, label_height = 4, 58
    rows = (len(rendered) + cols - 1) // cols
    contact = Image.new("RGB", (thumb[0] * cols, (thumb[1] + label_height) * rows), (245, 244, 238))
    draw = ImageDraw.Draw(contact)
    label_font = _font(23)
    for index, (label, image) in enumerate(rendered):
        x, y = (index % cols) * thumb[0], (index // cols) * (thumb[1] + label_height)
        draw.text((x + 8, y + 12), label, font=label_font, fill=(30, 35, 45))
        contact.paste(image.resize(thumb, Image.Resampling.LANCZOS), (x, y + label_height))
    contact.save(ROOT / "outputs" / "book_templates_calibrated_comparison.png", "PNG", optimize=True)


if __name__ == "__main__":
    main()
