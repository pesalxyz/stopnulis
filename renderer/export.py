from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image


def save_png_pages(pages: list[Image.Image], output_dir: Path, stem: str) -> list[Path]:
    paths: list[Path] = []
    for index, page in enumerate(pages, start=1):
        path = output_dir / f"{stem}_{index}.png"
        page.convert("RGB").save(path, "PNG", optimize=True)
        paths.append(path)
    return paths


def save_jpg_pages(pages: list[Image.Image], output_dir: Path, stem: str, quality: int = 92) -> list[Path]:
    paths: list[Path] = []
    for index, page in enumerate(pages, start=1):
        path = output_dir / f"{stem}_{index}.jpg"
        page.convert("RGB").save(path, "JPEG", quality=quality, optimize=True)
        paths.append(path)
    return paths


def save_pdf(pages: list[Image.Image], output_path: Path) -> Path:
    if not pages:
        raise ValueError("Tidak ada halaman untuk diekspor.")
    rgb_pages = [page.convert("RGB") for page in pages]
    rgb_pages[0].save(output_path, "PDF", resolution=150, save_all=True, append_images=rgb_pages[1:])
    return output_path


def preview_bytes(page: Image.Image, max_size: tuple[int, int] = (900, 1273)) -> bytes:
    preview = page.copy().convert("RGB")
    preview.thumbnail(max_size, Image.Resampling.LANCZOS)
    buffer = BytesIO()
    preview.save(buffer, "JPEG", quality=82, optimize=True)
    return buffer.getvalue()

