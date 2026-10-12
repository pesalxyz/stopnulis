from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.models import UserPreferences
from services.generation_service import GenerationService
from render_neat_presets import TEXT


def prefs(style: str) -> UserPreferences:
    return UserPreferences(
        telegram_user_id=1,
        handwriting_style=style,
        ink_color="blue",
        show_identity=False,
        show_date=False,
        date_mode="none",
    )


def main() -> None:
    output_dir = ROOT / "outputs"
    service = GenerationService(ROOT / "assets")
    rendered: list[tuple[str, Image.Image]] = []
    for label, style in (("Natural Student", "natural_student_neat_90"), ("Natural Student Upright", "natural_student_upright_01")):
        result = service.render(TEXT, prefs(style), seed=20261007)
        if len(result.pages) != 1:
            raise RuntimeError(f"{style} menghasilkan {len(result.pages)} halaman")
        image = result.pages[0].convert("RGB")
        image.save(output_dir / ("natural_student_current.png" if "Upright" not in label else "natural_student_upright.png"), "PNG", optimize=True)
        rendered.append((label, image))

    scale = 0.5
    thumb = (round(rendered[0][1].width * scale), round(rendered[0][1].height * scale))
    label_height = 76
    comparison = Image.new("RGB", (thumb[0] * 2, thumb[1] + label_height), (248, 247, 240))
    draw = ImageDraw.Draw(comparison)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    for index, (label, image) in enumerate(rendered):
        x = index * thumb[0]
        draw.text((x + 22, 17), label, font=font, fill=(35, 40, 50))
        comparison.paste(image.resize(thumb, Image.Resampling.LANCZOS), (x, label_height))
    comparison.save(output_dir / "student_style_comparison.png", "PNG", optimize=True)

    # Same crop on both pages: first paragraph plus the start of the repeated-word audit.
    crop_box = (130, 720, rendered[0][1].width - 130, 1660)
    crop_scale = 1.15
    crop_w = round((crop_box[2] - crop_box[0]) * crop_scale)
    crop_h = round((crop_box[3] - crop_box[1]) * crop_scale)
    zoom = Image.new("RGB", (crop_w * 2, crop_h + label_height), (248, 247, 240))
    draw = ImageDraw.Draw(zoom)
    for index, (label, image) in enumerate(rendered):
        x = index * crop_w
        draw.text((x + 22, 17), label, font=font, fill=(35, 40, 50))
        crop = image.crop(crop_box).resize((crop_w, crop_h), Image.Resampling.LANCZOS)
        zoom.paste(crop, (x, label_height))
    zoom.save(output_dir / "student_style_zoom.png", "PNG", optimize=True)
    print(f"current={output_dir / 'natural_student_current.png'}")
    print(f"upright={output_dir / 'natural_student_upright.png'}")
    print(f"comparison={output_dir / 'student_style_comparison.png'}")
    print(f"zoom={output_dir / 'student_style_zoom.png'}")


if __name__ == "__main__":
    main()
