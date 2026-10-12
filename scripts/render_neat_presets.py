from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.models import UserPreferences
from services.generation_service import GenerationService


TEXT = """Catatan Perkuliahan — Sistem Informasi, 7 Oktober 2026

Mahasiswa belajar merancang sistem yang rapi, efisien, dan mudah digunakan. Dalam pengembangan perangkat lunak, kita perlu memperhatikan kebutuhan pengguna, alur data, serta keamanan informasi. Angka pengujian: 10, 25, 48, dan 100%. Pertanyaan pentingnya: apakah hasil ini sudah natural?

Yang sering dilupakan adalah konsistensi. Dengan latihan berulang-ulang, tulisan akan tetap terbaca tanpa terasa terlalu sempurna. Kombinasi ng, ny, an, in, en, er, ar, ra, ri, si, ti, di, ke, me, pe, ber, ter, kan, yang, dan harus mengalir secara wajar.

Simbol uji: (A+B) = C; nilai #1 @ kelas — benar/salah? "Ya", jawabnya!"""


def main() -> None:
    output_dir = ROOT / "outputs"
    output_dir.mkdir(exist_ok=True)
    service = GenerationService(ROOT / "assets")
    preferences = UserPreferences(
        telegram_user_id=1,
        handwriting_style="natural_student_01",
        ink_color="blue",
        show_identity=False,
        show_date=False,
        date_mode="none",
    )
    levels = [("neat_95", 0.05), ("neat_90", 0.10), ("neat_85", 0.15)]
    pages: list[tuple[str, Image.Image]] = []
    for name, level in levels:
        result = service.render(TEXT, preferences, seed=20261007, variation_level=level)
        if len(result.pages) != 1:
            raise RuntimeError(f"Preset {name} menghasilkan {len(result.pages)} halaman; comparison harus satu halaman.")
        image = result.pages[0].convert("RGB")
        path = output_dir / f"{name}.png"
        image.save(path, "PNG", optimize=True)
        pages.append((name, image))
        print(f"{name}: {path} ({path.stat().st_size} bytes)")

    scale = 0.5
    thumb_size = (round(pages[0][1].width * scale), round(pages[0][1].height * scale))
    label_height = 76
    contact = Image.new("RGB", (thumb_size[0] * len(pages), thumb_size[1] + label_height), (248, 247, 240))
    draw = ImageDraw.Draw(contact)
    try:
        label_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 40)
    except OSError:
        label_font = ImageFont.load_default()
    for index, (name, image) in enumerate(pages):
        x = index * thumb_size[0]
        draw.text((x + 22, 17), name, font=label_font, fill=(35, 40, 50))
        contact.paste(image.resize(thumb_size, Image.Resampling.LANCZOS), (x, label_height))
    contact.save(output_dir / "neat_comparison.png", "PNG", optimize=True)
    print(f"neat_comparison: {output_dir / 'neat_comparison.png'} ({(output_dir / 'neat_comparison.png').stat().st_size} bytes)")


if __name__ == "__main__":
    main()
