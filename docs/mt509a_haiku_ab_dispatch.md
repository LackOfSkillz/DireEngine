# MT-509a - Haiku 4.5 A/B test against MT-505 Sonnet baseline

## Background

MT-509 (Generate Description production wiring) is queued but blocked on a
model decision. MT-505 confirmed Sonnet 4.5 produces production-viable
stateful descriptions with 100% per-group coverage and 100% syntactic
validity across 20 diverse rooms. MT-504 ran Haiku 4.5 but only on 3 rooms
and with an earlier less-tightened Pass 2 prompt that Sonnet later showed
needed grounding and per-group constraints.

This task runs Haiku 4.5 against the same 20-room set used in MT-505 with
the same tightened prompts, so the production model decision is made on
clean A/B data. Haiku at about one-third Sonnet's per-call cost is meaningfully
cheaper at scale; the question is whether quality is close enough to justify
the savings.

Cost: about $0.12 (40 Haiku calls).
Time: about 5 minutes.
Risk: zero codebase impact, evaluation only.
ANTHROPIC_API_KEY must be visible in the agent shell.

## Phase A - Build the Haiku capability runner

Create `tmp/mt509a_haiku_capability_run.py` modeled exactly on
`tmp/mt505_claude_capability_run.py` with one model change:

    model = "claude-haiku-4-5"

Use the same `TEST_ROOMS` list from `tmp/mt505_test_rooms.py` by importing it
directly. Use the same Pass 1 system prompt at
`world/builder/templates/room_description_system_prompt.txt` and the same
Pass 2 prompt at `tmp/mt505_state_markup_prompt.txt`.

Save outputs to `exports/mt509a_haiku_capability.txt` with the same per-room
format MT-505 used:

    ## {room_id} - {name}

    Environment: {environment}
    Applicable groups: {groups}
    Applicable states: {states}

    ### Pass 1 (plain prose):
    {pass_1_output}

    ### Pass 2 (with markup):
    {pass_2_output}

    ------------------------------------------------------------

Append a Run Summary block with total calls, errors, and timing.

If any room errors, log and continue. Do not retry within the run.

## Phase B - Render state combinations

Create `tmp/mt509a_render_state_combinations.py` modeled exactly on
`tmp/mt505_render_state_combinations.py`, but reading from
`exports/mt509a_haiku_capability.txt` and writing to
`exports/mt509a_haiku_state_renders.md`.

Use the same render combinations: default, morning_clear, midday_clear,
evening_clear, night_clear, morning_rain (if weather applicable),
evening_snow (if weather applicable), night_invasion (if invasion
applicable), winter_morning, summer_midday.

Use the fragment regex that preserves leading whitespace inside fragments.

## Phase C - Build A/B findings report

Create `exports/mt509a_findings.md` as a direct comparison report against
MT-505's Sonnet output. Keep it tight.

For each of the 20 rooms, evaluate Haiku output on these axes and explicitly
compare to the same axes in the MT-505 Sonnet output:

1. Per-group coverage: Did Haiku produce at least one fragment per applicable
   state group?
2. Syntactic correctness: Any malformed fragments? Any escaped or broken
   `$state()` syntax?
3. Whitespace handling: Do default and active-state renders read cleanly
   without merged words or double spaces?
4. Environment grounding: List any fragments whose content does not fit the
   room's environment.
5. Time coherence: Walk morning, midday, evening, and night renders. Flag any
   time fragment that does not make sense for its slot.
6. Embellishment style: Compare to Sonnet's same-room output. Is Haiku adding
   more or fewer atmospheric details not directly licensed by the room data?

End with a verdict section answering these questions:

- Coverage parity: Haiku coverage rate vs Sonnet's 20/20.
- Syntactic parity: Haiku malformed fragment count vs Sonnet's 0.
- Grounding gap: How many rooms had grounding violations in Haiku output that
  did not appear in Sonnet's same-room output? List them.
- Time-coherence gap: Same question for time-coherence violations.
- Subjective shippability: For each of the 20 rooms, would Haiku's output be
  acceptable to a builder using the project's actual quality standard? Report
  Haiku shippability count out of 20 alongside Sonnet's.
- Bottom-line judgment: At about 33% of Sonnet's cost, is Haiku close enough
  to Sonnet on this task to recommend as the production model, or are the gaps
  significant enough that Sonnet's quality is worth the premium?

Do not recommend a path forward beyond that judgment line.

## Stop conditions

- Single run only, no prompt iteration during the run.
- Per-room failures logged, run continues.
- Complete through Phase C and report all output paths.
- Do not modify the Pass 1 or Pass 2 prompts.
- Do not modify the room test set.

## Required artifacts

1. `exports/mt509a_haiku_capability.txt` - raw two-pass run output
2. `exports/mt509a_haiku_state_renders.md` - multi-state rendered combinations
3. `exports/mt509a_findings.md` - A/B comparison report with verdict
4. `tmp/mt509a_haiku_capability_run.py`
5. `tmp/mt509a_render_state_combinations.py`