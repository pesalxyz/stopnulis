from config.settings import HANDWRITING_STYLES


def test_handwriting_style_catalog_contains_reference_style() -> None:
    assert set(HANDWRITING_STYLES) == {
        "natural_student_01",
        "natural_student_upright_01",
        "school_notebook_01",
        "school_notebook_reference_rebuild_01",
        "authentic_student_handwriting_01",
    }
    assert HANDWRITING_STYLES["natural_student_01"]["label"] == "Agak Berantakan"
    assert HANDWRITING_STYLES["natural_student_upright_01"]["label"] == "Rapih"
    reference = HANDWRITING_STYLES["school_notebook_01"]
    assert reference["label"] == "Tulisan Screenshot"
    assert reference["font_scale"] == 0.82
    assert HANDWRITING_STYLES["school_notebook_reference_rebuild_01"]["label"].endswith("Reference Rebuild")
    authentic = HANDWRITING_STYLES["authentic_student_handwriting_01"]
    assert authentic["label"] == "Authentic Student Handwriting"
    assert authentic["asset_style"] == "authentic_student_handwriting_01"
    assert authentic["font_scale"] == 1.05
    assert authentic["approved_phase"].startswith("Phase 17.3")
    assert authentic["advance_factor"] == 1.0
    assert authentic["word_spacing_factor"] == 1.5
    assert authentic["enabled"] is True
    assert authentic["font_scale_by_book"] == {
        "book_buku_tulis_1": 1.05,
        "book_buku_tulis_3": 1.05,
        "book_buku_tulis_4": 1.05,
        "book_buku_tulis_6": 1.05,
        "book_kertas_folio_1": 1.05,
        "book_kertas_hvs": 1.05,
    }
