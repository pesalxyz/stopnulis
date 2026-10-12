from __future__ import annotations

import json
import random
import shutil
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "handwriting" / "natural_student_01"
STYLE_ID = "natural_student_01"
STYLE_LABEL = "Natural Student"
SOURCE_FONT_OVERRIDE: Path | None = None
BASE_SIZE = 96
COMMON = set("aeinrstumkoldghp")
PUNCTUATION = ".,:;!?()-/'\"%+=&@#"
LIGATURES = ["ng", "ny", "an", "in", "en", "er", "ar", "ra", "ri", "si", "ti", "di", "ke", "me", "pe", "ber", "ter", "kan", "yang", "dan"]
ASCENDERS = set("bdfhklt")
DESCENDERS = set("gjpqy")
ROUND_CHARS = set("aoecdgq0689")


class StrokeCanvas:
    """Small antialiased path canvas used for the common lowercase alphabet."""

    def __init__(self, width: int, height: int, stroke: int) -> None:
        self.factor = 3
        self.image = Image.new("L", (width * self.factor, height * self.factor), 0)
        self.draw = ImageDraw.Draw(self.image)
        self.stroke = stroke * self.factor

    def line(self, points: list[tuple[float, float]], fill: int = 235, width: int | None = None) -> None:
        scaled = [(round(x * self.factor), round(y * self.factor)) for x, y in points]
        self.draw.line(scaled, fill=fill, width=width or self.stroke, joint="curve")

    def curve(self, points: list[tuple[float, float]], fill: int = 235, width: int | None = None) -> None:
        # Cubic Bezier interpolation gives correlated path changes rather than pixel noise.
        if len(points) != 4:
            self.line(points, fill, width)
            return
        samples: list[tuple[float, float]] = []
        for step in range(25):
            t = step / 24
            u = 1 - t
            samples.append((
                u**3 * points[0][0] + 3 * u**2 * t * points[1][0] + 3 * u * t**2 * points[2][0] + t**3 * points[3][0],
                u**3 * points[0][1] + 3 * u**2 * t * points[1][1] + 3 * u * t**2 * points[2][1] + t**3 * points[3][1],
            ))
        self.line(samples, fill, width)

    def finish(self) -> Image.Image:
        return self.image.resize((self.image.width // self.factor, self.image.height // self.factor), Image.Resampling.LANCZOS)


def draw_stroke_char(canvas: StrokeCanvas, char: str, x: float, variant: int, rng: random.Random) -> float:
    """Draw one construction from a writer's stroke vocabulary and return advance."""
    mid, base, asc = 91, 128, 28
    wobble = rng.uniform(-2.0, 2.0)
    narrow = 1.0 + ((variant % 5) - 2) * 0.025
    x = x + wobble
    def P(px: float, py: float) -> tuple[float, float]:
        return x + (px - 20) * narrow, py + wobble * 0.18

    if char == "a":
        open_loop = variant in {2, 6}
        bowl_top = 70 + (variant % 4) * 3
        bowl_right = 53 + (variant % 3) * 3
        canvas.curve([P(18, 102), P(17, 79), P(39, bowl_top), P(bowl_right, 91)])
        canvas.curve([P(bowl_right, 91), P(65, 111), P(48, 124), P(29, 119)])
        if not open_loop:
            canvas.curve([P(29, 119), P(16, 113), P(18, 102), P(18, 102)])
        stem_x = 55 + (variant % 3) * 2
        canvas.curve([P(stem_x, 88), P(stem_x, 103), P(stem_x - 2, 119), P(61 + variant % 3, 126)])
        exit_end = 73 if variant in {4, 8} else 78
        canvas.curve([P(61, 126), P(68, 130), P(exit_end - 4, 128), P(exit_end, 126)])
    elif char == "e":
        canvas.curve([P(18, 103), P(27, 91), P(48, 93), P(59, 99)])
        canvas.curve([P(59, 99), P(48, 106), P(29, 104), P(20, 105)])
        canvas.curve([P(20, 105), P(22, 125), P(49, 128), P(66, 120)])
    elif char == "i":
        canvas.line([P(34, 96), P(34, 126)])
        canvas.curve([P(34, 126), P(39, 130), P(45, 128), P(49, 126)])
        dot_x = 34 + (variant % 3 - 1) * 2
        canvas.draw.ellipse((round((dot_x - 3) * 3), round(67 * 3), round((dot_x + 3) * 3), round(73 * 3)), fill=235)
    elif char == "n":
        canvas.curve([P(17, 126), P(22, 111), P(26, 100), P(31, 96)])
        arch_top = 81 if variant % 4 in {0, 3} else 88
        arch_width = 47 + (variant % 3) * 3
        canvas.curve([P(31, 96), P(39, arch_top), P(arch_width, arch_top + 1), P(49, 101)])
        canvas.curve([P(49, 101), P(50, 113), P(53, 124), P(60, 126)])
        canvas.curve([P(60, 126), P(67, 130), P(73 + variant % 2, 128), P(78 + variant % 3, 126)])
    elif char == "r":
        canvas.curve([P(22, 127), P(24, 112), P(25, 100), P(30, 96)])
        canvas.curve([P(30, 96), P(39, 87), P(48, 93), P(51, 101)])
        canvas.curve([P(51, 101), P(57, 91), P(65, 91), P(70, 97)])
    elif char == "s":
        canvas.curve([P(62, 96), P(52, 88), P(31, 91), P(25, 102)])
        canvas.curve([P(25, 102), P(20, 111), P(54, 108), P(59, 116)])
        canvas.curve([P(59, 116), P(62, 126), P(41, 131), P(22, 123)])
    elif char == "t":
        stem_top = 25 + (variant % 3) * 4
        canvas.curve([P(41, stem_top), P(39, 59), P(37, 101), P(37, 126)])
        canvas.curve([P(37, 126), P(42, 131), P(53, 128), P(63, 124)])
        crossbar_y = 78 + (variant % 4) * 3
        canvas.line([P(20 + variant % 3, crossbar_y), P(53 + (variant % 2) * 5, crossbar_y - 1)], width=max(5, canvas.stroke // 3 * 2))
    elif char == "m":
        canvas.curve([P(15, 127), P(20, 108), P(23, 98), P(30, 96)])
        canvas.curve([P(30, 96), P(39, 87), P(44, 101), P(45, 114)])
        canvas.curve([P(45, 114), P(47, 101), P(52, 91), P(59, 96)])
        canvas.curve([P(59, 96), P(66, 103), P(62, 121), P(72, 127)])
    elif char == "u":
        canvas.curve([P(19, 96), P(18, 111), P(21, 124), P(31, 126)])
        canvas.curve([P(31, 126), P(42, 129), P(48, 111), P(51, 97)])
        canvas.curve([P(51, 97), P(50, 112), P(54, 124), P(62, 127)])
        canvas.curve([P(62, 127), P(69, 130), P(75, 128), P(80, 125)])
    elif char == "k":
        canvas.curve([P(38, 29), P(37, 61), P(34, 100), P(34, 127)])
        canvas.curve([P(34, 101), P(45, 91), P(55, 87), P(61, 88)])
        canvas.curve([P(48, 103), P(55, 112), P(60, 123), P(70, 127)])
    elif char == "o":
        canvas.curve([P(42, 90), P(25, 87), P(18, 102), P(23, 115)])
        canvas.curve([P(23, 115), P(28, 131), P(52, 130), P(59, 113)])
        canvas.curve([P(59, 113), P(65, 98), P(55, 90), P(42, 90)])
        canvas.curve([P(59, 113), P(64, 123), P(70, 127), P(77, 126)])
    elif char == "l":
        canvas.curve([P(42, 30), P(32, 52), P(35, 97), P(37, 119)])
        canvas.curve([P(37, 119), P(39, 131), P(54, 131), P(67, 125)])
    elif char == "d":
        canvas.curve([P(43, 92), P(25, 87), P(18, 103), P(22, 115)])
        canvas.curve([P(22, 115), P(29, 131), P(53, 128), P(58, 113)])
        canvas.curve([P(58, 113), P(61, 96), P(57, 63), P(56, 29)])
        canvas.curve([P(56, 113), P(60, 123), P(68, 129), P(77, 126)])
    elif char == "g":
        draw_stroke_char(canvas, "o", x, variant, rng)
        canvas.curve([P(57, 112), P(72, 124), P(62, 143), P(48, 148)])
        canvas.curve([P(48, 148), P(36, 153), P(42, 169), P(58, 163)])
    elif char == "h":
        canvas.curve([P(38, 30), P(35, 60), P(34, 100), P(34, 127)])
        canvas.curve([P(34, 104), P(45, 88), P(55, 91), P(56, 104)])
        canvas.curve([P(56, 104), P(56, 118), P(63, 127), P(72, 126)])
    elif char == "p":
        canvas.curve([P(31, 96), P(31, 125), P(29, 153), P(28, 170)])
        canvas.curve([P(31, 105), P(38, 88), P(57, 89), P(60, 104)])
        canvas.curve([P(60, 104), P(63, 120), P(43, 128), P(31, 119)])
    elif char == "y":
        canvas.curve([P(18, 96), P(17, 111), P(20, 125), P(30, 126)])
        canvas.curve([P(30, 126), P(43, 130), P(49, 111), P(53, 97)])
        canvas.curve([P(53, 97), P(51, 127), P(47, 157), P(37, 168)])
        canvas.curve([P(37, 168), P(45, 174), P(62, 165), P(70, 153)])
    elif char == "c":
        canvas.curve([P(62, 96), P(51, 87), P(27, 90), P(21, 106)])
        canvas.curve([P(21, 106), P(17, 123), P(43, 132), P(65, 122)])
    elif char == "b":
        canvas.curve([P(38, 30), P(36, 63), P(35, 103), P(34, 127)])
        canvas.curve([P(34, 103), P(45, 88), P(62, 91), P(62, 107)])
        canvas.curve([P(62, 107), P(62, 124), P(44, 130), P(34, 119)])
    elif char == "j":
        canvas.curve([P(43, 96), P(42, 118), P(47, 129), P(56, 127)])
        canvas.curve([P(56, 127), P(68, 125), P(59, 157), P(43, 166)])
        canvas.curve([P(43, 166), P(35, 170), P(32, 165), P(36, 160)])
        dot_x = 43 + (variant % 3 - 1) * 2
        canvas.draw.ellipse((round((dot_x - 3) * 3), round(67 * 3), round((dot_x + 3) * 3), round(73 * 3)), fill=235)
    elif char == "q":
        canvas.curve([P(43, 92), P(25, 87), P(18, 103), P(23, 115)])
        canvas.curve([P(23, 115), P(29, 130), P(52, 129), P(59, 113)])
        canvas.curve([P(59, 113), P(64, 101), P(55, 91), P(43, 92)])
        canvas.curve([P(58, 105), P(58, 131), P(56, 155), P(48, 168)])
    elif char == "v":
        canvas.curve([P(17, 96), P(24, 112), P(28, 123), P(36, 127)])
        canvas.curve([P(36, 127), P(46, 125), P(50, 106), P(58, 96)])
        canvas.curve([P(58, 96), P(63, 110), P(69, 124), P(79, 126)])
    elif char == "w":
        canvas.curve([P(15, 96), P(21, 112), P(25, 124), P(32, 127)])
        canvas.curve([P(32, 127), P(39, 127), P(41, 110), P(44, 99)])
        canvas.curve([P(44, 99), P(48, 111), P(51, 125), P(58, 127)])
        canvas.curve([P(58, 127), P(67, 127), P(70, 106), P(79, 96)])
    elif char == "x":
        canvas.curve([P(20, 97), P(29, 108), P(43, 119), P(62, 127)])
        canvas.curve([P(62, 97), P(51, 107), P(37, 120), P(20, 127)])
    elif char == "z":
        canvas.curve([P(19, 98), P(34, 94), P(52, 97), P(66, 96)])
        canvas.curve([P(66, 96), P(53, 107), P(37, 118), P(21, 126)])
        canvas.curve([P(21, 126), P(37, 129), P(57, 126), P(70, 127)])
    else:
        canvas.curve([P(20, 118), P(30, 90), P(54, 90), P(66, 112)])
        canvas.curve([P(66, 112), P(60, 130), P(39, 131), P(21, 124)])
    return 56.0


def make_stroke_variant(token: str, variant: int, rng: random.Random) -> tuple[Image.Image, float, float]:
    width = max(120, 62 * len(token) + 45)
    canvas = StrokeCanvas(width, 190, rng.randint(8, 10))
    cursor = 17.0
    for index, char in enumerate(token):
        cursor += draw_stroke_char(canvas, char, cursor, variant + index % 3, rng) - (13 if index else 0)
        if index < len(token) - 1:
            # Not every pair connects; this is deliberately a nearly-connected writer.
            if (variant + index) % 3 != 1:
                canvas.line([(cursor - 7, 126), (cursor + 2, 126 + rng.uniform(-2, 2))], width=max(3, canvas.stroke // 2))
    image = canvas.finish()
    return image, 128.0, max(42.0, cursor - 17.0 + 2.0)


def source_font() -> Path:
    if SOURCE_FONT_OVERRIDE is not None:
        return SOURCE_FONT_OVERRIDE
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Font sumber lokal untuk membangun asset tidak ditemukan.")


def category(token: str) -> str:
    if len(token) > 1:
        return "ligatures"
    if token.islower():
        return "lowercase"
    if token.isupper():
        return "uppercase"
    if token.isdigit():
        return "numbers"
    return "punctuation"


def safe_name(token: str) -> str:
    return "_".join(f"u{ord(char):04x}" for char in token)


def distort(mask: Image.Image, rng: random.Random, variant: int, token: str) -> Image.Image:
    # Persistent local deformation changes bowls, stems, and terminals—not only rotation.
    width, height = mask.size
    split = height // 2
    primary = token[0]
    shape_width = rng.uniform(0.93, 1.07)
    if primary in ROUND_CHARS:
        shape_width *= (0.97, 0.985, 1.0, 1.015, 1.03)[(variant - 1) % 5]
    elif primary in "imnlrt":
        shape_width *= (0.98, 0.99, 1.01, 1.02)[(variant - 1) % 4]
    inverse_width = 1 / shape_width
    mask = mask.transform(
        mask.size,
        Image.Transform.AFFINE,
        (inverse_width, 0, 22 * (1 - inverse_width), 0, 1, 0),
        Image.Resampling.BICUBIC,
    )
    top_shift = rng.randint(-3, 3)
    lower_shift = rng.randint(-2, 3)
    ascender_factor = rng.uniform(0.97, 1.03) if primary.lower() in ASCENDERS else rng.uniform(0.985, 1.015)
    descender_factor = rng.uniform(0.97, 1.035) if primary.lower() in DESCENDERS else rng.uniform(0.985, 1.015)
    upper = mask.crop((0, 0, width, split)).transform(
        (width, split), Image.Transform.AFFINE,
        (rng.uniform(0.96, 1.04), rng.uniform(-0.025, 0.025), top_shift, 0, ascender_factor, 0),
        Image.Resampling.BICUBIC,
    )
    lower = mask.crop((0, split, width, height)).transform(
        (width, height - split), Image.Transform.AFFINE,
        (rng.uniform(0.95, 1.05), rng.uniform(-0.018, 0.018), lower_shift, 0, descender_factor, 0),
        Image.Resampling.BICUBIC,
    )
    result = Image.new("L", mask.size, 0)
    result.paste(upper, (0, 0))
    result.paste(lower, (0, split + rng.randint(-1, 1)))
    if variant % 4 == 1:
        thickened = result.filter(ImageFilter.MaxFilter(3))
        result = Image.blend(result, thickened, 0.16)
    elif variant % 4 == 3:
        result = result.filter(ImageFilter.GaussianBlur(0.42))
    # Sparse pressure loss produces subtle ballpoint texture within the stroke.
    pixels = result.load()
    for _ in range(max(5, width * height // 900)):
        px, py = rng.randrange(width), rng.randrange(height)
        if pixels[px, py] > 80:
            pixels[px, py] = max(0, pixels[px, py] - rng.randint(12, 48))
    # Make terminals slightly irregular by softening a few outermost stroke pixels.
    bbox = result.getbbox()
    if bbox:
        pixels = result.load()
        for _ in range(3 + variant % 3):
            py = rng.randrange(max(0, bbox[1]), max(bbox[1] + 1, bbox[3]))
            for px in range(bbox[2] - 1, max(bbox[0], bbox[2] - 7), -1):
                if pixels[px, py] > 40:
                    pixels[px, py] = int(pixels[px, py] * rng.uniform(0.45, 0.82))
                    break
    return result


def make_variant(token: str, variant: int, font: ImageFont.FreeTypeFont) -> tuple[Image.Image, dict]:
    rng = random.Random(f"{STYLE_ID}:{token}:{variant}")
    # The production profile deliberately uses the Phase 2-compatible font-derived
    # construction: it keeps words cohesive. Stroke paths above remain available for
    # future isolated experiments, but are not mixed into the neat student profile.
    stroke_based = False
    if stroke_based:
        canvas, baseline, stroke_advance = make_stroke_variant(token, variant, rng)
        natural_advance = stroke_advance
    else:
        canvas = Image.new("L", (max(180, len(token) * 105 + 50), 170), 0)
        draw = ImageDraw.Draw(canvas)
        baseline = 125 + rng.randint(-2, 2)
        draw.text((22, baseline), token, font=font, fill=rng.randint(224, 247), anchor="ls")
        canvas = distort(canvas, rng, variant, token)
        natural_advance = font.getlength(token)
    bbox = canvas.getbbox() or (0, 0, 8, 8)
    padding = 6
    crop_box = (max(0, bbox[0] - padding), max(0, bbox[1] - padding), min(canvas.width, bbox[2] + padding), min(canvas.height, bbox[3] + padding))
    glyph = canvas.crop(crop_box)
    baseline_in_crop = baseline - crop_box[1] + rng.uniform(-1.2, 1.2)
    advance_range = (0.98, 1.025) if len(token) > 1 else (0.91, 0.98)
    advance = natural_advance * rng.uniform(*advance_range)
    upright_profile = STYLE_ID == "natural_student_upright_01"
    metadata = {
        "char": token,
        "variant": variant,
        "advance": round(advance, 3),
        "baseline": round(baseline_in_crop, 3),
        "natural_width": glyph.width,
        "natural_height": glyph.height,
        "left_bearing": round(rng.uniform(-0.8, 1.4), 3),
        "right_bearing": round(rng.uniform(-1.0, 1.5), 3),
        "preferred_scale": round(rng.uniform(0.96, 1.04) if token[:1].isupper() else rng.uniform(0.975, 1.025), 4),
        "rotation_bias": round(rng.uniform(-0.34, 0.34), 3),
        "stroke_weight": round(rng.uniform(0.97, 1.03), 4),
    }
    return glyph, metadata


def counts_for(token: str) -> int:
    if len(token) > 1:
        return 3
    if token in COMMON:
        return 8
    if token.islower():
        return 5
    if token.isupper() or token.isdigit():
        return 4
    return 3


def main() -> None:
    global OUT, STYLE_ID, STYLE_LABEL, SOURCE_FONT_OVERRIDE
    parser = argparse.ArgumentParser(description="Generate persistent handwriting glyph assets")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--style-id", default=STYLE_ID)
    parser.add_argument("--label", default=STYLE_LABEL)
    parser.add_argument("--font", type=Path, default=None)
    args = parser.parse_args()
    OUT = args.out if args.out.is_absolute() else ROOT / args.out
    STYLE_ID = args.style_id
    STYLE_LABEL = args.label
    SOURCE_FONT_OVERRIDE = args.font
    if OUT.exists():
        shutil.rmtree(OUT)
    for folder in ("lowercase", "uppercase", "numbers", "punctuation", "ligatures"):
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(str(source_font()), BASE_SIZE)
    upright_profile = STYLE_ID == "natural_student_upright_01"
    metadata = {
        "style_id": STYLE_ID,
        "label": STYLE_LABEL,
        "base_size": BASE_SIZE,
        "space_advance": round(font.getlength(" ") * 1.22, 3),
        "ligature_probability": 0.22 if upright_profile else 0.43,
        "ligature_probabilities": {
            "ng": 0.64, "ny": 0.56, "an": 0.52, "in": 0.49, "en": 0.44,
            "er": 0.43, "ar": 0.46, "ra": 0.42, "ri": 0.48, "si": 0.51,
            "ti": 0.50, "di": 0.55, "ke": 0.53, "me": 0.54, "pe": 0.49,
            "ber": 0.58, "ter": 0.56, "kan": 0.61, "yang": 0.52, "dan": 0.55,
        },
        "glyphs": {},
        "ligatures": {},
    }
    if upright_profile:
        # Contextual pair rules: common joins stay occasional, while pairs that
        # otherwise create sweeping cursive remain mostly separate.
        metadata["ligature_probabilities"] = {
            "ng": 0.28, "ny": 0.22, "an": 0.20, "in": 0.18, "en": 0.16,
            "er": 0.15, "ar": 0.16, "ra": 0.14, "ri": 0.16, "si": 0.18,
            "ti": 0.18, "di": 0.20, "ke": 0.18, "me": 0.18, "pe": 0.16,
            "ber": 0.22, "ter": 0.20, "kan": 0.24, "yang": 0.20, "dan": 0.22,
        }
    tokens = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" + PUNCTUATION)
    for token in tokens + LIGATURES:
        entries = []
        folder = category(token)
        for variant in range(1, counts_for(token) + 1):
            glyph, entry = make_variant(token, variant, font)
            relative = f"{folder}/{safe_name(token)}_{variant:02d}.png"
            glyph.save(OUT / relative, "PNG", optimize=True)
            entry["file"] = relative
            entries.append(entry)
        target = metadata["ligatures"] if len(token) > 1 else metadata["glyphs"]
        target[token] = entries
    (OUT / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {sum(len(v) for group in (metadata['glyphs'], metadata['ligatures']) for v in group.values())} variants in {OUT}")


if __name__ == "__main__":
    main()
