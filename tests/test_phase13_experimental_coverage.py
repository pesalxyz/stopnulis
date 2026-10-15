from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PHASE13 = ROOT / "outputs" / "school_notebook_reference_rebuild" / "phase13"
ATLAS = PHASE13 / "phase13_experimental_atlas"
APPROVED = ROOT / "assets" / "handwriting" / "authentic_student_handwriting_01"
PHASE11 = ROOT / "outputs" / "school_notebook_reference_rebuild" / "phase11" / "phase11_candidate_b_atlas"
CONTRACT = ROOT / "assets" / "handwriting" / "natural_student_01" / "metadata.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase13_matches_coverage_contract_and_has_two_variants() -> None:
    metadata = json.loads((ATLAS / "metadata.json").read_text(encoding="utf-8"))
    required = set(json.loads(CONTRACT.read_text(encoding="utf-8"))["glyphs"])
    assert metadata["phase13_status"] == "EXPERIMENTAL_PENDING_VISUAL_APPROVAL"
    assert metadata["coverage_status"] == "COMPLETE_EXPERIMENTAL"
    assert set(metadata["glyphs"]) == required
    assert metadata["required_variant_count"] == 2
    assert all(len(entries) >= 2 for entries in metadata["glyphs"].values())
    assert set(metadata["provenance"]) == required

    for char, entries in metadata["glyphs"].items():
        for entry in entries:
            asset = ATLAS / entry["file"]
            assert asset.exists(), (char, asset)
            with Image.open(asset) as image:
                assert image.size == (entry["natural_width"], entry["natural_height"])
                assert image.mode in {"L", "RGBA"}
            assert entry["advance"] > 0
            assert 0 < entry["baseline"] <= 96


def test_phase13_preserves_approved_twenty_png_hashes() -> None:
    metadata = json.loads((ATLAS / "metadata.json").read_text(encoding="utf-8"))
    for char in "aeimnorstu":
        for entry in metadata["glyphs"][char]:
            experimental = ATLAS / entry["file"]
            approved = APPROVED / entry["file"]
            phase11 = PHASE11 / entry["file"]
            assert _sha(experimental) == _sha(approved) == _sha(phase11)


def test_phase13_render_audit_has_no_fallback_and_is_deterministic() -> None:
    report = (PHASE13 / "phase13_validation_report.md").read_text(encoding="utf-8")
    assert "Experimental glyph coverage: `True` (80/80)" in report
    assert "Two variants per required glyph: `True`" in report
    assert "Approved Phase 11 PNG hashes unchanged: `True`" in report
    assert "Deterministic mixed render: `True`" in report
    assert "Long multipage notebook fallback: `[]`, pages `4`" in report
    assert "fallback `[]`" in report


def test_phase13_keeps_approved_template_size_overrides() -> None:
    from config.settings import HANDWRITING_STYLES

    style = HANDWRITING_STYLES["authentic_student_handwriting_01"]
    assert style["enabled"] is True
    assert style["font_scale_by_book"] == {
        "book_buku_tulis_1": 1.05,
        "book_buku_tulis_3": 1.05,
        "book_buku_tulis_4": 1.05,
        "book_buku_tulis_6": 1.05,
        "book_kertas_folio_1": 1.05,
        "book_kertas_hvs": 1.05,
    }
