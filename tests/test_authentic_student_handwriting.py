from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / "assets" / "handwriting" / "authentic_student_handwriting_01"
SOURCE = ROOT / "outputs" / "school_notebook_reference_rebuild" / "phase11" / "phase11_candidate_b_atlas"
CONTRACT = ROOT / "assets" / "handwriting" / "natural_student_01" / "metadata.json"


def test_approved_atlas_preserves_candidate_b_pngs_and_variants() -> None:
    metadata = json.loads((STYLE / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["style_id"] == "authentic_student_handwriting_01"
    assert metadata["approved_candidate"].startswith("Phase 17.3")
    assert metadata["phase11_baseline_font_scale"] == 1.5
    assert metadata["font_size_factor"] == 0.70
    assert metadata["font_size_by_template"] == {"books": 1.05, "folio": 1.05, "hvs": 1.05}
    assert metadata["non_space_advance_factor"] == 0.95
    assert metadata["word_spacing_factor"] == 1.5
    assert metadata["space_advance_unchanged"] is True
    required = set(json.loads(CONTRACT.read_text(encoding="utf-8"))["glyphs"])
    assert set(metadata["glyphs"]) == required
    assert all(len(variants) == 2 for variants in metadata["glyphs"].values())
    for char, variants in metadata["glyphs"].items():
        for entry in variants:
            permanent = STYLE / entry["file"]
            assert permanent.exists()
            assert Image.open(permanent).size == (entry["natural_width"], entry["natural_height"])
            if char in "aeimnorstu":
                source = SOURCE / entry["file"]
                assert hashlib.sha256(permanent.read_bytes()).digest() == hashlib.sha256(source.read_bytes()).digest()


def test_complete_atlas_is_enabled_after_phase14_validation() -> None:
    from config.settings import HANDWRITING_STYLES

    style = HANDWRITING_STYLES["authentic_student_handwriting_01"]
    assert style["enabled"] is True
    assert style["coverage_status"] == "COMPLETE"
    assert style["missing_characters"] == ""


def test_production_service_renders_complete_style_without_fallback_error() -> None:
    from database.models import UserPreferences
    from services.generation_service import GenerationService

    preferences = UserPreferences(
        telegram_user_id=1,
        handwriting_style="authentic_student_handwriting_01",
        show_date=False,
        date_mode="none",
    )
    result = GenerationService(ROOT / "assets").render(
        "Mahasiswa 0123456789 menulis A-Z, punctuation: .,:;!?()-/'\"%+=&@#",
        preferences,
        seed=7,
    )
    assert result.pages
