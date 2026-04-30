# MT-508 — Room-tag vocab UI parity

## Status

MT-507z is accepted as complete.

Bugs fixed in MT-507z:

1. Zone vocab UI mismatch
2. Add-row dirty drafts being dropped (ambient, NPC, item)
3. Single-value atmosphere fields posted as strings instead of arrays

`exports/mt507z_field_roundtrip.md` is now the validation baseline for field-touching work. Future changes that affect editable DireBuilder fields should run an analogous matrix or extend that one.

## Goal

Apply the MT-507z fix pattern to room-level tag editors so the UI can only emit vocab-valid values for schema-constrained room tag fields.

The persistent save-error banner added in MT-507z remains in place as a safety net, but normal builder use should no longer rely on banner-visible backend rejection for these tag fields.

## In scope

Convert the following room-level tag fields from freeform editors to vocab-backed pill pickers:

- `tags.structure` (scalar)
- `tags.specific_function` (scalar)
- `tags.named_feature` (scalar)
- `tags.condition` (scalar)
- `tags.atmosphere.materials` (array)
- `tags.atmosphere.social_character` (array)
- `tags.atmosphere.surroundings` (array)
- `tags.atmosphere.sensory` (array)
- `tags.atmosphere.upkeep` (scalar)

Preserve as freeform:

- `tags.custom`

`tags.custom` is intentionally open-ended per schema and must not be converted to a vocab picker.

## Constraints

- Reuse the vocab-pill helpers introduced in MT-507z. Do not fork the pattern.
- Source vocab from:
  - `world/builder/vocab/room_vocab.yaml`
  - `world/builder/vocab/atmosphere_vocab.yaml`
- Do not duplicate vocab lists in frontend code.
- Inject vocab through the same template-context mechanism already used for zone vocab in MT-507z.
- Keep the MT-507z save-error banner as the fallback safety net.

## Serializer note

MT-507z fixed a real payload bug where atmosphere multi-value fields could collapse from arrays to strings when only one value was selected. MT-508 must explicitly verify that the room-level atmosphere serializer still preserves arrays for multi-select fields when exactly one value is selected.

If the existing serializer fix already covers this path, MT-508 only needs the picker conversion and regression verification. If any room-level atmosphere path still collapses a one-item array to a string, extend the serializer fix as part of MT-508.

## Validation

After conversion, run a focused validation on:

1. Scalar fields:
   - clicking a selected pill clears it
   - clicking a different pill switches selection
2. Array fields:
   - multi-select toggle works as add/remove
   - one selected value still serializes as an array on save
3. Save round-trip through refresh on at least one room with a full set of room-tag values populated
4. Normal save flow does not trigger the save-error banner, because the picker UI can no longer emit invalid vocab values

## Out of scope

- Adding new vocab entries
- Custom value affordances such as "other / specify"
- Room-tag UX redesign beyond pill conversion

## Deliverable

Live `/direbuilder/` where room-level schema-constrained tag fields are vocab-correct end to end, `tags.custom` remains freeform by design, and the save-error banner is a true safety net rather than the primary validation path for normal builder interaction.