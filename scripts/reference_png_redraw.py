#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image


ROOT = Path.cwd()
ASSETS_DIR = ROOT / "assets"


def task_dir(task):
    safe = task.strip().replace(" ", "-")
    return ASSETS_DIR / safe


def ensure_dirs(base):
    for name in ("source", "crops", "ai_raw", "generated", "manifests", "preview"):
        (base / name).mkdir(parents=True, exist_ok=True)


def read_json(path, fallback):
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return fallback


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def copy_reference(source, target):
    source = Path(source).expanduser()
    if not source.exists():
        raise SystemExit(f"Source not found: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def image_size(path):
    with Image.open(path) as im:
        return list(im.size)


def init(args):
    base = task_dir(args.task)
    ensure_dirs(base)
    source = copy_reference(args.source, base / "source" / Path(args.source).name)
    crop_name = f"{args.id}_reference.png"
    crop = copy_reference(args.source, base / "crops" / crop_name)
    width, height = image_size(crop)

    manifest_path = base / "manifests" / "crops_manifest.json"
    manifest = read_json(manifest_path, {"task": args.task, "source_image": str(source), "count": 0, "items": []})
    item = {
        "id": args.id,
        "bbox": [0, 0, width, height],
        "crop_file": str(crop),
        "notes": args.notes or "",
    }
    manifest["items"] = [existing for existing in manifest.get("items", []) if existing.get("id") != args.id]
    manifest["items"].append(item)
    manifest["count"] = len(manifest["items"])
    write_json(manifest_path, manifest)

    print(str(base))
    print(str(crop))
    print(str(manifest_path))


def chroma_helper():
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
    script = home / "skills" / ".system" / "imagegen" / "scripts" / "remove_chroma_key.py"
    if not script.exists():
        raise SystemExit(f"Chroma-key helper not found: {script}")
    return script


def validate_png(path):
    with Image.open(path) as im:
        if im.mode != "RGBA":
            raise SystemExit(f"Final PNG lacks RGBA alpha: {path}")
        alpha = im.getchannel("A")
        extrema = alpha.getextrema()
        corners = [
            alpha.getpixel((0, 0)),
            alpha.getpixel((im.width - 1, 0)),
            alpha.getpixel((0, im.height - 1)),
            alpha.getpixel((im.width - 1, im.height - 1)),
        ]
        if extrema[0] > 10:
            raise SystemExit(f"Alpha appears opaque everywhere: {path}, extrema={extrema}")
        if max(corners) > 20:
            raise SystemExit(f"PNG corners are not transparent enough: {path}, corners={corners}")
        return {"size": list(im.size), "alpha_extrema": list(extrema), "corner_alpha": corners}


def finalize(args):
    base = task_dir(args.task)
    ensure_dirs(base)
    raw_src = Path(args.ai_raw).expanduser()
    if not raw_src.exists():
        raise SystemExit(f"AI raw image not found: {raw_src}")

    raw_dest = base / "ai_raw" / f"{args.id}_raw.png"
    if raw_src.resolve() != raw_dest.resolve():
        shutil.copy2(raw_src, raw_dest)

    final = base / "generated" / f"{args.id}.png"
    cmd = [
        "python3",
        str(chroma_helper()),
        "--input",
        str(raw_dest),
        "--out",
        str(final),
        "--key-color",
        args.key_color,
        "--soft-matte",
        "--transparent-threshold",
        str(args.transparent_threshold),
        "--opaque-threshold",
        str(args.opaque_threshold),
        "--edge-contract",
        str(args.edge_contract),
        "--despill",
        "--force",
    ]
    subprocess.run(cmd, check=True)
    validation = validate_png(final)

    generated_path = base / "manifests" / "generated_manifest.json"
    generated = read_json(generated_path, {"task": args.task, "count": 0, "items": []})
    item = {
        "id": args.id,
        "crop_file": str(base / "crops" / f"{args.id}_reference.png"),
        "ai_raw_file": str(raw_dest),
        "generated_file": str(final),
        "key_color": args.key_color,
        "generation_tool": args.generation_tool,
        "reference_image_used": True,
        "validation": validation,
    }
    generated["items"] = [existing for existing in generated.get("items", []) if existing.get("id") != args.id]
    generated["items"].append(item)
    generated["count"] = len(generated["items"])
    write_json(generated_path, generated)

    print(str(final))
    print(str(generated_path))


def main():
    parser = argparse.ArgumentParser(description="Prepare and finalize reference -> AI redraw -> transparent PNG assets.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--task", required=True)
    p_init.add_argument("--source", required=True)
    p_init.add_argument("--id", required=True)
    p_init.add_argument("--notes", default="")
    p_init.set_defaults(func=init)

    p_final = sub.add_parser("finalize")
    p_final.add_argument("--task", required=True)
    p_final.add_argument("--id", required=True)
    p_final.add_argument("--ai-raw", required=True)
    p_final.add_argument("--key-color", required=True)
    p_final.add_argument("--transparent-threshold", type=int, default=10)
    p_final.add_argument("--opaque-threshold", type=int, default=210)
    p_final.add_argument("--edge-contract", type=float, default=1)
    p_final.add_argument("--generation-tool", default="Codex built-in image generation/editing")
    p_final.set_defaults(func=finalize)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
