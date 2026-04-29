# Phase 4 - Typed Tag Hierarchy and Constraint-Led Generation

## Background

Phase 3 established that flat atmosphere tags can improve texture, but they do
not reliably constrain the model. The failure mode was not just weak atmosphere;
it was that the model treated descriptive tags as loose inspiration rather than
typed constraints.

The critical distinction for the next iteration is:

1. What exists
2. What may be implied
3. What must not be invented

Tags can help only if the generation input separates those roles explicitly.

## Core design

Replace the current flat atmosphere treatment with a typed hierarchy using three
inheritance layers:

- Zone: broad world texture and background flavor
- Area: district-level motifs and local character
- Room: specific room-local facts that must remain grounded

Example shape:

```json
{
  "zone": {
    "name": "The Crossing",
    "tags": [
      "maritime republic",
      "dense old city",
      "salt air",
      "trade wealth",
      "stone streets",
      "crowded civic life"
    ]
  },
  "area": {
    "name": "Scholar's District",
    "tags": [
      "academic quarter",
      "ink",
      "vellum",
      "sage incense",
      "quiet courtyards",
      "hedges",
      "old lecture halls",
      "polished stone"
    ]
  },
  "room": {
    "name": "Hedge-Lined Walk",
    "tags": [
      "cobblestone path",
      "trimmed shrubs",
      "low hedges",
      "faint sage incense",
      "distant turning pages"
    ]
  }
}
```

Do not feed these as hashtags. Use labeled, typed lists.

## Priority model

Inherited tags are soft. Room tags are hard.

- Room tags are facts and must be represented.
- Area and zone tags are contextual flavor and should affect tone, vocabulary,
  and selective atmosphere only when they fit the room facts.
- Inherited tags should not be forced into every room.

Recommended prompt-facing structure:

```json
{
  "hard_tags": [
    "cobblestone path",
    "shrubs",
    "hedges",
    "smell of sage incense"
  ],
  "soft_tags": [
    "Scholar's District",
    "academic",
    "quiet",
    "old city stonework"
  ],
  "forbidden_tags": [
    "doors",
    "stairs",
    "crowds",
    "rain",
    "sunlight",
    "moonlight"
  ]
}
```

Generation rule:

- Hard tags must be represented.
- Soft tags may influence mood and vocabulary.
- Forbidden tags must not appear or be implied.

## Preferred LLM input structure

Flat prose prompts should be replaced with typed sections.

Example:

```json
{
  "zone_context": [
    "The Crossing is a dense maritime republic.",
    "Stonework, trade wealth, salt air, and civic bustle are common background textures."
  ],
  "area_context": [
    "This room is in the Scholar's District.",
    "Common motifs include ink, vellum, sage incense, trimmed hedges, lecture halls, and quiet courtyards."
  ],
  "room_specific_facts": [
    "A cobblestone path crosses the room.",
    "Shrubs and low hedges border the path.",
    "The air carries a faint smell of sage incense."
  ]
}
```

This gives the model structure:

- Zone and area tags are flavor
- Room tags are facts

## Required prompt contract

The generation prompt should treat tags as typed constraints, not as freeform
creative fuel.

Suggested contract:

```text
You write static MUD room descriptions.

Use the supplied tags as guidance, but obey tag priority:

HARD ROOM FACTS:
These must appear or be clearly represented.

SOFT CONTEXT:
These may influence mood, vocabulary, and atmosphere, but should not be forced into the room.

FORBIDDEN:
These must not be mentioned or implied.

Rules:
- Write one paragraph.
- Use 3 to 5 sentences.
- Present tense.
- Do not mention the player.
- Do not use "you" or "your".
- Do not invent objects, exits, structures, creatures, weather, time of day, or lighting sources.
- Do not include inherited zone/area details unless they fit the room facts.
- Prioritize playable clarity over literary flourish.
```

## Weights and categories

Not all tags should matter equally. Add explicit priority or weight metadata.

Example:

