# image-crop-to-png

A Codex skill for extracting elements from reference images and producing clean transparent PNG assets with an AI-assisted pipeline:

`crop -> hand the real crop image to built-in AI regeneration -> adaptive background removal -> PNG`

The final PNGs must come from AI-regenerated assets, not from merely making the original crops transparent.

## What this skill does

- Splits image elements into local crops
- Hands the real crop image content to Codex built-in image generation/editing to regenerate each crop as a clean keyed-background asset
- Removes keyed backgrounds with adaptive key-color logic
- Produces transparent PNG assets
- Writes manifests and contact-sheet previews

## Repository structure

```text
.
├── SKILL.md
├── README.md
├── references/
└── scripts/
    ├── extract_crops.py
    ├── remove_bg_adaptive.py
    └── build_contact_sheet.py
```

## Install (local Codex skill)

### Option A: clone directly into Codex skills directory

```bash
git clone https://github.com/PooKiZhang/croppng.git ~/.codex/skills/image-crop-to-png-pipeline
```

### Option B: clone anywhere, then copy

```bash
git clone https://github.com/PooKiZhang/croppng.git
cp -R croppng ~/.codex/skills/image-crop-to-png-pipeline
```

After install, restart Codex (or refresh skills) to load the new skill.

## Usage notes

- Treat `crops/` as AI reference inputs only.
- Run one sample through the available built-in image generation/editing capability first, inspect the result, then continue in batches.
- The AI regeneration step must pass the real crop image content, not just a file path, filename, bounding box, or text description.
- If the available image-generation tool cannot take or reference the crop image itself, stop and report that limitation instead of generating from text only or asking for an external API.
- Use **magenta key background** (`#FF00FF`) when subjects contain green details (leaf/plant) to avoid accidental foreground removal.
- Use **green key background** (`#00FF00`) when subjects contain magenta/pink-heavy regions.
- Remove only edge-connected key-color pixels, not every matching color in the whole image.
- Always validate alpha edges before final delivery.

## Output convention (recommended)

```text
assets/<task>/
  crops/
  ai_raw/
  generated/
  manifests/
    crops_manifest.json
    generated_manifest.json
  preview/
    crops_contact_sheet.jpg
    generated_contact_sheet.png
```

## License

MIT
