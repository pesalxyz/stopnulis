from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.books import discover_book_templates
from database.models import UserPreferences
from services.generation_service import GenerationService


TEXT = "Mahasiswa belajar merancang sistem yang rapi, efisien, dan mudah digunakan. Dalam pengembangan perangkat lunak, kita perlu memperhatikan kebutuhan pengguna serta keamanan informasi."


def main() -> None:
    menu_dir = ROOT / "menu_buku"
    output = ROOT / "outputs" / "book_templates"
    output.mkdir(parents=True, exist_ok=True)
    service = GenerationService(ROOT / "assets")
    pages: list[tuple[str, Image.Image]] = []
    for template in discover_book_templates(menu_dir):
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
        result = service.render(TEXT, preferences, seed=20261007)
        image = result.pages[0].convert("RGB")
        image.save(output / f"{template.template_id}.png", "PNG", optimize=True)
        pages.append((f"{template.template_id} · {template.label}", image))
        print(f"{template.template_id}: {template.filename} -> {image.size}")

    scale = 0.30
    thumb_size = (round(pages[0][1].width * scale), round(pages[0][1].height * scale))
    cols = 4
    label_height = 58
    rows = (len(pages) + cols - 1) // cols
    contact = Image.new("RGB", (thumb_size[0] * cols, (thumb_size[1] + label_height) * rows), (245, 244, 238))
    draw = ImageDraw.Draw(contact)
    try:
        label_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 23)
    except OSError:
        label_font = ImageFont.load_default()
    for index, (label, image) in enumerate(pages):
        x = (index % cols) * thumb_size[0]
        y = (index // cols) * (thumb_size[1] + label_height)
        draw.text((x + 8, y + 12), label, font=label_font, fill=(30, 35, 45))
        contact.paste(image.resize(thumb_size, Image.Resampling.LANCZOS), (x, y + label_height))
    contact.save(ROOT / "outputs" / "book_templates_comparison.png", "PNG", optimize=True)


if __name__ == "__main__":
    main()
