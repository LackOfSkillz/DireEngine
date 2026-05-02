# MT-514d Validation

## Scope Guard

This dispatch stayed within the diagnostic scope in `MT-514d.md`.

- No production code changes were made.
- No tests were modified.
- No room content files, zone YAMLs, prompts, or templates were edited.
- Temporary live DB fixture content was created for observation and then removed.
- The only file edits from this dispatch are this validation file and the findings file.

## Phase Completion

### Phase A: Room render path audit

Completed.

Validated findings:

- No local `CmdLook` implementation found under `commands/`.
- No room `return_appearance()` override found in local room classes.
- Local room description selection is implemented in
  `typeclasses/rooms_extended.py` via `get_stateful_desc()` and `get_display_desc()`.

### Phase B: `$state(...)` markup audit

Completed.

Validated findings:

- `$state(` appears in builder prompts/templates/tooltips and previously inspected
  docs/exports/tmp artifacts.
- No production parser/evaluator was found in the main runtime code surfaces searched.
- No runtime tests for literal `$state(...)` rendering were found.

### Phase C: `desc_<state>` switching audit

Completed.

Live DB query result:

```json
{
  "rooms_total": 1180,
  "rooms_with_desc_state_attrs": 0,
  "state_counts": [],
  "sample": []
}
```

Additional live DB query result:

```json
{
  "rooms_with_literal_state_markup": 0,
  "literal_markup_sample": [],
  "rooms_with_room_state_tags": 0,
  "room_state_tag_sample": []
}
```

### Phase D: Live observation

Completed.

Observation method:

- Created temporary fixture room of type
  `typeclasses.rooms_extended.ExtendedDireRoom` in the live DB.
- Moved `Jekar` into the fixture for runtime validation.
- Captured live `return_appearance()` output for three fixture states.
- Restored `Jekar` to original location and deleted the fixture.

Runtime output:

```json
{
  "case1_no_tag_no_desc_state": "|cMT514D Fixture(#27191)|n\nBASE DESC. $state(storm, STORM INLINE TEXT.) END DESC.",
  "case2_tag_no_desc_state": "|cMT514D Fixture(#27191)|n\nBASE DESC. $state(storm, STORM INLINE TEXT.) END DESC.",
  "case3_tag_with_desc_state": "|cMT514D Fixture(#27191)|n\nDESC_STORM OVERRIDE."
}
```

Validated conclusions:

- Literal `$state(...)` text renders literally.
- `room_state` tags alone do not trigger inline markup parsing.
- Matching `desc_<state>` attributes do switch when present.

Cleanup result:

```json
{
  "restored": true,
  "current_location": 4222,
  "fixture_deleted": true
}
```

## Deliverables

Produced:

- `docs/audits/render_time_state.md`
- `exports/mt514d_validation.md`

## Final Status

MT-514d executed successfully.

The audit supports this final answer:

- `$state(...)` is currently a generation-time authoring concept, not a live
  render-time room feature.
- `desc_<state>` selection exists in code, but current live content does not use it.