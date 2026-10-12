from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass(frozen=True, slots=True)
class GlyphVariant:
    char: str
    variant: int
    file: str
    advance: float
    baseline: float
    natural_width: int
    natural_height: int
    left_bearing: float
    right_bearing: float
    preferred_scale: float
    rotation_bias: float
    stroke_weight: float


class GlyphAssetLibrary:
    """Loads persistent handwritten glyph variants and keeps raster data cached."""

    def __init__(self, style_dir: Path) -> None:
        metadata_path = style_dir / "metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Asset handwriting tidak ditemukan: {style_dir.name}")
        self.style_dir = style_dir
        self.metadata: dict[str, Any] = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.base_size = int(self.metadata["base_size"])
        self.space_advance = float(self.metadata["space_advance"])
        self.ligature_probability = float(self.metadata.get("ligature_probability", 0.42))
        self.ligature_probabilities: dict[str, float] = self.metadata.get("ligature_probabilities", {})
        self.glyphs = self._decode_group(self.metadata["glyphs"])
        self.ligatures = self._decode_group(self.metadata.get("ligatures", {}))
        self._image_cache: dict[str, Image.Image] = {}

    @staticmethod
    def _decode_group(raw: dict[str, list[dict[str, Any]]]) -> dict[str, list[GlyphVariant]]:
        return {token: [GlyphVariant(**entry) for entry in entries] for token, entries in raw.items()}

    def variants_for(self, token: str) -> list[GlyphVariant]:
        return self.ligatures.get(token) or self.glyphs.get(token, [])

    def image_for(self, variant: GlyphVariant) -> Image.Image:
        image = self._image_cache.get(variant.file)
        if image is None:
            image = Image.open(self.style_dir / variant.file).convert("L")
            self._image_cache[variant.file] = image
        return image

    @property
    def variant_count(self) -> int:
        return sum(map(len, self.glyphs.values())) + sum(map(len, self.ligatures.values()))


class VariantSelector:
    """Controlled-random selector with per-token anti-repetition and context bias."""

    def __init__(self, random_source, history_size: int = 4) -> None:
        self.random = random_source
        self.history_size = history_size
        self.recent: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=history_size))

    def choose(self, token: str, variants: list[GlyphVariant], position: str = "middle", previous: str = "") -> GlyphVariant | None:
        if not variants:
            return None
        history = list(self.recent[token])
        # Recent variants remain possible but are heavily downweighted. The most recent
        # variant is excluded when alternatives exist, eliminating obvious doubles.
        pool = [item for item in variants if item.variant != (history[-1] if history else -1)] or variants
        offset = (1 if position == "start" else 2 if position == "end" else 0) + (1 if previous in "bdhklt" else 0)
        weights = []
        for item in pool:
            recency_penalty = 1.0
            if item.variant in history:
                age = len(history) - history.index(item.variant)
                recency_penalty = 0.10 + age * 0.05
            context_boost = 1.22 if (item.variant + offset) % 3 == 0 else 1.0
            weights.append(recency_penalty * context_boost)
        selected = self.random.choices(pool, weights=weights, k=1)[0]
        self.recent[token].append(selected.variant)
        return selected
