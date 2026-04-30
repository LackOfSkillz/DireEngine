# MT-507r Phase 2b.2 Dispatch

Goal: wire the existing DireBuilder working-copy model to a real backend save endpoint so builders can persist zone edits to YAML, clear dirty state on successful save, and use `Save & Switch` as an actual save-then-navigate action.

Precondition:
- Execute this only after Phase 2b.1 is already landed and verified in the current additive `/direbuilder/` route.
- Treat the current frontend contracts in `web/static/webclient/js/direbuilder.js` as authoritative for this phase unless a concrete blocker is discovered.

Non-goals for this phase:
- No discard-from-disk wiring for the overflow `Discard Changes` action.
- No hot-load wiring.
- No description generation wiring.
- No concurrency locking or collaborative conflict resolution.
- No normalization pass that rewrites population storage shapes.
- No changes to legacy `/builder/` behavior or code paths.

Implementation surface:
- Frontend:
  - `web/templates/webclient/direbuilder.html`
  - `web/static/webclient/js/direbuilder.js`
  - `web/static/webclient/css/direbuilder.css`
- Backend additive surface only:
  - `web/urls.py`
  - `web/views.py` or a route-local sibling view module if one already exists for additive DireBuilder work
  - a new helper module for DireBuilder YAML write-back if needed
- Do not modify `dragonsire-browser-v2.js`.
- Do not reuse or mutate legacy builder save logic.

## Existing frontend contract to preserve

These functions and state contracts already exist in 2b.1 and 2b.2 must build on them rather than redefining them:

- `originalZone`
  - immutable deep-frozen baseline captured on page load
- `workingZone`
  - mutable in-memory edit state
- `computeZoneDiff(original, working)`
  - currently returns `null` when clean and a truthy diff object when dirty
- `isDirty()`
  - currently reads `computeZoneDiff(originalZone, workingZone) !== null`
- `attemptZoneSwitch(nextZoneId)`
  - existing zone-switch interception helper used by the dropdown flow
- `window.DireBuilderPageApi`
  - existing lightweight page-local test harness API exposing `attemptZoneSwitch` and `isDirty`

2b.2 may extend these contracts, but it must not break current callers or redefine what clean versus dirty means to the rest of the page.

## New frontend contract to add

Add one dedicated save helper callable from both UI handlers and test automation:

- `saveWorkingZone(options?)`
  - reads the current `workingZone`
  - sends the save request to the backend
  - resolves with the canonical saved zone payload on success
  - rejects or returns a structured failure on error

Expose save observability through `window.DireBuilderPageApi` as well. At minimum add:

- `saveWorkingZone`
- `getDirtyState` or equivalent if useful for validation

This should mirror the same testability pattern already established by `attemptZoneSwitch`.

The `DireBuilderPageApi` must expose enough surface for a test harness to validate save flows without simulating clicks or DOM observation:

- `saveWorkingZone()`
  - triggers a save with the current `workingZone`
- `getSaveState()`
  - returns `idle`, `saving`, `succeeded`, or `failed`
- `getLastSaveError()`
  - returns the last error code or `null`
- `getDirtyState()`
  - returns the current `isDirty()` result

This mirrors the 2b.1 pattern where `attemptZoneSwitch` was exposed on the API for testability. Without these, validating in-flight save behavior in the cramped integrated browser will require simulating clicks and waiting for race-prone DOM mutations, which created friction in earlier phases.

## Save endpoint contract

Endpoint choice for 2b.2:
- Add a dedicated additive endpoint:
  - `POST /direbuilder/api/zone/<zone_id>/save/`

Reasoning:
- `POST` is sufficient for an action-style write in the existing Django stack.
- The route remains clearly scoped to DireBuilder and avoids any ambiguity with legacy builder APIs.

Request body:
- JSON payload containing the builder's current working zone state.
- The payload must include enough data to write both:
  - room-local zone content
  - zone-level generation-context content

