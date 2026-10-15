from __future__ import annotations

import random
from pathlib import Path

from PIL import Image

from database.models import UserPreferences
from renderer.glyph_assets import GlyphAssetLibrary, VariantSelector
from renderer.multiglyph import MultiGlyphHandwritingRenderer
from services.generation_service import GenerationService


STYLE = Path(__file__).resolve().parents[1] / "assets" / "handwriting" / "natural_student_01"


def renderer(seed: int = 12) -> MultiGlyphHandwritingRenderer:
    return MultiGlyphHandwritingRenderer(STYLE, 54, (24, 58, 135), seed)


def render_bytes(seed: int) -> bytes:
    image = Image.new("RGBA", (1000, 180), "white")
    renderer(seed).render_line(image, "Mahasiswa menulis dengan natural 2026!", 20, 30)
    return image.tobytes()


def test_asset_variant_targets() -> None:
    library = GlyphAssetLibrary(STYLE)
    assert len(library.glyphs["a"]) >= 8
    assert len(library.glyphs["z"]) >= 5
    assert len(library.glyphs["A"]) >= 4
    assert len(library.glyphs["7"]) >= 4
    assert library.variant_count >= 400
    for char in "aeinrstumkoldghpy":
        assert len({library.image_for(item).tobytes() for item in library.glyphs[char]}) >= 4


def test_variant_selection_avoids_recent_repeats() -> None:
    library = GlyphAssetLibrary(STYLE)
    selector = VariantSelector(random.Random(9), history_size=4)
    selected = [selector.choose("a", library.glyphs["a"]).variant for _ in range(40)]
    assert all(left != right for left, right in zip(selected, selected[1:]))
    recent_repeat_rate = sum(value in selected[max(0, index - 4):index] for index, value in enumerate(selected)) / len(selected)
    assert recent_repeat_rate < 0.15


def test_seed_is_deterministic_and_changes_output() -> None:
    assert render_bytes(77) == render_bytes(77)
    assert render_bytes(77) != render_bytes(78)


def test_missing_ligature_and_glyph_fallback_are_graceful() -> None:
    writer = renderer()
    assert writer.tokenize("zz", enable_ligatures=True) == ["z", "z"]
    image = Image.new("RGBA", (500, 180), "white")
    writer.render_line(image, "fallback: é — ✓", 10, 20)
    assert image.getbbox() is not None


def test_ligature_can_be_disabled() -> None:
    writer = renderer()
    assert writer.tokenize("yang dan", enable_ligatures=False) == list("yang dan")


def test_baseline_drift_is_smooth_and_bounded() -> None:
    first = renderer(42).baseline_series(80)
    second = renderer(42).baseline_series(80)
    assert first == second
    assert max(map(abs, first)) <= 2.2
    assert max(abs(b - a) for a, b in zip(first, first[1:])) < 0.35


def test_objective_debug_stats_are_available() -> None:
    writer = renderer(101)
    image = Image.new("RGBA", (1000, 180), "white")
    writer.render_line(image, "Mahasiswa menulis kalimat natural dengan pulpen.", 20, 30)
    stats = writer.debug_stats()
    assert stats["glyph_variant_count"] > 10
    assert stats["average_word_spacing"] > 0
    assert stats["baseline_stddev"] > 0
    assert stats["rotation_stddev"] > 0


def test_word_spacing_factor_changes_spaces_only() -> None:
    base = MultiGlyphHandwritingRenderer(STYLE, 54, (24, 58, 135), 12, word_spacing_factor=1.0)
    wide = MultiGlyphHandwritingRenderer(STYLE, 54, (24, 58, 135), 12, word_spacing_factor=1.5)
    assert wide.measure("ab") == base.measure("ab")
    assert wide.measure("a b") > base.measure("a b")


def test_natural_style_keeps_multi_page_rendering() -> None:
    service = GenerationService(STYLE.parents[1])
    text = "\n".join(f"Baris pengujian halaman nomor {index}." for index in range(80))
    result = service.render(text, UserPreferences(telegram_user_id=1), seed=44)
    assert len(result.pages) >= 3
    assert result.debug_stats is not None