```json
{
  "tags": [
    {
      "text": "cobblestone path",
      "source": "room",
      "priority": "required"
    },
    {
      "text": "shrubs and hedges",
      "source": "room",
      "priority": "required"
    },
    {
      "text": "sage incense",
      "source": "area",
      "priority": "optional"
    },
    {
      "text": "maritime republic",
      "source": "zone",
      "priority": "background"
    }
  ]
}
```

Also categorize tags so the model does not literalize district names or mood
labels as physical objects.

Example:

```json
{
  "surface": ["cobblestone"],
  "vegetation": ["shrubs", "hedges"],
  "smell": ["sage incense"],
  "district": ["Scholar's District"],
  "mood": ["quiet", "ordered", "academic"],
  "architecture": ["old stonework"],
  "exits": ["north path", "south path"]
}
```

## Validator requirements

The validator should not only scan for failures. It should score required tag
coverage.

Example result:

```json
{
  "required_tag_coverage": {
    "cobblestone path": true,
    "shrubs and hedges": true,
    "sage incense": true
  },
  "forbidden_violations": [],
  "second_person_count": 0,
  "sentence_count": 3,
  "status": "pass"
}
```

If required tags are missing, use a repair instruction that names the missing
fact and forbids invention.

Example:

```text
Revise the description to include the missing required room fact: shrubs and low hedges.
Do not add new objects. Keep 3 to 5 sentences. Do not use second person.
```

## Allowed/required/optional/forbidden model

Each generation payload should expose these four roles directly:

```json
{
  "allowed_features": [],
  "required_features": [],
  "optional_flavor": [],
  "forbidden_features": []
}
```

Without `forbidden_features`, the model will continue inventing plausible MUD
scenery.

## Target generation payload

Preferred final payload shape:

```json
{
  "room_id": "crossing_scholars_hedge_walk_01",
  "room_name": "Hedge-Lined Walk",
  "description_length": {
    "min_sentences": 3,
    "max_sentences": 5
  },
  "required_features": [
    "cobblestone path",
    "trimmed shrubs",
    "low hedges",
    "faint smell of sage incense"
  ],
  "optional_context": [
    "Scholar's District",
    "academic quiet",
    "ordered courtyards",
    "old stonework",
    "The Crossing"
  ],
  "allowed_senses": {
    "sight": ["cobblestone", "shrubs", "hedges", "old stonework"],
    "smell": ["sage incense"],
    "sound": []
  },
  "exits": [
    {
      "direction": "north",
      "description": "path continues north"
    },
    {
      "direction": "south",
      "description": "path continues south"
    }
  ],
  "forbidden": [
    "you",
    "your",
    "sunlight",
    "moonlight",
    "rain",
    "storm",
    "door",
    "gate",
    "stairs",
    "statue",
    "NPCs",
    "creatures"
  ]
}
```

With prompt text kept simple:

```text
Write a static MUD room description from this data.

Required features must be included.
Optional context may influence mood but should not be forced.
Do not mention forbidden features.
Do not invent anything not supported by the data.
Use 3 to 5 sentences, one paragraph, present tense, no second person.
```

## Why Phase 3 failed

The prior attempt did not merely need more atmosphere. It failed hard
constraints.

- Second-person usage increased.
- Geometry violations worsened.
- Banned nouns persisted.
- Structural fabrication remained.

Tags can help atmosphere, but tags alone do not solve fabrication. The tag
system must carry negative constraints alongside positive descriptive support.

## Implementation direction

The existing codebase does not support this yet.

Current state:

- `world/builder/schemas/room_tag_schema.py` only supports flat room-level
  `tags.atmosphere` values.
- `world/builder/prompting/room_description_prompt.py` emits room facts and
  zone context, but has no hard/soft/forbidden separation.
- `tools/generate_sample_descriptions.py` validates violations, but does not
  score required-feature coverage.

Next implementation should therefore be staged rather than patched in ad hoc.

## Phase 4 Microtasks

### MT-401: Add typed tag/input schema

Goal: Replace flat atmosphere tags with typed generation inputs.

Add support for these fields in the room description generation schema:

