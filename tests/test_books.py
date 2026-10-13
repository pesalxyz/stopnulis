from pathlib import Path

from PIL import Image

from bot.keyboards.books import books_menu
from config.books import discover_book_templates, book_registry
from renderer.paper import PAGE_SIZE, load_paper


ROOT = Path(__file__).resolve().parents[1]
MENU_DIR = ROOT / "menu_buku"


def test_book_registry_discovers_all_supported_templates() -> None:
    templates = discover_book_templates(MENU_DIR)
    assert len(templates) == 6
    assert [item.template_id for item in templates] == [
        "book_buku_tulis_1", "book_buku_tulis_3", "book_buku_tulis_4", "book_buku_tulis_6",
        "book_kertas_folio_1", "book_kertas_hvs",
    ]
    assert all((MENU_DIR / item.filename).exists() for item in templates)
    assert len({item.filename for item in templates}) == len(templates)
    book3 = next(item for item in templates if item.template_id == "book_buku_tulis_3")
    assert book3.source_baselines is not None
    assert len(book3.source_baselines) == 31
    book4 = next(item for item in templates if item.template_id == "book_buku_tulis_4")
    assert book4.source_baselines is not None
    assert len(book4.source_baselines) == 31


def test_menu_labels_use_user_facing_book_sequence() -> None:
    labels = {item.template_id: item.label for item in discover_book_templates(MENU_DIR)}
    assert labels["book_buku_tulis_1"] == "Buku Tulis 1"
    assert labels["book_buku_tulis_3"] == "Buku Tulis 2"
    assert labels["book_buku_tulis_4"] == "Buku Tulis 3"
    assert labels["book_buku_tulis_6"] == "Buku Tulis 4"
    assert labels["book_kertas_folio_1"] == "Kertas Folio"


def test_menu_contains_templates_without_custom_action() -> None:
    keyboard = books_menu()
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert "book:book_buku_tulis_1" in callbacks
    assert "book:book_kertas_hvs" in callbacks
    assert "book:custom" not in callbacks
    assert "book:lined" not in callbacks


def test_menu_templates_preserve_page_size_and_old_ids_fallback() -> None:
    registry = book_registry(MENU_DIR)
    for template_id, template in registry.items():
        image, layout = load_paper(template_id, ROOT / "assets" / "papers", MENU_DIR)
        assert image.size == PAGE_SIZE
        assert layout.margin_left < PAGE_SIZE[0] - layout.margin_right
        assert layout.header_top >= 80
        if template.source_baselines is None:
            # HVS is intentionally promoted to a virtual physical grid even
            # though the photographed template has no printed ruling.
            if template.filename == "kertas_hvs.jpg":
                assert layout.baseline_positions is not None
                assert len(layout.baseline_positions) == 28
            else:
                assert layout.baseline_positions is None
        else:
            assert layout.baseline_positions is not None
            assert len(layout.baseline_positions) >= 8
            assert tuple(sorted(layout.baseline_positions)) == layout.baseline_positions
            if template_id != "book_buku_tulis_4":
                assert layout.baseline_positions[0] > layout.header_top
            if template_id == "book_buku_tulis_4":
                assert layout.baseline_start_index == 4
                assert len(layout.baseline_positions) - layout.baseline_start_index == 27
    fallback, _ = load_paper("lined", ROOT / "assets" / "papers", MENU_DIR)
    assert fallback.size == PAGE_SIZE


def test_book3_body_scale_is_variant_d_only() -> None:
    _, book3 = load_paper("book_buku_tulis_3", ROOT / "assets" / "papers", MENU_DIR)
    _, book1 = load_paper("book_buku_tulis_1", ROOT / "assets" / "papers", MENU_DIR)
    _, folio1 = load_paper("book_kertas_folio_1", ROOT / "assets" / "papers", MENU_DIR)
    assert book3.handwriting_scale == 0.88
    assert folio1.handwriting_scale == 0.7392
    assert book1.handwriting_scale == 1.0
