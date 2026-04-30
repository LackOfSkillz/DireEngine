# MT-507v (Phase 2b.3) Execution Checklist

Authoritative spec: `docs/mt507u_2b3_dispatch.md`

This file is the execution checklist for Phase 2b.3. If anything here conflicts with the spec, the spec wins.

## Scope reminder

In scope:
- Add a DireBuilder-only read endpoint for canonical zone reload.
- Wire overflow `Discard Changes` to fetch fresh zone state from disk.
- Replace both baseline and working copy on successful discard.
- Clear dirty state only after confirmed discard success.
- Reset save state after successful discard.
- Expose discard observability through `window.DireBuilderPageApi`.

Out of scope:
- Full page reload as the main discard implementation.
- Hot load.
- Description generation.
- Auth redesign.
- Undo or history system.
- Legacy `/builder/` behavior changes.

## Execution order

### 1. Preserve the 2b.2 state contract

- Keep `originalZone`, `workingZone`, `computeZoneDiff(...)`, `isDirty()`, `saveWorkingZone(...)`, and `attemptZoneSwitch(...)` intact.
- Reuse the same canonical zone normalization path for both save success and discard success.
- Do not change the external meaning of clean vs dirty.

### 2. Add the backend read endpoint

- Add additive route in `web/urls.py`:
  - `GET /direbuilder/api/zone/<zone_id>/`
- Add a DireBuilder-scoped view that:
  - Validates the target zone.
  - Loads the canonical zone JSON from disk through the existing read helper.
  - Returns the same canonical JSON shape used by save success.
- Keep this route isolated from legacy builder flows.

Required backend failure status codes:
- `404` for `zone_not_found`
- `409` for `operation_in_progress`
- `500` for `internal_error`

### 3. Add a dedicated discard helper on the frontend

- Add `discardWorkingZone(options?)` in `direbuilder.js`.
- It should:
  - Fetch `/direbuilder/api/zone/<zone_id>/`.
  - Return the canonical zone JSON on success.
  - Surface structured failure details on error.
- Reuse the same baseline-replacement path already used after successful save.
- The function must be unconditional: it fetches from disk regardless of current dirty state. The "disable when clean" rule applies to the UI menu item, not the function.

Add a discard-state tracker so the UI can lock correctly during discard.
- Minimum states: `idle`, `discarding`, `succeeded`, `failed`.

The discard-state tracker must be readable through `window.DireBuilderPageApi` via:
- `getDiscardState()`
- `getLastDiscardError()`

### 4. Make discard state replacement explicit

- After successful discard:
  - Replace the baseline with the canonical zone returned by the server.
  - Replace `workingZone` with a mutable normalized clone of that canonical payload.
  - Fully re-render visible room editor, zone editor, and map panels from the new state. Do not DOM-patch — re-render.
  - Call `updateDirtyIndicator()` so the asterisk clears.
  - Reset save state: set `getSaveState()` to `idle` and clear `getLastSaveError()` to `null`.

### 5. Keep raw-data contracts intact

- Do not use display-formatted placeholder strings as canonical data.
- Keep display formatting in render helpers only.
- Ensure discard consumes raw `generation_context` values and canonical `_direbuilder` metadata exactly as provided by the server.
- The fresh canonical payload from discard must be acceptable as save input without modification.

### 6. Wire overflow Discard Changes

- Replace the inert 2b.2 placeholder behavior.
- When dirty:
  - Open a confirm modal with the locked destructive copy (see step 6a).
  - `Cancel` is the visually emphasized default action.
  - `Escape` closes the modal as Cancel.
  - Confirm action calls `discardWorkingZone()`.
- On success:
  - Close the modal.
  - Clear dirty through baseline replacement.
  - Reset save state.
  - Show success feedback.
- On failure:
  - Keep dirty state.
  - Keep unsaved edits in memory.
  - Show failure guidance per error code.

### 6a. Lock the modal copy verbatim

