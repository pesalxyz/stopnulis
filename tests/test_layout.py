from PIL import ImageFont

from renderer.layout import LayoutConfig, paginate_text, wrap_paragraph


def measure(text: str) -> float:
    return len(text) * 10


def test_word_wrapping_keeps_width() -> None:
    lines = wrap_paragraph("satu dua tiga empat", 80, measure)
    assert lines == ["satu dua", "tiga", "empat"]
    assert all(measure(line) <= 80 for line in lines)


def test_long_word_is_split() -> None:
    assert wrap_paragraph("abcdefghij", 40, measure) == ["abcd", "efgh", "ij"]


def test_page_breaking() -> None:
    cfg = LayoutConfig(margin_left=10, margin_right=10, margin_top=10, margin_bottom=10, line_spacing=20, paragraph_spacing=0)
    pages = paginate_text("a\nb\nc\nd\ne", 100, 65, cfg, measure)
    assert len(pages) == 3
    assert [len(page) for page in pages] == [2, 2, 1]