```json
{
  "required_room_facts": [],
  "allowed_but_not_required": [],
  "soft_zone_context": [],
  "soft_area_context": [],
  "soft_room_context": [],
  "forbidden_features": [],
  "allowed_exits": [],
  "interactive_objects": []
}
```

Rules:

- `required_room_facts` must be represented in the generated description.
- `allowed_but_not_required` may be used, but should not be forced.
- `soft_zone_context`, `soft_area_context`, and `soft_room_context` guide tone only.
- `forbidden_features` must not appear.
- `allowed_exits` are the only exits that may be described.
- `interactive_objects` are the only objects that may receive generated look text.

Done when:

- Existing flat tag data can be transformed into the new structure.
- The old path still works through a compatibility adapter if needed.
- Unit tests cover the new schema fields.

### MT-402: Add inheritance resolution

Goal: Build final room generation input from zone, area, and room data.

Implement a resolver that merges:

```text
zone tags -> area tags -> room tags
```

into a final structured payload.

Priority rules:

```text
Room required facts > area context > zone context
Room forbidden features override all inherited context.
Room facts are hard constraints.
Inherited tags are soft context unless explicitly promoted.
```

Example:

```json
{
  "zone": "The Crossing",
  "area": "Scholar's District",
  "room": "Hedge-Lined Walk",
  "required_room_facts": [
    "cobblestone path",
    "trimmed shrubs",
    "low hedges"
  ],
  "soft_area_context": [
    "academic quiet",
    "sage incense",
    "ink and vellum"
  ],
  "soft_zone_context": [
    "dense maritime republic",
    "old stone streets",
    "civic wealth"
  ],
  "forbidden_features": [
    "door",
    "stairs",
    "gate",
    "rain",
    "sunlight",
    "moonlight"
  ]
}
```

Done when:

- A room receives inherited zone and area context.
- Room-specific required facts remain separate from inherited flavor.
- Forbidden terms survive into the final generation payload.

### MT-403: Rewrite prompt assembly around typed fields

Goal: Make `room_description_prompt.py` consume `resolve_typed_generation_input(...)`.

Scope:

- Import the typed generation resolver.
- Build prompt sections from the resolved typed payload.
- Do not rewrite the whole style prompt.
- Do not add validator logic yet.

Prompt sections must include:

```text
Required room facts
Allowed but not required details
Soft room context
Soft area context
Soft zone context
Forbidden features
Allowed exits
Interactive objects
```

Done when:

- Prompt tests prove each typed section appears when data exists.
- Empty sections are omitted or rendered cleanly.
- Existing prompt tests still pass.

### MT-404: Add prompt fixture tests for hard/soft/forbidden separation

Goal: Prevent regression back to flat atmosphere tags.

Microtasks:

MT-404.1 — Identify existing typed prompt fixture coverage

- Inspect `tests/test_room_description_prompt.py`.
- Find the MT-403 typed fixture tests.
- Do not change production code unless a test exposes an actual mismatch.

MT-404.2 — Add required-facts section isolation test

- Add or strengthen a test proving room-level required facts render under `=== REQUIRED ROOM FACTS ===`.

MT-404.3 — Confirm required facts do not leak into soft sections

- Confirm those same values do not appear under `=== SOFT ROOM CONTEXT ===`, `=== SOFT AREA CONTEXT ===`, `=== SOFT ZONE CONTEXT ===`, or `=== FORBIDDEN FEATURES ===`.

MT-404.4 — Add soft area context isolation test

- Add or strengthen a test proving area context renders under `=== SOFT AREA CONTEXT ===`.

MT-404.5 — Add soft zone context isolation test

- Add or strengthen a test proving zone context renders under `=== SOFT ZONE CONTEXT ===`.

MT-404.6 — Confirm inherited context is not promoted

- Add or strengthen a test where zone and area context exist.
- Confirm none of those inherited values appear inside `=== REQUIRED ROOM FACTS ===`.
- Room-specific required facts should remain the only hard facts.

MT-404.7 — Add forbidden-feature isolation test

