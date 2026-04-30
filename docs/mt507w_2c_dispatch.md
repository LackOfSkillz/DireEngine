# MT-507w Phase 2c Dispatch

Goal: wire DireBuilder's `Hot Load` button to push the saved zone YAML to the running Evennia game via the existing `load_zone(... preserve_existing=True)` service, with explicit handling of the disk-first constraint, structured failure UX including partial-state warnings, and mutual exclusion with save and discard.

Precondition:
- Execute this only after Phase 2b.3 is landed and verified in the additive `/direbuilder/` route.
- Treat the current frontend contracts (`originalZone`, `workingZone`, `saveWorkingZone`, `discardWorkingZone`, `DireBuilderPageApi`) as authoritative.
- The 2c prep investigation (MT-507 read-only pass) established that the apply-to-live backend service already exists. Reuse it; do not redesign the warm-load mechanism.

Non-goals for this phase:
- No changes to `load_zone()` or `_warm_load_zone()` semantics.
- No new destructive-reload path (the admin `@zone load` non-preserve flow remains separate).
- No active-player count or occupancy check (Phase 3 candidate).
- No transaction/rollback wrapper around mid-operation failures (architectural change, out of scope).
- No description generation wiring.
- No changes to legacy `/builder/` behavior.

Implementation surface:
- Frontend:
  - `web/templates/webclient/direbuilder.html`
  - `web/static/webclient/js/direbuilder.js`
  - `web/static/webclient/css/direbuilder.css`
- Backend additive surface only:
  - `web/urls.py`
  - `web/views.py` or sibling DireBuilder view module
- Reuse:
  - `world/worlddata/services/import_zone_service.load_zone()` with `preserve_existing=True`
- Do not modify:
  - `dragonsire-browser-v2.js`
  - `import_zone_service.py` semantics
  - Legacy `/builder/api/reload-zone/` endpoint or its consumers

## Architectural truths to honor

The 2c prep investigation surfaced specific properties of the existing apply-to-live service that 2c must not contradict:

**Hot Load is disk-first.** `load_zone()` reads YAML from disk. It does not accept an in-memory payload. Therefore Hot Load on a dirty zone must save first, then apply.

**Warm load is not destructive reconciliation.** Stale rooms are preserved (not deleted). Existing room/exit typeclass changes are not applied to existing objects. Removed rooms remain in live game until a full server restart. This is an architectural property of `_warm_load_zone()`, not a bug. Do not paper over it.

**Mid-operation failures have no rollback.** If `_warm_load_zone()` throws partway through, runtime state is partially mutated. There is no transaction boundary. The failure UX must communicate this honestly to the builder.

**Runtime NPC/item objects are deleted and respawned on every Hot Load.** This is intentional; it ensures runtime contents match the import plan. Connected players in the affected zone will see object refresh. Hot Load is not invisible to players.

These truths shape the UX. The dispatch makes them visible to builders rather than hidden.

## Existing frontend contract to preserve

These functions and state contracts must build on, not replace, what 2b.2 and 2b.3 established:

- `originalZone`, `workingZone`, `computeZoneDiff`, `isDirty`
- `saveWorkingZone(options?)` from 2b.2
- `discardWorkingZone(options?)` from 2b.3
- `attemptZoneSwitch(nextZoneId)` from 2b.1
- `window.DireBuilderPageApi` extended in 2b.2 and 2b.3
- The mutual-exclusion lock pattern from 2b.2/2b.3 (`operation_in_progress` error code)
- The full re-render rule from 2b.3 (state replacement is canonical, not DOM-patched)

2c extends these contracts. It does not redefine them.

## New frontend contract to add

Add a dedicated hot-load helper:

- `hotLoadCurrentZone(options?)`
  - Performs save-first-then-hot-load when dirty.
  - Performs hot-load directly when clean.
  - Resolves with the hot-load summary dict on success.
  - Rejects with structured failure on error.

`hotLoadCurrentZone()` participates in the mutual-exclusion lock. It cannot run during in-flight save or discard. Save and discard cannot run during in-flight hot load.

Expose hot-load observability through `window.DireBuilderPageApi`:

- `hotLoadCurrentZone()` - triggers hot load for the current zone
- `getHotLoadState()` - returns `idle`, `hot_loading`, `succeeded`, `failed`
- `getLastHotLoadError()` - returns the last hot-load error code or `null`
- `getLastHotLoadSummary()` - returns the service's summary dict from the most recent successful hot load, or `null` if none has succeeded yet

## Hot Load endpoint contract

Endpoint:
- `POST /direbuilder/api/zone/<zone_id>/hot-load/`

Reasoning:
- Wraps the existing `load_zone(zone_id, dry_run=False, preserve_existing=True)` service.
- Maintains the additive-contract pattern from 2b.2 and 2b.3.
- Does not couple DireBuilder to the legacy `/builder/api/reload-zone/` response shape.

