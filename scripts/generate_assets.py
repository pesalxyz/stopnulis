from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "papers"
SIZE = (2480, 3508)


def base() -> Image.Image:
    return Image.new("RGB", SIZE, (252, 250, 242))


def lined() -> Image.Image:
    image = base()
    draw = ImageDraw.Draw(image)
    for y in range(500, SIZE[1] - 180, 104):
        draw.line((170, y + 68, SIZE[0] - 150, y + 68), fill=(153, 190, 219), width=2)
    draw.line((210, 90, 210, SIZE[1] - 120), fill=(222, 115, 120), width=3)
    return image


def grid() -> Image.Image:
    image = base()
    draw = ImageDraw.Draw(image)
    for x in range(180, SIZE[0] - 120, 100):
        draw.line((x, 80, x, SIZE[1] - 100), fill=(198, 218, 224), width=1)
    for y in range(100, SIZE[1] - 80, 100):
        draw.line((140, y, SIZE[0] - 120, y), fill=(198, 218, 224), width=1)
    return image


def plain() -> Image.Image:
    return Image.new("RGB", SIZE, (255, 254, 249))


def folio() -> Image.Image:
    image = lined()
    draw = ImageDraw.Draw(image)
    draw.line((285, 90, 285, SIZE[1] - 120), fill=(222, 115, 120), width=3)
    draw.line((SIZE[0] - 210, 90, SIZE[0] - 210, SIZE[1] - 120), fill=(222, 115, 120), width=3)
    return image


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, maker in {"lined": lined, "grid": grid, "plain": plain, "folio": folio}.items():
        maker().save(OUT / f"{name}.png", "PNG", optimize=True)


if __name__ == "__main__":
    main()