- Add or strengthen a test proving forbidden features render under `=== FORBIDDEN FEATURES ===`.

MT-404.8 — Confirm forbidden features do not leak into required or soft sections

- Confirm forbidden values are absent from `=== REQUIRED ROOM FACTS ===`, `=== SOFT ROOM CONTEXT ===`, `=== SOFT AREA CONTEXT ===`, and `=== SOFT ZONE CONTEXT ===`.

MT-404.9 — Add no-flattening regression test

- Add a test that fails if required, soft, and forbidden values collapse into one generic atmosphere or tag block.
- The test should inspect section boundaries, not just check that strings appear somewhere in the prompt.

MT-404.10 — Run focused validation

Run:

`c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_room_description_prompt`

Then run:

`c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_typed_generation_input_schema tests.test_room_description_prompt`

Tests should verify:

- Room required facts appear under a hard constraint section.
- Zone/area context appears only under soft context.
- Forbidden features appear under a forbidden section.
- A regression fixture fails if required, soft, and forbidden values are collapsed into a single flat section.
- Inherited context is not promoted to required facts.

Guardrails:

- Change prompt wording only if a test requires it.
- Do not add parser, validator, repair, fallback, or batch logic.
- Do not solve canonical area sourcing.
- Do not remove legacy prompt sections yet.

Done when:

- A fixture room with zone + area + room tags produces the expected prompt layout.
- Tests fail if all tags are flattened into one list.
- The implementation handoff reports files changed, tests added or updated, the regression each test protects, validation command output, and any compatibility risks.

### MT-405: Add allowed-exit prompt constraints

Goal: Ensure the LLM sees exits as hard geometry.

Prompt should say:

```text
Only these exits may be mentioned:
- north
- east
```

If exits have labels or features:

```text
- north: cobblestone path
- east: arched walkway
```

Guardrails:

- Do not add exit validation logic.
- Do not add parser logic.
- Do not add repair or fallback logic.
- Do not run the 20-room batch.
- Do not change the room slice.
- Do not broaden style guidance.

Execution microtasks:

- MT-405.1 — Inspect allowed-exit prompt rendering.
- MT-405.2 — Add zero-exit test.
- MT-405.3 — Add one-exit test.
- MT-405.4 — Add many-exit test.
- MT-405.5 — Add labeled-exit test.
- MT-405.6 — Confirm no-invented-exits instruction.
- MT-405.7 — Run MT-405 validation commands.

Focused validation:

`c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_room_description_prompt`

`c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_typed_generation_input_schema tests.test_room_description_prompt`

Done when:

- Prompt includes allowed exits from the typed payload.
- Prompt explicitly says not to invent exits.
- Tests cover rooms with zero, one, and multiple exits.
- Labeled exits render with labels or descriptions when supplied.
- The implementation handoff reports files changed, tests added or updated, prompt examples for zero, one, and many exits, validation command output, and any compatibility risks.
- MT-406 has not begun.

### MT-406: Add interactive object prompt constraints

Goal: Prevent invented look targets.

Execution microtasks:

- MT-406.1 — Inspect interactive-object prompt rendering.
- MT-406.2 — Add allowed interactive-object test.
- MT-406.3 — Add empty interactive-object prohibition test.

Prompt should say:

```text
Only these objects may receive look text:
- heavy timber door
- narrow stairway
```

If no interactive objects exist:

```text
No object look targets may be generated.
```

Done when:

- Prompt includes interactive object constraints.
- Empty interactive object lists produce a hard prohibition.

### MT-407: Add exact prompt contract tests for room description length/style target

Goal: Lock the production description target into prompt tests before changing generation behavior.

Room descriptions should be:

```text
3-5 sentences.
45-90 words.
Concrete, grounded, readable.
Not purple prose.
Not lazy stub prose.
```

This task is test-first. Do not change production prompt code unless the new test exposes a real mismatch.

Required test coverage:

- Add focused tests in `tests/test_room_description_prompt.py` proving the rendered prompt includes the production style contract.
- Prefer a focused helper that checks the style or constraints section only.
- If dash characters vary, normalize only inside the test helper, not in production code.

