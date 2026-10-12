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


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    database_path: Path = field(default_factory=lambda: _path("DATABASE_PATH", "data/bot.db"))
    output_dir: Path = field(default_factory=lambda: _path("OUTPUT_DIR", "outputs"))
    assets_dir: Path = ROOT_DIR / "assets"
    max_text_length: int = field(default_factory=lambda: int(os.getenv("MAX_TEXT_LENGTH", "15000")))
    max_output_bytes: int = field(default_factory=lambda: int(os.getenv("MAX_OUTPUT_BYTES", "50000000")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

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
    "natural_student_01": {"label": "Natural Student", "engine": "multi_glyph"},
    "natural_student_neat_01": {"label": "Natural Student Neat", "engine": "multi_glyph", "asset_style": "natural_student_01"},
    # Locked production profile: neat_90 geometry with only local glyph polish.
    "natural_student_neat_90": {"label": "Natural Student", "engine": "multi_glyph", "asset_style": "natural_student_01", "variation_level": 0.10},
    "natural_student_upright_01": {
        "label": "Natural Student Upright",
        "engine": "multi_glyph",
        "asset_style": "natural_student_upright_01",
        "variation_level": 0.10,
        "slant_factor": 0.22,
        "rotation_jitter": 0.05,
        "advance_factor": 1.0,
    },
    "neat": {"label": "Rapi", "rotation": 0.8, "x_jitter": 0.5, "y_jitter": 0.8, "scale": 0.025},
    "semi_neat": {"label": "Semi Rapi", "rotation": 1.3, "x_jitter": 1.0, "y_jitter": 1.5, "scale": 0.035},
    "student": {"label": "Mahasiswa", "rotation": 1.8, "x_jitter": 1.4, "y_jitter": 2.2, "scale": 0.045},
    "slanted": {"label": "Miring", "rotation": 1.2, "x_jitter": 0.9, "y_jitter": 1.4, "scale": 0.03, "slant": 0.18},
    "messy": {"label": "Agak Berantakan", "rotation": 2.0, "x_jitter": 2.0, "y_jitter": 3.0, "scale": 0.055},
}
