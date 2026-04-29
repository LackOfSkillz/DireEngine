# MT-421 -- Fix Prompt Truncation and Re-Test

## Background

MT-420 audit revealed that the assembled prompts for all three test rooms
were identical and consisted only of the system prompt, hard-truncated
mid-sentence at "Ma". The user-message section containing room name,
zone, structure tags, atmosphere tags, and allowed exits had been
entirely removed by the trimmer.

Cause: the live generation path was using `max_prompt_chars=5000`. The
system prompt alone is approximately 5,200 characters. The trimmer
deletes all user-prompt lines, then hard-truncates the system prompt
itself to 5,000 chars. The model never sees any room data.

This explains MT-417's cave-collapse and MT-419's environment
substitution. Neither was a model or sampling issue. Every room
received the same hollow prompt.

## Phase A: fix the truncation

In the generation path, increase `max_prompt_chars` from `5000` to
`12000`.

In `world/builder/prompting/room_description_prompt.py`, add a safety
check at the top of `assemble_room_description_prompt`:

```python
system_prompt = load_room_description_system_prompt()
if max_prompt_chars < len(system_prompt) + 500:
    raise ValueError(
        f"max_prompt_chars ({max_prompt_chars}) is too small to fit "
        f"the system prompt ({len(system_prompt)} chars) plus minimum "
        f"room context."
    )
```

Move the `system_prompt = load_room_description_system_prompt()` call
to the top of the function and reuse it.

In LM Studio, increase the loaded model context window from 4096 to at
least 8192 if the setting is available.

## Phase B: regenerate the diagnostic prompts

With `max_prompt_chars=12000`, re-capture the assembled prompts for:

- `amberwick-lane-western-run-4213-4213-4213`
- `saltward-street-and-amberwick-lane-4217-4217`
- `crossingV2_178_132`

Save as `exports/mt421_assembled_prompts.md`.

Confirm:

- each prompt is unique
- each contains the room name in plain text
- each contains the structure tag and atmosphere tags when present
- each has `Trimmed: False`

## Phase C: regenerate the 6-room sample

With the fixed configuration, regenerate the same 6-room slice from
MT-419:

- demo1: `CRO_500_100`, `CRO_500_150`
- crossingV2: `crossingV2_192_132`, `crossingV2_178_132`
- new_landing: `amberwick-lane-western-run-4213-4213-4213`, `saltward-street-and-amberwick-lane-4217-4217`

Save as `exports/sample_descriptions_mt421_qwen14b.txt`.

Apply the standard rubric. Compare against MT-419 results. Specifically
check whether the two `new_landing` rooms now produce urban descriptions
instead of generic stone chambers.

Save findings to `exports/mt421_findings.md`.

## Constraints

- Code changes are limited to the prompt budget, the safety check, and reordering the system prompt load
- Do not modify the system prompt template
- Do not modify the user-prompt assembly logic
- Do not change sampling parameters
- Do not change the model
- Stop after Phase C and report