# MT-507u Phase 2b.3 Dispatch

Goal: wire DireBuilder's overflow `Discard Changes` action to reload the current zone from disk without a full page refresh, replace both the baseline and working copy with that fresh canonical payload, and clear dirty state only after the discard fetch succeeds.

Precondition:
- Execute this only after Phase 2b.2 is landed and verified in the additive `/direbuilder/` route.
- Treat the current frontend contracts in `web/static/webclient/js/direbuilder.js` as authoritative unless a concrete blocker is discovered.
- Reuse the 2b.2 canonical zone JSON shape as the authoritative read/write contract for frontend state replacement.

Non-goals for this phase:
- No full page reload as the primary discard implementation.
- No hot-load wiring.
- No description generation wiring.
- No auth or permission redesign.
- No undo stack or change-history system.
- No changes to legacy `/builder/` behavior or code paths.

Implementation surface:
- Frontend:
  - `web/templates/webclient/direbuilder.html`
  - `web/static/webclient/js/direbuilder.js`
  - `web/static/webclient/css/direbuilder.css`
- Backend additive surface only:
  - `web/urls.py`
  - `web/views.py` or a route-local sibling view module if one already exists for additive DireBuilder work
- Do not modify `dragonsire-browser-v2.js`.
- Do not reuse or mutate legacy builder APIs.

## Architectural rule to preserve

2b.2 surfaced a real contract bug: display-formatted generation-context values such as `"(not set)"` were treated as canonical saveable data, causing the backend to correctly reject save attempts.

That lesson is authoritative for 2b.3 and all later phases:

- Discard must round-trip raw canonical data shapes only.
- Display formatting belongs in render helpers, not in in-memory state models.
- If the page needs user-facing placeholder text, generate it at render time from raw null/empty values.
- Do not let display strings leak into `workingZone`, discard payloads, or future generation/score inputs.

This rule applies equally to future Zone Score, Generate Description, and other Phase 3 surfaces.

## Existing frontend contract to preserve

These functions and state contracts already exist and 2b.3 must build on them rather than redefining them:

- `originalZone` — immutable deep-frozen baseline captured from the last authoritative server payload
- `workingZone` — mutable in-memory edit state
- `computeZoneDiff(original, working)` — returns `null` when clean and a truthy diff object when dirty
- `isDirty()` — reads `computeZoneDiff(originalZone, workingZone) !== null`
- `attemptZoneSwitch(nextZoneId)` — existing zone-switch interception helper
- `saveWorkingZone(options?)` — existing save helper from 2b.2
- `window.DireBuilderPageApi` — existing page-local test harness API

2b.3 may extend these contracts, but it must not break their current callers or redefine what clean versus dirty means.

## New frontend contract to add

Add a dedicated discard helper callable from both UI handlers and test automation:

- `discardWorkingZone(options?)`
  - fetches the current zone fresh from disk via the additive GET endpoint
  - resolves with the canonical zone payload on success
  - rejects or returns a structured failure on error

`discardWorkingZone()` always fetches from disk regardless of current dirty state. The "disable when clean" rule is a UI affordance, not a constraint on the function itself. Test automation and future features may need to fetch authoritative state independently of dirty status.

Expose discard observability through `window.DireBuilderPageApi`:

- `discardWorkingZone()` — triggers discard for the current zone
- `getDiscardState()` — returns `idle`, `discarding`, `succeeded`, or `failed`
- `getLastDiscardError()` — returns the last discard error code or `null`
- `getDirtyState()` — already present from 2b.2, returns the current `isDirty()` result

This mirrors the 2b.2 save observability pattern and keeps discard validation API-first.

## Discard endpoint contract

Endpoint:
- `GET /direbuilder/api/zone/<zone_id>/`

Reasoning:
- Avoids a disruptive full page reload.
- Preserves active tab, room selection, scroll state, and other in-page UI state unless the discard operation itself intentionally changes them.
- Reuses the same canonical JSON shape established by 2b.2 save success.
- Creates a reusable authoritative read endpoint for future compare-to-disk or refresh flows.

