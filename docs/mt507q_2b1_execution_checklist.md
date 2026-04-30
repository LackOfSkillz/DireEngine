# MT-507q (Phase 2b.1) Execution Checklist

Authoritative spec: `docs/mt507p_2b1_dispatch.md`

This file is the execution checklist for Phase 2b.1. If anything here conflicts with the spec, the spec wins.

## Scope reminder

In scope:
- lift `readonly` on permitted fields
- build working-copy state
- implement a diff helper
- wire dirty state to `Save Zone*`
- protect against zone switch and browser unload with unsaved changes

Out of scope:
- any backend call
- persistence to disk
- clearing dirty state on Save
- Hot Load
- Generate Description
- discard-from-disk behavior

## Execution order

### 1. State model

- Add `originalZone` as a deeply frozen clone of the embedded zone JSON.
- Add `workingZone` as a mutable clone of the same data.
- Keep all edits flowing through `workingZone`.

### 2. Diff function

- Add `computeZoneDiff(original, working)`.
- `null` means clean.
- Any truthy diff object means dirty.
- For 2b.1, a simple deep-equality based diff is acceptable.

### 3. Lift `readonly` per spec

- Identity: Name, Short Description, Environment editable; Room Id stays read-only.
- Description: Manual Description editable; preview pane stays read-only.
- Tags: pill toggles and custom tags editable.
- Stateful: room states and stateful descriptions editable.
- Connections: exit rows, details, and ambient messages editable.
- Population: NPC/item add-remove-reorder editable.
- Zone Editor: setting type, era, cultural palette, mood, climate, voice notes editable.
- Zone Browser stays read-only.

### 4. Dirty flag UI

- Add `updateDirtyIndicator()`.
- Toggle `Save Zone` vs `Save Zone*`.
- Add `is-dirty` styling to the primary save button.
- Optionally mark the zone switcher too.

### 5. Zone switch protection

- Clean zone: navigate normally.
- Dirty zone: restore dropdown, open confirm modal.
- Actions:
  - `Save & Switch`: visibly deferred to 2b.2, no fake save.
  - `Discard & Switch`: navigate away and abandon in-memory edits.
  - `Cancel`: stay put.

### 6. Browser unload protection

- Register `beforeunload` only when the working zone is dirty.

### 7. Save Zone button stays inert

- No backend call.
- No dirty clear.
- Optional toast: `Save wiring lands in Phase 2b.2`.

### 8. Cache-bust

- Bump `direbuilder.js` version in the template.
- Bump `direbuilder.css` too if CSS changes.

### 9. Verification

1. Page loads with no console errors.
2. Editing Name shows `Save Zone*`.
3. Reverting the edit removes the asterisk.
4. Editing a tag pill shows the asterisk.
5. Editing a zone-editor pill shows the asterisk.
6. Editing connections shows the asterisk.
7. Dirty zone switch opens the confirm modal.
8. Cancel keeps the current zone and dirty state.
9. Discard & Switch loads the next zone cleanly.
10. Dirty tab close or reload triggers browser warning.
11. Clicking Save Zone does not clear dirty state.
12. `/builder/` still loads unchanged.

## Stop conditions

- Edit only the DireBuilder template, CSS, and JS unless blocked.
- Do not begin backend save work.
- Do not begin disk reload work.
- Do not begin hot-load or description generation work.