Request body:
- Empty or `{}` (no payload needed; service reads from disk).

Success response:
- `200 OK` with the hot-load summary dict in the response body.
- Required fields:
  - `ok: true`
  - `summary: <dict>` containing the service's return values:
    - `zone_id`
    - `rooms_updated`
    - `rooms_created`
    - `rooms_preserved_stale` (rooms removed from YAML but kept in runtime)
    - `exits_updated`
    - `exits_created`
    - `exits_deleted`
    - `npcs_respawned`
    - `items_respawned`
    - `warnings: [str]`

The frontend renders this summary in a success toast or expandable result panel so builders see ground truth: what got applied, what was preserved, what generated warnings.

Failure response:
- Structured JSON:
  - `ok: false`
  - `error: <code>`
  - `message: <builder-readable summary>`
- Required error codes:
  - `validation_failed` - YAML on disk is malformed (caught by service before mutation begins)
  - `zone_not_found` - zone doesn't exist on disk
  - `runtime_error` - exception thrown during `_warm_load_zone()` after mutation began
  - `internal_error` - unexpected backend failure outside the warm-load loop
  - `operation_in_progress` - save, discard, or another hot-load is in flight
- Required HTTP status codes:
  - `400` for `validation_failed`
  - `404` for `zone_not_found`
  - `500` for `runtime_error`
  - `500` for `internal_error`
  - `409` for `operation_in_progress`

`runtime_error` is distinct from `internal_error` because it implies partial runtime mutation. The frontend retry guidance must reflect this:

- `validation_failed` - `Zone YAML is invalid. Fix the zone file on disk and try again.`
- `zone_not_found` - `This zone no longer exists on disk. Reload the page to recover.`
- `runtime_error` - `Hot load failed mid-operation. Live game state may be partially updated. Consider reloading the running server if behavior becomes unexpected.`
- `internal_error` - `Hot load failed unexpectedly. Try again. If this persists, check the server logs.`
- `network_error` - `Couldn't reach the server. Check your connection and try again.`
- `operation_in_progress` - `Another save, discard, or hot load is still running. Wait for it to finish, then try again.`

The `runtime_error` message is intentionally honest about partial-state risk. Do not soften it.

## Hot Load behavior requirements

Hot Load button:
- The Hot Load button is always enabled (unlike Discard, which is gated on dirty state).
- On click:
  1. Open the confirm modal. Modal copy depends on dirty state (see Modal copy section).
  2. If the builder cancels, close the modal. No-op.
  3. If the builder confirms:
     a. If the zone is dirty: call `saveWorkingZone()` first. If save fails, abort hot load and show the save failure UX. If save succeeds, proceed to step b.
     b. Call `hotLoadCurrentZone()`.
     c. Disable repeated submits during the operation.
- On hot-load success:
  - Show a success toast or panel summarizing what got applied (use the summary dict from the response).
  - Close the modal.
  - Save state and dirty state are unchanged (zone was already clean when hot load ran, either originally or after the save half).
- On hot-load failure:
  - Keep the builder on the page.
  - Show failure toast with retry guidance per error code.
  - For `runtime_error`, the message must include the partial-state warning verbatim from the error code mapping above.
  - Save state cleanup: if hot load was preceded by a successful save, the save state remains `succeeded` (the save itself did succeed; only the hot-load half failed).

Save and hot-load mutual exclusion:
- Save is blocked during in-flight hot load.
- Hot load is blocked during in-flight save.
- Discard is blocked during in-flight hot load.
- Hot load is blocked during in-flight discard.
- Zone switch is blocked during in-flight hot load.
- All operations participate in the same UI lock established in 2b.2.

Dirty state interaction:
- When dirty, Hot Load offers Save & Hot Load (combined action via the modal flow above).
- Hot Load itself does not modify `originalZone` or `workingZone`. The save half does that, via the existing 2b.2 baseline replacement.
- After successful Save & Hot Load: dirty is false (from save), live game is updated (from hot load).
- After failed Save & Hot Load: depends on which half failed. If save failed, dirty remains true and edits remain in memory. If save succeeded but hot load failed, dirty is false (save succeeded), and the live game is potentially in partial state.

## Confirm modal requirements

Hot Load is consequential regardless of dirty state. The modal always opens.

When the zone is clean:
- Title: `Apply Zone to Live Game?`
- Body: `Hot Load will refresh this zone in the running game. Connected players may notice runtime objects (NPCs and items) respawn. Removed rooms will remain in the live game until full server restart.`
- Cancel button label: `Cancel`
- Confirm button label: `Hot Load`

