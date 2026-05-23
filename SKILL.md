---
name: image-png-v1
description: 从用户上传或指定的图片中分析可独立提取的视觉元素，先裁切到本地作为参考素材，再用 Codex 可用的内置图片生成/编辑能力基于 crop 重绘成更干净、主体明确的图，随后使用纯色键色背景抠除并输出透明 PNG。用于贴纸拆解、图标/插画/吉祥物/装饰素材提取、图片素材整理、批量生成可复用 PNG；不要用于把 UI 设计稿还原到 Figma 或直接重建布局。
---

# Image PNG V1

## Goal

Turn a source image into reusable transparent PNG assets:

`source image -> analyze elements -> local crops -> AI redraw from each crop -> chroma-key removal -> transparent PNG`

The final PNGs must come from the AI-redrawn images, not from direct background removal on the original crops.

## Core Rules

- Treat this as an asset extraction workflow, not a Figma/UI reconstruction workflow.
- Analyze which visible elements are worth extracting before cropping: stickers, mascots, icons, illustrations, objects, decorative marks, logos, badges, and standalone text-art.
- Rebuild nothing as vector shapes unless the user explicitly asks for SVG/vector output. The default output is transparent PNG.
- Save original crops locally first. Crops are reference inputs only, never final deliverables.
- Use each crop's actual image content as the visual reference for AI redraw. Do not rely only on filename, bbox, or text description.
- Save AI raw outputs before background removal.
- Only run background removal on AI raw outputs, not on crops.
- If AI redraw cannot use the crop as an image reference in the current environment, stop at crops/reference package and clearly say final PNG generation is not complete.

## What "AI Redraw" Means

"AI redraw" means Codex itself uses the current conversation's available image generation/editing ability to generate a new image from the crop reference. It does not mean:

- Asking the user for an external API key.
- Writing a local script that pretends to generate an image.
- Only describing the crop in text without providing the crop image as visual reference.
- Directly removing the background from the original crop and calling it final.

The expected behavior is:

1. Open or display the crop so Codex can visually see it.
2. Ask Codex's image generation/editing capability to regenerate the subject from that crop.
3. Require a flat solid key-color background.
4. Save the generated result into `ai_raw/`.
5. Run the local chroma-key removal script to create the final transparent PNG.

If the current Codex runtime exposes a built-in image generation tool, use it. If the runtime lets Codex generate images from visible conversation images, use that. Do not block on external APIs or `OPENAI_API_KEY`.

Only enter handoff mode if the current runtime truly provides no way for Codex to generate/edit an image from the visible crop reference. In that case, do not fake the output; keep the crops and manifest as the handoff package.

## Output Directory

Create a task folder under the current workspace unless the user specifies another destination:

```text
assets/<task-name>/
  source/
  crops/
  ai_raw/
  generated/
  manifests/
    crops_manifest.json
    generated_manifest.json
  preview/
```

Use stable, descriptive filenames such as `01_dragon_frame.png`, `02_cool_logo.png`, or `03_flower_badge.png`.

## Step 1: Source Intake

1. Locate the exact source image.
2. If the image is uploaded in the chat but not available as a local file, use the visible image context when possible. If local cropping requires a file path and no file is available, ask the user to save/provide the local file path.
3. Copy or record the source under `assets/<task-name>/source/`.
4. Inspect the image dimensions and visual content before deciding crop strategy.

## Step 2: Element Analysis

List or internally plan the extractable elements:

- Keep complete, visually separate subjects.
- Include important text-art with its associated graphic when they form one sticker/logo.
- Skip partial elements cut off by the image edge unless the user asks to keep them.
- Split separate stickers/objects into separate crops when they do not visually belong together.
- Keep compound stickers together when separating would break their meaning.
- Use manual or semi-manual boxes when automatic segmentation merges nearby stickers.

Record each crop in `crops_manifest.json` with:

```json
{
  "id": "01_dragon_frame",
  "bbox": [x, y, width, height],
  "crop_file": "assets/<task>/crops/01_dragon_frame.png",
  "notes": "framed dragon portrait sticker"
}
```

