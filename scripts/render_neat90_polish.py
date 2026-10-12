from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.models import UserPreferences
from services.generation_service import GenerationService

from render_neat_presets import TEXT


def main() -> None:
    output_dir = ROOT / "outputs"
    output_dir.mkdir(exist_ok=True)
    service = GenerationService(ROOT / "assets")
    preferences = UserPreferences(
        telegram_user_id=1,
        handwriting_style="natural_student_neat_90",
        ink_color="blue",
        show_identity=False,
        show_date=False,
        date_mode="none",
    )
    result = service.render(TEXT, preferences, seed=20261007)
    if len(result.pages) != 1:
        raise RuntimeError(f"neat_90 menghasilkan {len(result.pages)} halaman; comparison harus satu halaman.")
    final = result.pages[0].convert("RGB")
    final_path = output_dir / "neat_90_final.png"
    final.save(final_path, "PNG", optimize=True)

    before_path = output_dir / "neat_90_before_polish.png"
    before = Image.open(before_path).convert("RGB")
    if before.size != final.size:
        raise RuntimeError(f"Ukuran before/final berbeda: {before.size} != {final.size}")
    scale = 0.5
    thumb_size = (round(final.width * scale), round(final.height * scale))
    label_height = 76
    contact = Image.new("RGB", (thumb_size[0] * 2, thumb_size[1] + label_height), (248, 247, 240))
    draw = ImageDraw.Draw(contact)
    try:
        label_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 40)
    except OSError:
        label_font = ImageFont.load_default()
    draw.text((22, 17), "before polish", font=label_font, fill=(35, 40, 50))
    draw.text((thumb_size[0] + 22, 17), "Natural Student", font=label_font, fill=(35, 40, 50))
    contact.paste(before.resize(thumb_size, Image.Resampling.LANCZOS), (0, label_height))
    contact.paste(final.resize(thumb_size, Image.Resampling.LANCZOS), (thumb_size[0], label_height))
    comparison_path = output_dir / "neat_90_polish_comparison.png"
    contact.save(comparison_path, "PNG", optimize=True)
    print(f"final: {final_path} ({final_path.stat().st_size} bytes)")
    print(f"comparison: {comparison_path} ({comparison_path.stat().st_size} bytes)")
    print(f"debug_stats: {result.debug_stats}")


if __name__ == "__main__":
    main()
