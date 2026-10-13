from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from renderer.layout import LayoutConfig


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


@dataclass(frozen=True, slots=True)
class BookTemplate:
    template_id: str
    label: str
    filename: str
    crop: tuple[float, float, float, float]
    layout: LayoutConfig
    source_left: int
    source_right: int
    source_header_bottom: int
    source_baselines: tuple[int, ...] | None
    handwriting_scale: float


# Crop boxes isolate the actual sheet in photographed templates. Coordinates are
# normalized source-image fractions and keep the source aspect ratio intact.
_CROPS: dict[str, tuple[float, float, float, float]] = {
    "buku_tulis_1.jpg": (0.01, 0.03, 0.99, 0.98),
    "buku_tulis_3.jpg": (0.15, 0.16, 0.88, 0.84),
    "buku_tulis_4.jpg": (0.01, 0.03, 0.99, 0.98),
    "buku_tulis_6.jpg": (0.02, 0.03, 0.98, 0.98),
    "kertas_folio_1.png": (0.23, 0.10, 0.83, 0.95),
    "kertas_hvs.jpg": (0.20, 0.12, 0.82, 0.88),
}

_LAYOUTS: dict[str, LayoutConfig] = {
    "buku_tulis_1.jpg": LayoutConfig(margin_left=280, margin_right=180, margin_top=540, margin_bottom=240, line_spacing=105),
    "buku_tulis_3.jpg": LayoutConfig(margin_left=530, margin_right=420, margin_top=470, margin_bottom=250, line_spacing=104),
    "buku_tulis_4.jpg": LayoutConfig(margin_left=270, margin_right=180, margin_top=470, margin_bottom=240, line_spacing=101),
    "buku_tulis_6.jpg": LayoutConfig(margin_left=300, margin_right=220, margin_top=520, margin_bottom=250, line_spacing=105),
    "kertas_folio_1.png": LayoutConfig(margin_left=400, margin_right=350, margin_top=500, margin_bottom=300, line_spacing=104),
    "kertas_hvs.jpg": LayoutConfig(margin_left=300, margin_right=300, margin_top=430, margin_bottom=260, line_spacing=108),
}

_SOURCE_GEOMETRY: dict[str, tuple[int, int, int, tuple[int, ...] | None, float]] = {
    "buku_tulis_1.jpg": (145, 1120, 140, tuple(range(270, 1602, 47)), 1.0),
    # Buku 3: first physical ruled row and writing starts immediately after
    # the vertical checkbox boundary.
    # 31 physical ruled rows detected on the photographed page. The ruling is
    # perspective-skewed, so it must not be represented by constant spacing.
    "buku_tulis_3.jpg": (
        210, 1000, 265,
        (433, 472, 511, 550, 590, 628, 667, 706, 745, 784, 823,
         861, 900, 938, 978, 1012, 1051, 1090, 1128, 1166, 1205,
         1245, 1283, 1322, 1361, 1401, 1440, 1479, 1519, 1559, 1601),
        # Variant D calibration: body glyphs at 88% of the original scale.
        # Header rendering uses a separate production-size writer.
        0.88,
    ),
    # Buku 4 has 31 photographed writing lines. The final darker line below
    # source y=1522 is the page/bottom border and is intentionally excluded.
    "buku_tulis_4.jpg": (
        145, 1110, 150,
        (88, 139, 185, 232, 279, 327, 374, 422, 470, 520, 568, 615,
         660, 708, 755, 802, 850, 900, 947, 994, 1042, 1090, 1138,
         1186, 1234, 1282, 1330, 1378, 1426, 1474, 1522),
        1.0,
    ),
    "buku_tulis_6.jpg": (
        145, 1000, 180,
        (219, 267, 315, 362, 410, 458, 506, 553, 601, 648, 696, 743,
         790, 837, 884, 932, 980, 1027, 1075, 1123, 1171, 1219, 1267,
         1316, 1364, 1413, 1461, 1510, 1559, 1608),
        1.0,
    ),
    # Folio 1 has a ruled body between the decorative top/bottom rules.  The
    # actual body contains 38 lines (source y=148..1110); y=123 and y=1137
    # are the printed border rules and are intentionally excluded.
    "kertas_folio_1.png": (
        270, 1000, 123,
        tuple(range(148, 1111, 26)),
        # Variant D calibration: 88% of the original Folio body scale
        # (0.84 * 0.88 = 0.7392). Header uses its established 0.84 scale.
        0.7392,
    ),
    "kertas_hvs.jpg": (125, 610, 120, None, 1.0),
}


def _display_name(path: Path) -> str:
    # The photographed source filenames retain their historical numbering;
    # these labels are the user-facing sequence shown in Telegram.
    display_aliases = {
        "buku_tulis_3.jpg": "Buku Tulis 2",
        "buku_tulis_4.jpg": "Buku Tulis 3",
        "buku_tulis_6.jpg": "Buku Tulis 4",
        "kertas_folio_1.png": "Kertas Folio",
    }
    if path.name in display_aliases:
        return display_aliases[path.name]
    words = path.stem.replace("_", " ").replace("-", " ").split()
    return " ".join("HVS" if word.lower() == "hvs" else word.capitalize() for word in words)


def _stable_id(path: Path) -> str:
    slug = "_".join(part for part in path.stem.lower().replace("-", "_").split() if part)
    return f"book_{slug}"


def discover_book_templates(menu_dir: Path) -> tuple[BookTemplate, ...]:
    files = sorted((path for path in menu_dir.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS), key=lambda item: item.name.lower())
    return tuple(
        BookTemplate(
            template_id=_stable_id(path),
            label=_display_name(path),
            filename=path.name,
            crop=_CROPS.get(path.name, (0.0, 0.0, 1.0, 1.0)),
            layout=_LAYOUTS.get(path.name, LayoutConfig()),
            source_left=_SOURCE_GEOMETRY.get(path.name, (80, max(81, 900), 100, None, 1.0))[0],
            source_right=_SOURCE_GEOMETRY.get(path.name, (80, max(81, 900), 100, None, 1.0))[1],
            source_header_bottom=_SOURCE_GEOMETRY.get(path.name, (80, max(81, 900), 100, None, 1.0))[2],
            source_baselines=_SOURCE_GEOMETRY.get(path.name, (80, max(81, 900), 100, None, 1.0))[3],
            handwriting_scale=_SOURCE_GEOMETRY.get(path.name, (80, max(81, 900), 100, None, 1.0))[4],
        )
        for index, path in enumerate(files, start=1)
    )


def book_registry(menu_dir: Path) -> dict[str, BookTemplate]:
    return {item.template_id: item for item in discover_book_templates(menu_dir)}


def default_book_id(menu_dir: Path) -> str:
    templates = discover_book_templates(menu_dir)
    if not templates:
        raise FileNotFoundError(f"Tidak ada template buku valid di {menu_dir}")
    return templates[0].template_id
