# AreaForge Report

## Scope

This report documents the AreaForge implementation, refinement, rebuild, and comparison work performed against the uploaded map `maps/CrossingMap (1).png`.

Primary goals covered in this report:
- run AreaForge live against the uploaded map
- build a parallel generated area named `new_landing`
- compare `new_landing` against the existing `the_landing`
- improve OCR-driven naming and room-description quality
- convert business and institution labels into adjacent POI stub rooms with exits like `go bank`
- validate whether the updated AreaForge pipeline now produces superior results

Current outcome in this report:
- AreaForge now rebuilds `new_landing` cleanly from the uploaded map
- the current `new_landing` output is structurally at parity with `the_landing`
- the earlier OCR naming regressions have been removed
- POI stubs such as `Bank`, `Guildhall`, `Shrine`, `Academy`, `Prison`, `Shop`, `General Store`, and `Forge` are live and enterable

## Implemented

### Phase 1 - Generalize AreaForge beyond `the_landing`

- Generalized area-specific namespaces and artifact paths in [world/area_forge/paths.py](c:/Users/gary/dragonsire/world/area_forge/paths.py).
- Refactored the AreaForge runner in [world/area_forge/run.py](c:/Users/gary/dragonsire/world/area_forge/run.py) so the DR-city profile can build arbitrary `area_id` values rather than only `the_landing`.
- Updated [world/the_landing.py](c:/Users/gary/dragonsire/world/the_landing.py) so extraction and build logic work for parallel areas such as `the_landing` and `new_landing`.
- Added area-specific tagging, node categories, exit categories, aliases, and artifact storage so both areas can coexist in the same database.

### Phase 2 - Build `new_landing` live from the uploaded map

- Used the uploaded map `maps/CrossingMap (1).png` as the AreaForge source.
- Created and used [manifests/new_landing.yaml](c:/Users/gary/dragonsire/manifests/new_landing.yaml).
- Generated AreaForge artifacts under [build/new_landing/areaspec.json](c:/Users/gary/dragonsire/build/new_landing/areaspec.json) and [build/new_landing/review.txt](c:/Users/gary/dragonsire/build/new_landing/review.txt).
- Validated that `new_landing` could be built live inside the Evennia runtime as a separate area.

### Phase 3 - Fix OCR naming regression

- Added OCR text-quality scoring in [world/area_forge/extract/ocr.py](c:/Users/gary/dragonsire/world/area_forge/extract/ocr.py).
- Added OCR label classification to distinguish:
  - `noise`
  - `exit_command`
  - `poi_stub`
  - `landmark`
  - `place`
  - `flavor`
- Removed the direct path from noisy OCR labels into outdoor room titles.
- Changed AreaForge adjudication in [world/area_forge/ai/adjudicator.py](c:/Users/gary/dragonsire/world/area_forge/ai/adjudicator.py) so OCR acts as evidence rather than authority.
- Restricted final room-title promotion to clearly promotable landmark-style OCR.
- Added AI-steered atmosphere and description refinement so the area feel is curated instead of purely deterministic.

### Phase 4 - Add POI stub generation

- Implemented POI stub derivation in [world/area_forge/extract/ocr.py](c:/Users/gary/dragonsire/world/area_forge/extract/ocr.py) for labels such as:
  - `bank`
  - `guild`
  - `shrine`
  - `prison`
  - `academy`
  - `store`
  - `shop`
  - `forge`
  - `smithy`
  - `temple`
  - `inn`
  - `tavern`
  - `office`
  - `hall`
- Implemented stub synthesis in [world/area_forge/ai/adjudicator.py](c:/Users/gary/dragonsire/world/area_forge/ai/adjudicator.py).
- Added special outward exits with aliases such as `go bank` and `enter bank`.
- Added return exits from stub interiors back to the anchor street room using `out` with alias `leave`.
- Persisted stub metadata in built rooms through [world/the_landing.py](c:/Users/gary/dragonsire/world/the_landing.py):
  - `is_stub`
  - `poi_anchor`
  - `poi_exit_name`

### Phase 5 - Improve POI titles and descriptions

- Tightened POI title preservation rules so noisy OCR no longer survives as stub room names.
- Normalized OCR-derived POI names into cleaner titles such as:
  - `Bank`
  - `Guildhall`
  - `Academy`
  - `Prison`
  - `Shrine`
  - `General Store`
  - `Forge`
- Added richer type-specific stub descriptions in [world/area_forge/ai/adjudicator.py](c:/Users/gary/dragonsire/world/area_forge/ai/adjudicator.py) for banks, shrines, guilds, prisons, academies, stores, shops, forges, inns, taverns, temples, and related interiors.
- Added small district-aware prose variation for market and river POIs.

