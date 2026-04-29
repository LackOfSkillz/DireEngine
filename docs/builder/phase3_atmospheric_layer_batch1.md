# Phase 3 - Atmospheric Layer (Batch 1)

## Background

Live-use review of 20 generated descriptions in crossingV2 surfaced that the
descriptions are positionally accurate but atmospherically sterile. Rooms tell
you where you are but not what it feels like to be there. No sense of materials,
no sense of socioeconomic character, no sense of surroundings.

The diagnosis: the v3 reinforced prompt's truth model is too thin. It only
permits physical detail derived from structure/function/feature/condition tags.
It explicitly forbids inventing materials, sensory detail, or surroundings from
zone context alone. That was the right call for preventing wholesale fabrication
in earlier sessions, but the cost is sterile prose.

The fix: expand what counts as truth the prompt will honor. Add an
atmosphere tag category that explicitly licenses sensory and contextual
detail. Tags in this category act as permission slips: when present, the LLM
may mention the atmospheric content they describe. When absent, the existing
truth restrictions apply.

This batch establishes atmospheric tagging at the room level first. District-
level application via a painter UI is a separate later batch - only built if
this room-level work demonstrates clear quality improvement.

## Methodology reminder

Per docs/builder/DireBuilder.md "Prompt Change Evaluation Methodology":
any prompt change requires a 4-run evaluation on the canonical six-room slice
plus the 20-room real-use slice from sample_descriptions_phase2_real_use_run1.
Single-run evaluations are insufficient.

## Microtasks

### MT-301: Atmosphere tag vocabulary

Create world/builder/vocab/atmosphere_vocab.yaml with five sub-categories:

```yaml
materials:
  - stone-walls
  - timber-walls
  - plaster-walls
  - brick-walls
  - mud-walls
  - log-walls
  - flagstone-floor
  - cobbled-floor
  - planked-floor
  - dirt-floor
  - earthen-floor
  - thatched-roof
  - tile-roof
  - slate-roof
  - timber-beams

social_character:
  - affluent
  - prosperous
  - middle-class
  - working-class
  - impoverished
  - destitute
  - mixed-class
  - residential
  - commercial
  - industrial
  - civic
  - religious
  - rough
  - genteel

surroundings:
  - shops-nearby
  - housing-nearby
  - taverns-nearby
  - market-nearby
  - temples-nearby
  - guilds-nearby
  - workshops-nearby
  - warehouses-nearby
  - docks-nearby
  - city-wall-nearby
  - water-nearby
  - fields-nearby
  - forest-nearby
  - quiet-area
  - busy-area

sensory:
  - smoke-smell
  - cooking-smell
  - fish-smell
  - rope-tar-smell
  - dung-smell
  - flowers-smell
  - sea-smell
  - rain-smell
  - dust-smell
  - sounds-of-traffic
  - sounds-of-commerce
  - sounds-of-water
  - sounds-of-bells
  - sounds-of-children
  - quiet-ambient
  - bustling-ambient

upkeep:
  - pristine-upkeep
  - well-maintained
  - lived-in
  - shabby
  - neglected
  - decaying
  - abandoned
```

These are advisory permission slips, not facts. The LLM uses them to know what
sensory and contextual detail is licensed for this room.

Unit test: vocab loading.

### MT-302: Room schema extension for atmosphere

Extend the room tags schema in world/builder/schemas/room_tag_schema.py with
a new sub-object:

```yaml
tags:
  structure: str | null
  specific_function: str | null
  named_feature: str | null
  condition: str | null
  custom: list[str]
  atmosphere:
    materials: list[str]
    social_character: list[str]
    surroundings: list[str]
    sensory: list[str]
    upkeep: str | null
```

Migration: existing rooms get an empty atmosphere object on load. No
existing data is destroyed.

Schema tests: serialization round-trip with atmosphere populated, and with
atmosphere as empty object, and with atmosphere field missing entirely (legacy
rooms).

### MT-303: Soften the prompt's reinforcement clause

In world/builder/templates/room_description_system_prompt.txt, update the
context-license clause to acknowledge atmospheric tags as legitimate license.

