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


def test_explicit_blank_lines_consume_writable_slots() -> None:
    cfg = LayoutConfig(margin_left=10, margin_right=10, margin_top=10, margin_bottom=10,
                       line_spacing=20, paragraph_spacing=0)
    pages = paginate_text("Judul\n\nIsi", 300, 200, cfg, measure)
    assert [line.text for line in pages[0]] == ["Judul", "", "Isi"]


def test_leading_and_repeated_spaces_are_preserved() -> None:
    cfg = LayoutConfig(margin_left=10, margin_right=10, margin_top=10, margin_bottom=10,
                       line_spacing=20, paragraph_spacing=0)
    pages = paginate_text("    1. github   vscode", 500, 200, cfg, measure)
    assert pages[0][0].text == "    1. github   vscode"


def test_crlf_is_normalized_without_losing_hard_lines() -> None:
    cfg = LayoutConfig(margin_left=10, margin_right=10, margin_top=10, margin_bottom=10,
                       line_spacing=20, paragraph_spacing=0)
    pages = paginate_text("satu\r\n\r\ndua", 300, 200, cfg, measure)
    assert [line.text for line in pages[0]] == ["satu", "", "dua"]


def test_tabs_use_stable_four_space_stops() -> None:
    cfg = LayoutConfig(margin_left=10, margin_right=10, margin_top=10, margin_bottom=10,
                       line_spacing=20, paragraph_spacing=0)
    pages = paginate_text("\titem", 300, 200, cfg, measure)
    assert pages[0][0].text == "    item"