When the zone is dirty:
- Title: `Save and Apply to Live Game?`
- Body: `You have unsaved changes. Hot Load will save your edits to disk first, then refresh the running game. Connected players may notice runtime objects (NPCs and items) respawn. Removed rooms will remain in the live game until full server restart.`
- Cancel button label: `Cancel`
- Confirm button label: `Save & Hot Load`

In both cases:
- Cancel must be visually emphasized as the safer default action.
- Escape closes the modal as Cancel.
- Modal copy is locked. Do not paraphrase or substitute alternative wording.

The "removed rooms remain" warning is intentionally present in both versions. This is an architectural property of warm load that builders need to understand, regardless of whether they're saving first.

## Success summary rendering

The hot-load success response includes a summary dict from the service. The success toast or panel must render this summary in human-readable form. Required fields to surface:

- Rooms updated, created, and preserved-stale (each with count)
- NPCs respawned (with count)
- Items respawned (with count)
- Warnings (list, if non-empty)

Example success message:

```text
Hot load complete.
- 3 rooms updated
- 1 room created
- 0 rooms preserved as stale
- 4 NPCs respawned
- 2 items respawned
- 1 warning: Missing NPC prototype 'tavern_keeper' fell back to generic typeclass
```

If the warnings list is non-empty, the message must surface them. Builders need visibility into what the service flagged.

## Hot Load failure UX

This phase must communicate honestly when hot load fails.

Required failure behavior:
- No silent failure.
- No automatic retry.
- No page reload.
- Dirty state is unchanged by failure (it was either already false or already true before hot load began).
- Save state cleanup if hot load was the second half of Save & Hot Load: leave save state alone. The save itself succeeded.

User-facing result on failed hot load:
- Show error toast or modal summary.
- Message reflects the specific error code.
- For `runtime_error`, the message must explicitly warn about possible partial live state and recommend server reload as recovery.
- `beforeunload` protection follows existing rules (active if dirty).

## In-flight hot-load behavior

Hot load must be race-safe.

Requirements:
- If a hot load is in flight, do not allow repeated hot-load submissions.
- If a hot load is in flight, save, discard, and zone switching are blocked.
- Do not mutate `workingZone` while hot load is in flight.
- Show a visible loading state on the confirm action and the Hot Load button.

The Save & Hot Load combined flow has two phases (save, then hot-load). Both phases participate in the lock. The lock does not release between save success and hot-load start.

## Validation and backend behavior

Backend responsibilities:
- Validate the target zone exists on disk.
- Call `load_zone(zone_id, dry_run=False, preserve_existing=True)`.
- Catch validation errors before mutation and return `validation_failed`.
- Catch runtime exceptions during warm-load and return `runtime_error`.
- Return the service's summary dict on success.

If the existing service throws an exception type that 2c doesn't anticipate, stop and report. Do not invent new error categories on the fly.

Auth/permission rule:
- Hot Load uses the same authentication and permission model as save and discard.
- Do not redesign auth logic in 2c.

## Validation targets

- Hot Load on clean zone: modal opens with clean copy, confirm fires hot load, success summary renders in toast/panel.
- Hot Load on dirty zone: modal opens with dirty copy, confirm fires save then hot load, success clears dirty and applies live.
- Save failure during Save & Hot Load: hot load is aborted, save failure UX surfaces, dirty preserved.
- Hot Load failure during Save & Hot Load: save state remains `succeeded`, dirty is false (from save), hot-load failure UX surfaces.
- `runtime_error` response triggers partial-state warning in failure message.
- `validation_failed` response triggers fix-zone-file message.
- Hot Load is blocked during in-flight save: returns `operation_in_progress`.
- Hot Load is blocked during in-flight discard: returns `operation_in_progress`.
- Save is blocked during in-flight hot load: returns `operation_in_progress`.
- Discard is blocked during in-flight hot load: returns `operation_in_progress`.
- Zone switch is blocked during in-flight hot load.
- Modal copy matches locked strings exactly for both clean and dirty cases.
- Success summary renders all required fields including warnings list.
- `getLastHotLoadSummary()` returns the most recent successful summary on `DireBuilderPageApi`.
- `/builder/` Reload Zone behavior is unchanged (regression test).

## Stop conditions

- Stop after Hot Load wiring is complete for the additive `/direbuilder/` route.
- Do not modify `load_zone()` or `_warm_load_zone()`.
- Do not add active-player checks.
- Do not add a destructive-reload path.
- Do not add transaction/rollback to the warm-load loop.
- Do not redesign auth or legacy builder flows.
- Do not wire description generation.

Follow-up notes:
- Phase 3 may add active-player count to the confirm modal.
- Phase 3 may revisit warm-load semantics to support true destructive reconciliation as an opt-in mode.
- Phase 3 may formalize the operation lock as a first-class state machine if the surface continues to grow.