from __future__ import annotations

import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.models import UserPreferences
from renderer.paper import load_paper
from services.generation_service import GenerationService

TEXT = "Oleh karena itu, penelitian merupakan suatu proses yang terus menerus disempurnakan untuk menghasilkan pengetahuan yang akurat dan bermanfaat bagi masyarakat."


def bbox_in_band(layer: Image.Image, y0: int, y1: int):
    alpha = layer.getchannel("A").crop((0, max(0, y0), layer.width, min(layer.height, y1)))
    box = alpha.getbbox()
    return None if box is None else (box[0], box[1] + y0, box[2], box[3] + y0)


def main() -> int:
    out = ROOT / "outputs" / "wordwrap_validation"
    out.mkdir(parents=True, exist_ok=True)
    service = GenerationService(ROOT / "assets")
    rows = []
    for book in ("book_buku_tulis_1", "book_buku_tulis_3", "book_buku_tulis_4", "book_buku_tulis_6", "book_kertas_folio_1", "book_kertas_hvs"):
        pref = UserPreferences(1, book_style=book, handwriting_style="natural_student_upright_01", ink_color="blue")
        final_result = service.render(TEXT, pref, seed=20261013)
        text_layer = service.render(TEXT, pref, seed=20261013, text_only=True).pages[0].convert("RGBA")
        base, layout = load_paper(book, ROOT / "assets" / "papers", ROOT / "menu_buku")
        debug = base.convert("RGBA"); debug.alpha_composite(text_layer); draw = ImageDraw.Draw(debug, "RGBA")
        lines = []
        # Recover the exact laid-out lines from the same renderer measurement.
        style_dir = ROOT / "assets" / "handwriting" / "natural_student_upright_01"
        from renderer.multiglyph import MultiGlyphHandwritingRenderer
        from config.settings import INK_COLORS
        writer = MultiGlyphHandwritingRenderer(style_dir, round(54 * layout.handwriting_scale * layout.body_scale_adjust), INK_COLORS["blue"], 20261013, .10, .22, .05, 1.0)
        from renderer.layout import paginate_text
        lines = paginate_text(TEXT, base.width, base.height, layout, writer.measure)[0]
        word_cursor = 0
        source_words = TEXT.split()
        for index, line in enumerate(lines):
            y0 = line.y - 10; y1 = line.y + 90
            box = bbox_in_band(text_layer, y0, y1)
            right = base.width - layout.margin_right
            if box:
                draw.rectangle(box, outline=(255, 120, 0, 220), width=3)
                actual_width = box[2] - line.x
            else:
                actual_width = 0
            draw.line((right, y0, right, y1), fill=(220, 30, 30, 210), width=3)
            consumed = len(line.text.split())
            next_word = source_words[word_cursor + consumed] if word_cursor + consumed < len(source_words) else ""
            next_width = writer.measure((line.text + " " + next_word).strip()) if next_word else 0.0
            decision = "FIT" if next_word and next_width <= right - line.x else ("WRAP" if next_word else "END")
            rows.append({"book": book, "line_index": index + 1, "text": line.text,
                         "predicted_width": round(writer.measure(line.text), 2),
                         "actual_ink_width": round(actual_width, 2),
                         "available_width": right - line.x,
                         "remaining_width": round(right - line.x - writer.measure(line.text), 2),
                         "next_word": next_word, "next_word_width": round(next_width, 2),
                         "decision": decision,
                         "status": "PASS" if writer.measure(line.text) <= right - line.x else "FAIL"})
            word_cursor += consumed
        debug.save(out / f"{book}_debug.png", optimize=True)
        final_result.pages[0].convert("RGB").save(out / f"{book}_final.png", optimize=True)
    with (out / "wordwrap_measurements.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (out / "wordwrap_debug.log").write_text("\n".join(
        f"Line: {row['line_index']} | Current text: {row['text']} | Next word: {row['next_word']} | Available width: {row['available_width']} | Current rendered width: {row['predicted_width']} | Next candidate width: {row['next_word_width']} | Actual rendered ink width: {row['actual_ink_width']} | Remaining width: {row['remaining_width']} | Decision: {row['decision']}"
        for row in rows if row["book"] == "book_buku_tulis_1"
    ) + "\n")
    print(f"validated={len(rows)} outputs={out}")
    return 0 if all(row["status"] == "PASS" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
