from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from renderer.glyph_assets import GlyphAssetLibrary, GlyphVariant, VariantSelector
from renderer.handwriting import load_font


PAIR_ADJUSTMENTS = {
    "ri": -1.8, "ra": -1.2, "ar": -1.0, "an": -0.8, "in": -0.7,
    "mm": 1.6, "nn": 0.8, "tt": -0.8, "ll": -0.7, "yo": -0.8,
    "di": -0.7, "ke": -0.5, "si": -0.6, "ng": -1.2, "ny": -1.0,
}

@dataclass(slots=True)
class RenderStats:
    variants: list[str] = field(default_factory=list)
    repeated_variants: int = 0
    word_spacings: list[float] = field(default_factory=list)
    baseline_offsets: list[float] = field(default_factory=list)
    rotations: list[float] = field(default_factory=list)
    scales: list[float] = field(default_factory=list)

    @staticmethod
    def _summary(values: list[float]) -> tuple[float, float]:
        if not values:
            return 0.0, 0.0
        return statistics.fmean(values), statistics.pstdev(values)

    def as_dict(self) -> dict[str, float | int]:
        spacing_mean, spacing_std = self._summary(self.word_spacings)
        baseline_mean, baseline_std = self._summary(self.baseline_offsets)
        rotation_mean, rotation_std = self._summary(self.rotations)
        scale_mean, scale_std = self._summary(self.scales)
        return {
            "glyph_variant_count": len(set(self.variants)),
            "glyph_occurrences": len(self.variants),
            "repeated_variant_rate": self.repeated_variants / max(1, len(self.variants)),
            "average_word_spacing": spacing_mean,
            "word_spacing_stddev": spacing_std,
            "average_baseline_offset": baseline_mean,
            "baseline_stddev": baseline_std,
            "rotation_mean": rotation_mean,
            "rotation_stddev": rotation_std,
            "scale_mean": scale_mean,
            "scale_stddev": scale_std,
        }


