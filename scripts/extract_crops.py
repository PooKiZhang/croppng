#!/usr/bin/env python3
"""Extract likely foreground elements from a flat-background source image.

The output crops are reference inputs for AI regeneration, not final assets.
This helper is intentionally conservative: it removes edge-connected background
colors, filters tiny confetti-like components, and writes a manifest that makes
each crop traceable to its source box.
"""

import argparse
import json
from collections import Counter, deque
from pathlib import Path

from PIL import Image


def dominant_edge_color(image: Image.Image, sample_step: int) -> tuple[int, int, int]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    samples: list[tuple[int, int, int]] = []

    for x in range(0, width, sample_step):
        samples.append(pixels[x, 0])
        samples.append(pixels[x, height - 1])
    for y in range(0, height, sample_step):
        samples.append(pixels[0, y])
        samples.append(pixels[width - 1, y])

    quantized = [tuple((channel // 8) * 8 for channel in color) for color in samples]
    color, _ = Counter(quantized).most_common(1)[0]
    return color


def color_distance_sq(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return sum((a[i] - b[i]) ** 2 for i in range(3))


def build_foreground_mask(
    image: Image.Image,
    background_color: tuple[int, int, int],
    tolerance: int,
) -> bytearray:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    threshold = tolerance * tolerance
    background = bytearray(width * height)
    visited = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def index(x: int, y: int) -> int:
        return y * width + x

    def is_background_like(x: int, y: int) -> bool:
        r, g, b, a = pixels[x, y]
        if a == 0:
            return True
        return color_distance_sq((r, g, b), background_color) <= threshold

    for x in range(width):
        for y in (0, height - 1):
            i = index(x, y)
            if not visited[i] and is_background_like(x, y):
                visited[i] = 1
                queue.append((x, y))
    for y in range(height):
        for x in (0, width - 1):
            i = index(x, y)
            if not visited[i] and is_background_like(x, y):
                visited[i] = 1
                queue.append((x, y))

    while queue:
        x, y = queue.popleft()
        background[index(x, y)] = 1
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                continue
            i = index(nx, ny)
            if visited[i] or not is_background_like(nx, ny):
                continue
            visited[i] = 1
            queue.append((nx, ny))

    foreground = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            i = index(x, y)
            if not background[i] and pixels[x, y][3] > 0:
                foreground[i] = 1
    return foreground


def connected_components(mask: bytearray, width: int, height: int, min_area: int) -> list[dict]:
    visited = bytearray(width * height)
    components = []

    def index(x: int, y: int) -> int:
        return y * width + x

    for y in range(height):
        for x in range(width):
            start = index(x, y)
            if visited[start] or not mask[start]:
                continue

            queue = deque([(x, y)])
            visited[start] = 1
            area = 0
            min_x = max_x = x
            min_y = max_y = y

            while queue:
                cx, cy = queue.popleft()
                area += 1
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)

                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        continue
                    i = index(nx, ny)
                    if visited[i] or not mask[i]:
                        continue
                    visited[i] = 1
                    queue.append((nx, ny))

            if area >= min_area:
                components.append(
                    {
                        "area": area,
                        "bbox": [min_x, min_y, max_x + 1, max_y + 1],
                        "touches_edge": min_x == 0 or min_y == 0 or max_x == width - 1 or max_y == height - 1,
                    }
                )

    components.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    return components


def save_crop(image: Image.Image, bbox: list[int], padding: int, output: Path) -> list[int]:
    width, height = image.size
    left, top, right, bottom = bbox
    padded = [
        max(0, left - padding),
        max(0, top - padding),
        min(width, right + padding),
        min(height, bottom + padding),
    ]
    image.crop(tuple(padded)).save(output)
    return padded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_image")
    parser.add_argument("task_dir")
    parser.add_argument("--background-color", help="Override detected background color, e.g. #9AC83A")
    parser.add_argument("--tolerance", type=int, default=34)
    parser.add_argument("--min-area", type=int, default=180)
    parser.add_argument("--padding", type=int, default=8)
    parser.add_argument("--sample-step", type=int, default=5)
    parser.add_argument(
        "--skip-edge-components",
        action="store_true",
        help="Skip foreground components cut off by the image edge",
    )
    args = parser.parse_args()

    source = Path(args.source_image).expanduser().resolve()
    task_dir = Path(args.task_dir).expanduser().resolve()
    crops_dir = task_dir / "crops"
    manifests_dir = task_dir / "manifests"
    crops_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    image = Image.open(source).convert("RGBA")
    if args.background_color:
        value = args.background_color.strip().lstrip("#")
        background_color = tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))
    else:
        background_color = dominant_edge_color(image, args.sample_step)

    mask = build_foreground_mask(image, background_color, args.tolerance)
    components = connected_components(mask, image.width, image.height, args.min_area)
    skipped_edge_components = 0
    if args.skip_edge_components:
        before = len(components)
        components = [component for component in components if not component["touches_edge"]]
        skipped_edge_components = before - len(components)

    items = []
    for index, component in enumerate(components, start=1):
        filename = f"crop_{index:03d}.png"
        path = crops_dir / filename
        padded_bbox = save_crop(image, component["bbox"], args.padding, path)
        items.append(
            {
                "id": f"crop_{index:03d}",
                "file": str(path),
                "bbox": component["bbox"],
                "padded_bbox": padded_bbox,
                "area": component["area"],
                "touches_edge": component["touches_edge"],
                "ai_status": "pending",
                "note": "Reference crop only; hand the real image content to an available built-in image generation/editing tool before final PNG delivery.",
            }
        )

    manifest = {
        "source": str(source),
        "background_color": "#{:02X}{:02X}{:02X}".format(*background_color),
        "tolerance": args.tolerance,
        "min_area": args.min_area,
        "skip_edge_components": args.skip_edge_components,
        "skipped_edge_components": skipped_edge_components,
        "count": len(items),
        "items": items,
    }
    out = manifests_dir / "crops_manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out} with {len(items)} crop(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