The test should assert wording equivalent to:

```text
Write 3-5 plain, concrete sentences.
Target 45-90 words.
Use only grounded facts.
Too short looks unfinished.
Too long will not be read.
If facts are sparse, describe room shape, exits, surfaces, boundaries, and safe environment-specific features rather than inventing props.
```

Required assertions:

- `3`
- `5`
- `45`
- `90`
- `plain`
- `concrete`
- `grounded facts`
- `Too short`
- `Too long`
- `facts are sparse`
- `room shape`
- `exits`
- `surfaces`
- `boundaries`
- `inventing props`

Production-code rule:

- Do not edit production prompt code unless the contract is genuinely absent.
- If the prompt already contains the contract, update tests only.
- If a prompt-template edit is required, make the smallest change necessary.
- Do not reintroduce `atmospheric`, `vivid fantasy prose`, broad mood-driven language, voice-driven prose, `in the heart of`, `the air is thick with`, `whispers`, `secrets`, `sentinel`, or `symphony`.

Focused validation:

`c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_room_description_prompt`

`c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_typed_generation_input_schema tests.test_room_description_prompt`

Done when:

- Prompt tests prove the production style contract is present.
- Production code changes only if the contract is actually missing.
- The implementation handoff reports files changed, tests added or updated, validation command output, whether production code changed, and any compatibility risks.

### MT-408: Add useful-description scoring to the sampler

Goal: Report whether generated room descriptions actually satisfy the locked prompt contract.

Implementation scope:

- Update `tools/generate_sample_descriptions.py` reporting only.
- Do not change room YAML, import paths, prompt wording, or batch-apply generated text.
- Keep tests deterministic and fixture-based with no live LLM calls.

Safe sample criteria:

- No poetic filler hits.
- No fabrication watchlist hits.
- No YAML, metadata, mechanics, or `player` mention.
- One paragraph only.

Useful sample criteria:

- Safe sample.
- 45 to 90 words.
- 3 to 5 sentences.
- No stub phrase hits.

Required reporting:

- `Safe samples: X/Y`
- `Useful samples: X/Y`
- `Useful acceptance rate: N.N%`
- `Average words`
- `Under 45 words`
- `45 to 90 words`
- `Over 90 words`
- `Under 3 sentences`
- `3 to 5 sentences`
- `Over 5 sentences`
- `Poetic filler counts`
- `Fabrication watchlist counts`
- `Stub phrase counts`

Phrase groups:

- `POETIC_FILLER`: `in the heart of`, `the air is`, `the air is thick with`, `whispers`, `secrets`, `sentinel`, `symphony`, `dance of`, `as if`, `awaits`, `unfurls`, `pulsating`
- `FABRICATION_WATCHLIST`: `lantern`, `tower`, `staircase`, `mist`, `fog`, `cobweb`, `peaks`, `forest`, `ruins`, `fountain`, `statue`, `market stall`
- `STUB_PHRASES`: `enclosed room, no exits`, `a room with no exits`, `a narrow passage`, `an empty room`, `there is nothing here`

Done when:

- Unit tests cover word-count buckets.
- Unit tests cover sentence-count buckets.
- Unit tests cover safe but not useful, useful, poetic-filler unsafe, fabrication-watchlist unsafe, and stub-phrase not-useful samples.
- Export/report output includes the new MT-408 summary lines.

### MT-409: Add sentence-count validator

Goal: Enforce 3 to 5 sentence room descriptions.

Validation:

```json
{
  "sentence_count": 4,
  "sentence_count_status": "pass"
}
```

Rules:

- Fewer than 3 sentences fails.
- More than 5 sentences fails.
- Look-target text is validated separately later.

Done when:

- Unit tests cover 1, 2, 3, 5, and 6 sentence descriptions.

### MT-410: Add second-person validator

Goal: Enforce no direct player mention.

Detect:

```text
you
your
yours
yourself
you're
you've
you'll
```