### Phase 6 - Reset and rebuild for a fresh comparison

- Removed the live `new_landing` area from the database.
- Deleted the generated `new_landing` manifest, areaspec, review artifact, and snapshot.
- Rebuilt `new_landing` from scratch and confirmed the rebuild reported `Initial build` rather than an incremental diff.
- Restarted Evennia and validated the rebuilt area is present live.

## Validation

Validated build/runtime outcomes:
- AreaForge runs successfully through the live Evennia shell.
- `new_landing` rebuild succeeds from `maps/CrossingMap (1).png`.
- Current fresh build metrics:
  - `Rooms: 210`
  - `Exits: 468`
  - `Review flags: 470`
- Current generated POI stubs in `new_landing`:
  - `Academy`
  - `Bank`
  - `Forge`
  - `Guildhall`
  - `Prison`
  - `Shop`
  - `Shop`
  - `Shrine`
  - `General Store`

Validated bank-stub behavior live:
- The `Bank` stub exists in `new_landing` with persisted stub metadata.
- The street room `Crowstep Street and Charter Lane 2` has a `bank` exit with aliases:
  - `enter bank`
  - `go bank`
- That bank exit leads to the `Bank` stub room.
- The `Bank` stub room has an `out` exit with alias `leave` that returns to `Crowstep Street and Charter Lane 2`.
- The room number for the street room where `go bank` works is `#4351`.

## Comparison Results

### Earlier regressed AreaForge build

Before the OCR and POI improvements, the first `new_landing` build showed clear naming regression against `the_landing`:
- room-name mismatches at shared coordinates: `84`
- suspicious room names: `32`
- examples included OCR-garbled labels being used as outdoor room names

This earlier state was inferior to `the_landing`.

### Improved intermediate build

After OCR gating, landmark-only promotion, and description refinement:
- room-name mismatches dropped from `84` to `7`
- suspicious room names dropped from `32` to `15`

This was a substantial improvement and removed most of the direct OCR-title regression.

### Current fresh build comparison

Comparing the current generated specs in [build/new_landing/areaspec.json](c:/Users/gary/dragonsire/build/new_landing/areaspec.json) and [build/the_landing/areaspec.json](c:/Users/gary/dragonsire/build/the_landing/areaspec.json):

- street-room coverage: `201` vs `201`
- shared street-room coordinates: `201`
- missing street coordinates on either side: `0`
- street-room name mismatches: `0`
- normalized topology/edge differences: `0`
- normalized stub differences: `0`
- review-report content: identical except for area identity

Description differences observed in the current comparison:
- `13` main-room descriptions differ only because one build says `The Landing` and the other says `New Landing`
- `1` stub description difference remains because the old stub title was `Lawn Forge` and the new cleaned title is `Forge`

Current conclusion:
- against the earlier regressed AreaForge output, the updated AreaForge pipeline is clearly superior
- against the current `the_landing` artifact, the updated `new_landing` output has reached parity
- the current output is slightly cleaner in one visible place because `Forge` is better than `Lawn Forge`

## Files Touched

Primary implementation files involved in this work:
- [world/area_forge/extract/ocr.py](c:/Users/gary/dragonsire/world/area_forge/extract/ocr.py)
- [world/area_forge/ai/adjudicator.py](c:/Users/gary/dragonsire/world/area_forge/ai/adjudicator.py)
- [world/area_forge/run.py](c:/Users/gary/dragonsire/world/area_forge/run.py)
- [world/area_forge/paths.py](c:/Users/gary/dragonsire/world/area_forge/paths.py)
- [world/area_forge/review.py](c:/Users/gary/dragonsire/world/area_forge/review.py)
- [world/the_landing.py](c:/Users/gary/dragonsire/world/the_landing.py)

Generated artifacts validated during this work:
- [manifests/new_landing.yaml](c:/Users/gary/dragonsire/manifests/new_landing.yaml)
- [build/new_landing/areaspec.json](c:/Users/gary/dragonsire/build/new_landing/areaspec.json)
- [build/new_landing/review.txt](c:/Users/gary/dragonsire/build/new_landing/review.txt)
- [build/the_landing/areaspec.json](c:/Users/gary/dragonsire/build/the_landing/areaspec.json)
- [build/the_landing/review.txt](c:/Users/gary/dragonsire/build/the_landing/review.txt)

## Notes

- AreaForge is intentionally being kept as a hybrid system rather than a purely deterministic parser.
- Geometry, IDs, and reproducibility stay procedural where useful.
- Naming, atmosphere, landmark handling, and final area feel are steered through the adjudication layer.
- The remaining review flags are mostly OCR-confidence and naming-review artifacts rather than structural build failures.
- The current `new_landing` build is a clean fresh rebuild from the uploaded map, not a reused incremental artifact.