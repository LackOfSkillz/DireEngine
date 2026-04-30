# MT-512 Terrain Validation

## Scope

- Added strict room terrain fields (`terrain.primary`, `terrain.secondary`) to the DireBuilder room payload path.
- Added canonical terrain vocabulary in `world/builder/vocab/terrain_vocab.yaml`.
- Reused existing DireBuilder chip-editor UI for strict single-select terrain pickers in the Identity tab.
- Injected a flattened forage summary from `world/builder/content/forage_catalog.yaml` into the DireBuilder template context.
- Added room terrain tooltip entries.
- Left legacy `/builder/` and live engine forage behavior untouched.

## Data Checks

- Confirmed `world/builder/content/forage_catalog.yaml` parses successfully.
- Confirmed catalog counts: `139` total entries, `34` healing herbs, `9` categories.
- Confirmed terrain summary is available in the page and drives preview text.

## Live DireBuilder Validation

URL validated: `http://localhost:4001/direbuilder/?zone=builder2`

### Runtime refresh

- The first browser load served stale template/static assets (`direbuilder.css?v=14`, `direbuilder.js?v=17`).
- Restarted the local Evennia web server with `startWeb.bat`.
- Confirmed refreshed page served updated assets (`direbuilder.css?v=15`, `direbuilder.js?v=18`).

### UI checks

- Confirmed the Identity tab now contains a collapsible `Terrain` accordion.
- Confirmed `Primary` picker renders `Outdoor` and `Indoor` as strict single-select pills.
- Confirmed `Specific` picker renders the full strict secondary terrain vocabulary.
- Confirmed tooltips data includes `room.terrain_primary` and `room.terrain_secondary` entries.
- Confirmed preview line is empty when no terrain is selected.

### Save / reload check

Room used for validation: `CRO_450_300` in `builder2`

1. Selected `Primary = outdoor`.
2. Selected `Specific = coastal`.
3. Confirmed summary updated to `Outdoor, Coastal`.
4. Confirmed preview updated to `21 resources available · 9 healing: Georin grass, Nilos grass, Sufil sap`.
5. Saved the zone successfully.
6. Reloaded the DireBuilder page.
7. Confirmed terrain selections persisted after reload.

### Validation failure check

- Intercepted the outgoing DireBuilder save request in-browser and replaced the room payload with `terrain.secondary = bogus_terrain`.
- Confirmed backend returned HTTP `400` with `validation_failed`.
- Confirmed the persistent DireBuilder save error banner appeared.
- Confirmed banner message was explicit:

`room.terrain.secondary must be one of: boreal_forest, chaparral, coastal, deciduous_forest, desert, badland, freshwater_wetland, highland_mountain, ice_cap, marine, photophobic, rainforest, rural_cultivated, savannah, scrub_and_thorn, steppe, subterranean, urban_cultivated`

## Legacy Route Check

URL validated: `http://localhost:4001/builder/`

- Confirmed legacy `/builder/` still loads.
- Confirmed DireBuilder terrain DOM ids are not present on the legacy builder page.

## Cleanup

- Cleared the temporary `outdoor/coastal` validation selection from `builder2` after verification.
- Confirmed `worlddata/zones/builder2.yaml` returned to `terrain.primary: null` and `terrain.secondary: null` for the validated room.