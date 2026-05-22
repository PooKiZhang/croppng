#!/usr/bin/env python3
"""Remove a flat key-color background while preserving same-colored subject pixels.

This is intended for AI-generated intermediate assets. It only removes pixels
connected to the canvas edge, so magenta cheeks or green leaves inside the
subject are not accidentally erased just because they resemble the key color.
"""

import argparse
from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter


KEY_COLORS = {
    "magenta": (255, 0, 255),
    "green": (0, 255, 0),
    "#ff00ff": (255, 0, 255),
    "#00ff00": (0, 255, 0),
}


def parse_color(value: str) -> tuple[int, int, int]:
    value = value.strip().lower()
    if value in KEY_COLORS:
        return KEY_COLORS[value]
    if value.startswith("#") and len(value) == 7:
        return tuple(int(value[i : i + 2], 16) for i in (1, 3, 5))
    raise ValueError(f"Unsupported color {value!r}; use #RRGGBB, magenta, or green")


def pick_key_color(subject_hint: str) -> tuple[int, int, int]:
    hint = (subject_hint or "").lower()
    green_terms = ["leaf", "green", "plant", "grass", "tree", "vegetable", "叶", "草", "绿"]
    magenta_terms = ["pink", "magenta", "purple", "violet", "rose", "粉", "紫", "洋红"]
    if any(term in hint for term in green_terms):
        return (255, 0, 255)
    if any(term in hint for term in magenta_terms):
        return (0, 255, 0)
    return (255, 0, 255)


def color_distance_sq(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return sum((a[i] - b[i]) ** 2 for i in range(3))


def remove_edge_connected_key(
    image: Image.Image,
    key_color: tuple[int, int, int],
    tolerance: int,
    feather: int,
) -> Image.Image:
    rgba = image.convert("RGBA")
    px = rgba.load()
    width, height = rgba.size
    threshold = tolerance * tolerance
    visited = bytearray(width * height)
    remove = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def index(x: int, y: int) -> int:
        return y * width + x

    def is_key_like(x: int, y: int) -> bool:
        r, g, b, a = px[x, y]
        if a == 0:
            return True
        return color_distance_sq((r, g, b), key_color) <= threshold

    for x in range(width):
        for y in (0, height - 1):
            i = index(x, y)
            if not visited[i] and is_key_like(x, y):
                visited[i] = 1
                queue.append((x, y))
    for y in range(height):
        for x in (0, width - 1):
            i = index(x, y)
            if not visited[i] and is_key_like(x, y):
                visited[i] = 1
                queue.append((x, y))

    while queue:
        x, y = queue.popleft()
        remove[index(x, y)] = 1
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                continue
            i = index(nx, ny)
            if visited[i] or not is_key_like(nx, ny):
                continue
            visited[i] = 1
            queue.append((nx, ny))

    for y in range(height):
        for x in range(width):
            if remove[index(x, y)]:
                r, g, b, _ = px[x, y]
                px[x, y] = (r, g, b, 0)

    if feather > 0:
        alpha = rgba.getchannel("A")
        alpha = alpha.filter(ImageFilter.GaussianBlur(feather))
        rgba.putalpha(alpha)

    return rgba


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="AI-generated keyed image")
    parser.add_argument("--output", required=True, help="Transparent PNG output")
    parser.add_argument("--key-color", help="#RRGGBB, magenta, or green")
    parser.add_argument("--subject-hint", default="", help="Used only when key color is omitted")
    parser.add_argument("--tolerance", type=int, default=18, help="RGB distance tolerance, 0-255")
    parser.add_argument("--feather", type=int, default=0, help="Optional alpha blur radius")
    parser.add_argument(
        "--allow-crop-input",
        action="store_true",
        help="Override the pipeline guard. Use only when the user explicitly asked for local crop cleanup.",
    )
    args = parser.parse_args()

    source = Path(args.input).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if "crops" in source.parts and not args.allow_crop_input:
        raise SystemExit(
            "Refusing to process a crops/ image as a final asset. "
            "Run AI reference-image regeneration first and use an ai_raw/ input, "
            "or pass --allow-crop-input only for an explicit local-only cleanup task."
        )

    key_color = parse_color(args.key_color) if args.key_color else pick_key_color(args.subject_hint)

    image = Image.open(source)
    result = remove_edge_connected_key(image, key_color, args.tolerance, args.feather)

    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output)
    print(f"Wrote {output} with edge-connected key removal using {key_color}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
