from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True, slots=True)
class Variation:
    rotation: float = 1.5
    x_jitter: float = 1.0
    y_jitter: float = 2.0
    scale: float = 0.04
    opacity_min: int = 210
    opacity_max: int = 250
    slant: float = 0.0


def load_font(font_path: Path | None, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        font_path,
        Path(__file__).resolve().parents[1] / "assets/fonts/handwriting.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Comic Sans MS.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    raise FileNotFoundError("Font tulisan tangan tidak ditemukan di assets/fonts/.")


class HandwritingRenderer:
    def __init__(self, font_path: Path | None, font_size: int, color: tuple[int, int, int], variation: Variation, seed: int | None = None) -> None:
        self.font_path = font_path
        self.font_size = font_size
        self.color = color
        self.variation = variation
        self.random = random.Random(seed)
        self.font = load_font(font_path, font_size)
        self._font_cache: dict[int, ImageFont.FreeTypeFont] = {font_size: self.font}

    def measure(self, text: str) -> float:
        # The renderer advances using the same font metrics.  Keep a small
        # allowance for per-glyph jitter instead of the old 4% conservative
        # padding, which caused avoidable line breaks.
        return self.font.getlength(text) * 1.012

    def render_line(self, image: Image.Image, text: str, x: int, y: int, optimized: bool = False, baseline_slope: float = 0.0) -> None:
        if not text:
            return
        if optimized:
            draw = ImageDraw.Draw(image, "RGBA")
            draw.text((x, y), text, font=self.font, fill=(*self.color, 235))
            return
        cursor = float(x)
        for char in text:
            size_factor = 1 + self.random.uniform(-self.variation.scale, self.variation.scale)
            size = max(10, round(self.font_size * size_factor))
            font = self._font_cache.get(size)
            if font is None:
                font = load_font(self.font_path, size)
                self._font_cache[size] = font
            advance = font.getlength(char)
            if char.isspace():
                cursor += advance * self.random.uniform(0.92, 1.12)
                continue
            bbox = font.getbbox(char)
            width = max(8, bbox[2] - bbox[0] + 18)
            height = max(8, bbox[3] - bbox[1] + 22)
            glyph = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            alpha = self.random.randint(self.variation.opacity_min, self.variation.opacity_max)
            ImageDraw.Draw(glyph).text((9 - bbox[0], 8 - bbox[1]), char, font=font, fill=(*self.color, alpha))
            angle = self.random.uniform(-self.variation.rotation, self.variation.rotation)
            glyph = glyph.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
            if self.variation.slant:
                shear = self.variation.slant
                glyph = glyph.transform(
                    (glyph.width + int(abs(shear) * glyph.height), glyph.height),
                    Image.Transform.AFFINE, (1, -shear, 0, 0, 1, 0),
                    resample=Image.Resampling.BICUBIC,
                )
            px = round(cursor + self.random.uniform(-self.variation.x_jitter, self.variation.x_jitter))
            py = round(y + self.random.uniform(-self.variation.y_jitter, self.variation.y_jitter))
            image.alpha_composite(glyph, (px, py))
            cursor += advance + self.random.uniform(-0.8, 1.3)