Find the existing clause that begins:
"you may not invent specific physical objects..."

Replace it with:

```
You may use atmospheric tags from the THIS ROOM section to inform sensory,
material, and contextual detail. When a room is tagged with materials,
social_character, surroundings, sensory, or upkeep values, those values
license related descriptive content. For example: a room tagged with
materials including 'timber-walls' permits mentions of wood, planks, or
timber. A room tagged with sensory including 'rope-tar-smell' permits
mention of those smells. A room tagged with social_character including
'affluent' permits descriptive cues of wealth or order.

Do not invent specific named NPCs, specific named objects, or specific
named events. You may invoke the general sensory and material character
of the place when atmospheric tags grant license.

When atmospheric tags are absent, restrict descriptive content to what the
basic structural tags directly support. Do not fabricate materials,
sensory details, or socioeconomic context without tag-licensed permission.
```

Update unit tests in tests/test_room_description_prompt.py:
- Verify the new clause is present in the assembled prompt
- Verify a room with atmosphere tags produces a prompt with those tags
  visible in the THIS ROOM section
- Verify a room without atmosphere tags produces a prompt that lacks the
  atmosphere section

### MT-304: Prompt assembly for atmosphere tags

Update world/builder/prompting/room_description_prompt.py to render
atmosphere tags into the THIS ROOM section when present.

Format suggestion:

```text
THIS ROOM:
- structure: passage
- specific_function: tavern
- named_feature: hearth
- condition: worn
- custom: taproom, riverfront

ATMOSPHERE:
- materials: timber-walls, planked-floor
- social_character: working-class, lived-in
- surroundings: shops-nearby, taverns-nearby
- sensory: cooking-smell, sounds-of-commerce
- upkeep: well-maintained
```

Use natural-language clauses where helpful, e.g. "The room is in a
working-class area, with shops and taverns nearby. Wood-walled and
plank-floored, with the smells of cooking and sounds of commerce drifting
in. The space is well-maintained."

Both formats may coexist; the structured list is the canonical input,
the natural-language version is supplementary if the LLM responds better
to it.

Unit tests: prompt assembly with various atmosphere combinations,
including all-empty atmosphere object.

### MT-305: Include atmosphere in input_hash

Update _input_hash in world/builder/prompting/room_description_generation.py
to include atmosphere tags. Changing any atmosphere field invalidates cache
on next generation call.

Test: generate description, change one atmosphere field, call generate without
force, verify regeneration occurs.

### MT-306: Atmosphere tagging in the Inspector UI

Extend the room tags Inspector section in
web/templates/webclient/builder.html and
web/static/webclient/js/dragonsire-browser-v2.js with an "Atmosphere"
sub-section below the existing room tags.

Five chip groups (one per atmosphere category):
- Materials (multi-select chips, allows custom)
- Social character (multi-select chips, allows custom)
- Surroundings (multi-select chips, allows custom)
- Sensory (multi-select chips, allows custom)
- Upkeep (single-select chips)

Reuse the existing TagChipGroup component. Persistence flows through the
same zone save path as the rest of the room tags.

Manual test: open a room, set atmosphere tags across all five categories,
save the zone, full-reload, confirm all atmosphere tags persist and render
correctly.

### MT-307: Add 6 representative atmosphere-tagged rooms in crossingV2

Pick 6 of the 20 rooms from the prior live-use sample. The selection should
mirror the original tagged/untagged distribution but add rich atmosphere tags
to half:

- 3 rooms that previously had no atmosphere tags (untagged in prior batch)
  -> tag them with atmosphere (rich) AND keep their existing room-level tags
  unchanged
- 3 rooms that previously had room-level tags but no atmosphere
  -> add atmosphere to them

Document which 6 rooms and what atmosphere combinations were applied.
The other 14 of the 20 stay unchanged so the comparison is clean.

Use atmospherically rich combinations. Examples:

For a working tavern room (tags: tavern, hearth, worn):
```yaml
atmosphere:
  materials: [timber-walls, planked-floor]
  social_character: [working-class, lived-in]
  surroundings: [taverns-nearby, housing-nearby]
  sensory: [cooking-smell, sounds-of-commerce]
  upkeep: lived-in
```

