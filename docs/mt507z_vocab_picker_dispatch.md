# MT-507z — Constrain zone-level controlled-vocabulary editors to vocab pickers

## Background

MT-507y diagnosed the zone-save persistence regression as a UI/schema
contract mismatch, not a save round-trip integrity hole. The DireBuilder
zone-level editors for setting_type, era_feel, climate, culture, and
mood currently accept freeform text input. The backend save schema at
world/builder/schemas/generation_context_schema.py enforces a fixed
vocabulary sourced from world/builder/vocab/zone_vocab.yaml. Values
outside the vocab return validation_failed (HTTP 400), and the user's
edit silently reverts on refresh because nothing was persisted.

The dirty-state machinery is correct (asterisk persists on 400, save
toast surfaces). The actual bug is that the UI permits values the
schema rejects.

This task converts the affected zone editors to vocab-backed pickers
that can only emit allowed values, and makes the save-error toast more
visible so future schema mismatches don't go unnoticed.

In scope:
- Convert generation_context editors to vocab-constrained selection UI
- Source the vocab from the existing zone_vocab.yaml; do not duplicate
- Make save-error feedback visible enough to be unmissable
- Preserve existing voice and voice notes as freeform (no schema
  constraint on those)

Out of scope:
- Backend schema changes
- Backend save view changes
- Adding new vocabulary entries (that's a content decision, not a wiring
  task)
- Custom-value affordances ("other / specify" inputs) — we can
  consider that as a follow-up if builders find the vocab too narrow,
  but not in this dispatch

## Phase A — Read the existing vocabulary and the existing pill pattern

Before changing any UI, gather the constraints:

1. Read world/builder/vocab/zone_vocab.yaml. Note the exact vocab lists
   for each affected field. Identify which fields are scalar (one value)
   vs array (multiple values).

2. Read world/builder/schemas/generation_context_schema.py to confirm
   which fields are validated against vocab and which are freeform.
   Cross-reference with the vocab YAML — they must agree on which fields
   are controlled.

3. Read web/static/webclient/js/direbuilder.js sections that handle
   room-level tag pills (the existing working pattern). The room tag
   pills already do vocab-backed pill selection. Identify the helper
   functions, event handlers, and DOM patterns. The zone-level fix
   should reuse these helpers, not invent a new pattern.

4. Read web/templates/webclient/direbuilder.html zone editor section
   to see the current freeform inputs that need replacement.

Save findings as a brief inline note in the agent report. Don't write
a separate findings file; this is short.

## Phase B — Surface the vocab to the page

The vocab lives in YAML on the server. The frontend needs it as JSON.
Reuse the existing pattern that surfaces zone data to the page:

- Add a new <script id="direbuilder-zone-vocab-data" type="application/json">
  block to direbuilder.html, populated by the view from the parsed
  zone_vocab.yaml.
- The view (direbuilder_index in views.py) reads the vocab file once on
  request and embeds it as JSON in the template context.
- The frontend reads this on page load into a module-scoped vocab
  object alongside originalZone and workingZone.

Field shape of the embedded vocab object should mirror the YAML
structure as closely as possible. Don't reshape it; let the picker
code consume it directly.

## Phase C — Convert each controlled editor to a vocab picker

For each of these fields, replace the freeform input + Set button with
a pill-based picker mirroring the room tag pattern:

Scalar fields (one value, click to select, click again to clear):
- generation_context.setting_type
- generation_context.era_feel
- generation_context.climate

Array fields (multiple values, click to toggle each):
- generation_context.culture
- generation_context.mood

Each picker:
1. Renders one pill per vocab entry inside the existing accordion body
2. Pill click toggles the value in workingZone.generation_context.<field>
3. Pill click triggers updateDirtyIndicator()
4. Selected pills get the .is-selected class (or whatever the room tag
   pattern uses); unselected pills are unstyled
5. The accordion summary line shows the current selected value(s) or
   "(not set)" when empty, matching the existing summary pattern

For scalar fields, clicking a selected pill clears it (sets the field
to null or empty string per the schema's expectation — check schema for
which is correct).

For array fields, clicking a selected pill removes it; clicking an
unselected pill adds it. No upper limit on selections unless the schema
specifies one.

Preserve as freeform (no change):
- generation_context.voice (textarea)
- generation_context.voice_notes if separate field
- Any other zone-level field NOT listed in the vocab YAML

If a freeform input is removed in favor of a picker, the old DOM
elements and their event handlers must be cleaned up. Don't leave
dead listeners attached.

## Phase D — Harden the save-error toast