Success response:
- `200 OK` with the canonical saved zone JSON in the response body.
- Do not return only `{success: true}`.

Reasoning:
- The frontend should replace `originalZone` with the server-authoritative canonical payload after save.
- This keeps future `isDirty()` checks correct even if the backend normalizes field order, fills defaults, or rebuilds a sibling context field.

Failure response:
- Return structured JSON with this required shape:
  - `ok: false`
  - `error: <code>`
  - `message: <builder-readable summary>`
- Required error codes:
  - `validation_failed`
  - `zone_not_found`
  - `write_failed`
  - `internal_error`
- Required HTTP status codes:
  - `400` for `validation_failed`
  - `404` for `zone_not_found`
  - `500` for `write_failed`
  - `500` for `internal_error`

Frontend retry guidance must differ by error code:
- `validation_failed`
  - `Save was rejected. Some fields may be invalid. Please check your edits and try again.`
- `zone_not_found`
  - `This zone no longer exists on disk. Reload the page to recover.`
- `write_failed`
  - `Couldn't write to disk. Try again, or check the server logs.`
- `internal_error`
  - `Save failed unexpectedly. Try again. If this persists, check the server logs.`

Do not turn save failures into hard crashes in the browser. Failure is a normal recoverable UX path in this phase.

## Generation-context persistence rule

2b.1 established that `generation_context` is not always reliably present on the embedded `current_zone` payload and may be supplied through a separate export path.

2b.2 must preserve that architectural reality:
- Save must explicitly persist zone-level generation-context fields.
- Do not assume every generation-context field naturally lives on the same in-memory shape as room-local zone data on disk.
- If the backend write path needs to split the incoming payload into:
  - zone body fields
  - sibling generation-context fields
  that split is correct and should be implemented intentionally.

Write path guidance:
- Follow the same pattern in reverse that 2b.1 used for reading.
- Do not silently drop generation-context fields because they were supplied by a separate JSON export.

## Population persistence rule

2b.1 established a dual-path population model:
- NPCs and items may come from zone-level `placements`
- or from room-local arrays on the room object

2b.2 must preserve the shape that was loaded.

Decision for this phase:
- Use Option A: save matches read shape exactly.

Rules:
- If a room's NPCs/items were loaded from room-local arrays, save them back as room-local arrays.
- If they were loaded from zone-level `placements`, save them back to `placements`.
- Do not normalize all population data to placements.
- Do not normalize all population data to room-local arrays.
- Do not silently migrate hand-edited YAML to a new storage shape during save.

If the current read payload is insufficient to determine which shape was originally loaded for a given zone, stop and report. Hidden normalization is not allowed in 2b.2.

## YAML write-back expectations

For Phase 2b.2, the save endpoint must normalize YAML output. The write path:

1. Loads zone data via the existing read helper or equivalent.
2. Applies the validated incoming mutations.
3. Writes normalized YAML back to disk using the project's standard YAML dumper.

Normalization is acceptable and expected. This means:
- Field order may differ from the original file.
- Default values may be made explicit where they were implicit.
- Comments will not be preserved.
- Whitespace and quote styles may change.
- Block versus flow style may be normalized.

Do not attempt round-trip YAML preservation in this phase. `ruamel.yaml` or similar comment-preserving parsers are explicitly out of scope.

If a builder discovers that hand-formatted YAML is being normalized by save, that is expected behavior for 2b.2. Round-trip fidelity is deferred to a future phase if it becomes a real problem in practice.

Implementation note:
- add a comment in the YAML writer explaining that formatting normalization is intentional and not a bug.

## Save behavior requirements

Save Zone button:
- `Save Zone` becomes live in this phase.
- On click:
  1. call `saveWorkingZone()`
  2. disable repeated submits while the request is in flight
  3. on success:
     - replace `originalZone` with the canonical saved zone payload
     - replace `workingZone` with a mutable clone of that canonical payload
     - update the dirty indicator so the asterisk clears
     - show a success toast
  4. on failure:
     - keep the current `workingZone`
     - keep dirty state intact
     - show a failure toast with retry guidance

