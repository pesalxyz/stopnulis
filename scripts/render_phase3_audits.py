from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from renderer.multiglyph import MultiGlyphHandwritingRenderer
from renderer.paper import load_paper


STYLE = ROOT / "assets" / "handwriting" / "natural_student_01"
BLUE = (24, 58, 135)


def page() -> Image.Image:
    image, _ = load_paper("lined", ROOT / "assets" / "papers")
    return image


def main() -> None:
    glyph_image = page()
    glyph_writer = MultiGlyphHandwritingRenderer(STYLE, 54, BLUE, seed=303)
    rows = ["a", "e", "i", "n", "r", "s", "t", "m", "u", "g"]
    for index, char in enumerate(rows):
        glyph_writer.render_line(glyph_image, char * 16, 250, 430 + index * 255)
    glyph_image.convert("RGB").save(ROOT / "outputs" / "glyph_audit.png", "PNG", optimize=True)

    word_image = page()
    word_writer = MultiGlyphHandwritingRenderer(STYLE, 54, BLUE, seed=404)
    words = [
        "informasi informasi informasi informasi",
        "mahasiswa mahasiswa mahasiswa mahasiswa",
        "pengembangan pengembangan pengembangan",
        "sistem sistem sistem sistem sistem",
        "yang yang yang yang yang yang",
        "dan dan dan dan dan dan",
    ]
    for index, text in enumerate(words):
        word_writer.render_line(word_image, text, 250, 430 + index * 300)
    word_image.convert("RGB").save(ROOT / "outputs" / "word_audit.png", "PNG", optimize=True)
    print("wrote glyph_audit.png and word_audit.png")


if __name__ == "__main__":
    main()
