# MT-510 (continued) — Apply accepted vocabulary additions

## Background

MT-510 Phase A surveyed the existing zones (only `new_landing` had
substantive prose; the other 14 zones are scaffolds, clones, or test
fixtures) and produced a list of single-zone candidate additions in
exports/mt510_zone_atmosphere_survey.md. The human reviewer has now
marked accept / reject / rename / defer decisions on each candidate.

This phase reads those decisions, applies the accepted additions to
the canonical vocabulary YAML files, and verifies AI generation still
works on a sample of rooms with the expanded vocabulary.

## Phase C — Read decisions and apply

1. Read exports/mt510_zone_atmosphere_survey.md.

2. For each candidate, identify the marked decision:
   - "[x] accept" — apply the term as proposed
   - "[x] rename: <new-slug>" — apply the term using the renamed slug
   - "[x] reject" or "[x] defer" — skip, do not apply
   - No mark or unclear mark — STOP and report; do not guess

3. For each accepted/renamed candidate, add the term to the appropriate
   YAML file in world/builder/vocab/:
   - Atmosphere terms go in atmosphere_vocab.yaml under the correct axis
   - Structure / specific_function / named_feature / condition terms go
     in room_vocab.yaml under the correct field
   - Maintain alphabetical order within each list to keep diffs clean

4. The schema reads vocab YAML at import time (per
   generation_context_schema.py and room_tag_schema.py patterns). No
   schema code changes should be needed. If a code change IS needed,
   stop and report — that's outside scope for this phase.

## Phase D — UI verification (no code change expected)

The pill pickers read the same YAML the schema reads via the
template-context injection pattern from MT-507z and MT-508. After the
YAML edits and a server restart, new pills should appear automatically
in the relevant pickers.

Verify by loading /direbuilder/?zone=builder2 in browser:

1. Restart server via .\startWeb.bat (necessary because vocab YAML is
   read on import, not per-request).
2. Load the page. Open the Tags tab on any room.
3. For each new term, find its picker (the correct atmosphere axis or
   room tag field) and verify the pill is present with the expected
   label.
4. Click each new pill to verify it toggles cleanly (selected state
   activates, click again deselects).
5. Save Zone with one new term selected. Refresh. Verify the term
   round-trips through to YAML and reloads correctly.

If new pills do NOT appear after restart, debug the YAML-to-template-
context path:
- Check the relevant view function in web/views.py for vocab loading
- Check the template script tag for the JSON payload
- Check the JS picker render function for filtering logic

Do not invent a new mechanism.

## Phase E — AI generation regression check

The expanded vocabulary should not degrade AI output quality. Run a
small regression test:

1. Pick 3 rooms across diverse environment types from any zone (e.g.,
   one urban, one interior, one wilderness).

2. For each room, tag it with at least one new vocabulary term where
   it fits. If a new term doesn't fit any of the test rooms, skip
   that term for this regression check (the test set isn't covering
   it; that's fine).

3. Run Generate Description on each tagged room (the production
   Sonnet 4.5 path from MT-509).

4. Save outputs to exports/mt510_ai_regression_check.txt with this
   format per room:

   ## <room_id>

   Tags applied (new terms in **bold**): <list>

   ### Pass 2 output:
   <pass_2_output>

   ### Telemetry:
   - input_tokens: ...
   - output_tokens: ...
   - elapsed_ms: ...

5. In the findings note (Phase E artifact below), evaluate:
   - Did the new terms surface in or influence the generated prose?
     (Not every term will appear verbatim — the AI uses tags as
     atmospheric hints. The test is whether the prose feels consistent
     with the term, not whether the term is quoted.)
   - Did any room degrade in quality compared to its earlier
     generation (if it had one)? Flag specific issues.
   - Any malformed $state markup, grounding violations, or time
     coherence issues?

6. After the regression check, restore the test rooms' tag state to
   what it was before this phase. Use the disk-backup-and-restore
   pattern from MT-507z if you need to.

## Stop conditions

- Edit only: world/builder/vocab/atmosphere_vocab.yaml,
  world/builder/vocab/room_vocab.yaml
- Do not edit schemas, prompt templates, generation pipeline, or
  DireBuilder UI code
- Do not propose new terms during this phase — only apply what the
  reviewer marked
- If a survey decision is ambiguous, stop and ask
- If a new term collides with an existing vocab entry (different
  spelling, same concept), stop and ask before adding

## Required artifacts

1. Updated atmosphere_vocab.yaml and/or room_vocab.yaml with accepted
   additions in alphabetical order
2. exports/mt510_ai_regression_check.txt — regression test outputs
3. exports/mt510_findings.md — short note capturing:
   - List of accepted additions actually applied
   - List of rejected/deferred candidates
   - Phase D UI verification results
   - Phase E regression assessment