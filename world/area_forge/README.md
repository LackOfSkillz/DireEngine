# AreaForge

AreaForge converts map images into playable Evennia areas through a staged build pipeline.

## CLI usage

Run the AreaForge CLI with:

```bash
python -m world.area_forge.cli.forge_area --map "maps/CrossingMap (1).png" --area-id the_landing
```

Disable OCR for parser-only testing with:

```bash
python -m world.area_forge.cli.forge_area --map "maps/CrossingMap (1).png" --area-id the_landing --no-ocr
```

Select a pipeline mode with `--mode extract`, `--mode enrich`, `--mode build`, or `--mode full`.

Use an existing manifest with:

```bash
python -m world.area_forge.cli.forge_area --map "maps/CrossingMap (1).png" --area-id the_landing --manifest manifests/the_landing.yaml --mode full
```

## OCR setup

Install the Python dependencies in the project environment:

```bash
pip install pytesseract pillow
```

Install the Tesseract OCR engine separately at the system level. The Python package does not include the native executable.

To verify OCR is available to AreaForge, import `world.area_forge.extract.ocr` and confirm `ocr_available()` returns `True`.

## Artifacts

AreaForge writes these standard artifacts during operation:

- `manifests/<area_id>.yaml`
- `build/areaspec.json`
- `build/review.txt`
- `build/snapshots/<area_id>.json`