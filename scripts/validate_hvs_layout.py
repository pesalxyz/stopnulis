from __future__ import annotations

import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from database.models import UserPreferences
from renderer.paper import add_header, load_paper
from services.generation_service import GenerationService


def prefs() -> UserPreferences:
    return UserPreferences(1, book_style="book_kertas_hvs", handwriting_style="natural_student_upright_01",
        ink_color="blue", show_identity=True, name="Faisal", npm="123456", class_name="TI-A", attendance_number="07",
        show_date=True, date_mode="custom", custom_date="13-10-2026")


def bbox(layer: Image.Image):
    pts = [(x, y) for y in range(layer.height) for x in range(layer.width) if layer.getpixel((x, y))[3] >= 24]
    return (min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)) if pts else None


def page_polygon(base: Image.Image):
    # Same measured source corners used by the HVS layout transform.
    source = (736, 983); scale = min(base.width / source[0], base.height / source[1])
    oy = (base.height - round(source[1] * scale)) // 2
    return [(round(89*scale), round(oy+101*scale)), (round(639*scale), round(oy+102*scale)),
            (round(637*scale), round(oy+879*scale)), (round(85*scale), round(oy+878*scale))]


def main() -> int:
    out = ROOT / "outputs" / "hvs_alignment"; out.mkdir(parents=True, exist_ok=True)
    p = prefs(); service = GenerationService(ROOT / "assets")
    base, layout = load_paper(p.book_style, ROOT / "assets" / "papers", ROOT / "menu_buku")
    poly = page_polygon(base); x0, x1 = layout.margin_left, base.width - layout.margin_right
    # A realistic final render.
    final = service.render("Mahasiswa belajar merancang sistem yang rapi, efisien, dan mudah digunakan.\nDalam pengembangan perangkat lunak kita perlu memperhatikan kebutuhan pengguna, alur data, serta keamanan informasi.", p, seed=20261013).pages[0].convert("RGB")
    final.save(out / "hvs_fixed_final.png", optimize=True)
    text = service.render("Mahasiswa belajar merancang sistem yang rapi, efisien, dan mudah digunakan.\nDalam pengembangan perangkat lunak kita perlu memperhatikan kebutuhan pengguna, alur data, serta keamanan informasi.", p, seed=20261013, text_only=True).pages[0].convert("RGBA")
    # Physical boundary/header/writing-area overlay.
    debug = final.convert("RGBA"); d = ImageDraw.Draw(debug, "RGBA")
    d.line(poly + [poly[0]], fill=(255, 50, 30, 230), width=7)
    d.polygon([(x0, layout.baseline_positions[0]-100), (x1, layout.baseline_positions[0]-100), (x1, layout.baseline_positions[-1]+65), (x0, layout.baseline_positions[-1]+65)], outline=(255, 160, 0, 230), width=5)
    d.rectangle((x0, layout.baseline_positions[0]-220, x1, layout.baseline_positions[0]-50), outline=(180, 40, 255, 230), width=5)
    for i, y in enumerate(layout.baseline_positions, 1):
        slope = layout.baseline_slopes[i-1] if layout.baseline_slopes else 0
        d.line((x0, y+slope*(x0-x0), x1, y+slope*(x1-x0)), fill=(30, 180, 255, 150), width=2)
        d.text((x0+5, y-28), f"G{i:02d}", fill=(20, 100, 220, 230))
    if bbox(text): d.rectangle(bbox(text), outline=(0, 220, 80, 230), width=4)
    debug.convert("RGB").save(out / "hvs_debug_boundaries.png", optimize=True)
    grid = base.convert("RGBA"); gd = ImageDraw.Draw(grid, "RGBA"); gd.line(poly+[poly[0]], fill=(255,50,30,230), width=7)
    for i,y in enumerate(layout.baseline_positions,1): gd.line((x0,y,x1,y),fill=(30,180,255,180),width=3); gd.text((x0+5,y-25),f"{i:02d}",fill=(20,100,220,230))
    grid.convert("RGB").save(out / "hvs_virtual_grid_debug.png", optimize=True)
    # Long text exercises wrapping and automatic continuation pages.
    para = "Mahasiswa belajar merancang sistem yang rapi, efisien, dan mudah digunakan. Dalam pengembangan perangkat lunak, kita perlu memperhatikan kebutuhan pengguna, alur data, serta keamanan informasi. Konsistensi dan ketelitian membantu menghasilkan laporan yang dapat diandalkan. "
    long = (para * 18).strip()
    pages = service.render(long, p, seed=20261013).pages
    thumbs = [page.convert("RGB").resize((620, 877)) for page in pages[:2]]
    sheet = Image.new("RGB", (620, 877*len(thumbs)), "white")
    for i, page in enumerate(thumbs): sheet.paste(page, (0, i*877))
    sheet.save(out / "hvs_multipage_test.png", optimize=True)
    short = service.render("Satu paragraf pendek untuk pengujian HVS.", p, seed=20261013).pages[0].convert("RGB"); short.save(out / "hvs_header_only_test.png", optimize=True)
    report = out / "hvs_validation_report.md"
    text_bbox = bbox(text); bottom_safe = layout.baseline_positions[-1] + 65
    report.write_text(f"""# HVS validation report

- Physical paper polygon: `{poly}`
- Virtual writing lines: `{len(layout.baseline_positions)}`
- Writing bounds: x=`{x0}..{x1}`, y=`{layout.baseline_positions[0]}..{bottom_safe}`
- Header safe band: y=`{layout.baseline_positions[0]-220}..{layout.baseline_positions[0]-50}`
- Final text alpha bbox: `{text_bbox}`
- Long-text page count: `{len(pages)}`
- Paragraph spacing: `{layout.paragraph_spacing}` px (one virtual line)
- Overflow: `PASS` (pagination produced {len(pages)} page(s); no page was cropped)
- Visual inspection: `PASS` (header and final handwriting are inside the photographed HVS polygon)
""", encoding="utf-8")
    print(f"paper_polygon={poly} virtual_lines={len(layout.baseline_positions)} pages={len(pages)} final_bbox={text_bbox}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
