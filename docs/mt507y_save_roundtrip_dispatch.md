# MT-507y — Save round-trip validation across all editable fields

## Background

Manual testing surfaced a bug: zone-level attributes (Setting Type, Era,
Cultural Palette, Mood, Climate, Voice Notes) were edited, Save Zone
succeeded with dirty cleared, but a browser refresh reverted the changes
to pre-edit state.

This indicates a save round-trip integrity hole somewhere in the
frontend payload -> backend write -> disk YAML -> backend read -> frontend
page load chain. 2b.2 validation only covered room.name; zone-level and
most room-level fields were never validated end-to-end.

This dispatch is a DIAGNOSTIC + FIX pass. Diagnose first, then fix the
specific layer that's broken. Do not assume which layer is broken.

## Phase A — Diagnostic: reproduce and trace

Reproduce the bug in the live browser at /direbuilder/?zone=builder2:

1. Edit a zone-level field (e.g., toggle a Setting Type pill).
2. Confirm Save Zone* asterisk appears.
3. Click Save Zone. Confirm asterisk clears, success toast appears.
4. Refresh the page (F5).
5. Observe: is the zone-level edit still present, or reverted?

If the bug reproduces, trace the failure layer-by-layer:

### Layer 1 check: frontend payload

Use browser dev tools (Network tab) or the page API to inspect the
exact JSON payload POSTed to /direbuilder/api/zone/<zone_id>/save/.

- Does the payload include the zone-level field that was edited?
- Specifically check generation_context (setting_type, era_feel,
  culture, mood, climate, voice) for the edited values.
- If the payload is missing the zone-level edit, Layer 1 is broken.
  The frontend isn't capturing the edit into workingZone, or isn't
  serializing it into the save payload.

### Layer 2 check: backend write to disk

After a successful save, inspect the YAML file on disk:
worlddata/zones/<zone_id>.yaml

- Does the saved YAML reflect the edited zone-level field?
- Compare to a pre-save backup if available.
- If the YAML on disk does NOT reflect the edit, Layer 2 is broken.
  Either the backend view drops the field before write, or
  _prepare_builder_zone_yaml_for_dump() filters it out.

### Layer 3 check: backend read on page load

If the YAML on disk is correct but refresh shows stale state, Layer 3
is broken. The page-load read path doesn't surface the saved field.

- Inspect the embedded JSON in direbuilder.html on a fresh page load
  (View Source -> find the script id="direbuilder-zone-data" or
  "direbuilder-zone-context-data" blocks).
- Does the embedded JSON reflect the saved zone-level field?
- If not, the read helper that builds the page context is dropping
  fields that are in YAML on disk.

### Layer 4 check (less likely but possible): canonical response mismatch

The save endpoint returns a canonical JSON response. The frontend
adopts that as the new baseline.

- Compare the canonical response from save to the embedded JSON on
  the next page load.
- If they differ, the page-load read path and the save-write+read-back
  path are using different field-shape logic. That's a real bug
  regardless of which one is "right."

### Report findings

After tracing all four layers, report:
- Which layer (or layers) drops the zone-level field
- The exact field path that's failing (e.g.,
  zone.generation_context.setting_type)
- The code location responsible (file + function name)
- A proposed fix scoped to that specific layer

DO NOT fix yet. Report findings first.

## Phase B — Comprehensive field validation

Once the zone-level bug is diagnosed, expand validation to confirm
which other fields (if any) have the same round-trip integrity hole.

For each editable field listed below, test:
1. Edit the field
2. Save
3. Refresh
4. Observe whether the edit persisted

Room-level fields:
- Identity tab: Name, Short Description, Environment
- Description tab: Manual Description textarea
- Tags tab: each pill axis (atmosphere, function, era_marker, condition,
  geography). Custom tag add/remove.
- Stateful tab: room states pills, stateful descriptions add/remove
- Connections tab: exit direction edit, exit type edit, exit add/remove,
  details list edit, ambient messages
- Population tab: NPC add/remove, item add/remove

Zone-level fields:
- Setting Type pill selection
- Era pill selection
- Cultural Palette pill selection
- Mood pill selection
- Climate pill selection
- Voice Notes textarea

Population shape preservation (regression check from 2b.2):
- Test on a zone with room-local population (e.g., builder2).
- Test on a zone with placements-style population (e.g., new_landing).
- Verify save does not change storage shape.

For each field that fails round-trip, capture which layer broke
(per Phase A diagnostic categories).

## Phase C — Fix

Based on the diagnostic findings, implement a targeted fix.

If Layer 1 (frontend): ensure pill toggles, text inputs, and other
zone-level controls write to the correct path in workingZone, and
that workingZone serialization in the save payload includes
generation_context fields.

If Layer 2 (backend write): ensure the save view passes
generation_context (and any other affected zone-level fields) to
_prepare_builder_zone_yaml_for_dump() and that the dumper writes
them to YAML.

If Layer 3 (backend read): ensure the page-load read helper surfaces
all canonical fields that the save endpoint accepts and persists.
The page-load read shape MUST match the save canonical response shape
exactly.

If Layer 4 (canonical mismatch): align the page-load read path with
the save canonical response path. Both should call the same
underlying read helper.

Out of scope:
- Do not refactor the save endpoint contract.
- Do not change the canonical response shape.
- Do not modify the YAML schema.
- Do not touch legacy /builder/.

## Phase D — Verification

After the fix lands, re-run the comprehensive field validation from
Phase B. Every editable field must pass round-trip:

1. Edit
2. Save (asterisk clears)
3. Refresh (edit persists in the loaded UI)
4. Re-edit and verify the now-loaded state is editable again

Also verify:
- Save Zone success toast still appears.
- Save Zone* asterisk still tracks dirty state correctly.
- Zone-switch confirm modal still works.
- Discard Changes still works.
- Hot Load still works.
- /builder/ still unchanged.

## Stop conditions

- Diagnose before fixing.
- Fix only the specific layer that's broken; do not refactor adjacent
  code paths.
- Do not modify import_zone_service.py.
- Do not modify legacy /builder/ behavior.
- Do not skip the comprehensive field validation in Phase B; partial
  validation is what created this gap in the first place.

## Deliverable

A diagnostic report identifying which layer is broken, a targeted
fix, and a comprehensive field-by-field round-trip validation result
showing which fields pass and which fail (target: all pass).