Done when:

- Validator returns count and matched terms.
- Matching is case-insensitive.
- Word-boundary tests prove `young` does not match `you`.

### MT-411: Add forbidden-feature validator

Goal: Enforce per-room forbidden features.

Input:

```json
"forbidden_features": ["door", "stairs", "gate", "rain"]
```

Output:

```json
{
  "forbidden_feature_violations": ["door"]
}
```

Done when:

- Validator checks description and look targets.
- Matching is case-insensitive.
- Tests cover singular/plural basics where practical.

### MT-412: Add allowed-exit validator

Goal: Prevent invented exits or directions.

Detect directional terms:

```text
north, south, east, west, northeast, northwest, southeast, southwest, up, down, out
```

Rule:

- If a direction appears in prose, it must exist in `allowed_exits`.

Done when:

- `path leads north` passes only if north is allowed.
- `door leads west` fails if west is not allowed.
- Tests cover all common directions.

### MT-413: Add required-feature coverage validator

Goal: Ensure hard room facts are represented.

Each required fact should support coverage terms:

```json
{
  "feature": "shrubs and hedges",
  "coverage_terms": [
    "shrub",
    "shrubs",
    "hedge",
    "hedges",
    "trimmed greenery"
  ]
}
```

Done when:

- Validator reports covered and missing required facts.
- Exact string matching is not the only option.
- Tests cover synonym coverage.

### MT-414: Add coverage-term generation helper

Goal: Provide default coverage terms for simple facts.

Examples:

```text
"cobblestone path" → ["cobblestone", "path"]
"low hedges" → ["hedge", "hedges"]
"sage incense" → ["sage", "incense"]
```

Rules:

- Deterministic only.
- Do not use the LLM to generate coverage terms.
- Keep generated terms conservative.

Done when:

- Required facts without explicit coverage terms still get basic checks.
- Tests prove generated terms are useful but not overbroad.

### MT-415: Add interactive object validator

Goal: Ensure `look_targets` only contains allowed objects.

Rules:

- Every `look_targets` key must exist in `interactive_objects`.
- If `interactive_objects` is empty, `look_targets` must be `{}`.
- Look text must not include forbidden features.
- Look text must not use second person.

Done when:

- Extra look target keys fail validation.
- Empty interactive list with generated look text fails.
- Valid look targets pass.

### MT-416: Add combined validation report object

Goal: Produce one structured validation result per room.

Shape:

```json
{
  "room_id": "...",
  "status": "pass",
  "sentence_count": 3,
  "second_person_count": 0,
  "forbidden_feature_violations": [],
  "exit_violations": [],
  "missing_required_features": [],
  "invented_interactive_objects": []
}
```

Done when:

- All validators feed one report object.
- Failure reasons are explicit.
- Tests cover one clean pass and one multi-failure case.

### MT-417: Add constrained repair prompt builder

Goal: Build a repair prompt from validation failures only.

Repair prompt must include:

- Original description.
- Original look targets.
- Typed generation payload.
- Specific validation failures.
- Instruction to preserve valid content where possible.

Do not include vague improvement language.

Done when:

- Repair prompt contains only detected issues.
- Tests verify missing facts, forbidden terms, and invented exits are listed correctly.

### MT-418: Add one-attempt repair workflow

Goal: Run repair once after failed validation.

Flow:

```text
generate -> parse -> validate
if fail:
  repair once -> parse -> validate again
```

Rules:

- No infinite retries.
- If repair fails, mark for fallback.
- Preserve both original and repaired validation reports.

Do not run fallback inside this task unless already implemented.

Done when:

- Unit tests mock generation failure and repair success.
- Unit tests mock repair failure and fallback-needed status.

### MT-419: Add deterministic fallback generator

Goal: Produce valid plain room text when LLM output fails.

Fallback uses only:

- required room facts
- allowed exits
- allowed sensory details
- interactive objects only if supplied

Example:

```text
A cobblestone path runs between trimmed shrubs and low hedges. The faint scent of sage incense lingers in the quiet air. The path continues north and south through the district.
```

