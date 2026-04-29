# MT-414: Convert Room-Description Prompt Shape From Form Packet To Prose Packet

## Ready-To-Send Dispatch

```text
Proceed with MT-414 only.

Use this file as the acceptance source of truth:

docs/builder/phase4_mt414_prompt_shape_handoff.md

Follow MT-414.01 through MT-414.12 in order.

Do not expand scope.
Do not run live LLM batches.
Do not proceed to MT-415.
Stop after unit validation and report the result.
```

Proceed with MT-414 microtasks only.

Acceptance source:

```text
docs/builder/phase4_mt414_prompt_shape_handoff.md
```

Goal:

Convert the actual model-facing room-description prompt from a form-style or section-heavy prompt into a prose-style instruction packet, because the model is echoing prompt structure back as `Room Data` / `Atmospheric Tags` / `Description` wrappers.

Do not change sampler scoring.
Do not change length targets.
Do not change sentence targets.
Do not change room YAML.
Do not import generated descriptions.
Do not batch apply descriptions.
Do not run live LLM batches.
Do not change LM Studio config.
Do not add post-processing that strips bad output.

Complete the following microtasks in order.

## MT-414.01 — Identify the actual model-facing prompt path

```text
Find the code path that builds the prompt actually sent to the LLM.

Likely file:
world/builder/prompting/room_description_prompt.py

Confirm the distinction between:
- prompt.prompt / actual model-facing text
- user_prompt / debug or compatibility text, if present
- typed prompt/debug sections, if present

Do not edit yet.

Report which field is sent to the model by generate_sample_descriptions.py or room_description_generation.py.
```

Acceptance:

```text
Aedan identifies the exact model-facing prompt variable and the compatibility/debug prompt variable, if separate.
```

## MT-414.02 — Add a focused failing test for form-section removal

```text
In tests/test_room_description_prompt.py, add a test proving the actual model-facing prompt does NOT contain form-style section headers likely to be echoed.

The test should inspect prompt.prompt, not debug/user_prompt unless prompt.prompt does not exist.
```

Forbidden in `prompt.prompt`:

```text
Room Data
Atmospheric Tags
Description:
Structure:
Materials:
Tags:
```

Do not forbid normal prose words like `description` in every context unless that is necessary. The target is form labels and section headers.

Acceptance:

```text
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_room_description_prompt
```

Expected at first: may fail if the current prompt is still section-heavy.

## MT-414.03 — Add a focused test that required facts still survive

```text
Add or update a test proving the prose-style model-facing prompt still includes the facts the model needs.
```

The test must verify `prompt.prompt` includes:

```text
room name
zone/environment or equivalent setting context
exits
room shape
allowed facts or safe factual constraints
interactive-object rule
3-5 sentence target
45-90 word target
grounded-only rule
```

Acceptance:

```text
The test protects against removing too much data while removing labels.
```

## MT-414.04 — Preserve typed/debug compatibility separately

```text
If existing tests require typed/debug section headings such as INTERACTIVE OBJECTS or other typed prompt sections, do not delete those blindly.

If needed, keep section-heavy output only in compatibility/debug fields, not in the actual model-facing prompt.prompt.
```

Acceptance:

```text
Existing MT-401 through MT-413 prompt-boundary tests remain green, or are updated only when they were incorrectly checking model-facing prompt instead of debug text.
```

## MT-414.05 — Refactor model-facing prompt into natural-language packet

```text
Change room_description_prompt.py so prompt.prompt reads like an instruction packet, not a form.

Avoid large uppercase section headers.
Avoid bullet-heavy metadata.
Avoid field-label patterns that look like:
Structure:
Exits:
Materials:
Tags:
Description:
```

Preferred model-facing shape:

```text
Write one player-facing DireMud room description.

Known facts: The room is named Amberwick Lane. It is an urban street in New Landing. Its exits run north and east. Its shape is a simple crossing. Allowed surfaces or boundaries include fitted cobbles, building fronts, and close boundaries. No interactive objects may receive look text.

Use only those facts. Return one plain paragraph only. Do not output labels, headings, markdown, bullets, or field names. Now write the room description as one plain paragraph.
```

Acceptance:

```text
prompt.prompt looks like prose instructions, not a schema/form.
```

## MT-414.06 — Add the final natural-language generation command

```text
Ensure the final line before generation is a plain natural-language command, not a heading, label, or field name.
```

Required final command concept:

```text
Now write the room description as one plain paragraph.
```

Acceptance test must confirm this final line appears near the end of `prompt.prompt`.

## MT-414.07 — Keep the LM/style contract intact

```text
Do not weaken the existing style contract while reshaping the prompt.
```

The model-facing prompt must still include these constraints:

```text
3-5 sentences
45-90 words
plain/concrete/readable
grounded facts only
no headings
no labels
no markdown
no bullets
no blank lines
no Room Description / Room Data / Atmospheric Tags
no unsupported props/details
```

Acceptance:

```text
Existing MT-407, MT-410, and MT-412 style-contract tests remain meaningful.
```

## MT-414.08 — Avoid overcorrecting into under-description

```text
Do not remove factual context so aggressively that the model only has exits and shape.

The prompt must still give enough safe material to produce a 3-5 sentence, 45-90 word room description.
```

Required safe content should include, when available:

```text
environment
shape/topology
exits
surfaces
boundaries
allowed details
interactive objects rule
safe fallback features
```

Acceptance:

```text
Prompt still gives enough grounded material for a useful paragraph.
```

## MT-414.09 — Run narrow prompt tests

Run:

```text
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_room_description_prompt
```

If failures occur:

```text
Fix only failures related to the prompt-shape refactor.
Do not widen into sampler scoring or live generation.
```

## MT-414.10 — Run typed prompt compatibility tests

Run:

```text
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_typed_generation_input_schema tests.test_room_description_prompt
```

Acceptance:

```text
Typed generation input and prompt boundaries remain green.
```

## MT-414.11 — Run sampler unit tests only

Run:

```text
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_generate_sample_descriptions
```

Important:

```text
This is unit validation only.
Do not run LLM sampler batches in MT-414.
```

## MT-414.12 — Report exact prompt-shape result

Return:

```text
MT-414 complete.

Files changed:
- ...

Tests added/updated:
- ...

Model-facing prompt changed:
- yes/no

Debug/user_prompt compatibility preserved:
- yes/no / not applicable

Validation:
- command...
- result...

Production code changed:
- yes/no

Compatibility risks:
- ...

Live rerun performed:
- no
```

## Guardrail for Aedan

```text
Stop after MT-414 validation. Do not proceed to MT-415. The live rerun is a separate task.
```