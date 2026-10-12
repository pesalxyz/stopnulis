from __future__ import annotations

import csv
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from database.models import UserPreferences
from renderer.paper import add_header, load_paper
from services.generation_service import GenerationService


def fit_line(base, expected, x0, x1):
    rgb = base.convert("RGB"); pts = []
    for x in range(x0, x1, 24):
        end = min(x + 24, x1)
        ys = [(sum(sum(rgb.getpixel((xx, y))) for xx in range(x, end)), y)
              for y in range(max(0, expected - 18), min(base.height, expected + 19))]
        pts.append((x + (end - x) / 2, min(ys)[1]))
    n = len(pts); sx = sum(x for x, _ in pts); sy = sum(y for _, y in pts)
    sxx = sum(x*x for x, _ in pts); sxy = sum(x*y for x, y in pts)
    den = n*sxx-sx*sx; a = (n*sxy-sx*sy)/den if den else 0
    return a, (sy-a*sx)/n


def bbox(layer, box):
    x0,y0,x1,y1 = box
    pts = [(x,y) for y in range(max(0,y0), min(layer.height,y1))
           for x in range(max(0,x0), min(layer.width,x1)) if layer.getpixel((x,y))[3] >= 24]
    return (min(x for x,_ in pts),min(y for _,y in pts),max(x for x,_ in pts),max(y for _,y in pts)) if pts else None


def prefs():
    return UserPreferences(1, book_style="book_kertas_folio_1", handwriting_style="natural_student_upright_01",
        ink_color="blue", show_identity=True, name="Faisal", npm="123456", class_name="TI-A", attendance_number="07",
        show_date=True, date_mode="custom", custom_date="12-10-2026")


def main():
    out = ROOT / "outputs" / "folio1_alignment"; out.mkdir(parents=True, exist_ok=True)
    p = prefs(); service = GenerationService(ROOT / "assets")
    base, layout = load_paper(p.book_style, ROOT / "assets" / "papers", ROOT / "menu_buku")
    n = len(layout.baseline_positions or ()); numbered = "\n".join(f"Baris {i:02d} tulisan uji" for i in range(1,n+1))
    final = service.render(numbered,p,seed=20261012).pages[0].convert("RGB")
    text = service.render(numbered,p,seed=20261012,text_only=True).pages[0].convert("RGBA")
    final.save(out/"folio1_final.png", optimize=True)
    final.save(out/"folio1_recalibrated_final.png", optimize=True)
    x0,x1=layout.margin_left,base.width-layout.margin_right; rows=[]
    debug=base.convert("RGBA"); debug.alpha_composite(text); draw=ImageDraw.Draw(debug,"RGBA")
    for i,ruling in enumerate(layout.baseline_positions or (),1):
        a,b=fit_line(base,ruling,x0,x1)
        calibrated_offset = layout.baseline_offsets[i-1] if layout.baseline_offsets else layout.baseline_offset
        origin=ruling-calibrated_offset
        # Folio's physical pitch is ~51 px on the output canvas; keep the
        # per-line alpha window below the next rule so adjacent glyphs cannot
        # create a false overlap.
        box=bbox(text,(x0-20,origin-8,x1+20,origin+48))
        if box:
            left,top,right,bottom=box
            clearances=[a*x+b-y for y in range(top,bottom+1) for x in range(left,right+1) if text.getpixel((x,y))[3]>=24]
            v=min(clearances); vmax=max(clearances)
            # The photographed sheet edge is about 45 px left of the safe
            # writing origin at this canvas scale; validate against that
            # actual boundary rather than the origin itself.
            left_boundary = x0 - 48
            lc=left-left_boundary; rc=x1-right; status="PASS" if v>=8 and lc>=8 and rc>=8 else "FAIL"; draw.rectangle(box,outline=(0,180,255,220),width=3)
        else: left=top=right=bottom=-1; v=vmax=lc=rc=-1; status="UNVERIFIED"
        draw.line((x0,a*x0+b,x1,a*x1+b),fill=(225,40,40,230),width=3); rows.append({"line_index":i,"min_ink_clearance_px":round(v,2),"max_ink_clearance_px":round(vmax,2),"baseline_offset_px":calibrated_offset,"ruling_error_px":round(abs((a*x1+b)-(a*x0+b)),2),"collision_detected":v < 8,"status":status,"ruling_y_left":round(a*x0+b,2),"ruling_y_right":round(a*x1+b,2),"baseline_y_left":round(a*x0+b-calibrated_offset,2),"baseline_y_right":round(a*x1+b-calibrated_offset,2),"ink_top":top,"ink_bottom":bottom,"vertical_clearance_px":round(v,2),"left_clearance_px":lc,"right_clearance_px":rc})
    debug.save(out/"folio1_debug_overlay.png",optimize=True)
    debug.save(out/"folio1_recalibrated_debug.png",optimize=True)
    with (out/"folio1_calibration.csv").open("w",newline="") as f: w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with (out/"folio1_recalibrated_calibration.csv").open("w",newline="") as f: w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    hl=Image.new("RGBA",base.size,(0,0,0,0)); add_header(hl,p,"12-10-2026",None,layout); hb=bbox(hl,(0,0,base.width,layout.baseline_positions[0])); hv=base.convert("RGB"); hd=ImageDraw.Draw(hv,"RGBA");
    if hb: hd.rectangle(hb,outline=(255,120,0,240),width=4)
    hd.line((x0,layout.baseline_positions[0],x1,layout.baseline_positions[0]),fill=(225,40,40,230),width=4); hv.save(out/"folio1_header_validation.png",optimize=True)
    long=("Mahasiswa belajar merancang sistem yang rapi, efisien, dan mudah digunakan. Dalam pengembangan perangkat lunak, ""kita perlu memperhatikan kebutuhan pengguna, alur data, serta keamanan informasi. Konsistensi penting dalam setiap tugas. ")*5
    service.render(long,p,seed=20261012).pages[0].convert("RGB").save(out/"folio1_fullwidth_test.png",optimize=True)
    before=base.convert("RGB").resize((1240,1754)); after=final.resize((1240,1754)); comp=Image.new("RGB",(2480,1754),"white"); comp.paste(before,(0,0)); comp.paste(after,(1240,0)); comp.save(out/"folio1_before_after.png",optimize=True)
    for name,a,b in (("top",0,12),("middle",12,26),("bottom",26,38)):
        final.crop((0,max(0,layout.baseline_positions[a]-120),final.width,min(final.height,layout.baseline_positions[b-1]+100))).save(out/f"folio1_closeup_{name}.png",optimize=True)
    failed=[r for r in rows if r["status"]!="PASS"]; print(f"physical_lines={n} header_bbox={hb} failed={len(failed)}")
    return 1 if n != 38 or failed or (hb and hb[3] >= layout.baseline_positions[0]-8) else 0


if __name__ == "__main__": raise SystemExit(main())