- Title: `Discard Changes?`
- Body: `You have unsaved changes in this zone. Discarding now will permanently lose those edits and reload the zone from disk.`
- Cancel button label: `Cancel`
- Confirm button label: `Discard Changes`

Do not paraphrase, abbreviate, or substitute alternative copy.

### 7. Disable discard when clean

- If `isDirty()` is false:
  - Disable the overflow `Discard Changes` menu item.
  - Do not open the confirm modal.
  - Do not show a no-op confirmation flow.

### 8. Enforce save/discard mutual exclusion

- While save is in flight:
  - Overflow interactions remain locked.
  - Discard cannot start.
- While discard is in flight:
  - Save cannot start.
  - Zone switch cannot start.
- If `saveWorkingZone()` is called while discard is in flight, reject with structured failure carrying error code `operation_in_progress`.
- If `discardWorkingZone()` is called while save is in flight, reject the same way.
- Do not race. Do not queue.

### 9. Enforce the in-flight discard lock

- While discard is in flight:
  - Do not allow repeated discard submissions.
  - Block save and zone switching.
  - Block mid-discard edits that would mutate `workingZone`.
  - Show a visible loading state on the confirm action.
- When discard resolves:
  - On success: unlock fields, clear dirty, reset save state.
  - On failure: unlock fields, keep dirty.

### 10. Preserve useful UI context

- Keep the current tab selected after discard.
- Preserve current room selection if that room still exists in the reloaded zone.
- If the selected room no longer exists, fall back to the first room or empty-state behavior.
- Do not do a full page reload.

Accordion expansion state is optional and should not block the phase.

### 11. Implement graceful failure UX

- On discard failure:
  - Keep the current page state intact.
  - Keep dirty state intact.
  - Show toast or modal summary with retry guidance.
- Frontend messaging must switch on the backend error code:
  - `zone_not_found`
  - `internal_error`
  - `network_error`
  - `operation_in_progress`
- No page reload as an error fallback.

### 12. Extend `window.DireBuilderPageApi`

- Add:
  - `discardWorkingZone()`
  - `getDiscardState()`
  - `getLastDiscardError()`
- Keep existing save API methods intact.

### 13. Keep beforeunload semantics correct

- Dirty should remain true while discard is in flight.
- Do not clear dirty optimistically.
- `beforeunload` must still warn until discard succeeds and the page reaches a confirmed clean state.

### 14. Cache-bust

- Bump `direbuilder.js` version in the template.
- Bump `direbuilder.css` if CSS changes for discard state, locked menu styling, or modal copy adjustments.

### 15. Verification

1. Page loads with no console errors.
2. Dirty the zone, trigger Discard Changes, confirm. Discard succeeds, dirty clears, save state resets to `idle`.
3. Discard preserves the current active tab.
4. Discard preserves the selected room when that room still exists after reload.
5. If feasible, simulate a case where the selected room disappears between load and discard. Verify safe fallback behavior.
6. Clean-zone Discard Changes menu item is disabled. Modal does not open.
7. While save is in flight, calling discard rejects with `operation_in_progress`.
8. While discard is in flight, calling save rejects with `operation_in_progress`.
9. Force a failing discard path. Dirty remains, edits remain, failure message appears with correct error code.
10. Discard response shape is accepted by the same normalization path used for save success.
11. Modal copy matches the locked strings exactly: title `Discard Changes?`, body verbatim, buttons `Cancel` and `Discard Changes`.
12. After successful discard, the right-column editor and map both fully re-render. Stale DOM from before discard is not visible.
13. `"(not set)"` regression check: edit a zone, leave generation_context fields unset, click Discard, then attempt save. Save must succeed without `validation_failed`. This catches regressions of the 2b.2 display-string leak.
14. `/builder/` still loads unchanged.

## Stop conditions

- Backend changes stay limited to the additive DireBuilder read route and its helpers.
- Do not add page reload fallback as the main implementation.
- Do not wire hot-load.
- Do not wire description generation.
- Do not redesign auth or legacy builder flows.