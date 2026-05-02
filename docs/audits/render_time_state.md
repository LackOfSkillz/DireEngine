# MT-514d Render-time State Diagnostic

## Verdict

Current Dragonsire room description rendering is not evaluating literal `$state(...)`
markup at render time.

The only local state-aware room description logic found in production is
`typeclasses.rooms_extended.ExtendedDireRoom.get_display_desc()`, which delegates
to `get_stateful_desc()` and selects among pre-split `desc_<state>` attributes.

In the current live database, that mechanism is effectively unused:

- Total room objects audited: `1180`
- Rooms with any `desc_<state>` attributes: `0`
- Rooms with literal `$state(` inside base `desc`: `0`
- Rooms tagged with category `room_state`: `0`

That makes the present system functionally equivalent to plain `desc` rendering for
live content, with one code-level exception: seasonal fallback support exists in
`ExtendedDireRoom`, and is covered by one test, but no live room data currently uses
that generalized `desc_<state>` path.

## Phase A: Room Render Path

### Entry point used in production

The repo does not define a local `CmdLook` implementation under `commands/`, and the
room classes do not override `return_appearance()` locally. The room-specific display
hook found in project code is:

- `typeclasses/rooms_extended.py`
  - `ExtendedDireRoom.get_stateful_desc()`
  - `ExtendedDireRoom.get_display_desc()`

`get_display_desc()` simply returns `get_stateful_desc()`. This indicates the local
customization point is description selection, not a custom end-to-end appearance
renderer.

### What the room description selector actually reads

`ExtendedDireRoom.get_stateful_desc()` reads room attributes and tags in this order:

1. Non-season tags in category `room_state`; if a matching `desc_<tag>` exists, it is
   returned immediately.
2. Seasonal tags in category `room_state`; if a matching `desc_<season>` exists, it is
   returned.
3. Current season fallback; if `desc_<current season>` exists, it is returned.
4. Base `desc`.
5. Fallback text if no description exists.

Notable boundaries:

- `get_time_of_day()` exists, but the current selector does not use it.
- No weather lookup is performed here.
- No invasion lookup is performed here.
- No terrain lookup is performed here.
- No markup parser or transformation step is applied between attribute read and
  display.

## Phase B: `$state(...)` Markup Audit

### Where `$state(...)` appears

Repo search found `$state(` heavily in builder-facing assets, not in the production
room render path. Representative hits:

- `world/builder/prompting/room_description_prompt.py`
- `world/builder/templates/room_description_system_prompt.txt`
- `world/builder/templates/room_description_state_markup_prompt.txt`
- `world/builder/content/tooltips.yaml`
- previously inspected docs/exports/tmp research artifacts

These hits consistently describe `$state(...)` as authoring or generation guidance.

### Where `$state(...)` is parsed

No production parser/evaluator was found under the main runtime code surfaces searched:

- `commands/**`
- `engine/**`
- `server/**`
- `systems/**`
- `typeclasses/**`
- `utils/**`
- `web/**`
- `world/**`

Searches for parser-like helpers such as `parse_state_fragments`, `render_text`, and
regex-based state evaluators returned no production matches. Parser-like helpers do
exist in `tmp/` research scripts from earlier experiments, but those are not wired into
the live render path.

### Test coverage for runtime parsing

No tests were found that verify literal `$state(...)` evaluation during room rendering.

The relevant room-description test found during this audit is seasonal only:

- `tests/test_calendar.py` verifies `get_stateful_desc()` can return a seasonal
  description.

No tests were found for:

- weather-driven room description switching
- invasion-driven room description switching
- time-of-day-driven room description switching
- literal `$state(...)` render-time parsing

### Generation-time vs render-time conclusion

Current evidence supports a generation-time-only interpretation of `$state(...)` in this
repo.

- Builder prompts/templates/tooltips teach or expect `$state(...)` syntax.
- Production room rendering does not parse that syntax.
- Live room content does not currently store literal `$state(...)` text in base `desc`.
- Live room content also does not currently store pre-split `desc_<state>` variants.

So today, `$state(...)` is an authoring convention, not a live render feature.

## Phase C: `desc_<state>` Attribute Switching Audit

### Code-level support

Code-level support does exist for `desc_<state>` selection in
`ExtendedDireRoom.get_stateful_desc()`.

The selector is generic enough to handle:

- arbitrary `room_state` tag names with matching `desc_<state>` attributes
- seasonal fallback through `desc_spring`, `desc_summer`, `desc_autumn`,
  `desc_winter`

### Live content coverage

Live database audit results:

```json
{
  "rooms_total": 1180,
  "rooms_with_desc_state_attrs": 0,
  "state_counts": [],
  "sample": []
}
```

Additional live DB audit results:

```json
{
  "rooms_with_literal_state_markup": 0,
  "literal_markup_sample": [],
  "rooms_with_room_state_tags": 0,
  "room_state_tag_sample": []
}
```

This means the switching code is present but dormant in current live content.

## Phase D: Live Observation

No production room with state-aware description content was available in the live DB, so
the dispatch fallback was used: a minimal temporary fixture room was created with the
real room typeclass `typeclasses.rooms_extended.ExtendedDireRoom`, observed through the
live Evennia runtime, and then deleted.

The browser client was available, but its fixed 20-line feed window contained reconnect
noise that made the fixture output non-authoritative for capture. The decisive runtime
observation was therefore taken directly through live `return_appearance()` calls inside
the configured game environment. This still exercised the real production room render
path.

Fixture cases and verbatim outputs:

```json
{
  "case1_no_tag_no_desc_state": "|cMT514D Fixture(#27191)|n\nBASE DESC. $state(storm, STORM INLINE TEXT.) END DESC.",
  "case2_tag_no_desc_state": "|cMT514D Fixture(#27191)|n\nBASE DESC. $state(storm, STORM INLINE TEXT.) END DESC.",
  "case3_tag_with_desc_state": "|cMT514D Fixture(#27191)|n\nDESC_STORM OVERRIDE."
}
```

Interpretation:

- Case 1: literal `$state(...)` was displayed verbatim.
- Case 2: adding `room_state=storm` alone did not trigger any inline markup parsing.
- Case 3: once `desc_storm` existed, the room switched to that pre-split attribute.

This is the strongest direct evidence in the audit:

- There is no live render-time parser for literal `$state(...)` text.
- `desc_<state>` switching does work when both the matching attribute and the matching
  `room_state` tag exist.

## Findings

1. Literal `$state(...)` markup is not evaluated at room render time in the current
   production path.
2. Local room rendering customization is narrow and lives in
   `ExtendedDireRoom.get_display_desc()` / `get_stateful_desc()`.
3. The current selector supports pre-split `desc_<state>` attributes, but live content
   does not currently use them.
4. Seasonal fallback is the only stateful variant behavior clearly represented in code
   and tests.
5. Weather, invasion, and time-of-day state are not currently wired into room
   description selection through the audited production path.

## Recommendations

1. Decide which architecture is intended before implementation work starts: literal
   `$state(...)` parsing at render time, pre-split `desc_<state>` attributes, or a
   hybrid with explicit import-time compilation.
2. If pre-split attributes remain the chosen design, define how weather, invasion,
   time-of-day, and other runtime state should populate or map into `room_state` tags,
   because the current selector depends on those tags.
3. Add focused tests for whichever design is chosen, especially for weather, invasion,
   and time-of-day cases. The current test surface is too narrow to prevent drift.
4. If builder prompts continue to instruct authors to use `$state(...)`, either add the
   missing runtime/import-time support or change the prompts so they no longer imply a
   live feature that does not exist.