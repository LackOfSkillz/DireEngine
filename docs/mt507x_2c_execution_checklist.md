# MT-507x (Phase 2c) Execution Checklist

Authoritative spec: `docs/mt507w_2c_dispatch.md`

This file is the execution checklist for Phase 2c. If anything here conflicts with the spec, the spec wins.

## Scope reminder

In scope:
- Add a DireBuilder-only Hot Load endpoint that wraps existing `load_zone(... preserve_existing=True)` service.
- Wire the Hot Load button to fire the endpoint, with save-first-when-dirty combined flow.
- Render the service's summary dict in a success message including warnings.
- Implement structured failure UX including the partial-state warning for `runtime_error`.
- Extend mutual-exclusion lock to include hot load (save, discard, hot load, zone switch all mutually exclude).
- Expose hot-load observability through `window.DireBuilderPageApi`.

Out of scope:
- Changes to `load_zone()` or `_warm_load_zone()` service code.
- Active-player counting or occupancy checks.
- Destructive-reload path.
- Transaction/rollback for mid-operation failures.
- Description generation.
- Legacy `/builder/` behavior changes.

## Execution order

### 1. Preserve the 2b.1/2b.2/2b.3 state contracts

- Keep all existing state model functions intact: `originalZone`, `workingZone`, `computeZoneDiff`, `isDirty`, `saveWorkingZone`, `discardWorkingZone`, `attemptZoneSwitch`.
- Reuse the canonical zone normalization path established in 2b.2 and 2b.3.
- Do not change clean/dirty semantics.

### 2. Add the backend hot-load endpoint

- Add additive route in `web/urls.py`:
  - `POST /direbuilder/api/zone/<zone_id>/hot-load/`
- Add a DireBuilder-scoped view that:
  - Validates the target zone exists.
  - Calls `world.worlddata.services.import_zone_service.load_zone(zone_id, dry_run=False, preserve_existing=True)`.
  - Catches `ValueError` and similar pre-mutation validation errors -> returns `validation_failed`.
  - Catches general `Exception` from inside warm load -> returns `runtime_error`.
  - Returns the service's summary dict on success.
- Keep this route isolated from `/builder/api/reload-zone/`.

Required backend status codes:
- `400` for `validation_failed`
- `404` for `zone_not_found`
- `409` for `operation_in_progress`
- `500` for `runtime_error`
- `500` for `internal_error`

### 3. Add a dedicated hot-load helper on the frontend

- Add `hotLoadCurrentZone(options?)` in `direbuilder.js`.
- It should:
  - If dirty: call `saveWorkingZone()` first. Abort on save failure.
  - POST `/direbuilder/api/zone/<zone_id>/hot-load/`.
  - Return the summary dict on success.
  - Surface structured failure on error.
- Reuse the existing fetch helper pattern from save and discard.

Add a hot-load state tracker:
- Minimum states: `idle`, `hot_loading`, `succeeded`, `failed`.
- Tracker is the source of truth for both UI lock state and test harness inspection.

### 4. Extend `window.DireBuilderPageApi`

- Add:
  - `hotLoadCurrentZone()`
  - `getHotLoadState()`
  - `getLastHotLoadError()`
  - `getLastHotLoadSummary()`
- Keep all existing API methods intact.

### 5. Wire the Hot Load button

- Replace any inert placeholder behavior on the Hot Load button.
- On click, always open the confirm modal (regardless of dirty state).
- Modal copy depends on dirty state (see step 5a for locked text).
- Cancel closes modal with no-op.
- Confirm fires `hotLoadCurrentZone()`.

### 5a. Lock the modal copy verbatim

When clean:
- Title: `Apply Zone to Live Game?`
- Body: `Hot Load will refresh this zone in the running game. Connected players may notice runtime objects (NPCs and items) respawn. Removed rooms will remain in the live game until full server restart.`
- Cancel button label: `Cancel`
- Confirm button label: `Hot Load`

When dirty:
- Title: `Save and Apply to Live Game?`
- Body: `You have unsaved changes. Hot Load will save your edits to disk first, then refresh the running game. Connected players may notice runtime objects (NPCs and items) respawn. Removed rooms will remain in the live game until full server restart.`
- Cancel button label: `Cancel`
- Confirm button label: `Save & Hot Load`

