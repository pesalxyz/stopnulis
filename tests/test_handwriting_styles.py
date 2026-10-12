from config.settings import HANDWRITING_STYLES


def test_only_two_handwriting_styles_are_available() -> None:
    assert set(HANDWRITING_STYLES) == {
        "natural_student_01",
        "natural_student_upright_01",
    }
    assert HANDWRITING_STYLES["natural_student_01"]["label"] == "Agak Berantakan"
    assert HANDWRITING_STYLES["natural_student_upright_01"]["label"] == "Rapih"
