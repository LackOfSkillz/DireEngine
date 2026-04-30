# MT-507p Phase 2b.1 Dispatch

Goal: convert DireBuilder from display-only selection rendering into local editable state with dirty tracking, unsaved-change protections, and explicit save deferral.

Precondition:
- Execute this only after manual browser verification that Phase 2a works at normal browser width:
  - Clicking between rooms updates all right-column tabs from selected room data.
  - Clicking empty map space shows the empty room-editor state.
  - Dropdown contrast is readable.
  - Initial page load renders the expected first selected room.

Non-goals for this phase:
- No backend calls.
- No persistence to disk.
- No live-world hot load.
- No description generation.
- No fake save that clears dirty state.
- No changes to legacy `/builder/` behavior.

Implementation surface:
- Primary files should remain local to the additive DireBuilder route and its assets:
  - `web/templates/webclient/direbuilder.html`
  - `web/static/webclient/js/direbuilder.js`
  - `web/static/webclient/css/direbuilder.css`
- Do not refactor or extend `dragonsire-browser-v2.js` unless a concrete blocker appears.
- Do not add backend endpoints in this phase.

State model:
- Keep the originally loaded zone payload as an immutable baseline object captured once on page load.
- Maintain a separate mutable in-memory working copy for all DireBuilder edits.
- Re-render the page from the mutable working copy, not from DOM-local ad hoc field state.
- Add one helper that can diff `originalZoneState` against `workingZoneState`.
- The diff does not need to be sent anywhere in 2b.1, but the helper must exist so 2b.2 can reuse it for save payload generation.
- Dirty state for 2b.1 is zone-level only:
  - `isDirty = diff(originalZoneState, workingZoneState) is non-empty`
  - No mutation log is required.
  - No per-field dirty badges are required.

Core behavior:
- All editable DireBuilder UI should write into the mutable working copy.
- Switching selected rooms should preserve unsaved in-memory edits for the current zone.
- Selecting a different room should render that room from the working copy, not reload original data.
- Clearing room selection should keep the zone dirty state intact and only affect the visible room editor.

Room editor field rules:

Identity tab:
- Editable:
  - Room Name
  - Short Description
  - Environment
- Read-only:
  - Room Id
- Changing any editable field must update the working room object and mark the zone dirty.

Description tab:
- Editable:
  - Manual Description textarea
- Interactive but not data-editing:
  - Preview As dropdown
- Read-only:
  - Generated markup preview pane
- Preview content should continue to reflect the currently selected room in the working copy.

Tags tab:
- All tag accordions should become interactive.
- Existing pills should toggle selected/unselected state.
- Custom tags must support local add and remove.
- Tag edits update the selected room in the working copy and mark the zone dirty.

Stateful tab:
- Custom state list becomes editable.
- `Add Custom State` button works locally only.
- Stateful description entries should be editable for the selected room.
- Room state changes update the working copy and mark the zone dirty.

Connections tab:
- Exits become editable in-memory.
- Required local interactions:
  - direction dropdowns
  - type dropdowns
  - delete exit buttons
  - `Add Exit` button
- Details list becomes editable.
- Ambient messages become editable.
- All connection/detail/ambient edits stay local and mark the zone dirty.

Population tab:
- Assigned NPC list becomes editable.
- Assigned item list becomes editable.
- Required local interactions:
  - add
  - remove
  - reorder
- All population edits remain local and mark the zone dirty.

Left column zone editor rules:
- The zone editor also participates in the same working-copy and dirty-tracking model.
- Editable:
  - Setting Type pill selections
  - Era pill selections
  - Cultural Palette pill selections
  - Mood pill selections
  - Climate pill selections
  - Voice Notes textarea
- Read-only:
  - Zone Browser navigation structure
- Zone-level edits update the working zone object and mark the zone dirty.

Dirty indicator requirements:
- The primary visible dirty indicator is the existing save-button convention:
  - `Save Zone` becomes `Save Zone*` when dirty.
- This indicator must update immediately on the first change and revert only when dirty state becomes false.
- Because save is not implemented in 2b.1, dirty should remain true until the user abandons changes by navigation or reload.
- Optional but recommended enhancement:
  - Add a subtle unsaved marker to the zone switcher label, such as a trailing bullet.
  - If this creates layout or readability problems, omit it and keep only `Save Zone*`.

Unsaved-change protections:

Zone switching:
- If the current zone is clean, switching zones behaves as it does now.
- If the current zone is dirty, intercept zone switching and show a confirm modal.
- Modal copy should clearly state that the current zone has unsaved changes.
- Required actions:
  - `Save & Switch`
  - `Discard & Switch`
  - `Cancel`
- Phase 2b.1 behavior for those actions:
  - `Save & Switch`: do not fake persistence. Show a clear `not implemented until 2b.2` message and remain on the current zone.
  - `Discard & Switch`: abandon the in-memory working copy for the current zone and navigate to the requested zone.
  - `Cancel`: close the modal and stay on the current zone.

Browser unload:
- If the current zone is dirty, register a standard `beforeunload` warning.
- If the current zone is clean, do not warn on unload.

Buttons and actions that must remain deferred:
- `Save Zone` button must not pretend to save.
- `Save Zone` in 2b.1 may either:
  - show a toast such as `Save lands in Phase 2b.2`, or
  - open a lightweight not-yet-implemented modal.
- It must not clear dirty state.
- `Discard Changes` overflow action must remain non-persistent and must not reload from disk in this phase.
- `Hot Load` remains not implemented.
- `Generate Description` remains not implemented.

Recommended UI behavior details:
- Preserve the current tab and selected room while editing.
- Do not reset active tab when a room field changes.
- When switching rooms, keep the active tab selected and show that tab's content for the newly selected room.
- For editable pills, selected and unselected states must remain visually obvious within the existing DireBuilder aesthetic.
- Avoid introducing temporary placeholder controls that will need to be thrown away in 2b.2.

Validation targets:
- Manual room edits update only the selected room in the working copy.
- Switching between two rooms preserves each room's unsaved local edits.
- Zone-editor edits persist in memory while moving between room selections.
- `Save Zone*` appears after the first change and stays visible.
- Refreshing the page discards 2b.1-only local changes because persistence is not yet wired.
- Dirty zone switch shows the confirm modal.
- `Discard & Switch` leaves the page and loads the next zone.
- `Save & Switch` does not navigate and clearly states that save is not implemented yet.
- Closing or reloading the tab with unsaved changes triggers browser unload protection.
- `/builder/` remains unaffected.

Stop conditions:
- Stop after local editability, dirty tracking, unsaved-change protections, and deferred save behavior are complete.
- Do not begin backend save wiring in this dispatch.
- Do not begin disk reload wiring for the overflow `Discard Changes` action in this dispatch.
- Do not begin hot-load or generation work in this dispatch.

Follow-up note:
- Phase 2b.2 will attach the diff helper and working-copy state to a real save endpoint.
- Phase 2b.2 is also the first phase allowed to clear dirty state after a successful persistence response.
- Phase 2b.3 will wire `Discard Changes` to reload the current zone from disk.