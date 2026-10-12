from pathlib import Path

from PIL import Image

from renderer.handwriting import HandwritingRenderer, Variation


def test_handwriting_renderer_changes_image() -> None:
    image = Image.new("RGBA", (600, 200), "white")
    before = image.tobytes()
    renderer = HandwritingRenderer(None, 42, (20, 40, 120), Variation(), seed=7)
    renderer.render_line(image, "Tulisan uji", 20, 50)
    assert image.tobytes() != before
    assert renderer.measure("Tulisan") > 0

