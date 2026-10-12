from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.models import UserPreferences
from services.generation_service import GenerationService
from render_neat_presets import TEXT


STYLE = "natural_student_upright_01"


def preferences() -> UserPreferences:
    return UserPreferences(telegram_user_id=1, handwriting_style=STYLE, ink_color="blue", show_identity=False, show_date=False, date_mode="none")


def render(service: GenerationService, text: str) -> Image.Image:
    result = service.render(text, preferences(), seed=20261007)
    if len(result.pages) != 1:
        raise RuntimeError(f"Expected one page, got {len(result.pages)}")
    return result.pages[0].convert("RGB")


def font() -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 40)
    except OSError:
        return ImageFont.load_default()


def main() -> None:
    output = ROOT / "outputs"
    service = GenerationService(ROOT / "assets")
    after = render(service, TEXT)
    after_path = output / "upright_after_micro_polish.png"
    after.save(after_path, "PNG", optimize=True)
    before = Image.open(output / "upright_before_micro_polish.png").convert("RGB")
    if before.size != after.size:
        raise RuntimeError(f"Baseline size changed: {before.size} != {after.size}")

    label_font = font()
    scale = 0.5
    thumb = (round(after.width * scale), round(after.height * scale))
    label_height = 76
    comparison = Image.new("RGB", (thumb[0] * 2, thumb[1] + label_height), (248, 247, 240))
    draw = ImageDraw.Draw(comparison)
    for index, (label, image) in enumerate((("current Upright", before), ("micro-polished Upright", after))):
        x = index * thumb[0]
        draw.text((x + 22, 17), label, font=label_font, fill=(35, 40, 50))
        comparison.paste(image.resize(thumb, Image.Resampling.LANCZOS), (x, label_height))
    comparison.save(output / "upright_micro_comparison.png", "PNG", optimize=True)

    crop_box = (130, 720, after.width - 130, 1660)
    crop_scale = 1.15
    crop_size = (round((crop_box[2] - crop_box[0]) * crop_scale), round((crop_box[3] - crop_box[1]) * crop_scale))
    zoom = Image.new("RGB", (crop_size[0] * 2, crop_size[1] + label_height), (248, 247, 240))
    draw = ImageDraw.Draw(zoom)
    for index, (label, image) in enumerate((("current Upright", before), ("micro-polished Upright", after))):
        x = index * crop_size[0]
        draw.text((x + 22, 17), label, font=label_font, fill=(35, 40, 50))
        zoom.paste(image.crop(crop_box).resize(crop_size, Image.Resampling.LANCZOS), (x, label_height))
    zoom.save(output / "upright_micro_zoom.png", "PNG", optimize=True)

    glyph_text = "\n".join([
        "aaaaaaaaaaaaaaaa", "eeeeeeeeeeeeeeee", "iiiiiiiiiiiiiiii", "nnnnnnnnnnnnnnnn",
        "rrrrrrrrrrrrrrrr", "ssssssssssssssss", "tttttttttttttttt", "mmmmmmmmmmmmmmmm", "llllllllllllllll",
    ])
    render(service, glyph_text).save(output / "upright_micro_glyph_audit.png", "PNG", optimize=True)
    word_text = "\n\n".join([
        "mahasiswa mahasiswa mahasiswa mahasiswa",
        "informasi informasi informasi informasi",
        "sistem sistem sistem sistem",
        "pengembangan pengembangan pengembangan",
        "konsistensi konsistensi konsistensi",
        "yang yang yang yang yang",
    ])
    render(service, word_text).save(output / "upright_micro_word_audit.png", "PNG", optimize=True)
    print(f"after={after_path} ({after_path.stat().st_size} bytes)")
    for name in ("upright_micro_comparison.png", "upright_micro_zoom.png", "upright_micro_glyph_audit.png", "upright_micro_word_audit.png"):
        path = output / name
        print(f"{name}={path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