For a market intersection (tags: intersection, signpost):
```yaml
atmosphere:
  materials: [cobbled-floor, stone-walls]
  social_character: [commercial, mixed-class]
  surroundings: [shops-nearby, market-nearby]
  sensory: [sounds-of-commerce, cooking-smell, dust-smell]
  upkeep: well-maintained
```

For a quiet shrine (tags: temple, shrine, well-maintained):
```yaml
atmosphere:
  materials: [stone-walls, flagstone-floor]
  social_character: [religious, genteel]
  surroundings: [quiet-area, water-nearby]
  sensory: [quiet-ambient, sounds-of-water]
  upkeep: well-maintained
```

### MT-308: Run 4-pass evaluation on the same 20-room slice

With the new prompt, the new schema, and the 6 atmospherically tagged rooms
in place, regenerate the same 20-room slice from
sample_descriptions_phase2_real_use_run1.txt.

Run 4 passes. Save as:
- exports/sample_descriptions_phase3_real_use_run1.txt
- exports/sample_descriptions_phase3_real_use_run2.txt
- exports/sample_descriptions_phase3_real_use_run3.txt
- exports/sample_descriptions_phase3_real_use_run4.txt

Use the same temp 0.5, the same canonical zone, the same room IDs.

### MT-309: Aggregate analysis report

Produce sample_descriptions_phase3_real_use_summary.json with per-run metrics:
- Banned-noun violations per run, per room
- Geometry violations per run
- Identity-term distribution per run
- Repeated phrases (top 10 across all 4 runs)
- "The floor is..." sentence-start count per run

Also produce a comparison delta against
sample_descriptions_phase2_real_use_run1.txt:
- Did atmospherically tagged rooms gain texture?
- Did untagged rooms stay the same (sterile but accurate) or did the
  softened prompt accidentally loosen them too much (fabrication)?
- Did banned-noun leak rate stay near baseline (1/4 runs)?

Format the report with three sections:
1. Per-run metrics (the number tables)
2. Per-room before/after pairs for the 6 atmospherically tagged rooms
3. Per-room before/after pairs for 3 of the 14 untagged rooms (random
   sample) - to verify the prompt softening didn't loosen unauthorized
   fabrication

### MT-310: Stop and report

Do not propose further changes based on the metrics. Do not iterate the
prompt. The decision about how to interpret these results is mine to make
after reviewing the report.

Report deliverables:
- exports/sample_descriptions_phase3_real_use_run1.txt through _run4.txt
- exports/sample_descriptions_phase3_real_use_summary.json
- A brief markdown summary in the chat response covering:
  * Atmospheric quality verdict on the 6 tagged rooms (better, same, worse)
  * Compliance verdict on all 20 rooms (banned nouns, geometry, fabrication)
  * Whether tagged rooms feel materially different from their Phase 2 versions
  * Whether untagged rooms drifted from their Phase 2 baselines (regression
    check)

## Constraints for the entire batch

- Do not change the existing 6-room canonical slice anywhere in code or docs.
  This batch uses the 20-room slice as the evaluation set, not the 6-room slice.
- Do not modify the District Painter scope. That is a separate batch deferred
  until this room-level atmospheric work is reviewed.
- Do not modify the v3 prompt's existing constraint block (sentence count,
  exit list rule, etc.). The only prompt change is the reinforcement clause
  in MT-303.
- Use the same prompt change evaluation methodology in
  docs/builder/DireBuilder.md. 4-run distributions, no single-run conclusions.
- All tests pass before declaring the batch complete.

## Stop conditions

Pause the batch and report if:
- Banned-noun leak rate goes above 2/4 runs in MT-308 (regression)
- Untagged rooms in the comparison sample show fabrication (e.g. inventing
  walls, materials, or surroundings without atmospheric license) - this means
  the prompt softening went too far
- The MT-307 tagging exercise reveals the atmosphere vocab needs values
  not currently in the vocab file - surface those gaps before continuing