Cancel is visually emphasized in both. Escape closes as Cancel.

Do not paraphrase, abbreviate, or substitute alternative copy.

### 6. Implement Save & Hot Load combined flow

- When confirmed on dirty zone:
  - Call `saveWorkingZone()` first.
  - If save rejects: abort. Show save failure UX (existing 2b.2 behavior). Hot load does not run.
  - If save succeeds: proceed immediately to hot-load call without releasing the UI lock.
- The lock holds across both phases. Builder cannot edit, click another save, or switch zones during the combined flow.

### 7. Render the success summary

- On hot-load success, show a toast or panel containing:
  - Rooms updated count
  - Rooms created count
  - Rooms preserved-stale count
  - NPCs respawned count
  - Items respawned count
  - Warnings list (if non-empty)
- Format example provided in the dispatch.
- The summary is the service's return value, surfaced as ground truth.

### 8. Implement graceful failure UX

- On hot-load failure:
  - Keep current page state intact.
  - Save state remains whatever it was before hot-load began.
  - Show toast or modal summary with retry guidance per error code.
- Frontend messaging must switch on the backend error code:
  - `validation_failed` -> fix-zone-file message
  - `zone_not_found` -> reload-page message
  - `runtime_error` -> partial-state warning with server-reload recommendation (locked copy from dispatch)
  - `internal_error` -> generic retry message
  - `network_error` -> connection-check message
  - `operation_in_progress` -> wait-for-other-operation message
- The `runtime_error` message must explicitly warn about possible partial live state. Do not soften.

### 9. Extend mutual-exclusion lock

- Save blocks Hot Load. Hot Load blocks Save.
- Discard blocks Hot Load. Hot Load blocks Discard.
- Hot Load blocks Zone Switch.
- All four operations participate in the same UI lock from 2b.2.
- If a second operation is invoked while one is in flight, reject with `operation_in_progress`.

### 10. Enforce the in-flight hot-load lock

- While hot load is in flight:
  - All editable controls disabled.
  - Save, discard, zone switching, Hot Load buttons all disabled.
  - Visible loading state on the confirm action and Hot Load button.
- For Save & Hot Load combined flow: the lock holds across both phases.
- When hot load resolves:
  - On success: unlock fields, show success summary.
  - On failure: unlock fields, show failure UX, dirty unchanged.

### 11. Keep beforeunload semantics correct

- Hot Load does not affect dirty state directly (zone was clean when hot load ran).
- `beforeunload` warning behavior is unchanged.
- The lock prevents tab close mid-operation through the existing UI lock pattern.

### 12. Cache-bust

- Bump `direbuilder.js` version in the template.
- Bump `direbuilder.css` if styling changes for the Hot Load button or modal.

### 13. Verification

1. Page loads with no console errors.
2. Hot Load on clean zone: modal opens with clean copy. Confirm fires hot load. Success summary appears.
3. Hot Load on dirty zone: modal opens with dirty copy. Confirm fires save then hot load. Dirty clears. Success summary appears.
4. Save failure during Save & Hot Load: save failure UX appears. Hot load does not run. Dirty preserved.
5. Force a `runtime_error` if feasible (e.g., temporary mock). Failure message includes partial-state warning verbatim.
6. Force a `validation_failed` (e.g., temporarily corrupt a YAML file). Failure message tells builder to fix the zone file.
7. While save is in flight, calling hot load rejects with `operation_in_progress`.
8. While discard is in flight, calling hot load rejects with `operation_in_progress`.
9. While hot load is in flight, calling save rejects with `operation_in_progress`.
10. While hot load is in flight, calling discard rejects with `operation_in_progress`.
11. While hot load is in flight, zone switch is blocked.
12. Modal copy matches locked strings exactly for both clean and dirty cases.
13. Success summary renders all required fields including non-empty warnings list.
14. `getLastHotLoadSummary()` returns the most recent summary on `DireBuilderPageApi`.
15. `/builder/` Reload Zone still works unchanged. Regression test.

## Stop conditions

- Backend changes stay limited to the additive DireBuilder hot-load route and its helpers.
- Do not modify `import_zone_service.py`.
- Do not add player-counting logic.
- Do not add destructive reload.
- Do not add transaction/rollback.
- Do not redesign auth or legacy builder flows.
- Do not wire description generation.