## Step 3: Local Cropping

Crop each planned element into `crops/` with enough padding to preserve the full subject and outline.

After cropping:

- Inspect a crop contact sheet or a few key crops.
- Fix tight crops, merged elements, or accidental partial elements before AI redraw.
- Do not present crops as final PNG assets.

## Step 4: AI Redraw

For each crop, load or view the crop so the image generation/editing step can actually see it as a reference.

Prompt pattern:

```text
Use the provided crop as the exact visual reference.
Regenerate a clean standalone PNG-style asset of only the main subject.
Preserve the original subject identity, pose, proportions, colors, line weight, and cute sticker/illustration style.
Make the subject complete, centered, and separated from the background with a small safe margin.
Remove unrelated neighboring elements, dirty crop edges, screenshots, frames, and background clutter unless they are part of the subject.
Place the subject on a perfectly flat solid KEY_COLOR background only.
No shadow, no texture, no gradient, no watermark, no extra objects.
Do not use KEY_COLOR anywhere in the subject.
```

Save each generated source image to `ai_raw/`. The `ai_raw/` file is the proof that the final PNG came from AI redraw.

## Step 5: Key Color Choice

Choose a chroma key color that does not appear in the subject:

- Subject has green leaves, grass, plants, or teal details: use magenta `#FF00FF`.
- Subject has pink, magenta, purple, hearts, blush-heavy details, or red-purple gradients: use green `#00FF00` if the subject has no important green.
- Subject has both green and magenta/pink: use a rarer key such as pure yellow `#FFFF00` or cyan `#00FFFF`, choosing the one least present in the subject.
- Blue-heavy subjects should avoid cyan/blue keys.

Always state the chosen key color in the generation prompt and tell the model not to use it in the subject.

## Step 6: Background Removal

Use the installed chroma-key helper on AI raw outputs:

```bash
python "${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/remove_chroma_key.py" \
  --input assets/<task>/ai_raw/<id>_raw.png \
  --out assets/<task>/generated/<id>.png \
  --key-color "#FF00FF" \
  --soft-matte \
  --transparent-threshold 10 \
  --opaque-threshold 210 \
  --edge-contract 1 \
  --despill \
  --force
```

Prefer explicit `--key-color` once a key has been chosen. Use edge-connected/background-aware removal; never replace that color globally across the whole image, because that can delete legitimate subject details.

If subject details are accidentally removed:

1. Regenerate the AI raw image using a different key color.
2. Tighten the prompt: "Do not use KEY_COLOR anywhere in the subject."
3. Retry removal with explicit key color and edge-aware settings.
4. Inspect alpha and subject integrity before continuing the batch.

## Step 7: Validation

Before final response, verify:

- Each final file is a PNG with alpha.
- Corners/background are transparent.
- Subject is complete and centered.
- Important green/pink/blue subject details are not removed.
- No original screenshot background, crop edge, dirty pixels, watermark, or extra nearby object remains.
- `generated_manifest.json` links `crop_file -> ai_raw_file -> generated_file`.

`generated_manifest.json` minimum item:

```json
{
  "id": "01_dragon_frame",
  "crop_file": "assets/<task>/crops/01_dragon_frame.png",
  "ai_raw_file": "assets/<task>/ai_raw/01_dragon_frame_raw.png",
  "generated_file": "assets/<task>/generated/01_dragon_frame.png",
  "key_color": "#FF00FF",
  "generation_tool": "Codex built-in image generation/editing",
  "reference_image_used": true
}
```

## Batch Strategy

For many elements:

1. Crop everything first.
2. Generate a contact sheet for human/agent inspection.
3. Run one or two sample AI redraws.
4. Validate transparency and subject quality.
5. Continue in small batches.
6. Update the manifest as each PNG is completed.

Do not claim the batch is finished if only crops exist or if `ai_raw/` is missing.

## Final Response

Report:

- The final transparent PNG folder.
- The manifest path.
- Any elements skipped and why.
- The key-color strategy if relevant.

Keep the response concise. The user mainly needs the saved PNG paths and confidence that the workflow was followed.
