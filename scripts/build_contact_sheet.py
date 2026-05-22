#!/usr/bin/env python3
"""Build simple contact sheet from a directory of images."""

import sys
from pathlib import Path
from PIL import Image, ImageDraw


def checkerboard(size: tuple[int, int], tile: int = 16) -> Image.Image:
    width, height = size
    canvas = Image.new("RGB", size, (238, 238, 238))
    draw = ImageDraw.Draw(canvas)
    for y in range(0, height, tile):
        for x in range(0, width, tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=(218, 218, 218))
    return canvas


def flatten_for_preview(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    background = checkerboard(image.size)
    background.paste(image, mask=image.getchannel("A"))
    return background


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: build_contact_sheet.py <image_dir> <output_png>")
        return 1

    image_dir = Path(sys.argv[1]).expanduser().resolve()
    out = Path(sys.argv[2]).expanduser().resolve()
    files = sorted([p for p in image_dir.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}])
    if not files:
        print("No images found.")
        return 1

    cols = 4
    cell_w, cell_h = 260, 260
    rows = (len(files) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * cell_w, rows * cell_h), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)

    for i, path in enumerate(files):
        img = flatten_for_preview(path)
        img.thumbnail((220, 200))
        x = (i % cols) * cell_w + 20
        y = (i // cols) * cell_h + 20
        canvas.paste(img, (x, y))
        draw.text((x, y + 210), path.name, fill=(30, 30, 30))

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
