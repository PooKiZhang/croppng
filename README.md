# image-png-v1

A Codex skill for extracting elements from reference images and producing clean transparent PNG assets with an AI-assisted pipeline:

`source image -> analyze elements -> local crops -> AI redraw from crop references -> chroma-key removal -> transparent PNG`

The final PNGs must come from AI-regenerated assets, not from merely making the original crops transparent.

## What this skill does

- Splits image elements into local crops
- Hands the real crop image content to Codex built-in image generation/editing to regenerate each crop as a clean keyed-background asset
- Removes keyed backgrounds with adaptive key-color logic
- Produces transparent PNG assets
- Writes manifests; contact-sheet previews are optional QA helpers

## Repository structure

```text
.
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
└── scripts/
    ├── extract_crops.py
    ├── remove_bg_adaptive.py
    └── build_contact_sheet.py
```

## Install (local Codex skill)

### Option A: clone directly into Codex skills directory

```bash
git clone https://github.com/PooKiZhang/croppng.git ~/.codex/skills/image-png-v1
```

### Option B: clone anywhere, then copy

```bash
git clone https://github.com/PooKiZhang/croppng.git
cp -R croppng ~/.codex/skills/image-png-v1
```

After install, restart Codex (or refresh skills) to load the new skill.

## Usage notes

- Treat `crops/` as AI reference inputs only.
- Run one sample through the available built-in image generation/editing capability first, inspect the result, then continue in batches.
- The AI regeneration step must pass the real crop image content, not just a file path, filename, bounding box, or text description.
- If the available image-generation tool cannot take or reference the local crop image itself, enter handoff mode: produce the crops folder, manifest, and a reference zip; clearly say these are not final PNGs and ask the user to reattach the crop/zip as image input.
- When the user reattaches a crop or reference zip, resume from AI regeneration instead of cutting the source image again.
- Do not check or ask for `OPENAI_API_KEY`, external image-generation API keys, SDKs, or command-line generation setup. This skill defaults to Codex's current conversation/UI image capabilities.
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
  preview/  # optional
    crops_contact_sheet.jpg
    generated_contact_sheet.png
```

## License

MIT
