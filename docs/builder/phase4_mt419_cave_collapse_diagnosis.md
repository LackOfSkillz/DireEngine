# MT-419: Diagnose Cave Collapse, Then Test Model Swap

## Ready-To-Send Dispatch

```text
Proceed with MT-419 only.

Acceptance source:
docs/builder/phase4_mt419_cave_collapse_diagnosis.md

This is a diagnosis-first task.
Do not patch production code.
Do not modify room data.
Do not modify the codebase prompt.
Do not modify production sampling parameters.
Do not run the full 17-room MT-417 slice again.
Run Phase A first, then Phase B.
Phase C is gated and requires explicit user direction before any model download or swap.
Stop after writing exports/mt419_findings.md and reporting the verdicts.
```

## Background

MT-417 surfaced a decisive new failure mode: catastrophic environment substitution. Across three zones (`demo1`, `crossingV2`, `new_landing`), the model produced cave-passage descriptions with damp air, stone walls, dripping water, and related subterranean imagery even for rooms whose ids and human context clearly imply urban streets or non-cave spaces.

Examples include `Amberwick Lane`, `Saltward Street`, and `Kingshade Street` rooms in `new_landing` being described as cave passages, chambers, or tunnel-like spaces. This is distinct from the earlier wrapper-leakage problem. It indicates either:

1. Bad room data reaching the model
2. Prompt assembly corrupting or over-emphasizing structure tags
3. Sampling parameter collapse causing the model to lock onto one environment pattern

MT-417 also confirmed a separate issue: the codebase client sends a single `user` message and no `system` role, so the LM Studio UI system prompt is not reliably governing output behavior. That matters, but the cave-collapse behavior is now the higher-priority diagnosis.

The working hypotheses are:

1. Sampling parameters changed from the more varied MT-415 run and may have narrowed the model into a cave-default mode.
2. Some `new_landing` room data may actually contain cave-flavored structure tags such as `cave-passage`.
3. If neither of those explains the collapse, a model swap becomes the next serious candidate.

## Phase A: Verify room data integrity

Read the actual YAML data for these three rooms from:

```text
worlddata/zones/new_landing.yaml
```

Target room ids:

```text
amberwick-lane-western-run-4213-4213-4213
saltward-street-and-amberwick-lane-4217-4217
kingshade-street-and-amberwick-lane-4212-4212
```

For each room, report:

- The full room entry from the YAML
- The `tags.structure` value if present
- Any `atmosphere.materials` values if present
- Whether the data contains `cave-passage` or similar cave-flavored values

### Phase A decision rule

If the room data itself contains `cave-passage` or equivalent cave-oriented structure/material values, record that as the explanation for MT-417's cave-collapse behavior. Report that the data is wrong or unexpectedly cave-flavored. Do not modify the data. Continue to Phase B anyway, because the sampling rollback test is still useful context.

If the room data is urban-coded or otherwise non-cave, inspect:

```text
world/builder/prompting/room_description_prompt.py
```

Report how structure tags and atmosphere/material values are forwarded into the model-facing prompt, and whether prompt assembly appears to be corrupting or over-emphasizing those fields.

Do not patch code in this phase. Report only.

## Phase B: Sampling parameter rollback test

Run a one-off live generation slice using the same model as MT-417:

```text
mistral-nemo-12b-instruct
```

Use the original MT-415-style sampling parameters:

- Temperature `0.5`
- Repeat penalty `1.0` or disabled
- Keep Top P unchanged from current config
- Keep Top K unchanged from current config
- Keep Min P unchanged from current config

Keep everything else the same:

- Same codebase prompt
- No LM Studio UI override assumptions
- No production code changes

Use a 6-room slice spanning all three zones, 2 rooms per zone:

```text
demo1:
  CRO_500_100
  CRO_500_150

crossingV2:
  crossingV2_192_132
  crossingV2_214_132

new_landing:
  amberwick-lane-western-run-4213-4213-4213
  saltward-street-and-amberwick-lane-4217-4217
```

Save the output to:

```text
exports/sample_descriptions_mt419_param_rollback.txt
```

Then read the outputs and report:

- Did the cave-collapse pattern persist or break?
- Are urban rooms described as urban or still as caves/chambers/passages?
- Did wrapper leakage change materially?
- Subjective quality relative to MT-417

Where useful, include a small metric summary using the existing rubric from:

```text
tools/generate_sample_descriptions.py
```

but the core purpose of Phase B is diagnostic, not a full formal batch evaluation.

## Phase C: Qwen 2.5 14B model swap test

Run Phase C only if the human explicitly directs you to do so after Phase A and Phase B are reported.

If explicitly directed, download and load:

```text
Qwen 2.5 14B Instruct GGUF at Q4_K_M
```

Then run the same 6-room slice with:

- Qwen 2.5 14B as the model
- Temperature `0.5`
- Repeat penalty `1.0` or disabled
- Same codebase prompt

Save the output to:

```text
exports/sample_descriptions_mt419_qwen14b.txt
```

Compare against both:

- `exports/sample_descriptions_mt417_run1.txt`
- `exports/sample_descriptions_mt419_param_rollback.txt`

Specifically report:

- Wrapper leakage behavior
- Whether cave collapse disappears
- Second-person violations
- Geometry violations
- Subjective quality versus both prior runs

Do not start Phase C without explicit user direction.

## Stop and report

Write findings to:

```text
exports/mt419_findings.md
```

That report must include:

- Phase A room-data integrity verdict
- Phase B parameter-rollback verdict
- Phase C verdict if Phase C was explicitly run
- A consolidated recommendation for the next move

## Constraints

- Do not modify room data even if it is wrong.
- Do not modify production sampling parameters.
- Do not modify the codebase prompt.
- Do not rerun the full MT-417 17-room slice.
- Use one-off commands or scripts for diagnosis only.
- Phase C requires explicit user direction before any download or model swap.