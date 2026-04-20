# builderdebug

This folder is a copied, end-to-end slice of the map pipeline used to:

- scan and OCR a source map
- build the AreaForge review graph
- normalize and export zone YAML
- load that YAML through the builder backend
- render the map on the builder page

The tree mirrors the original repo paths so imports and ownership stay obvious.

## Included Areas

- `world/area_forge/cli/forge_area.py`: CLI entry point for running AreaForge
- `world/area_forge/run.py`: orchestration for extract/review/build/full
- `world/area_forge/extract/`: OCR and YAML-graph extraction
- `world/area_forge/build/`: review graph conversion, normalization, YAML export, snapshots, diffs
- `world/area_forge/intake/manifest.py`: manifest loading/creation
- `world/area_forge/serializer.py`: JSON artifact persistence
- `world/area_forge/paths.py`: artifact path definitions
- `world/area_forge/review.py`: review-flag generation
- `world/area_forge/model/confidence.py`: OCR confidence scoring
- `world/area_forge/ai/adjudicator.py`: optional AI adjudication pass
- `web/views.py`: builder API loading for zone YAML and review graphs
- `web/urls.py`: builder API route registration
- `web/templates/webclient/builder.html`: builder page shell
- `web/static/webclient/js/dragonsire-browser-v2.js`: builder runtime and zone-to-graph conversion
- `web/static/webclient/react/`: React Flow source components
- `web/static/webclient/js/builder-reactflow.js`: compiled React Flow bundle used by the page
- `web/static/webclient/js/builder-reactflow.css`: React Flow stylesheet used by the page
- `web/static/webclient/css/dragonsire-browser.css`: builder page styling
- `server/.static/webclient/js/builder-reactflow.js`: mirrored served React Flow bundle copy
- `worlddata/zones/`: copied live builder YAML payloads, including `test_crossing.yaml`

## Notes

- Live builder YAML files have been copied into `builderdebug/worlddata/zones/` for inspection.
- Review-graph artifacts are still produced under `build/<area_id>/` in the main repo.
- This folder is a debug copy for inspection and handoff, not a new runnable app root.