Success response:
- `200 OK` with the canonical zone JSON in the response body.
- The response shape MUST match the canonical save response from 2b.2.
- Do not return a wrapper like `{zone: ...}` if save returns the bare canonical payload.

Failure response:
- Return structured JSON with this required shape:
  - `ok: false`
  - `error: <code>`
  - `message: <builder-readable summary>`
- Required error codes:
  - `zone_not_found`
  - `internal_error`
  - `operation_in_progress` (when a save or another discard is already in flight)
- Required HTTP status codes:
  - `404` for `zone_not_found`
  - `500` for `internal_error`
  - `409` for `operation_in_progress`

Frontend retry guidance must differ by error code:
- `zone_not_found` — `This zone no longer exists on disk. Reload the page to recover.`
- `internal_error` — `Couldn't reload this zone from disk. Try again. If this persists, check the server logs.`
- `network_error` — `Couldn't reload this zone from disk. Check your connection and try again.`
- `operation_in_progress` — `Another save or discard is still running. Wait for it to finish, then try again.`

Do not turn discard failures into hard crashes or implicit full reloads.

## Discard behavior requirements

Overflow `Discard Changes` action:
- `Discard Changes` becomes live in this phase.
- On click when dirty:
  1. Open the confirm modal.
  2. If the builder confirms, call `discardWorkingZone()`.
  3. Disable repeated discard submits while the request is in flight.
  4. On success:
     - Replace `originalZone` with the canonical zone payload fetched from disk.
     - Replace `workingZone` with a mutable clone of that canonical payload.
     - Fully re-render the room editor, zone editor, and map from that payload (see "Full re-render rule" below).
     - Clear dirty state through baseline replacement.
     - Reset save state: `getSaveState()` returns `idle` and `getLastSaveError()` returns `null`. This prevents stale save-failure indicators from persisting after a successful discard, since the failed save's intent (saving the edits) no longer applies once those edits have been discarded.
     - Close the overflow modal.
     - Show a success toast.
  5. On failure:
     - Keep the current `workingZone`.
     - Keep dirty state intact.
     - Leave the builder on the page.
     - Show a failure toast with retry guidance per error code.

Clean-zone behavior:
- If `isDirty()` is false, the `Discard Changes` overflow menu item is disabled.
- Do not open the confirm modal when there is nothing to discard.
- No no-op confirm flow is needed for clean state.

Save and discard are mutually exclusive operations:
- Save is blocked during in-flight discard.
- Discard is blocked during in-flight save.
- Zone switch is blocked during either.
- The UI lock established in 2b.2 must extend to cover both directions.
- If the test harness calls `saveWorkingZone()` while a discard is in flight (or vice versa), the second call must reject with a structured failure carrying error code `operation_in_progress`. Do not race; do not queue.

Dirty clearing:
- Dirty state may clear only after successful discard fetch and baseline replacement.
- Do not clear dirty optimistically before the fresh canonical payload returns.

## Confirm modal requirements

Discard is destructive. The modal copy is locked.

Required modal content:
- Title: `Discard Changes?`
- Body: `You have unsaved changes in this zone. Discarding now will permanently lose those edits and reload the zone from disk.`
- Cancel button label: `Cancel`
- Confirm button label: `Discard Changes`
- Cancel must be visually emphasized as the safer default action.
- Escape closes the modal as Cancel.

Do not paraphrase or substitute alternative copy.

## Full re-render rule

After successful discard, the right-column editor must fully re-render from the fresh canonical room payload, not patch the existing rendered DOM. Stale-state bugs where edits made before discard remain visible in editor controls even though working state has been reset are not acceptable.

The map workspace must also re-render from canonical state. If the zone graph changed on disk between page load and discard (exits added or removed by another process, rooms added or deleted, etc.), the map must reflect the new graph.