Right now save errors surface as a toast. The MT-507y reproduction
revealed this can be easy to miss if the builder is mid-edit. Make
validation errors persist until acknowledged:

- On HTTP 400 (validation_failed), show an error banner at the top of
  the page (or pinned modal) with the exact validation message from the
  backend response. The banner stays until the user dismisses it or
  successfully saves.
- On HTTP 5xx (internal_error, runtime_error from the save view), same
  treatment but with appropriate copy.
- Standard success toast is unchanged for 2xx responses.

The dirty-state asterisk continues to persist on any non-2xx response
(this is already correct per MT-507y verification — don't break it).

The banner CSS should match the existing modal/toast style language.
Keep it consistent with the dark parchment theme.

## Phase E — Verification

After changes land, verify in a real browser at full viewport width:

1. Page loads, no console errors.
2. Open Setting Type accordion. Verify pills render (one per vocab
   value). No text input visible.
3. Click a pill. Asterisk appears on Save Zone.
4. Click the same pill again. Selection clears. Asterisk persists if
   any other change is dirty, clears if this was the only change.
5. Click a different pill. Selection switches.
6. Repeat for Era Feel and Climate (scalar fields).
7. Open Cultural Palette accordion. Verify pills render. Click multiple
   pills — multiple should stay selected.
8. Click a selected pill — it deselects without affecting others.
9. Repeat for Mood (array field).
10. Voice Notes textarea remains freeform; typing into it dirties as
    before.
11. Click Save Zone with all changes. Verify save returns 200.
    Asterisk clears.
12. Refresh the page. Verify all pill selections persisted: setting
    type, era, climate, culture array, mood array.
13. Make an edit. Click Save Zone. While save is in flight, observe
    no race conditions (button disabled during save, etc.).
14. As a sanity check on error handling: temporarily modify a payload
    via dev tools to inject an invalid value, post it to the save
    endpoint, and confirm:
    a. Backend returns 400 validation_failed
    b. Error banner appears at top with the validation message
    c. Asterisk persists
    d. Banner stays until dismissed or successful save
15. Verify /builder/ legacy route is still untouched.
16. Cache-bust: bump direbuilder.js and direbuilder.css versions in
    direbuilder.html template. Restart server via .\startWeb.bat.

## Phase F — Comprehensive field round-trip (deferred from MT-507y
Phase B)

Run the comprehensive round-trip validation that MT-507y deferred. For
each editable field across all tabs, perform:
1. Edit
2. Save (asterisk clears)
3. Refresh (edit persists in loaded UI)
4. Re-verify the loaded state is editable

Fields to validate:

Room-level:
- Identity: name, short_desc, environment
- Description: manual description textarea
- Tags: each pill axis (atmosphere, function, era_marker, condition,
  geography). Custom tag add/remove.
- Stateful: room states pills, stateful descriptions add/remove
- Connections: exit direction, exit type, exit add/remove, details
  edit, ambient messages
- Population: NPC add/remove, item add/remove

Zone-level (post-fix):
- Setting Type pill (scalar)
- Era Feel pill (scalar)
- Climate pill (scalar)
- Cultural Palette pills (array)
- Mood pills (array)
- Voice Notes textarea (freeform)

Population shape preservation regression check:
- Test on a zone with room-local population (builder2)
- Test on a zone with placements-style population (new_landing)
- Verify save does not change storage shape

For each field that fails, capture the failure layer per MT-507y's
diagnostic categories.

Save findings to exports/mt507z_field_roundtrip.md.

## Stop conditions

- Edit only direbuilder.js, direbuilder.css, direbuilder.html, and the
  view function that injects vocab data
- Do not modify backend schemas, save logic, or vocabulary YAML
- Do not modify the room-tag pill helpers — reuse them, don't fork
- Do not introduce new vocabulary entries (content decision, not in
  scope)
- If the room-tag pill pattern doesn't cleanly support array fields,
  stop and report. Don't invent a new pattern; we want consistency

## Deliverable

Live /direbuilder/ where:
- All zone-level controlled-vocabulary fields render as pills, not
  freeform text inputs
- Pill selections write to workingZone and trigger dirty indicator
- Save round-trips correctly for every editable field across all tabs
- Save validation errors surface as a persistent banner, not just a
  fleeting toast
- Voice Notes remains freeform
- /builder/ legacy route is untouched

Plus:
- exports/mt507z_field_roundtrip.md with comprehensive field validation
  results

Report:
- Files modified
- Any deviations from this dispatch
- Any data-shape ambiguity discovered (especially around how the
  scalar-vs-array distinction is represented in workingZone and the
  save payload)