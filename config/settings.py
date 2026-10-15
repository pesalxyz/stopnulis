from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[1]


def _path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else ROOT_DIR / value


def _optional_int(name: str) -> int | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} harus berupa angka Telegram user ID.") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    database_path: Path = field(default_factory=lambda: _path("DATABASE_PATH", "data/bot.db"))
    output_dir: Path = field(default_factory=lambda: _path("OUTPUT_DIR", "outputs"))
    assets_dir: Path = ROOT_DIR / "assets"
    max_text_length: int = field(default_factory=lambda: int(os.getenv("MAX_TEXT_LENGTH", "15000")))
    max_output_bytes: int = field(default_factory=lambda: int(os.getenv("MAX_OUTPUT_BYTES", "50000000")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    admin_telegram_id: int | None = field(default_factory=lambda: _optional_int("ADMIN_TELEGRAM_ID"))

    def prepare(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.assets_dir / "papers" / "custom").mkdir(parents=True, exist_ok=True)


INK_COLORS: dict[str, tuple[int, int, int]] = {
    "blue": (24, 58, 135),
    "black": (32, 32, 35),
    "red": (150, 35, 40),
    "purple": (85, 45, 125),
}

HANDWRITING_STYLES = {
    "natural_student_01": {
        "label": "Agak Berantakan",
        "engine": "multi_glyph",
        "asset_style": "natural_student_01",
    },
    "natural_student_upright_01": {
        "label": "Rapih",
        "engine": "multi_glyph",
        "asset_style": "natural_student_upright_01",
        "variation_level": 0.10,
        "slant_factor": 0.22,
        "rotation_jitter": 0.05,
        "advance_factor": 1.0,
    },
    "school_notebook_01": {
        "label": "Tulisan Screenshot",
        "engine": "multi_glyph",
        "asset_style": "natural_student_upright_01",
        # Compact, thin school-notebook proportions based on the supplied
        # reference sample; this is an approximation, not a traced font.
        "font_scale": 0.82,
        # Experimental reference match: subtle variation only; activation is
        # intentionally kept out of the Telegram menu until visual approval.
        "variation_level": 0.10,
        "slant_factor": 0.22,
        "rotation_jitter": 0.05,
        "advance_factor": 0.98,
    },
    "school_notebook_reference_rebuild_01": {
        "label": "Tulisan Screenshot — Reference Rebuild",
        "engine": "multi_glyph",
        # Rollback baseline: use the last readable atlas while the isolated
        # eight-glyph redesign is reviewed separately.
        "asset_style": "natural_student_upright_01",
        "font_scale": 0.82,
        "variation_level": 0.10,
        "slant_factor": 0.22,
        "rotation_jitter": 0.05,
        "advance_factor": 0.98,
    },
    "authentic_student_handwriting_01": {
        "label": "Authentic Student Handwriting",
        "engine": "multi_glyph",
        "asset_style": "authentic_student_handwriting_01",
        # Phase 17.3 final spacing: books use 70%; Folio/HVS remain at 70%.
        "phase11_baseline_font_scale": 1.50,
        "font_scale": 1.05,
        "approved_phase": "Phase 17.3 final (70% books / 95% characters / 150% word spacing)",
        "font_scale_by_book": {
            # All currently registered notebook/book templates use 70%.
            "book_buku_tulis_1": 1.05,
            "book_buku_tulis_3": 1.05,
            "book_buku_tulis_4": 1.05,
            "book_buku_tulis_6": 1.05,
            # Folio and HVS use the approved 70% size.
            "book_kertas_folio_1": 1.05,
            "book_kertas_hvs": 1.05,
        },
        # Body-only upward corrections measured from final alpha pixels
        # against each template's local ruling/virtual baseline. Positive
        # values move this style's glyph ink upward; other styles are
        # unaffected because they do not define this map.
        "vertical_alignment_by_book": {
            "book_buku_tulis_1": 15,
            "book_buku_tulis_3": 0,
            "book_buku_tulis_4": 5,
            "book_buku_tulis_6": 18,
            "book_kertas_folio_1": 11,
            "book_kertas_hvs": 10,
        },
        "variation_level": 0.10,
        "slant_factor": 0.35,
        "rotation_jitter": 0.08,
        "advance_factor": 1.0,
        "word_spacing_factor": 1.50,
        "enabled": True,
        "menu_enabled": True,
        "coverage_status": "COMPLETE",
        "missing_characters": "",
    },
}
