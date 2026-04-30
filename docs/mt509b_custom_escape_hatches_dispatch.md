# MT-509b — Custom escape hatches on atmosphere axes

## Background

DireBuilder's vocab-backed pill pickers (MT-507z + MT-508) give
builders schema-correct tag selection but no way to express concepts
the canonical vocabulary doesn't yet cover. Room-level `tags.custom`
serves as a universal escape hatch, but atmospheric concepts often
belong on a specific axis (a one-off material on `atmosphere.materials`,
a one-off sensory cue on `atmosphere.sensory`) where they would
contribute correctly to AI-generated descriptions.

This dispatch adds a "+ Add custom" affordance to the five atmosphere
axis pickers. Zone-level fields (setting_type, era_feel, climate,
cultural_palette, mood) stay strict, since those drive AI broad-framing
and freeform values would compromise prompt assembly quality.

The Pass 2 prompt and Sonnet 4.5 already handle non-vocab values
gracefully — the AI treats them as descriptive hints without confusion.
The backend save normalizer needs to be checked: it must accept custom
values on atmosphere axes the same way it accepts custom values in
`tags.custom`.

## In scope

- "+ Add custom" affordance on the five atmosphere axis pickers:
  - tags.atmosphere.materials
  - tags.atmosphere.social_character
  - tags.atmosphere.surroundings
  - tags.atmosphere.sensory
  - tags.atmosphere.upkeep
- Custom values persist in workingZone alongside canonical pills
- Custom values render as pills with a visual marker (small dot, tilde
  prefix, or different border) so builders can distinguish "added by me"
  from "in canonical vocab"
- Custom values save round-trip through to YAML and reload correctly
- Backend normalizer validates atmosphere axis values against vocab OR
  accepts custom values per the same rules as tags.custom

## Out of scope

- Custom escape hatches on zone-level fields (setting_type, era_feel,
  climate, cultural_palette, mood) — these stay strict
- Custom escape hatches on room-level non-atmosphere tags (structure,
  specific_function, named_feature, condition) — these stay strict;
  tags.custom remains the catch-all
- Promotion mechanism (turning a frequently-used custom value into
  canonical vocab) — that's a curation question, not a UI question
- Conflict detection on custom values
- Tooltip changes (the existing field-level tooltips remain accurate;
  if a tooltip explicitly says "vocab-only," it gets a small update)

## Phase A — Backend acceptance check

Read web/views.py — specifically the room normalization path used by
the save endpoint. Find where atmosphere axis values are validated
against the atmosphere_vocab.yaml.

If the current normalizer rejects values not in the vocab for these
five axes, change it to accept them the same way `tags.custom` is
accepted. The schema for atmosphere axes already declares them as
arrays of strings; no schema change should be needed.

If the normalizer already accepts custom values silently (because the
freeform fallback wasn't tightened), that's an MT-507z/MT-508 oversight
that needs verification: write a small Python sanity check that posts
a custom value through the save normalizer and confirms it round-trips.

Either way, the backend behavior after this phase: vocab values pass
through unchanged, custom values pass through unchanged, malformed
input still gets rejected.

## Phase B — Picker UI: add the affordance

In direbuilder.js, find the atmosphere axis picker rendering. The
current pattern (from MT-508) renders a list of pills with click-to-
toggle on each canonical vocab term.

Add to each atmosphere axis picker:

1. A small text input + "+ Add" button below the pill list, styled
   subtly (smaller than the main pills, label like "Add custom...").
2. On Add button click or Enter key in input:
   - Trim the input value
   - If empty, do nothing
   - If the value matches a canonical vocab term (case-insensitive),
     toggle that pill on instead of adding a duplicate (graceful
     deduplication)
   - Otherwise, slug the value (kebab-case, lowercase) and add it to
     workingZone.rooms[i].tags.atmosphere.<axis> as a new array entry
3. Re-render the picker with the new custom value visible as a pill,
   alongside the canonical pills, but visually marked.

The custom-value pill should be:
- Toggleable like any other pill (click to remove)
- Visually distinct: a small leading marker (a tilde "~", a small dot
  "•", or a different border color — use whatever fits the existing
  parchment theme without adding visual noise)
- Tooltipped with "Custom — added in this zone" or similar so builders
  understand at a glance

Custom values render in the picker even if the YAML round-trip preserved
them as plain strings — the renderer derives "is custom" by checking
membership in the canonical vocab list at render time. Don't store a
separate "is custom" flag in YAML; the data shape stays a flat string
array.

## Phase C — Persistence and reload

Verify (in browser) that adding a custom value:

1. Marks the zone dirty (Save Zone shows asterisk)
2. On Save Zone, custom value persists to YAML
3. On page refresh, custom value reloads as a pill in the picker,
   visually marked as custom
4. Custom value can be removed by clicking its pill, same UX as
   canonical pills

Verify that the AI generation path (MT-509) correctly receives custom
values. The Pass 1 user message already includes atmosphere axis values
verbatim from the room dict — no prompt assembly change needed unless
the renderer is filtering by vocab somewhere.

If the prompt assembly was filtering against vocab anywhere (it
shouldn't be — the prompt works at the natural-language level), remove
that filter. Custom values are already valid prompt input.

## Phase D — Cache-bust and verify

Bump direbuilder.js and direbuilder.css versions in direbuilder.html.
Restart server via .\startWeb.bat.

Verification checklist:

1. Page loads, no console errors.
2. Open Tags tab on any room. Click open atmosphere.materials accordion.
3. "+ Add custom" affordance is visible below the canonical pills.
4. Enter a custom value (e.g., "weathered-brickwork") and click Add.
5. New pill appears, visually marked as custom.
6. Save Zone. Asterisk clears. Refresh page. Custom pill reloads.
7. Generate Description. Verify the custom value can appear in the
   generated prose (not guaranteed every generation, but the AI should
   receive it in the prompt — confirm by checking the prompt log if
   you have one, or by running 2-3 generations and observing whether
   the custom term influences output).
8. Click custom pill to remove. Save Zone. Refresh. Custom pill is
   gone from YAML.
9. Repeat for all five atmosphere axes — each should support custom
   values independently.
10. Verify zone-level pickers (setting_type, era_feel, climate,
    cultural_palette, mood) do NOT have the affordance. They stay
    strict.
11. Verify room-level non-atmosphere pickers (structure,
    specific_function, named_feature, condition) do NOT have the
    affordance. They stay strict — tags.custom remains the catch-all.
12. /builder/ legacy route is untouched.

## Stop conditions

- Edit only: web/views.py (if backend normalizer change needed),
  web/static/webclient/js/direbuilder.js, web/static/webclient/css/direbuilder.css,
  web/templates/webclient/direbuilder.html
- Do not modify schema YAML (vocab files stay as-is)
- Do not modify the Pass 1 / Pass 2 prompts
- Do not implement conflict detection
- Do not implement custom value promotion (custom-to-canonical) flow
- If the backend normalizer change touches more than 20 lines, stop
  and report the exact constraint before continuing

## Required artifacts

1. Updated direbuilder.js, direbuilder.css, direbuilder.html
2. Updated web/views.py if backend acceptance change was needed
3. exports/mt509b_custom_escape_hatches_validation.md — short note
   capturing:
   - One full add/save/reload cycle for a custom value
   - One generation that received a custom value in the prompt and the
     resulting Pass 2 output
   - Verification that strict fields (zone-level + non-atmosphere
     room-level) did not receive the affordance