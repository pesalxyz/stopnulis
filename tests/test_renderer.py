from pathlib import Path

from PIL import Image

from renderer.handwriting import HandwritingRenderer, Variation
from database.models import UserPreferences
from services.generation_service import GenerationService
from renderer.paper import load_paper


def test_handwriting_renderer_changes_image() -> None:
    image = Image.new("RGBA", (600, 200), "white")
    before = image.tobytes()
    renderer = HandwritingRenderer(None, 42, (20, 40, 120), Variation(), seed=7)
    renderer.render_line(image, "Tulisan uji", 20, 50)
    assert image.tobytes() != before
    assert renderer.measure("Tulisan") > 0


def test_dynamic_identity_renders_active_templates() -> None:
    root = Path(__file__).resolve().parents[1]
    service = GenerationService(root / "assets", max_text_length=50000)
    identity = [{"label": "Sekolah", "value": "SMP Negeri 1"},
                {"label": "Mata Pelajaran", "value": "Matematika"},
                {"label": "Kelompok", "value": "3"}]
    for book in ("book_buku_tulis_1", "book_buku_tulis_3", "book_buku_tulis_4",
                 "book_buku_tulis_6", "book_kertas_folio_1", "book_kertas_hvs"):
        pref = UserPreferences(1, book_style=book, show_identity=True, identity=identity)
        result = service.render("Tes identitas dinamis.", pref, seed=7)
        assert result.pages and result.pages[0].size == (2480, 3508)


def test_long_text_continues_without_repeating_header() -> None:
    root = Path(__file__).resolve().parents[1]
    service = GenerationService(root / "assets")
    pref = UserPreferences(1, book_style="book_buku_tulis_1", show_identity=True,
                           name="Faisal", handwriting_style="natural_student_upright_01")
    result = service.render(("kata " * 1300).strip(), pref, seed=7)
    assert 2 <= len(result.pages) <= 4
    # Header is composited only on page one; the top header band on page two
    # remains exactly the template background while body ink continues below.
    base, _ = load_paper(pref.book_style, root / "assets" / "papers", root / "menu_buku")
    assert result.pages[1].crop((0, 0, 2480, 400)).tobytes() == base.crop((0, 0, 2480, 400)).tobytes()


def test_text_beyond_four_pages_is_rejected() -> None:
    root = Path(__file__).resolve().parents[1]
    service = GenerationService(root / "assets", max_text_length=50000)
    pref = UserPreferences(1, book_style="book_buku_tulis_1", handwriting_style="natural_student_upright_01")
    import pytest
    with pytest.raises(ValueError, match="maksimal 4 halaman"):
        service.render(("kata " * 5000).strip(), pref, seed=7)
