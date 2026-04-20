# AreaForge

AreaForge converts map images into reviewable graph artifacts and YAML zone files through a staged build pipeline.

## CLI usage

Run the AreaForge CLI with:

```bash
python -m world.area_forge.cli.forge_area --map "maps/CrossingMap (1).png" --area-id test_crossing --profile yaml_graph --mode full
```

Disable OCR for parser-only testing with:

```bash
python -m world.area_forge.cli.forge_area --map "maps/CrossingMap (1).png" --area-id test_crossing --profile yaml_graph --no-ocr --mode extract
```

Select a pipeline mode with `--mode extract`, `--mode enrich`, `--mode build`, or `--mode full`.

- `yaml_graph` is the YAML-first extractor. `extract` writes `areaspec.json` and review flags. `build` or `full` writes `worlddata/zones/<area_id>.yaml`.
- `dr_city` keeps the older Landing-specific pipeline.

Use an existing manifest with:

```bash
python -m world.area_forge.cli.forge_area --map "maps/CrossingMap (1).png" --area-id test_crossing --manifest manifests/test_crossing.yaml --mode full
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
- `build/<area_id>/areaspec.json`
- `build/<area_id>/review.txt`
- `build/snapshots/<area_id>.json`
- `worlddata/zones/<area_id>.yaml` for `yaml_graph` build/full runs