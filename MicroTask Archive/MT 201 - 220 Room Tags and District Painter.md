# Builder Description Feature — Phase 2 (Room-Level Tags)

## Goal
Add room-level tag editing with chip UI. Prompts compose zone + room context.
Output becomes more specific to individual rooms.

## Success criteria
- Builder can toggle structure/function/feature/condition tags on a room via chips
- Custom tags can be added as free text
- Generation prompt includes room tags automatically
- Visible quality improvement over Phase 1 (rooms in same zone produce
  differentiated output)
- Cache correctly invalidates when tags change

## Microtasks

### MT-201: Room tag vocabulary
Create `dire_builder/vocab/room_vocab.yaml` (or equivalent path under
`world/builder/vocab/`) with:

```yaml
structure:
  - street
  - square
  - intersection
  - plaza
  - alley
  - courtyard
  - building-interior
  - threshold
  - bridge
  - dock
  - stair
  - hallway
  - chamber
  - entrance

specific_function:
  - shop
  - tavern
  - inn
  - temple
  - guild-hall
  - forge
  - bakery
  - brothel
  - jail
  - residence
  - barracks
  - library
  - warehouse
  - market-stall
  - kitchen
  - cellar

named_feature:
  - fountain
  - statue
  - well
  - signpost
  - gibbet
  - shrine
  - well-house
  - firepit
  - altar
  - pulpit
  - throne
  - hearth
  - workbench

condition:
  - pristine
  - well-maintained
  - worn
  - crumbling
  - burnt-out
  - abandoned
  - refurbished
```

Unit test: vocab loading, schema validation.

### MT-202: Room schema extension
Add to room data model:

```yaml
tags:
  structure: str | null
  specific_function: str | null
  named_feature: str | null
  condition: str | null
  custom: list[str]  # default []
```

Migration: existing rooms get an empty tags object on next load. Schema tests;
verify existing rooms load without errors.

### MT-203: Reusable chip component
Build a `TagChipGroup` component in the existing builder frontend code:
- Props: label, vocabulary (list of strings), value (current selection),
  multi (bool, default false), onChange(newValue), allowCustom (bool, default false)
- Renders a label row of chips. Active chip is filled with accent color,
  inactive is outlined.
- Click toggles active state.
- If allowCustom, a "+ add custom" action appears at end of row, opens a small
  input field, Enter adds the custom tag, Escape cancels.
- If multi=false, clicking an active chip deactivates it.

Component tests if framework supports them; otherwise manual test in isolation.

### MT-204: Room tags in Inspector
Add a "Tags" section to the existing Inspector panel, between basic room info
and descriptions. Structure:

- INHERITED TAGS (if zone has generation_context): muted chip row showing
  zone's setting_type, era_feel, culture, mood, climate. Non-editable.
- ROOM TAGS: one TagChipGroup per category — Structure (single), Function
  (single), Feature (single), Condition (single). Vocabulary from MT-201.
- CUSTOM TAGS: TagChipGroup with vocabulary=[] and allowCustom=true.

Persistence on change (debounced if needed). Manual test: set tags, reload,
verify persistence.

### MT-205: Extend prompt assembly for room tags
Update `build_base_prompt` in `world/builder/prompting/room_description_prompt.py`
to include room tags in the "=== THIS ROOM ===" section. Translate tags into
natural clauses where helpful:
- structure: tavern → "This is a tavern."
- named_feature: well → "A public well stands here."
- condition: crumbling → "The stonework is crumbling, clearly long past its prime."

Custom tags: list as comma-separated "Also: tag1, tag2, tag3."

Unit tests: prompt assembly with various tag combinations.

Quality validation: per the prompt evaluation methodology in DireBuilder.md,
generate descriptions for the canonical six-room set across 4 runs after this
microtask, with at least one room tagged with each of structure/function/feature/
condition. Verify output meaningfully differs between rooms while preserving
zone voice.

### MT-206: Include room tags in input hash
Update `_input_hash` in `world/builder/prompting/room_description_generation.py`
to include room tags (deterministic serialization — sort lists, sort keys).
Editing any tag invalidates cache on next force=false call.

Test: generate description, change one tag, call generate without force,
verify regeneration occurs.

## PHASE 2 CHECKPOINT (after MT-206)

Generate descriptions per the four-run methodology on the canonical
crossingV2 six-room slice with these constraints:
- At least 3 of the 6 rooms must have explicit room tags before the run
- Configure at least 2 different tag combinations across those 3 rooms

Report:
- Banned-noun leak rate across the 4 runs
- Geometry violation count across the 4 runs
- Identity term distribution per run
- Tag-supported specificity: do tagged rooms reflect their tag content in
  output? Does the output for a "tavern" room sound different from a
  "bridge" room?
- Subjective read on whether the addition of room tags compounded with zone
  context to produce more atmospheric, specific output

Do not begin Phase 3 (district painter) work until this checkpoint is
reviewed and approved.

## Bonus tasks (MT-EXTRA-1 through 3)

### MT-EXTRA-1: Voice preset library
Create `world/builder/presets/voice_presets.yaml` with 6 starter voice presets:

```yaml
presets:
  gritty-urban:
    description: "Gritty, pragmatic. Present tense. Acknowledge weather, smells, sounds. Avoid florid adjectives."
  scholarly-tranquil:
    description: "Measured, observational. Acknowledge scholarly details, books, lamp-light, the smell of parchment and ink."
  mercantile-terse:
    description: "Direct, transactional. Focus on goods, prices, people working. Short sentences."
  mythic-reverent:
    description: "Elevated, reverent. Acknowledge the weight of history and the sacred. Longer, flowing sentences."
  wilderness-observational:
    description: "Present tense. Sensory focus on terrain, weather, fauna, distances. No urban vocabulary."
  mercantile-bustling:
    description: "Energetic, noisy. Crowds, shouts, the press of people. Short descriptive bursts."
```

Add to zone generation_context.voice field: accept either a preset ID
(e.g. "gritty-urban") or a custom string. Prompt assembly resolves ID to
preset text. Add "Voice preset" dropdown to zone context form, with
"Custom..." option that reveals the textarea.

### MT-EXTRA-2: LLM call logging
Already partially exists in llm_client.py. Verify it logs: timestamp,
correlation_id, prompt_hash, model, temperature, input_chars, output_chars,
latency_ms, success (bool), error_type (if failure). Format: JSON lines.
Path: logs/llm_calls.log. If any fields are missing, add them.

Config field log_llm_calls (bool, default true) controls whether to log.

Verify log format and rotation behavior.

### MT-EXTRA-3: Prompt hash for debugging
Already exists at POST /api/rooms/{room_id}/generate-description?debug=true.
Verify it returns the assembled prompt and hash. Verify it does NOT expose
prompts in normal responses.

## Methodology reminders
- Per DireBuilder.md "Prompt Change Evaluation Methodology" section: any
  prompt change requires 4 runs of the canonical six-room set with
  distribution comparison.
- Stop at the Phase 2 checkpoint. Do not begin Phase 3 (district painter)
  without explicit approval.
- Do not change the system prompt's existing constraint or reinforcement
  blocks during MT-201 through MT-206. Only the room-context section
  changes.
