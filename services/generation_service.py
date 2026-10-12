from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image

from config.settings import HANDWRITING_STYLES, INK_COLORS
from database.models import UserPreferences
from renderer.handwriting import HandwritingRenderer, Variation
from renderer.layout import paginate_text
from renderer.multiglyph import MultiGlyphHandwritingRenderer
from renderer.paper import add_header, load_paper


@dataclass(slots=True)
class RenderResult:
    pages: list[Image.Image]
    text_hash: str
    debug_stats: dict[str, float | int] | None = None


class GenerationService:
    MAX_PAGES = 4
    def __init__(self, assets_dir: Path, max_text_length: int = 15000) -> None:
        self.assets_dir = assets_dir
        self.max_text_length = max_text_length

    def render(self, text: str, preferences: UserPreferences, seed: int | None = None, preview_only: bool = False, variation_level: float | None = None, text_only: bool = False) -> RenderResult:
        # Keep the raw Telegram payload: indentation, repeated spaces,
        # explicit newlines, and trailing line breaks are meaningful layout
        # input. Reject only an actually empty/whitespace-only document.
        if not text or not text.strip():
            raise ValueError("Teks tidak boleh kosong.")
        if len(text) > self.max_text_length:
            raise ValueError(f"Teks terlalu panjang. Maksimal {self.max_text_length:,} karakter.")
        style_id = preferences.handwriting_style
        style = HANDWRITING_STYLES.get(style_id, HANDWRITING_STYLES["natural_student_upright_01"])
        font_path = self.assets_dir / "fonts" / f"{style_id}.ttf"
        if not font_path.exists():
            font_path = None
        color = INK_COLORS.get(preferences.ink_color, INK_COLORS["blue"])
        base, layout = load_paper(preferences.book_style, self.assets_dir / "papers", self.assets_dir.parent / "menu_buku")
        if style.get("engine") == "multi_glyph":
            asset_style = style.get("asset_style", style_id)
            profile_level = float(style.get("variation_level", 0.10))
            writer = MultiGlyphHandwritingRenderer(
                self.assets_dir / "handwriting" / asset_style,
                round(54 * layout.handwriting_scale * layout.body_scale_adjust),
                color,
                seed,
                profile_level if variation_level is None else variation_level,
                float(style.get("slant_factor", 1.0)),
                float(style.get("rotation_jitter", 0.14)),
                float(style.get("advance_factor", 1.0)),
            )
        else:
            variation = Variation(**{key: value for key, value in style.items() if key not in {"label", "engine"}})
            writer = HandwritingRenderer(font_path, round(54 * layout.handwriting_scale * layout.body_scale_adjust), color, variation, seed)
        positioned_pages = paginate_text(text, base.width, base.height, layout, writer.measure)
        if len(positioned_pages) > self.MAX_PAGES:
            raise ValueError(
                f"Teks melebihi kapasitas maksimal {self.MAX_PAGES} halaman "
                f"(terdeteksi {len(positioned_pages)} halaman). Silakan perpendek teks "
                "atau bagi menjadi beberapa permintaan."
            )
        date_text = self._date_text(preferences)
        pages: list[Image.Image] = []
        optimized = len(text) > 6000
        render_pages = positioned_pages[:1] if preview_only else positioned_pages
        for page_index, lines in enumerate(render_pages):
            page = Image.new("RGBA", base.size, (0, 0, 0, 0)) if text_only else base.copy()
            for line in lines:
                writer.render_line(page, line.text, line.x, line.y, optimized=optimized, baseline_slope=line.baseline_slope)
            # Render the identity after the body so the body consumes exactly
            # the same deterministic handwriting sequence as before. The
            # header still uses the same active writer/style, but cannot alter
            # glyph variants or spacing in the production body.
            if not text_only and page_index == 0:
                add_header(page, preferences, date_text, font_path, layout, writer)
            pages.append(page)
        debug_stats = writer.debug_stats() if hasattr(writer, "debug_stats") else None
        return RenderResult(pages, hashlib.sha256(text.encode("utf-8")).hexdigest(), debug_stats)

    @staticmethod
    def _date_text(preferences: UserPreferences) -> str | None:
        if not preferences.show_date or preferences.date_mode == "none":
            return None
        if preferences.date_mode == "custom":
            return preferences.custom_date
        return datetime.now().strftime("%d-%m-%Y")
