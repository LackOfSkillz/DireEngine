# DRG-LANDING-V2-MANIFEST-AND-MAP-FILTER-001

## Purpose

- Fix the Builder V2 dropdown so it reads canonical Landing from a V2 YAML manifest.
- Remove hidden and secret exits from AreaForge map rendering so local and zone maps match room exit visibility.

## Sections

### A. Write `worlddata/zones/the_landing.yaml`

- Use the existing `write_zone_export("the_landing")` service.
- Validate the generated manifest by loading it through `web.views._load_builder_zone_yaml`.

### B. Archive `worlddata/zones/new_landing.yaml`

- Move the stale V2 manifest to `worlddata/zones/_archive/`.
- Preserve the file for diagnostics; do not delete it.

### C. Startup V2 manifest sync

- After `ensure_full_canonical_crossing()`, verify `the_landing.yaml` exists and has an expected room count.
- Regenerate with `write_zone_export("the_landing")` if missing or stale.
- Log and append guard traces for pass/fail without blocking startup.

### D. Hidden-exit map filter

- Add a shared helper in `world/area_forge/map_api.py` that hides exits where `db.hidden_exit` or `db.secret` is truthy.
- Apply the helper in both `get_local_map()` and `_collect_room_edges()`.

### E. Tests

- Cover manifest write/load, V2 zone listing, manifest archive behavior, startup regeneration, and hidden-exit filtering for local and zone maps.

## Halts

- Do not hand-write the V2 manifest; use `write_zone_export`.
- Do not add character-aware discovery logic for hidden exits in this dispatch.
- Do not touch FIXTURE-SAFETY-001 guards.
- Do not raise from the startup manifest verification path.

## Expected Outcome

- Builder V2 shows `the_landing` and no longer shows `new_landing`.
- Local and zone maps omit hidden and secret exits while room descriptions remain unchanged.