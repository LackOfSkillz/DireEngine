# Phase 3 v3.1 - Tighten the Gate, Add Craft Direction

## Background

Phase 3 batch 1 produced real texture improvements on atmosphere-tagged rooms,
but human review revealed three failure modes:

1. **Compliance regression.** Banned-noun leak rate went from 1/4 (Phase 2) to
   4/4 runs. Untagged rooms (`_472_564`, `_686_294`) drifted, picking up
   atmospheric cues without tag license. The atmospheric clause from MT-303
   leaked permission across its conditional gate.

2. **Structural fabrication on tagged rooms.** Several tagged rooms gained
   texture by also inventing structural content the metrics didn't catch:
   - `_120_702` invented a vaulted ceiling and a north exit
   - `_96_918` invented an irregular rectangle and three exits
   - `_352_326` upgraded a 3-path intersection to 4 paths, added an archway
   - `_252_536` turned an enclosed (no-exits) room into a three-passage
     timber-walled room
   The LLM treated atmospheric license as general license - permission to
   mention materials became permission to invent the architecture.

3. **Sterility persists where it isn't fabricated.** Rooms that don't
   fabricate are still atmospherically empty. The user feedback that
   triggered Phase 3 ("the descriptions are clinically sterile, I don't
   know if buildings are stone or wood, if it's affluent or a slum") is
   not fully resolved by atmospheric tags alone. Some tagged rooms keyword-
   stuff atmosphere words without actually feeling textured.

The diagnosis: the prompt has been engineered around what NOT to do (no
banned nouns, no fabrication, no geometry violations) but not around what
GOOD looks like. Atmospheric tags gave the LLM permission, but didn't tell
it how to use that permission with craft. The result is a model that either
(a) writes sterile-but-truthful prose, (b) writes textured prose by also
fabricating, or (c) keyword-stuffs atmospheric words without producing
real sensory richness.

This batch addresses all three with a coordinated prompt revision. The
prompt becomes both tighter (where it leaked) and more directive (where
it was silent on craft).

## Reference: MUD craft principles

Research on MUD room description writing across multiple sources (Discworld
MUD's "Ten Commandments of Descriptions," Writing Games' guide, Rotjmud's
builder guide, and others) consistently identifies these principles:

**Hard rules (every source):**
- No second-person ("you"). Descriptions must work for players who arrive
  standing, sitting, scrying, or just logging in.
- No assuming player action, emotion, or direction of travel.
- No relative directions ("ahead," "behind," "left," "right").
- No mention of weather, time of day, or other dynamic state.
- No NPCs in description text.
- No command hints in description text.
- No hidden exits - every exit in prose must be a real exit.

**Craft principles (consistent across sources):**
- Engage multiple senses. Sight is default; smell, sound, and touch separate
  competent prose from sterile prose.
- 3-5 sentences. Long enough to convey character, short enough to avoid
  spam in "brief mode."
- One specific or unique anchor per room - a detail that distinguishes
  this room from its neighbors.
- Show, don't tell. Don't say "old" - describe what shows age. Don't say
  "busy" - describe what makes it busy.
- Active voice. Specific nouns over abstract ones. Sparse adjectives.
- Proper sentences with verbs.

The craft principles, not just permission expansion, are the missing piece
for moving from sterile-but-truthful to textured-and-truthful prose.

## Microtasks

### MT-311: Replace the system prompt with a constraint+craft hybrid

Update `world/builder/templates/room_description_system_prompt.txt`. The
existing constraint block stays, but two new sections are added: a tightened
atmospheric clause and a positive craft direction block.

Target structure (in order):
1. Existing role/voice header (no change)
2. Existing constraint block (no change to sentence count rule, exit list
   rule, etc.)
3. Tightened atmospheric clause (replaces MT-303)
4. New craft direction block (new)
5. New example pairs (new)
6. Existing reinforcement clause (modified per below)

**Section 3 - Tightened atmospheric clause (replaces MT-303):**

```
When atmospheric tags are absent from THIS ROOM, restrict descriptive
content to what the structural tags directly support. Do not fabricate
materials, sensory details, or surroundings.

When atmospheric tags ARE present, you may use them to inform sensory
and contextual detail aligned with their values: materials values
license mention of those materials; sensory values license those
sensory details; social_character values license that character;
surroundings values license those nearby features; upkeep values
license that condition.

Atmospheric tags do NOT authorize structural or architectural changes.
You may not invent exits beyond those listed in the exit data. You may
not invent ceilings, doors, archways, windows, vaulted spaces, or any
architectural feature not established by the room's structural tags.
You may not redescribe the room's shape or exit count beyond what the
exit data and structural tags provide.

Banned nouns from the constraint block remain forbidden regardless of
atmospheric context.
```

**Section 4 - Craft direction block (new):**

```
Write each description with these craft principles:

- Engage at least two senses. Sight is default; pair it with smell,
  sound, or touch when atmospheric tags license those details.
- Include one specific anchor unique to this room - a particular
  sensory detail, material, or sound that makes this room different
  from a neighboring one. Avoid generic phrases like "worn smooth by
  countless footsteps" that could fit any room.
- Show, don't tell. Do not say a place is "busy," "old," "quiet," or
  "bustling." Describe what makes it so, using licensed details.
- Use active voice. Choose specific nouns over abstract ones. Use
  adjectives sparingly.
- Never use "you" or address the reader. Write in third-person
  descriptive voice.
- Never assume player action, emotion, or direction of travel.
- Do not list or describe exits in prose. Exits are presented to the
  player separately by the game.
- Do not mention weather, time of day, NPCs, or specific objects that
  could be picked up.
- Aim for 3-5 sentences.
```

**Section 5 - Example pairs (new):**

```
Examples of the craft level expected:

URBAN EXAMPLE (a tavern room - note: tagged with structure: building-
interior, function: tavern, named_feature: hearth, materials: timber-
walls, planked-floor, sensory: cooking-smell, social_character:
working-class):

Low-hanging timber beams, blackened with age and smoke, make this
cramped tavern room feel intimate. The plank floor is sticky underfoot,
and the sharp scent of roasted meat cuts through the smell of stale ale.
A hearth set into the far wall throws unsteady light across the room,
catching on the rough grain of the walls.

WILDERNESS EXAMPLE (a forest path - note: tagged with structure:
passage, surroundings: forest-nearby, sensory: quiet-ambient,
materials: dirt-floor):

Sunlight barely filters through the dense canopy, leaving the forest
floor in green twilight. A dirt path, half-covered with moss, twists
between ancient oaks. The chirping of birds carries through the
branches, then cuts short, as if something nearby has gone still.

These examples show what "engaging two senses," "one specific anchor,"
and "show don't tell" look like in practice. Match this level of craft
when atmospheric tags license the sensory and material details.
```

**Section 6 - Reinforcement clause (modified):**

The existing reinforcement clause should be updated to reference both
the new restrictive default and the new craft block:

```
Stay within the licensed truth set: structural tags, exit data,
zone context, and atmospheric tags when present. Do not invent
content beyond what these license. Do not slip into second-person.
Do not include exits in prose. Apply the craft principles
consistently.
```

Update existing tests in `tests/test_room_description_prompt.py` to verify:
- The tightened atmospheric clause is present
- The craft direction block is present
- The example pairs are present
- The reinforcement clause is updated
- Existing assertions about atmosphere tag rendering still pass

### MT-312: Remove or tighten the natural-language atmosphere paraphrase

Inspect `world/builder/prompting/room_description_prompt.py`. The MT-304
work introduced atmospheric tags as both a structured list AND an optional
natural-language clause. The natural-language clause is the most likely
contributor to the cross-leak failure mode (it presents tags as prose,
which the LLM may read as license to write loosely).

Remove the natural-language clause entirely. Atmospheric tags are presented
to the LLM as a structured list only, in the same format as other room tags
(THIS ROOM section).

Document the change in the commit message.

### MT-313: Add structural fabrication detection to the metrics pipeline

Update `tools/generate_sample_descriptions.py` to detect structural
fabrication on atmosphere-tagged rooms.

For each tagged room in each run, compare:
- Number of cardinal directions mentioned in the description vs the actual
  exit count in room data
- Mention of architectural features (ceiling, door, archway, vaulted,
  staircase, gate, arch, window, balcony, alcove) that aren't licensed by
  structural tags

Add a new top-level field to the summary JSON:
`structural_fabrication_per_room`, listing per-room per-run any structural
inventions detected.

This is detection-only. The new metric does not change generation behavior.

### MT-314: Add second-person and assumption detection to the metrics pipeline

While MT-313 is being added, also add detection for two of the craft-rule
violations from MT-311:

- Second-person pronoun violations: any occurrence of "you," "your,"
  "yours" in description text
- Player-assumption violations: phrases like "you decide," "you feel,"
  "you notice," "as you walk," etc.

Add as separate fields in the summary JSON: `second_person_violations_per_run`
and `player_assumption_violations_per_run`.

Detection-only. Does not change generation.

### MT-315: Re-run 4-pass evaluation with v3.1 prompt

With MT-311 (constraint+craft hybrid prompt), MT-312 (paraphrase removed),
MT-313 (structural detection), and MT-314 (second-person detection) in
place, run the same 4-pass evaluation on the same 20-room slice.

Save as:
- `exports/sample_descriptions_phase3_v3_1_run1.txt` through `_run4.txt`
- `exports/sample_descriptions_phase3_v3_1_summary.json`

Same temperature (0.5), same canonical zone, same room IDs, same tagged
vs untagged split.

### MT-316: Comparison report

Produce a brief markdown report `exports/phase3_v3_1_comparison.md`
documenting:

**Compliance metrics (target: improve over Phase 3 batch 1):**
- Banned-noun leak rate: v3.1 vs Phase 3 batch 1 (target <=2/4 runs)
- Geometry violations: v3.1 vs Phase 3 batch 1 (target <=1/4)
- Structural fabrication on tagged rooms: per-room counts
- Second-person violations: count
- Player-assumption violations: count
- Untagged drift in the 3-room sample: per-room verdict

**Quality metrics (target: retain or improve over Phase 3 batch 1):**
- Atmospheric keyword hits on tagged rooms: v3.1 vs Phase 3 batch 1
- Repeated phrases (top 10): is "intersection three paths diverge" still
  4/4? Is the homogeneity less or worse?

**Spot-check verdict on 5 specific rooms (read the actual prose):**
- `_252_536` - does it stay enclosed (no exits)? Was severely fabricated
  in batch 1.
- `_96_918` - does it stop inventing exits and irregular rectangles?
  Was severely fabricated in batch 1.
- `_204_360` - does it retain cobbles/commerce/smell richness? Was a
  clean win in batch 1; verify the tightening didn't sterilize it.
- `_472_564` - has the unauthorized atmosphere drift gone away? Was
  a regression-check room.
- `_318_564` - has the `hall`/`door` banned-noun leak stopped? Was the
  recurring banned-noun source.

**Overall verdict:** one of:
- "Ready to ship Phase 3" (compliance back to Phase 2 baseline, atmosphere
  retained or improved, sterility reduced on tagged rooms)
- "Needs another pass" (specifies what failed)
- "Approach not viable at this model size" (specifies why)

### MT-317: Stop and report

Do not iterate further. The decision about acceptance, another revision
pass, or revert is mine to make after reviewing the comparison report.

## Stop conditions

Pause the batch and report immediately if:

- Banned-noun leak rate stays above 2/4 runs after MT-311 prompt change
  (would indicate the constraint tightening didn't take, deeper rethinking
  needed)
- Structural fabrication is still present on `_252_536` or `_96_918`
  (would indicate the no-structural-license clause didn't work)
- Atmospheric keyword hits drop more than 50% from batch 1 on tagged rooms
  (would indicate the tightening went too far and killed the texture)
- Second-person violations appear in any run (would indicate the craft
  block isn't being attended to at all)

## Constraints

- Do not change the atmosphere vocab (MT-301), schema (MT-302), prompt
  assembly for atmosphere tags' structured list portion (MT-304's structured
  list survives; only the paraphrase is removed per MT-312), input_hash
  inclusion (MT-305), or Inspector UI (MT-306). Those are working as
  intended.
- Do not change the 6 atmosphere-tagged rooms in `crossingV2.yaml`.
- Do not change the 14 untagged rooms.
- Do not change the canonical 6-room slice anywhere in code or docs.
- Do not change the District Painter scope. That batch is deferred until
  this room-level work demonstrates clear quality improvement.
- The deliberate changes are: prompt rewrite (MT-311), paraphrase removal
  (MT-312), structural detection (MT-313), second-person detection
  (MT-314), and the evaluation pass (MT-315/316).

## A note on prompt length

The v3.1 prompt is significantly longer than v3 because it adds craft
direction and examples. This is deliberate. Mistral Nemo 12B has shown in
prior phases that it follows positive direction better than negative
constraint alone. The example pairs give it concrete patterns to imitate
rather than abstract rules to follow.

If batch 1 of v3.1 reveals that the longer prompt diluted constraint
attention (e.g. compliance got worse instead of better), report this
specifically - that finding would indicate the model can't hold both
constraint pressure and craft direction at this prompt size, which is a
useful constraint on future architecture.