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


PARAGRAPH = (
    "Mahasiswa belajar merancang sistem yang rapi, efisien, dan mudah digunakan. "
    "Dalam pengembangan perangkat lunak, kita perlu memperhatikan kebutuhan pengguna, "
    "alur data, serta keamanan informasi. Konsistensi menjadi bagian penting dalam setiap tugas. "
    "Dengan latihan yang teratur, tulisan tetap terbaca dan nyaman dilihat. "
)
FULL_TEXT = "\n\n".join(PARAGRAPH for _ in range(8))


def font(size: int):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def main() -> None:
    menu_dir = ROOT / "menu_buku"
    output_dir = ROOT / "outputs" / "book_templates_full_lines"
    output_dir.mkdir(parents=True, exist_ok=True)
    service = GenerationService(ROOT / "assets")
    rendered: list[tuple[str, Image.Image]] = []
    for template in discover_book_templates(menu_dir):
        _, layout = load_paper(template.template_id, ROOT / "assets" / "papers", menu_dir)
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
            custom_date="12-10-2026",
        )
        result = service.render(FULL_TEXT, preferences, seed=20261012)
        image = result.pages[0].convert("RGB")
        image.save(output_dir / f"{template.template_id}.png", "PNG", optimize=True)
        rendered.append((f"{template.template_id} · {template.label}", image))
        print(f"{template.template_id}: baselines={len(layout.baseline_positions or ()) or 'virtual'}")

    scale = 0.30
    thumb = (round(rendered[0][1].width * scale), round(rendered[0][1].height * scale))
    cols, label_height = 3, 58
    rows = (len(rendered) + cols - 1) // cols
    contact = Image.new("RGB", (thumb[0] * cols, (thumb[1] + label_height) * rows), (245, 244, 238))
    draw = ImageDraw.Draw(contact)
    for index, (label, image) in enumerate(rendered):
        x, y = (index % cols) * thumb[0], (index // cols) * (thumb[1] + label_height)
        draw.text((x + 8, y + 12), label, font=font(23), fill=(30, 35, 45))
        contact.paste(image.resize(thumb, Image.Resampling.LANCZOS), (x, y + label_height))
    contact.save(ROOT / "outputs" / "book_templates_full_lines_comparison.png", "PNG", optimize=True)


if __name__ == "__main__":
    main()