Done when:

- Fallback output passes validators.
- Fallback does not invent objects.
- Fallback does not invent exits.
- Fallback does not invent weather or time of day.
- Tests cover rooms with and without exits.

### MT-420: Add Phase 4 generation metadata

Goal: Track how each final room description was produced.

Metadata:

```json
{
  "generation_status": "initial_pass | repaired_pass | fallback_pass | failed",
  "repair_attempted": true,
  "fallback_used": false,
  "validation_before_repair": {},
  "validation_after_repair": {}
}
```

Done when:

- Export files include generation status.
- Summary JSON can count initial, repaired, fallback, and failed rooms.

### MT-421: Expand Phase 4 summary report

Goal: Make batch evaluation objective.

Summary JSON should include:

```json
{
  "total_rooms": 20,
  "initial_pass_count": 0,
  "repair_success_count": 0,
  "fallback_count": 0,
  "failed_count": 0,
  "second_person_total": 0,
  "forbidden_feature_violation_rooms": [],
  "exit_violation_rooms": [],
  "required_feature_coverage_rate": 0.0,
  "prompt_leakage_rooms": []
}
```

Done when:

- Report separates initial passes from repaired passes.
- Report separates repaired passes from fallback passes.
- Five known problem rooms are highlighted.
- Phase 3.1 vs Phase 4 comparison is possible.

### MT-422: Run controlled 20-room Phase 4 batch

Goal: Rerun the same 20-room comparison only after schema, prompt, validation, repair, and fallback exist.

Do not change the test slice.

Do not change:

```text
- room slice
- model target
- comparison criteria
- batch size
```

Pass criteria:

```text
0 second-person violations
0 invented exit/geometry violations
0 forbidden-feature violations
>= 90% required-feature coverage
>= 80% initial or repaired pass without fallback
No prompt leakage
No cave/dungeon contamination in non-cave rooms
```

Done when:

- Fresh Phase 4 exports are generated.
- Summary JSON is rebuilt.
- Markdown comparison report is rebuilt.
- Final verdict is recorded with concrete examples.

## Hard guardrails for Aedan

```text
Do not rewrite the entire style prompt.
Do not broaden the prose target.
Do not add new atmosphere categories mid-pass.
Do not change the 20-room test slice.
Do not judge success by beauty before correctness.
Do not promote inherited zone/area context into required room facts.
Do not run MT-422 until MT-408 through MT-421 exist.
Do not add multi-retry repair loops.
Do not let fallback invent objects, exits, weather, or time of day.
Do not solve the missing canonical area-source problem inside MT-403.
```

## Recommended execution order

```text
MT-403: typed prompt assembly
MT-404: prompt fixture tests
MT-405: allowed-exit prompt constraints
MT-406: interactive object prompt constraints
MT-407: JSON output contract
MT-408: JSON output parser
MT-409: sentence-count validator
MT-410: second-person validator
MT-411: forbidden-feature validator
MT-412: allowed-exit validator
MT-413: required-feature coverage validator
MT-414: coverage-term helper
MT-415: interactive object validator
MT-416: combined validation report
MT-417: repair prompt builder
MT-418: one-attempt repair workflow
MT-419: deterministic fallback generator
MT-420: generation metadata
MT-421: summary/report expansion
MT-422: controlled 20-room batch
```

The important thing: MT-403 through MT-407 make the LLM easier to control. MT-408 through MT-416 prove whether it obeyed. MT-417 through MT-419 recover failures. MT-420 through MT-422 make the batch result measurable.

## Bottom line

The tag idea should not be abandoned. It should be formalized.

The winning structure is not a flat list of atmosphere prompts. It is:

```text
Required room facts:
- cobblestone path
- shrubs and hedges
- sage incense smell

Soft inherited context:
- The Crossing
- Scholar's District
- academic quiet
- old city stonework

Forbidden:
- dynamic weather
- time of day
- invented doors/stairs/gates
- direct player mention
```

That gives the model creative direction while keeping it inside the actual
room data.