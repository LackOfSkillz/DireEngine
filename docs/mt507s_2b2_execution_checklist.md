# MT-507s (Phase 2b.2) Execution Checklist

Authoritative spec: `docs/mt507r_2b2_dispatch.md`

This file is the execution checklist for Phase 2b.2. If anything here conflicts with the spec, the spec wins.

## Scope reminder

In scope:
- add a DireBuilder-only save endpoint
- send `workingZone` to that endpoint
- receive canonical saved zone JSON back
- replace the local baseline on success
- clear dirty state only after confirmed save
- make `Save & Switch` perform save-then-navigate

Out of scope:
- discard-from-disk
- hot load
- description generation
- legacy `/builder/` save behavior
- population normalization
- concurrency locking

## Execution order

### 1. Preserve the 2b.1 state contract

- Keep `originalZone`, `workingZone`, `computeZoneDiff(...)`, `isDirty()`, and `attemptZoneSwitch(...)` intact as the existing page contract.
- If needed, change `const originalZone` to a writable baseline holder so successful saves can replace it safely.
- Do not change the external meaning of clean vs dirty.

### 2. Add a dedicated save helper on the frontend

- Add `saveWorkingZone(options?)` in `direbuilder.js`.
- It should:
  - read the current `workingZone`
  - POST it to `/direbuilder/api/zone/<zone_id>/save/`
  - return the canonical saved zone JSON on success
  - surface structured failure details on error
- Reuse this function from both the Save Zone button and Save & Switch modal path.

Add a small save-state tracker as well so the UI can lock correctly during save.
- Minimum states:
  - `idle`
  - `saving`
  - `succeeded`
  - `failed`

The save-state tracker must be readable through `window.DireBuilderPageApi` via:
- `getSaveState()`
- `getLastSaveError()`

The tracker is the source of truth for both the UI lock and the test harness.

### 3. Make baseline replacement explicit

- After successful save:
  - replace the baseline with the canonical saved zone returned by the server
  - replace `workingZone` with a mutable normalized clone of that canonical payload
  - rerender visible room and zone panels if needed
  - call `updateDirtyIndicator()` so the asterisk clears

### 4. Preserve generation-context persistence

- Treat zone-level `generation_context` as a first-class save surface.
- Persist it through the backend write path even if it is supplied separately from the embedded zone payload on read.
- Do not drop `setting_type`, `era_feel`, `culture`, `mood`, `climate`, or `voice`.

### 5. Preserve loaded population shape

- Respect the 2b.1 dual-path population model.
- If the loaded zone used room-local NPC/item arrays, write room-local arrays back.
- If the loaded zone used zone-level `placements`, write `placements` back.
- Do not normalize storage shape during save.
- If the loaded payload does not preserve enough shape information to do this safely, stop and report.

### 6. Add the backend save endpoint

- Add additive route in `web/urls.py`:
  - `POST /direbuilder/api/zone/<zone_id>/save/`
- Add a DireBuilder-scoped view that:
  - validates the request body
  - loads the target zone
  - writes the updated YAML to disk
  - returns canonical saved zone JSON
- Keep this route isolated from legacy builder save flows.

### 7. Return canonical saved JSON

- Do not return only `{success: true}`.
- Return the server-authoritative zone JSON payload that the frontend can adopt as both:
  - new baseline
  - new working copy source

### 8. Implement graceful failure UX

- On save failure:
  - keep the current page state intact
  - keep dirty state intact
  - show toast or modal summary with retry guidance
- Frontend messaging must switch on the backend error code:
  - `validation_failed`
  - `zone_not_found`
  - `write_failed`
  - `internal_error`
- This must cover:
  - validation errors
  - `500` responses
  - network failures
  - timeouts
- No page reload as an error fallback.

Required backend status codes:
- `400` for `validation_failed`
- `404` for `zone_not_found`
- `500` for `write_failed`
- `500` for `internal_error`

### 9. Wire Save Zone button

- Replace the inert 2b.1 handler.
- On click:
  - if a save is already in flight, ignore extra clicks
  - set save state to `saving`
  - disable all editable controls while save is in flight
  - visibly mark the button as saving
  - call `saveWorkingZone()`
  - on success, clear dirty state through baseline replacement
  - on failure, keep dirty and show failure guidance
  - in both cases, unlock the page when the request resolves

### 10. Wire Save & Switch

- Update `attemptZoneSwitch(nextZoneId)` so dirty-zone Save & Switch:
  - calls `saveWorkingZone()`
  - waits for success
  - navigates only after success
- On failure:
  - stay on current zone
  - keep dirty state
  - show the save error

### 11. Keep beforeunload semantics correct

- Dirty should remain true while save is in flight.
- Do not clear dirty optimistically.
- `beforeunload` must still warn during an in-flight save if the page has not yet reached a confirmed clean state.

### 11a. Enforce the in-flight UI lock

- While save is in flight:
  - all editable fields, pills, and accordions are disabled
  - save buttons and zone switching are blocked
  - modal dismiss remains allowed
- Do not allow mid-save edits to create a newer `workingZone` than the snapshot being persisted.

### 12. Leave discard inert

- Do not wire overflow `Discard Changes` to disk reload in this phase.
- Keep current placeholder behavior or equivalent explanatory modal.
- Do not clear dirty state through discard in 2b.2.

### 13. Cache-bust

- Bump `direbuilder.js` version in the template.
- Bump `direbuilder.css` too if CSS changes for saving state or error styling.

### 13a. Normalize YAML intentionally

- Use the standard YAML dumper.
- Accept formatting normalization as expected behavior.
- Add a writer comment explaining that comment/format preservation is intentionally out of scope.

### 14. Verification

1. Page loads with no console errors.
2. Edit a room field and click Save Zone. Save succeeds, dirty clears, success toast appears.
3. Edit a zone-level generation-context field and save. Dirty clears and data survives reload.
4. Edit NPCs/items in a zone using room-local population shape. Save preserves room-local shape.
5. Edit NPCs/items in a zone using `placements`. Save preserves `placements` shape.
6. Force a failing save path if feasible. Dirty remains, edits remain, failure message appears.
7. Dirty zone switch -> Save & Switch saves and navigates only after success.
8. Failed Save & Switch keeps the user on the same zone with dirty state intact.
9. While save is in flight, repeated save clicks do not double-submit.
10. While save is in flight, editable controls are locked and cannot mutate `workingZone`.
11. Overflow Discard Changes still does not reload from disk.
12. `/builder/` still loads unchanged.

## Stop conditions

- Backend changes stay limited to the additive DireBuilder save route and its helpers.
- Do not redesign zone loading for full round-trip YAML fidelity.
- Do not wire discard.
- Do not wire hot-load.
- Do not wire description generation.