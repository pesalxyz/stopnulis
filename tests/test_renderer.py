from pathlib import Path

from PIL import Image

from renderer.handwriting import HandwritingRenderer, Variation
from database.models import UserPreferences
from services.generation_service import GenerationService


def test_handwriting_renderer_changes_image() -> None:
    image = Image.new("RGBA", (600, 200), "white")
    before = image.tobytes()
    renderer = HandwritingRenderer(None, 42, (20, 40, 120), Variation(), seed=7)
    renderer.render_line(image, "Tulisan uji", 20, 50)
    assert image.tobytes() != before
    assert renderer.measure("Tulisan") > 0


def test_dynamic_identity_renders_active_templates() -> None:
    root = Path(__file__).resolve().parents[1]
    service = GenerationService(root / "assets")
    identity = [{"label": "Sekolah", "value": "SMP Negeri 1"},
                {"label": "Mata Pelajaran", "value": "Matematika"},
                {"label": "Kelompok", "value": "3"}]
    for book in ("book_buku_tulis_1", "book_buku_tulis_3", "book_buku_tulis_4",
                 "book_buku_tulis_6", "book_kertas_folio_1", "book_kertas_hvs"):
        pref = UserPreferences(1, book_style=book, show_identity=True, identity=identity)
        result = service.render("Tes identitas dinamis.", pref, seed=7)
        assert result.pages and result.pages[0].size == (2480, 3508)
