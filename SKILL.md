---
name: reference-png-redraw
description: >-
  Use when the user wants to turn one or more local reference images or crops into clean reusable transparent PNG assets through the strict workflow of local reference image or crop, then AI redraw on a flat chroma-key background, then local transparent background removal, then saved final PNG. Trigger for phrases like "本地参考图 重绘 PNG 透明抠图落盘", "按这个流程处理图片", "把 crop 生成 PNG", "贴纸/图标/插画/吉祥物抠成透明 PNG", or "AI 重绘后落盘". Do not use for Figma layout reconstruction by itself.
---

# Reference PNG Redraw

## Contract

This skill converts local reference images into final transparent PNG assets:

`local reference/crop -> AI redraw -> ai_raw -> chroma-key removal -> generated PNG`

The final deliverable must come from the AI-redrawn image, not from direct background removal on the original reference. Original references are inputs only.

## Use This For

- Single crop to clean transparent PNG.
- Batch sticker, mascot, illustration, badge, decoration, or complex icon extraction.
- UI asset preparation when the target is a reusable PNG, not a Figma layout.
- Figma reconstruction asset prep for banner images, mascots, photos, complex illustrations, complex backgrounds, and icons that cannot be sourced from an open SVG library.

## Do Not

- Do not hand-draw the asset as vector shapes unless the user explicitly asks for SVG/vector.
- Do not remove the background from the original crop and call it final.
- Do not claim completion if only crops/references exist.
- Do not skip visual inspection of the local reference before prompting image generation.

## Folder Layout

Create a task folder under the current workspace unless the user gives a destination:

```text
assets/<task-name>/
  source/
  crops/
  ai_raw/
  generated/
  manifests/
  preview/
```

Use stable names such as `01_dragon_drink_reference.png`, `01_dragon_drink_raw.png`, and `01_dragon_drink.png`.

## Workflow

1. Locate the local reference image. If the image is only visible in chat and no path exists, ask for a path before local cropping/landing.
2. Initialize the task folder with `scripts/reference_png_redraw.py init`.
3. View each reference with the local image viewer so the AI redraw step can actually use the crop as visual reference.
4. Choose a chroma key that is not in the subject:
   - Use `#FF00FF` when the subject contains greens, leaves, grass, plants, or teal.
   - Use `#00FF00` when the subject contains pink, magenta, purple, blush-heavy areas, or red-purple gradients and has no important green.
   - Use `#FFFF00` or `#00FFFF` only when both common key colors conflict; avoid cyan for blue-heavy subjects.
5. Generate the AI redraw using the visible reference image. Require a perfectly flat solid chroma-key background.
6. Save the raw AI output to `ai_raw/`.
7. Run `scripts/reference_png_redraw.py finalize` to remove the chroma key into `generated/` and update the manifest.
8. Validate alpha, transparent corners, complete subject, centered padding, and no key-color fringe.

## Prompt Pattern

```text
Use the provided reference crop as the exact visual reference.
Regenerate a clean standalone PNG-style asset of only the main subject.
Preserve the subject identity, pose, proportions, colors, line weight, and illustration/sticker style.
Make the subject complete, centered, and separated from the background with a small safe margin.
Remove dirty crop edges, screenshots, original background, neighboring fragments, and unrelated objects.
Place the regenerated asset on a perfectly flat solid KEY_COLOR chroma-key background only.
The background must be one uniform color with no shadows, gradients, texture, reflections, floor plane, or lighting variation.
Do not use KEY_COLOR anywhere in the subject.
No watermark and no extra text unless the reference text is part of the subject.
```

## Built-In Image Generation

Prefer the current Codex built-in image generation/editing tool when available. For local files, view the reference crop first so the image is visible in conversation context, then generate from that reference. Move or copy the selected generated file from `$CODEX_HOME/generated_images/...` into `ai_raw/`.

If no image generation/editing capability is available, stop after preparing the reference package and say the final PNG generation is not complete. Do not fake the AI redraw with scripts.

## Script Usage

Initialize a task package:

```bash
python3 skills/reference-png-redraw/scripts/reference_png_redraw.py init \
  --task dragon-drink \
  --source /path/to/reference.png \
  --id 01_dragon_drink \
  --notes "cute blue dragon holding drink"
```

Finalize after AI redraw:

```bash
python3 skills/reference-png-redraw/scripts/reference_png_redraw.py finalize \
  --task dragon-drink \
  --id 01_dragon_drink \
  --ai-raw assets/dragon-drink/ai_raw/01_dragon_drink_raw.png \
  --key-color "#FF00FF"
```

The script writes or updates:

- `manifests/crops_manifest.json`
- `manifests/generated_manifest.json`
- final transparent PNG under `generated/`

## Final Response

Report the final `generated/` folder, the generated manifest, and any skipped assets. Mention the chosen key color only when useful for verification or debugging.
