from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image
import pytest


ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / "assets" / "handwriting" / "authentic_student_handwriting_01"
OUT = ROOT / "outputs" / "school_notebook_reference_rebuild" / "phase14"
OUT_141 = ROOT / "outputs" / "school_notebook_reference_rebuild" / "phase14_1"
CONTRACT = ROOT / "assets" / "handwriting" / "natural_student_01" / "metadata.json"
PHASE11 = ROOT / "outputs" / "school_notebook_reference_rebuild" / "phase11" / "phase11_candidate_b_atlas"
UPPER75 = ROOT / "outputs" / "school_notebook_reference_rebuild" / "phase13_2" / "upper75_medium" / "atlas"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase14_production_atlas_is_complete_and_approved() -> None:
    metadata = json.loads((STYLE / "metadata.json").read_text(encoding="utf-8"))
    required = set(json.loads(CONTRACT.read_text(encoding="utf-8"))["glyphs"])
    assert metadata["phase14_status"] == "READY_FOR_DEPLOYMENT_REVIEW"
    assert metadata["coverage_status"] == "COMPLETE"
    assert set(metadata["glyphs"]) == required
    assert all(len(entries) == 2 for entries in metadata["glyphs"].values())
    assert metadata["uppercase_dimension_factor"] == 0.75
    assert metadata["digit_dimension_factor"] == 0.70
    assert metadata["large_punctuation_dimension_factor"] == 0.85
    assert metadata["font_size_by_template"] == {"books": 1.05, "folio": 1.05, "hvs": 1.05}


def test_phase11_hashes_and_upper75_assets_are_preserved() -> None:
    metadata = json.loads((STYLE / "metadata.json").read_text(encoding="utf-8"))
    upper_metadata = json.loads((UPPER75 / "metadata.json").read_text(encoding="utf-8"))
    for char in "aeimnorstu":
        for entry in metadata["glyphs"][char]:
            assert _sha(STYLE / entry["file"]) == _sha(PHASE11 / entry["file"])
    for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for entry in metadata["glyphs"][char]:
            assert _sha(STYLE / entry["file"]) == _sha(UPPER75 / entry["file"])
            with Image.open(STYLE / entry["file"]) as image:
                assert image.size == (entry["natural_width"], entry["natural_height"])


def test_phase14_enabled_and_menu_callback_available() -> None:
    from bot.keyboards.handwriting import handwriting_menu
    from config.settings import HANDWRITING_STYLES

    style = HANDWRITING_STYLES["authentic_student_handwriting_01"]
    assert style["enabled"] is True
    assert style["coverage_status"] == "COMPLETE"
    callbacks = [button.callback_data for row in handwriting_menu().inline_keyboard for button in row if button.callback_data]
    assert "handwriting:authentic_student_handwriting_01" in callbacks
    assert HANDWRITING_STYLES["natural_student_upright_01"]["label"] == "Rapih"


def test_phase14_1_alignment_is_style_specific_and_validated() -> None:
    from config.settings import HANDWRITING_STYLES

    assert HANDWRITING_STYLES["authentic_student_handwriting_01"]["vertical_alignment_by_book"] == {
        "book_buku_tulis_1": 15,
        "book_buku_tulis_3": 0,
        "book_buku_tulis_4": 5,
        "book_buku_tulis_6": 18,
        "book_kertas_folio_1": 11,
        "book_kertas_hvs": 10,
    }
    report = (OUT_141 / "phase14_1_per_template_alignment.md").read_text(encoding="utf-8")
    assert "Before status: `ALIGNMENT_PENDING_FIXES`" in report
    assert "After status: `ALIGNMENT_VALIDATED`" in report
    assert "OVERLAP" not in report.split("## After", 1)[1]
    parity = (OUT_141 / "phase14_1_telegram_rendering_parity.md").read_text(encoding="utf-8")
    assert parity.count("| `book_") == 6
    assert parity.count("| `True` |") == 6


def test_phase14_pipeline_and_telegram_reports_pass() -> None:
    validation = (OUT / "phase14_validation_report.md").read_text(encoding="utf-8")
    telegram = (OUT / "phase14_telegram_flow_report.md").read_text(encoding="utf-8")
    assert "Required coverage: `80/80`" in validation
    assert "Long multipage fallback: `[]`" in validation
    assert "Deterministic render: `True`" in validation
    assert "Menu callback present: `True`" in telegram


@pytest.mark.asyncio
async def test_phase14_style_selection_persists_and_can_switch_back(tmp_path) -> None:
    from database.db import Database
    from database.repository import UserRepository

    repo = UserRepository(Database(tmp_path / "phase14.db"))
    await repo.database.initialize()
    selected = await repo.update(1384091979, handwriting_style="authentic_student_handwriting_01")
    assert selected.handwriting_style == "authentic_student_handwriting_01"
    restored = await repo.update(1384091979, handwriting_style="natural_student_upright_01")
    assert restored.handwriting_style == "natural_student_upright_01"
