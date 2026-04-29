# MT-417: Verify And Evaluate LM Studio System Prompt Override

## Ready-To-Send Dispatch

```text
Proceed with MT-417 only.

Acceptance source:
docs/builder/phase4_mt417_lmstudio_override_verification.md

This is a verification + small-batch test, not a full 4-pass evaluation.
Do not patch code.
Do not modify the codebase prompt.
Do not modify the LM Studio UI prompt.
Do not change sampling parameters in the codebase.
Run Phase A first. If the override is not taking effect, stop and report.
Only run Phase B if Phase A confirms the LM Studio UI prompt is taking effect.
Stop after reporting.
```

## Background

A new system prompt was added to LM Studio's UI configuration with the intent of layering rules on top of the codebase prompt. Sampling parameters were also changed:

- temperature 0.35
- repeat penalty 1.1
- Top K 40
- Top P 0.95
- Min P 0.05

Before running any evaluation, this task verifies whether the LM Studio UI system prompt is actually taking effect when the codebase client makes generation calls. If the UI prompt is being overridden by the client's own system prompt, the rest of the evaluation is meaningless.

This task answers two questions cheaply:

1. Is the LM Studio UI system prompt taking effect?
2. If yes, does it materially change output behavior compared to MT-415?

## Phase A: Verify the prompt layering

### Step A1: Read the LM Studio configuration

LM Studio's UI was configured with a system prompt that begins with:

```text
You are the DireMud Room Description Generator.
```

That prompt includes explicit anti-wrapper rules with first-character validation and bad/good example contrasts.

The codebase prompt at `world/builder/templates/room_description_system_prompt.txt` is a different prompt that the codebase client sends via the API.

### Step A2: Make a single test call with diagnostic logging

Without modifying any production code, run a one-off Python snippet that:

1. Constructs a generation request as the codebase normally would, using `tools.generate_sample_descriptions.generate_room_description` or equivalent.
2. Logs the raw request payload that gets sent to the LM Studio endpoint.
3. Specifically logs the full `messages` array including any system message.
4. Sends the request and logs the response.
5. Reports both the sent payload and the response.

Use the same room as a representative test case:

```text
crossingV2_192_132
```

Use the same env overrides as previous live runs:

```text
LLM_ENABLED=true
LLM_BASE_URL=http://127.0.0.1:1234
```

Save the diagnostic output to:

```text
tmp/mt417_prompt_layering_test.txt
```

### Step A3: Determine layering behavior

Read the diagnostic output. Three possible findings:

**Finding 1: The codebase prompt is being sent in the API messages.**
This is the expected case given how `LocalLLMClient` works. Then the question is whether LM Studio's UI prompt was applied in addition to or in place of the codebase prompt.

**Finding 2: No system message in the API payload.**
Then LM Studio's UI prompt is the only system prompt the model sees.

**Finding 3: Both system prompts visible somehow.**
Concatenation behavior, which would be unusual.

### Step A4: Confirm which prompt is taking effect

Compare the response from Step A2 against the patterns characteristic of each prompt.

**Codebase prompt taking effect**:
- May contain `**Room Description:**` or `**Room Data:**` headers
- May contain bullet lists of room data
- Body matches the style of bodies seen in `exports/sample_descriptions_mt415.txt`

**LM Studio UI prompt taking effect**:
- First character is a normal sentence character, not `*`, `#`, `-`, `[`, `{`, or `` ` ``
- No markdown headings or labels anywhere
- Output is one plain paragraph starting immediately with prose
- Body avoids the explicit invented-prop list such as torches, lanterns, smells, drips, slopes unless room data provided them

**Both taking effect**:
- Output may show conflicting behavior, sometimes following one, sometimes the other

Report which finding applies.

If Finding 1 applies with the codebase prompt winning, stop here and report. The override is not taking effect and the test cannot proceed meaningfully.

## Phase B: Small-batch comparison

Run Phase B only if Phase A confirms the LM Studio UI prompt is taking effect, either alone or in addition to the codebase prompt.

### Step B1: Generate 20 rooms

Use the same 20-room slice from MT-415 for direct comparison. The room ids are:

```text
crossingV2 zone:
  crossingV2_178_132
  crossingV2_192_132
  crossingV2_200_132
  crossingV2_214_132
  crossingV2_222_132
  crossingV2_236_132

demo1 zone:
  CRO_450_100
  CRO_500_100
  CRO_400_150
  CRO_450_150
  CRO_500_150

new_landing zone:
  amberwick-lane-western-run-4213-4213-4213
  amberwick-lane-midway-4214-4214
  amberwick-lane-eastern-run-4215-4215
  amberwick-lane-east-reach-4216-4216-4216
  saltward-street-and-amberwick-lane-4217-4217
  kingshade-street-and-amberwick-lane-4212-4212
```

Generate one description per room. Single pass only. Do not run a 4-pass evaluation in MT-417.

Save outputs as:

```text
exports/sample_descriptions_mt417_run1.txt
```

### Step B2: Run the safe/useful rubric

Apply the existing rubric from `tools/generate_sample_descriptions.py`.

Report:
- Generated samples count
- Safe samples count
- Useful samples count
- Useful acceptance rate
- Wrapper leakage total and wrapper-affected sample count
- Average word count
- Distribution of word counts: under 45, 45-90, over 90
- Distribution of sentence counts: under 3, 3-5, over 5
- Poetic filler total
- Fabrication watchlist total
- Stub phrase total
- Second-person violations
- Geometry violations
- Structural-fabrication flag count

### Step B3: Compare directly to MT-415 metrics

Produce a side-by-side comparison table:

```text
| Metric | MT-415 | MT-417 | Delta |
```

Include at least:
- Wrapper-affected samples, baseline 17/17
- Useful samples, baseline 0/17
- Safe samples, baseline 0/17
- Average words
- Length compliance in the 45-90 band
- Sentence count compliance in the 3-5 band
- Poetic filler total
- Geometry violations
- Second-person violations

### Step B4: Read 5 bodies and report verdict

Read these 5 specific samples in the new export:

- `CRO_500_100`
- `crossingV2_192_132`
- `saltward-street-and-amberwick-lane-4217-4217`
- `amberwick-lane-western-run-4213-4213-4213`
- `CRO_500_150`

For each, report:
- Did the wrapper disappear, persist, or partially disappear?
- Did the specific MT-415 failure recur?
  - lantern fabrication
  - slopes or curves geometry
  - second-person
- Is the body quality better, the same, or worse than MT-415?

Save the comparison and verdicts to:

```text
exports/mt417_comparison.md
```

## Stop and report

Do not iterate the prompt or sampling parameters based on these results.
Do not run a full 4-pass evaluation.
The decision about next steps belongs to the human reviewer.

The end state of this task is:

- `tmp/mt417_prompt_layering_test.txt`
- `exports/sample_descriptions_mt417_run1.txt` only if Phase B ran
- `exports/mt417_comparison.md` only if Phase B ran
- A clear statement of which Phase A finding applied
- The metric comparison and 5-room verdicts from Phase B if it ran

## Constraints

- No production code changes. Verification and evaluation only.
- No changes to the codebase prompt template.
- No changes to the LM Studio UI configuration.
- No changes to sampling parameters in the codebase.
- Phase A is mandatory. Do not skip to Phase B even if Phase B feels obvious.
