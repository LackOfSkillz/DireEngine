# MT-507z Field Round-Trip Report

## Scope

- Frontend under test: `http://localhost:4001/direbuilder/`
- Zones exercised: `builder2`, `new_landing`
- Asset under validation: `web/static/webclient/js/direbuilder.js?v=12`
- Supporting template change: `web/templates/webclient/direbuilder.html`

## Implementation Outcome

- Passed: zone-level controlled generation-context fields remain vocab-backed and round-trip through save and refresh.
- Passed: persistent save-error banner remains visible on validation failure and preserves dirty state.
- Passed: ambient message, NPC, and item add-row flows now render editable draft rows instead of collapsing immediately.
- Passed: room atmosphere multi-value tags now serialize as arrays even when only one value is selected.

## Builder2 Validation

### Zone-level generation context

- Passed: `setting_type` pill selection persisted as `town`.
- Passed: `era_feel` pill selection persisted as `medieval`.
- Passed: `climate` pill selection persisted as `temperate`.
- Passed: `culture` multi-select pills persisted as `generic-fantasy`, `multicultural`.
- Passed: `mood` multi-select pills persisted as `tense`.
- Passed: freeform `voice` persisted as `MT507Z zone voice note`.
- Passed: full page reload returned clean state after save.

### Room-level add/update cycle

- Passed: identity fields persisted through save and refresh.
	- `name = MT507Z Room Name`
	- `environment = forest`
	- `short_desc = MT507Z short`
- Passed: manual description persisted as `MT507Z manual description`.
- Passed: room tags persisted with vocab-valid values.
	- `structure = plaza`
	- `specific_function = shop`
	- `named_feature = fountain`
	- `condition = worn`
	- `custom = [mt507z-custom]`
	- `atmosphere.materials = [stone-walls]`
	- `atmosphere.social_character = [commercial]`
	- `atmosphere.surroundings = [market-nearby]`
	- `atmosphere.sensory = [sounds-of-commerce]`
	- `atmosphere.upkeep = well-maintained`
- Passed: stateful fields persisted.
	- `room_states = [foggy]`
	- `stateful_descs.dawn = MT507Z dawn stateful text`
- Passed: connections persisted.
	- `details.graffiti = MT507Z graffiti detail`
	- `ambient.rate = 5`
	- `ambient.messages = [MT507Z ambient message]`
	- existing exit updated to `south -> CRO_450_350` with `typeclasses.exits_slow.SlowDireExit`
	- new exit persisted as `east -> CRO_500_300`
- Passed: room-local population persisted.
	- NPCs: `training_goblin`, `mt507z_npc`
	- Items: `chain_greaves x1`, `mt507z_item x2`
- Passed: save returned `succeeded`, dirty state cleared, and a full reload preserved the edited values.

### Room-level remove cycle

- Passed: removing newly added room state, stateful description, detail, ambient message, NPC, item, and east exit persisted through save and refresh.
- Passed: reverting the edited south exit back to `typeclasses.exits.Exit` persisted.
- Passed: removing added room tag values persisted, leaving only `atmosphere.materials = [stone-walls]` from the interim baseline state.

## New Landing Placements Regression

- Passed: real save on `new_landing` preserved placements-style population storage.
- Passed: top-level placements counts remained unchanged after save.
	- `placements.npcs = 16`
	- `placements.items = 6`
- Passed: no room-local `npcs` or `items` arrays were introduced.

## Legacy Route Smoke Check

- Passed: `/builder/` still loads successfully after the MT-507z changes.

## Failures Found During Validation

### Fixed in this pass

- Room atmosphere multi-value tags were being written as strings when only one value was present.
	- Layer: frontend payload construction
	- Symptom: save returned `validation_failed` even with vocab-valid room tag values.
	- Fix: keep non-`upkeep` atmosphere fields serialized as arrays in `renderTags()`.

### Residual risk

- Room tag and room atmosphere editors still accept arbitrary freeform input even though the backend vocab normalizer only accepts approved values.
	- Layer: frontend validation / editor contract
	- Impact: invalid manual values are still rejected on save, but the persistent banner now makes the failure visible.
	- Status: not addressed in MT-507z code changes; requires a follow-up UI contract pass similar to the zone-level vocab picker work.

## Fixture Restoration

- `worlddata/zones/builder2.yaml` restored from disk backup after validation.
- `worlddata/zones/new_landing.yaml` restored from disk backup after validation.
- Post-restore SHA-256 hashes matched the saved backups for both files.