Save & Switch modal action:
- `Save & Switch` stops being inert in 2b.2.
- Required behavior:
  1. call `saveWorkingZone()`
  2. if save succeeds, navigate to the requested zone
  3. if save fails, stay on the current zone, keep dirty state, and show the save-failure message

Dirty clearing:
- Dirty state may clear only after successful persistence and baseline replacement.
- Do not clear dirty state optimistically before the save returns success.

## Save-failure UX

This phase must degrade gracefully when save fails.

Required failure behavior:
- no uncaught modal explosions
- no page reloads as an error escape hatch
- no dirty-state loss
- no silent failure

User-facing result on failed save:
- show an error toast or modal summary
- message should tell the builder that the zone was not saved and they can retry
- keep `Save Zone*` visible
- keep `beforeunload` protection active

Timeouts and `500` responses must follow the same principle:
- dirty stays dirty
- builder remains on the page
- retry is possible

## In-flight save behavior

2b.2 save handling must be cancellation-safe.

Requirements:
- If a save is in flight and the page is still dirty, `beforeunload` protection must continue to behave correctly.
- Do not mark the zone clean until the request succeeds.
- Avoid double-submit races from repeated clicks on `Save Zone` or `Save & Switch`.

## In-flight save UI lock

While a save request is in flight:
- All editable fields, pills, and accordions are disabled.
- `Save Zone`, `Save & Switch`, and zone switching are blocked.
- A saving state is visible on the `Save Zone` button.
- Modal close buttons remain functional. The modal may be dismissed, but the save continues running.

When the save resolves:
- On success:
  - unlock fields
  - replace baseline
  - update the dirty indicator
- On failure:
  - unlock fields
  - keep `workingZone`
  - keep dirty state
  - show the error

Reasoning:
- this prevents a race where the builder edits during save and ends up with a newer `workingZone` than baseline in a confusing state.

An explicit loading state on the save button is required.

## Validation and backend behavior

Backend responsibilities for this phase:
- validate that the target zone exists
- validate the incoming payload shape enough to prevent destructive malformed writes
- persist zone data to disk
- return canonical saved JSON after write

If save-to-disk requires changing the zone read model because the current load path does not preserve enough information to write back safely, stop and report. Redesigning round-trip zone loading is not part of 2b.2.

Concurrency model for 2b.2:
- accept last-write-wins
- do not add locking in this phase
- note this limitation in code comments or implementation notes if needed

## Discard remains deferred

The overflow `Discard Changes` action must remain inert in 2b.2.

Allowed behavior in this phase:
- same explanatory modal as 2b.1
- same non-persistent placeholder behavior

Disallowed behavior in this phase:
- reloading from disk
- resetting `workingZone`
- clearing dirty state

Discard-from-disk is Phase 2b.3 work and must not be partially wired here.

## Validation targets

- Saving a dirty zone writes YAML successfully and clears `Save Zone*`.
- Saving a clean zone is harmless and does not introduce dirty state.
- Failed save keeps `Save Zone*` visible and keeps all unsaved edits in memory.
- `Save & Switch` saves first and only navigates after success.
- Failed `Save & Switch` leaves the user on the current zone with dirty state intact.
- Zone-level generation-context edits are persisted correctly.
- Population writes preserve the original storage shape used by the loaded zone.
- `/builder/` remains unaffected.

## Stop conditions

- Stop after real save wiring is complete for the additive `/direbuilder/` route.
- Do not wire discard-from-disk behavior.
- Do not wire hot-load.
- Do not wire description generation.
- Do not mutate legacy builder save code.

Follow-up note:
- Phase 2b.3 will wire `Discard Changes` to reload the current zone from disk and replace `workingZone` from a fresh baseline.