## State replacement and UI preservation rules

The discard flow should preserve page-local UI context when that context is still valid after baseline replacement.

Required behavior:
- Preserve the current active tab (Identity, Description, Tags, Stateful, Connections, Population).
- Preserve the current room selection if that room still exists in the freshly reloaded zone.
- If the previously selected room no longer exists, fall back to the first available room or empty-state behavior.
- Keep the page in place without a full reload.

Accordion expansion state preservation is optional for 2b.3:
- If cheap to preserve, that is acceptable.
- If it materially increases complexity, do not add it in this phase.

## Population and generation-context rules

Discard must reload the same canonical shape that save success returns. That means:

- Zone-level `generation_context` comes back in raw canonical form.
- `_direbuilder.population_storage` metadata is present in JSON if that is part of the canonical frontend contract.
- YAML-only formatting concerns remain backend-local and must not leak into frontend state assumptions.

Do not rebuild a partial zone shape on the frontend. Replace state from the authoritative server response.

## Discard-failure UX

This phase must degrade gracefully when discard fails.

Required failure behavior:
- No uncaught modal explosions.
- No page reload as an error escape hatch.
- No dirty-state loss.
- No silent failure.

User-facing result on failed discard:
- Show an error toast or modal summary.
- Message tells the builder that the zone was not reloaded from disk and they can retry.
- Keep `Save Zone*` visible if the zone was dirty before discard.
- Keep `beforeunload` protection active.

Timeouts and network failures follow the same principle:
- Dirty stays dirty.
- Builder remains on the page.
- Retry is possible.

## In-flight discard behavior

2b.3 discard handling must be race-safe.

Requirements:
- If a discard is in flight, do not allow repeated discard submissions.
- If a discard is in flight, save and zone switching are blocked until it resolves.
- Do not mutate `workingZone` while the discard fetch is in flight.
- Do not clear dirty until the authoritative reload succeeds.

An explicit loading state on the discard confirmation action is required.

## Validation and backend behavior

Backend responsibilities for this phase:
- Validate that the target zone exists.
- Load the canonical zone JSON from disk using the same read path as page load and save success.
- Return that canonical JSON unchanged in meaning.

If the existing load helper cannot return the same canonical shape that save success returns, stop and report. Divergent read models are not acceptable for 2b.3.

Auth/permission rule for this phase:
- Discard uses the same authentication and permission model as save.
- Do not redesign auth logic in 2b.3.
- If auth enforcement is not yet implemented on save, do not invent a new auth layer just for discard.

## Validation targets

- Dirty discard fetches the current zone from disk and clears `Save Zone*`.
- Discard preserves the current tab and selected room when that room still exists.
- Discard falls back safely if the selected room no longer exists in the refreshed zone.
- Clean-zone Discard Changes menu item is disabled and does not open the modal.
- Discard is blocked during in-flight save with structured `operation_in_progress` rejection.
- Save is blocked during in-flight discard with structured `operation_in_progress` rejection.
- Failed discard keeps `Save Zone*` visible and keeps all unsaved edits in memory.
- Successful discard resets `getSaveState()` to `idle` and `getLastSaveError()` to `null`.
- Discard response shape matches the canonical save response shape exactly.
- Right-column editor and map both fully re-render from canonical state, not DOM-patched.
- `"(not set)"` regression check: discard a zone with unset generation_context fields, then save the post-discard state. Save must succeed without `validation_failed` rejection. (This catches any regression of the 2b.2 display-string leak bug class.)
- `/builder/` remains unaffected.

## Stop conditions

- Stop after real discard-from-disk wiring is complete for the additive `/direbuilder/` route.
- Do not add hot-load wiring.
- Do not add description generation.
- Do not add an undo system.
- Do not redesign auth or legacy builder flows.

Follow-up note:
- Phase 3 may formalize page-level interactive-element registration if the save/discard UI-lock surface continues to grow.