class MultiGlyphHandwritingRenderer:
    """Raster multi-glyph renderer tuned for natural, legible student handwriting."""

    def __init__(self, style_dir: Path, font_size: int, color: tuple[int, int, int], seed: int | None = None, variation_level: float = 0.10, slant_factor: float = 1.0, rotation_jitter: float = 0.14, advance_factor: float = 1.0, word_spacing_factor: float = 1.0) -> None:
        self.library = GlyphAssetLibrary(style_dir)
        self.font_size = font_size
        self.color = color
        self.random = random.Random(seed)
        self.variation_level = max(0.05, min(0.15, variation_level))
        self.variation_factor = self.variation_level / 0.10
        self.slant_factor = max(0.0, slant_factor)
        self.rotation_jitter = max(0.0, rotation_jitter)
        self.advance_factor = max(0.80, min(1.10, advance_factor))
        # Word spacing is independent from non-space glyph advances.  Existing
        # styles omit this key and therefore retain the exact historical value.
        self.word_spacing_factor = max(0.75, min(2.0, word_spacing_factor))
        self.selector = VariantSelector(self.random)
        self.scale = font_size / self.library.base_size
        self._fallback_font = load_font(None, font_size)
        self._tint_cache: dict[tuple[str, tuple[int, int, int]], Image.Image] = {}
        self.stats = RenderStats()
        self.base_slant = self.random.uniform(-0.12, 0.20) * self.slant_factor
        self._previous_variant: dict[str, int] = {}

    def _average_advance(self, token: str) -> float:
        variants = self.library.variants_for(token)
        if not variants:
            return self._fallback_font.getlength(token)
        return sum(item.advance for item in variants) / len(variants) * self.scale * self.advance_factor

    def measure(self, text: str) -> float:
        width = 0.0
        previous = ""
        for char in text:
            if char.isspace():
                width += self.library.space_advance * self.scale * self.word_spacing_factor
            else:
                width += self._average_advance(char)
                width += PAIR_ADJUSTMENTS.get(previous + char, 0.0) * self.scale
            previous = char
        # Advances already include the asset's real glyph metrics, pair
        # adjustments, and scaled word spacing.  A large blanket allowance
        # caused premature wraps; retain only a small rasterisation safety
        # margin for rotation/anti-aliasing at the right edge.
        return width * 1.006

    def baseline_series(self, length: int) -> list[float]:
        """Smooth correlated drift; exposed for deterministic behavioral tests."""
        value = 0.0
        velocity = self.random.uniform(-0.06, 0.06) * self.variation_factor
        result: list[float] = []
        for _ in range(length):
            velocity = velocity * 0.84 + self.random.uniform(-0.055, 0.055) * self.variation_factor
            value = max(-1.05 * self.variation_factor, min(1.05 * self.variation_factor, value + velocity))
            result.append(value)
        return result

    def _word_position(self, text: str, start: int, length: int) -> str:
        before = start == 0 or not text[start - 1].isalnum()
        after_index = start + length
        after = after_index >= len(text) or not text[after_index].isalnum()
        if before:
            return "start"
        if after:
            return "end"
        return "middle"

    def tokenize(self, text: str, enable_ligatures: bool = True) -> list[str]:
        tokens: list[str] = []
        candidates = sorted(self.library.ligatures, key=len, reverse=True)
        index = 0
        while index < len(text):
            matched = None
            if enable_ligatures and text[index].isalnum():
                for candidate in candidates:
                    end = index + len(candidate)
                    if text.startswith(candidate, index) and end <= len(text):
                        within_word = (index == 0 or text[index - 1].isalpha()) and (end == len(text) or text[end].isalpha())
                        chance = self.library.ligature_probabilities.get(candidate, self.library.ligature_probability)
                        if within_word and self.random.random() < chance:
                            matched = candidate
                            break
            token = matched or text[index]
            tokens.append(token)
            index += len(token)
        return tokens

    def _tinted(self, variant: GlyphVariant) -> Image.Image:
        key = (variant.file, self.color)
        cached = self._tint_cache.get(key)
        if cached is not None:
            return cached
        mask = self.library.image_for(variant)
        mask = self._polish_mask(mask, variant)
        # A fractionally softened edge resembles ballpoint ink absorbed by paper.
        mask = mask.filter(ImageFilter.GaussianBlur(0.28))
        rgba = Image.new("RGBA", mask.size, (*self.color, 0))
        rgba.putalpha(mask)
        self._tint_cache[key] = rgba
        return rgba

    @staticmethod
    def _polish_mask(mask: Image.Image, variant: GlyphVariant) -> Image.Image:
        """Add tiny, deterministic pen-form details without changing glyph metrics.

        The production assets already provide the neat_90 silhouette. These marks are
        deliberately faint and confined to existing terminals/shoulders so they read
        as pen movement differences after downscaling, rather than texture or noise.
        """
        token = variant.char.lower()
        if token not in {"a", "n", "m", "r", "e", "s", "t", "i", "u", "k", "g", "l", "o", "j"}:
            return mask
        bbox = mask.getbbox()
        if not bbox:
            return mask
        polished = mask.copy()
        draw = ImageDraw.Draw(polished)
        left, top, right, bottom = bbox
        width = max(1, right - left)
        height = max(1, bottom - top)
        # Only every other asset gets the alternate pen gesture; all coordinates
        # stay inside the glyph's ink bounds and use low alpha (subpixel after scale).
        if variant.variant % 2 == 0:
            ink = 72
            if token in {"a", "e", "o", "g"}:
                y = top + max(1, round(height * 0.48))
                x0 = left + max(1, round(width * 0.66))
                draw.line((x0, y, min(right - 1, x0 + max(1, round(width * 0.06))), y), fill=ink, width=1)
            elif token in {"n", "m", "u"}:
                y = top + max(1, round(height * 0.28))
                x = left + max(1, round(width * 0.45))
                draw.point((x, y), fill=ink)
            elif token == "r":
                y = top + max(1, round(height * 0.30))
                x0 = left + max(1, round(width * 0.52))
                draw.line((x0, y, min(right - 1, x0 + max(1, round(width * 0.05))), y - 1), fill=ink, width=1)
            elif token == "t":
                y = top + max(1, round(height * 0.31))
                x = left + max(1, round(width * 0.38))
                draw.point((x, y), fill=ink)
            elif token in {"i", "j"}:
                y = top + max(1, round(height * 0.16))
                x = left + max(1, round(width * 0.54))
                draw.point((x, y), fill=ink)
            elif token in {"s", "k", "l"}:
                y = top + max(1, round(height * 0.62))
                x = left + max(1, round(width * 0.62))
                draw.point((x, y), fill=ink)
        return polished

    @staticmethod
    def _vary_stroke(glyph: Image.Image, factor: float) -> Image.Image:
        if abs(factor - 1.0) < 0.006:
            return glyph
        alpha = glyph.getchannel("A")
        if factor > 1:
            altered = alpha.filter(ImageFilter.MaxFilter(3))
        else:
            altered = alpha.filter(ImageFilter.MinFilter(3))
        amount = min(0.16, abs(factor - 1.0) * 2.3)
        alpha = Image.blend(alpha, altered, amount)
        result = glyph.copy()
        result.putalpha(alpha)
        return result

    def _fallback(self, token: str) -> tuple[Image.Image, float, float]:
        bbox = self._fallback_font.getbbox(token)
        width = max(4, bbox[2] - bbox[0] + 8)
        height = max(4, bbox[3] - bbox[1] + 8)
        mask = Image.new("L", (width, height), 0)
        from PIL import ImageDraw
        ImageDraw.Draw(mask).text((4 - bbox[0], 4 - bbox[1]), token, font=self._fallback_font, fill=238)
        rgba = Image.new("RGBA", mask.size, (*self.color, 0))
        rgba.putalpha(mask.filter(ImageFilter.GaussianBlur(0.22)))
        return rgba, float(self._fallback_font.getlength(token)), height * 0.84

    def render_line(self, image: Image.Image, text: str, x: int, y: int, optimized: bool = False, baseline_slope: float = 0.0) -> None:
        if not text:
            return
        tokens = self.tokenize(text, enable_ligatures=not optimized)
        drifts = self.baseline_series(len(tokens))
        line_scale = 1.0 + self.random.uniform(-0.015, 0.015) * self.variation_factor
        line_offset = self.random.uniform(-0.45, 0.45) * self.variation_factor
        cursor = float(x) + self.random.uniform(-0.8, 0.9) * self.variation_factor
        previous = ""
        word_scale = max(0.97, min(1.03, line_scale + self.random.uniform(-0.008, 0.008)))
        word_baseline = self.random.uniform(-0.4, 0.4) * self.variation_factor
        word_slant = self.random.uniform(-0.08, 0.08) * self.variation_factor * self.slant_factor
        word_shear = self.random.uniform(-0.006, 0.006) * self.variation_factor
        word_pressure = 1.0 + self.random.uniform(-0.025, 0.025) * self.variation_factor
        word_spacing_factor = 1.0 + self.random.uniform(-0.02, 0.02) * self.variation_factor
        spacing_velocity = self.random.uniform(-0.006, 0.006) * self.variation_factor
        baseline_origin = y + self.font_size * 1.18 + line_offset
        for index, token in enumerate(tokens):
            if token.isspace():
                spacing_velocity = spacing_velocity * 0.68 + self.random.uniform(-0.009, 0.009) * self.variation_factor
                spacing_limit = 0.04 * self.variation_factor
                word_spacing_factor = max(1.0 - spacing_limit, min(1.0 + spacing_limit, word_spacing_factor + spacing_velocity))
                if self.random.random() < 0.06 * self.variation_factor:
                    word_spacing_factor = max(1.0 - spacing_limit, min(1.0 + spacing_limit, word_spacing_factor + self.random.choice((-0.018, 0.02)) * self.variation_factor))
                ligature_release = 1.045 if len(previous) > 1 else 1.0
                spacing = self.library.space_advance * self.scale * self.word_spacing_factor * self.advance_factor * word_spacing_factor * ligature_release
                cursor += spacing
                self.stats.word_spacings.append(spacing)
                word_scale = max(0.97, min(1.03, word_scale * 0.68 + line_scale * 0.32 + self.random.uniform(-0.009, 0.009) * self.variation_factor))
                word_baseline = max(-0.55 * self.variation_factor, min(0.55 * self.variation_factor, word_baseline * 0.72 + self.random.uniform(-0.22, 0.22) * self.variation_factor))
                word_slant = max(-0.16 * self.variation_factor, min(0.16 * self.variation_factor, word_slant * 0.72 + self.random.uniform(-0.08, 0.08) * self.variation_factor))
                word_shear = max(-0.012 * self.variation_factor, min(0.012 * self.variation_factor, word_shear * 0.72 + self.random.uniform(-0.005, 0.005) * self.variation_factor))
                word_pressure = max(0.96, min(1.04, word_pressure * 0.65 + (0.35 + self.random.uniform(-0.01, 0.01) * self.variation_factor)))
                previous = token
                continue
            position = self._word_position(text, sum(map(len, tokens[:index])), len(token))
            variants = self.library.variants_for(token)
            selected = self.selector.choose(token, variants, position, previous[-1:] if previous else "")
            if selected is None:
                glyph, advance, glyph_baseline = self._fallback(token)
                local_scale = 1.0
                rotation = self.base_slant + word_slant + self.random.uniform(-self.rotation_jitter, self.rotation_jitter) * self.variation_factor
                left_bearing = 0.0
                right_bearing = 0.0
                stroke_factor = word_pressure
            else:
                glyph = self._tinted(selected)
                advance = selected.advance * self.scale * self.advance_factor
                glyph_baseline = selected.baseline
                capital_scale = (1.0 + self.random.uniform(-0.015, 0.025) * self.variation_factor) if token[:1].isupper() else 1.0
                variant_scale = 1.0 + (selected.preferred_scale - 1.0) * self.variation_factor
                local_scale = self.scale * variant_scale * word_scale * capital_scale * (1 + self.random.uniform(-0.008, 0.008) * self.variation_factor)
                rotation = self.base_slant + word_slant + selected.rotation_bias * 0.45 * self.variation_factor * self.slant_factor + self.random.uniform(-self.rotation_jitter, self.rotation_jitter) * self.variation_factor
                left_bearing = selected.left_bearing * self.scale
                right_bearing = selected.right_bearing * self.scale
                stroke_factor = 1.0 + (selected.stroke_weight - 1.0) * self.variation_factor
                stroke_factor *= word_pressure
                variant_key = f"{token}:{selected.variant}"
                self.stats.variants.append(variant_key)
                if self._previous_variant.get(token) == selected.variant:
                    self.stats.repeated_variants += 1
                self._previous_variant[token] = selected.variant
                glyph = self._vary_stroke(glyph, stroke_factor)
            if selected is not None:
                target = (max(1, round(glyph.width * local_scale)), max(1, round(glyph.height * local_scale)))
                glyph = glyph.resize(target, Image.Resampling.LANCZOS)
                glyph_baseline *= local_scale
            glyph_shear = word_shear + self.random.uniform(-0.0025, 0.0025) * self.variation_factor
            if abs(glyph_shear) > 0.002:
                extra_width = max(2, round(abs(glyph_shear) * glyph.height) + 1)
                glyph = glyph.transform(
                    (glyph.width + extra_width, glyph.height),
                    Image.Transform.AFFINE,
                    (1, -glyph_shear, max(0.0, glyph_shear * glyph.height), 0, 1, 0),
                    Image.Resampling.BICUBIC,
                )
            alpha_factor = self.random.uniform(0.95, 0.975) if self.random.random() < 0.08 * self.variation_factor else self.random.uniform(0.975, 1.0)
            if alpha_factor < 0.998:
                alpha = glyph.getchannel("A")
                alpha = ImageEnhance.Brightness(alpha).enhance(alpha_factor)
                glyph = glyph.copy()
                glyph.putalpha(alpha)
            unrotated_height = glyph.height
            glyph = glyph.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)
            rotation_padding = (glyph.height - unrotated_height) / 2
            px = round(cursor + left_bearing + self.random.uniform(-0.14, 0.14) * self.variation_factor)
            local_noise = self.random.uniform(-0.23, 0.23) * self.variation_factor
            if self.random.random() < 0.05 * self.variation_factor:
                local_noise += self.random.uniform(-0.35, 0.35) * self.variation_factor
            baseline_offset = drifts[index] + word_baseline + local_noise
            # A photographed ruled page can be perspectively tilted. Apply only
            # the template's calibrated line slope; glyph assets remain unchanged.
            baseline_y = baseline_origin + baseline_slope * (cursor - float(x))
            py = round(baseline_y + baseline_offset - glyph_baseline - rotation_padding - 2.5)
            image.alpha_composite(glyph, (px, py))
            pair = (previous[-1:] if previous else "") + token[:1]
            cursor += advance + right_bearing + PAIR_ADJUSTMENTS.get(pair, 0.0) * self.scale + self.random.uniform(-0.16, 0.18) * self.variation_factor
            self.stats.baseline_offsets.append(baseline_offset + line_offset)
            self.stats.rotations.append(rotation)
            self.stats.scales.append(local_scale)
            previous = token

    def debug_stats(self) -> dict[str, float | int]:
        return self.stats.as_dict()
