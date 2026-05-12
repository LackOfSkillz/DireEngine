# MT-515-impl-followup — Re-scoped non-magic migrations

## Background

MT-515 stopped at the blocker condition explicitly named in the
dispatch: arcana and attunement do not expose clean
skill-threshold failure boundaries at the character layer.
Inventing those boundaries would be a design change to the
spell/mana system, not a bounded migration. The agent correctly
stopped and reported.

Phase B shipped: shared helper at
`world/helpers/skill_attempts.py` with 6 passing tests.

This dispatch completes MT-515 v1 with the non-magic roster:
- first_aid, perception, tactics, scholarship migrations
- Stealth dual-path collapse
- Empathy guild gating

Magic skills (arcana, attunement) deferred to MT-515-magic, a
separate dispatch that will lock specific skill-threshold design
decisions for charge magnitude and prep level before any
migration. That's a gameplay design question, not a coding
question, and is not part of this dispatch.

## Architectural guardrails (READ FIRST)

This dispatch is the resumption of MT-515 with magic deferred.
The helper exists; tests pass. The work is the four non-magic
migrations plus stealth collapse and empathy gating.

The biggest risk is scope drift back into magic. The agent
correctly stopped before. Don't reverse that decision in this
dispatch.

The second-biggest risk is fixing the duplicate `is_empath`
during the empathy migration. Resist. Surface it; don't fix it.

**Frozen scope:**

1. Phase A: Re-confirm context. Read the audit on the four
   target skills, stealth, empathy. Read the shipped helper.
   Do not modify the helper unless a migration surfaces a
   genuine bug in it.
2. Phase B: Already shipped. Helper exists at
   `world/helpers/skill_attempts.py` with passing tests.
3. Phase C: Migrate four skills using the helper:
   - `first_aid`
   - `perception`
   - `tactics`
   - `scholarship`
4. Phase D: Collapse stealth dual-path. Route `CmdHide`
   through the same deferred `record_stealth_contest` /
   `finalize_stealth_learning` path the abilities use. Remove
   legacy immediate-XP code from `CmdHide`.
5. Phase E: Add empathy guild gating. Non-empaths hard-fail
   with no XP. Empaths attempt at any rank with failure XP
   via the helper. The audit flagged that `characters.py`
   contains duplicate `is_empath` definitions; identify which
   is active (the later one shadows the earlier per Python
   resolution) and add the gate to the active definition.
   Surface the duplicate as a separate followup bug; do NOT
   fix it in this dispatch.
6. Phase F: Tests for each migration plus stealth and empathy.
7. Phase G: Live verification with fixtures.
8. Phase H: Documentation at
   `docs/architecture/skill_attempts.md` with explicit note
   that magic skills are deferred to MT-515-magic.
9. Phase I: Validation artifact at
   `exports/mt515_validation.md`.

**Frozen what-not-to-do list:**

- DO NOT migrate arcana, attunement, or any magic skill. They
  are deferred to MT-515-magic.
- DO NOT design new skill-threshold gates anywhere in the
  spell or mana systems.
- DO NOT migrate registry-only skills (backstab, instinct,
  thanatology, etc.).
- DO NOT touch combat weapon training (queued as MT-515b).
- DO NOT touch armor training (queued as MT-515c).
- DO NOT consolidate the parallel training paths.
- DO NOT modify the storage layer (`db.skills` vs
  `exp_skill_state`).
- DO NOT modify the foraging system. Forage is the reference
  implementation; cleanup migration to consume the helper is
  v2 work.
- DO NOT fix the duplicate `is_empath` definitions. Surface
  as a followup bug; do NOT remove the duplicate in this
  dispatch.
- DO NOT modify the helper at `world/helpers/skill_attempts.py`
  unless a migration genuinely requires it. The helper passed
  Phase B tests; treat it as stable.
- DO NOT extend the migration roster beyond the four non-magic
  skills + stealth collapse + empathy gating.
- DO NOT modify weather, calendar, terrain, invasion,
  state-aware descriptions, object presentation, or any
  non-skill system.
- DO NOT modify the ability framework's wrong-guild hard-fail
  logic. It's already correct per the audit.
- DO NOT report SHIPPED until live verification confirms each
  migrated skill works at low rank.

**Stop-and-report conditions:**

- If first_aid, perception, tactics, or scholarship migration
  reveals an unexpected gating dependency that wasn't in the
  audit, stop and report.
- If stealth collapse breaks tests in ways not attributable
  to the deferred-path consolidation, stop and report.
- If empathy gating affects spell visibility, ability
  visibility, or other downstream consumers in unexpected
  ways, stop and report.
- If the duplicate `is_empath` definitions can't be cleanly
  identified as active vs shadowed via static read, stop and
  report — don't guess which to gate.
- If perception migration reveals high-frequency call sites
  where helper invocation creates measurable performance
  concerns, stop and report.
- If live verification surfaces additional broken behaviors
  beyond the four migrations + stealth + empathy, list them
  but do NOT fix them in this dispatch. Surface as separate
  dispatches.
- If the bounded-time test (helper invocations should stay
  under 1ms) is violated on hot paths, stop and report.

## Phase A — Confirm context

The agent reads:
- `docs/audits/skill_system_state.md` (sections on first_aid,
  perception, tactics, scholarship, stealth, empathy)
- `world/helpers/skill_attempts.py` (the shipped helper)
- `tests/test_skill_attempts.py` (the passing helper tests)

Confirms the helper API is right for the four non-magic
migrations. If the helper API needs adjustment to handle a
migration cleanly, document why before modifying.

## Phase C — Migrate four non-magic skills

For each skill, the agent identifies the existing failure
branches in the owning code, then routes the skill_too_low
branch through the helper.

### C.1 First Aid

Per audit: tend / stabilize corpse / study anatomy paths.
Wound/corpse/state checks in owning methods. Currently
success-only XP.

Migration:
- Identify each attempt entry point in `typeclasses/characters.py`
  for first-aid (`process_first_aid_tend_training` or
  equivalent, `stabilize_corpse`, anatomy study handlers)
- Plus the command-level handlers in `commands/cmd_diagnose.py`
  and `commands/cmd_study_anatomy.py`
- For paths where the wound/state check fails because the
  character's first_aid skill is too low, fire the helper with
  `skill_too_low` and the appropriate failure multiplier
- Preserve all existing success-path behavior unchanged
- Skill-too-low failure should produce a clear player message
  (agent picks message text)

### C.2 Perception

Per audit: search/observe abilities, trap detection, mark,
stealth observer detection. Mixed direct `award_xp` and
`use_skill` paths currently.

Migration:
- `SearchAbility` and `ObserveAbility` execute methods in
  `typeclasses/abilities_perception.py`
- `CmdMark` in `commands/cmd_mark.py`
- `detect_traps_in_room` in `typeclasses/characters.py`
- For attempts that fail because perception rank is too low,
  fire the helper with `skill_too_low`
- Perception is high-frequency. If the agent identifies hot
  paths where firing the helper on every check would generate
  excessive XP awards or performance concerns, document the
  approach taken (rate-limiting, cooldown, conditional firing)
  rather than firing unconditionally
- Preserve existing success-path behavior

### C.3 Tactics

Per audit: `assess_stance` is the primary attempt path.
Currently uses `use_skill("tactics")` → `award_practice` with
no failure handling.

Migration:
- `Character.assess_stance` in `typeclasses/characters.py`
- Plus `commands/cmd_assessstance.py` if relevant
- For assess_stance attempts where the result is imprecise
  due to low tactics rank, fire the helper with `skill_too_low`
- Preserve high-rank vs low-rank message variations

### C.4 Scholarship

Per audit: recall_knowledge, study_item, study_anatomy. Study
item below-skill failure currently returns a message with no
XP.

Migration:
- `Character.study_item` and `Character.recall_knowledge` in
  `typeclasses/characters.py`
- Plus `commands/cmd_recall.py` if relevant
- For study attempts where the item exceeds the character's
  scholarship rank, fire the helper with `skill_too_low`
- For recall attempts where knowledge is incomplete due to
  low scholarship, fire the helper with `skill_too_low`
- Preserve partial-knowledge / full-knowledge / no-knowledge
  message variations

## Phase D — Stealth dual-path collapse

Per audit:
- Ability path: `HideAbility`, `SneakAbility`, `StalkAbility`,
  `AmbushAbility` defer XP via `record_stealth_contest` and
  `finalize_stealth_learning` with margin-based partial/failure
  modifiers
- Legacy `CmdHide`: awards XP immediately on success only, no
  failure handling

Collapse:
- `CmdHide.func()` in `commands/cmd_hide.py` should route
  through `record_stealth_contest` to match the ability path
- The actual XP award becomes deferred and margin-based,
  matching the ability path
- Remove the legacy immediate-XP path from `CmdHide`
- Preserve the immediate-feedback player message (so UX
  doesn't degrade — the player still sees their attempt
  acknowledged, but the XP is deferred behind the scenes)

The helper is not directly involved here. This is path
consolidation, not helper migration.

If `CmdHide` legacy behavior turns out to be load-bearing for
something not surfaced in the audit (a script, a hidden test,
an external consumer), stop and report.

## Phase E — Empathy guild gating

Per locked decision: empathy is guild-locked for non-empaths.

**Critical: characters.py has duplicate `is_empath` definitions
per audit findings.** Per Python resolution, the later
definition shadows the earlier. The active definition is the
later one. The earlier one is dead code.

Steps:
1. Identify both `is_empath` definitions in
   `typeclasses/characters.py`
2. Confirm which one is the later/active one via static read
3. If the duplication is unclear or the active definition
   can't be confidently identified, stop and report
4. Add the empathy guild gate at the active definition OR at
   the calling sites where empathy XP is awarded — agent picks
   based on what's cleaner; documents the choice
5. Wrong-guild (non-empath) attempts hard-fail with no XP and
   a clear message ("You lack the empathic training to do this."
   or similar)
6. Empath attempts at any rank work, with failure-XP via the
   helper for skill_too_low cases
7. Surface the duplicate `is_empath` as a separate followup
   bug. Document in the followup queue. Do NOT remove the
   duplicate definition in this dispatch.

If updating the empathy guild gate breaks empath spell access
tests (because spell access also checks profession), stop and
report. Empathy gating may interact with spell layer
visibility in ways the audit didn't fully map.

## Phase F — Tests

For each migrated skill, focused unit tests at
`tests/test_skill_attempts_<skill>.py` or extending existing
test files (agent picks structure).

Per skill:
- `test_<skill>_success_awards_full_xp`
- `test_<skill>_skill_too_low_failure_awards_quarter_xp`
- `test_<skill>_other_failure_awards_no_xp`
- `test_<skill>_at_zero_rank_can_attempt`
- Skill-specific edge cases the migration surfaces

For empathy:
- `test_empathy_non_empath_hard_fails_no_xp`
- `test_empathy_empath_low_rank_awards_failure_xp`

For stealth collapse:
- `test_cmdhide_uses_deferred_learning`
- `test_cmdhide_no_immediate_xp_award`

All existing tests must continue to pass.

## Phase G — Live verification

Same fixture pattern proven in MT-516 and MT-516-mixed-fix1.
Temporary character with controlled skill ranks; observe
attempt outcomes; capture verbatim.

### G.1 Per-skill verification

For each migrated skill, create a fixture character at rank 0
in an appropriate room. Attempt the skill. Capture:
- The exact command typed
- The exact player message returned
- The XP gained (before/after pool comparison)
- Confirmation that XP > 0 for skill_too_low (failure-learning
  fired) or == 0 for other failure types

### G.2 Empathy verification

Two fixture characters: empath and non-empath. Both attempt
an empathy-using action.
- Empath at rank 0: attempt allowed; failure XP awarded if
  the action requires more skill than they have
- Non-empath: hard-fail with clear message; no XP

Capture verbatim outputs for both.

### G.3 Stealth verification

Fixture character types `hide` via `CmdHide`. Verify:
- The player message acknowledges the attempt (immediate
  feedback preserved)
- The XP award is deferred (not immediate)
- Both success and failure outcomes train via the deferred
  path

Capture verbatim outputs.

### G.4 Bounded-time

Helper invocations should be fast (under 1ms for typical
calls). Perception especially fires often. Document timings.

## Phase H — Documentation

`docs/architecture/skill_attempts.md`:

```markdown
# Skill Attempts and Failure Learning

## Overview
[Pattern: any character can attempt any general skill they
could theoretically learn. Failed attempts at low rank award
25% of successful XP for skill_too_low only. Guild-gated
abilities hard-fail with no XP for wrong-guild characters.]

## Helper API
[Signature, parameters, return value, examples from the
shipped helper at world/helpers/skill_attempts.py]

## When to use the helper
[Adding new general skills. Migrating existing general skills
that have a clean skill_too_low failure boundary at the
attempt layer.]

## When NOT to use the helper
[Guild-gated abilities (use existing ability framework
hard-fail). Combat weapon training (TBD MT-515b). Armor
passive training (TBD MT-515c). Magic skills like arcana
and attunement (TBD MT-515-magic — see deferral note below).]

## Failure reason taxonomy
- skill_too_low: awards failure XP at default 25% multiplier
- weather_blocked, generic, no_resource, etc.: no XP awarded
- Custom reasons can be added; default is no XP unless
  explicitly skill_too_low

## Migration roster (v1 — this dispatch)
- first_aid (tend, stabilize, anatomy study)
- perception (search, observe, mark, trap detection)
- tactics (assess_stance)
- scholarship (recall, study)
- stealth (dual-path collapse, deferred learning canonical)
- empathy (guild-gated for non-empaths)

## Deferred to MT-515-magic
arcana and attunement currently lack clean skill_too_low
failure boundaries at the character layer. Spell prep and
luminar charge fail on resource, access, room, circle,
known-spell, and destabilization conditions, but not on a
local skill threshold. MT-515-magic will lock specific design
decisions for what "skill too low" means for:
- charge_luminar (charge magnitude vs arcana rank)
- prepare_spell (prep mana level vs attunement rank)
- center_empath_self (centering depth vs attunement rank)
- Non-targeted spell casts (cast difficulty vs category rank)

These are gameplay design decisions. They affect how casting
feels at low rank and need playtesting input before
implementation.

## Future migration candidates
[Per audit's gap analysis: ~20 additional general skills with
attempt paths not covered by v1. Triaged into MT-515b
(combat weapons), MT-515c (armor passive), MT-515d (remaining
general), and MT-515-magic (magic family).]
```

## Phase I — Validation artifact

`exports/mt515_validation.md`:

```markdown
# MT-515 v1 validation

Status: SHIPPED (v1 — non-magic)

## Phase A — Context confirmed
[Notes on what was extracted from audit and helper]

## Phase B — Helper (already shipped pre-followup)
- world/helpers/skill_attempts.py
- tests/test_skill_attempts.py — 6 passing tests
- Status: stable, not modified in followup

## Phase C — Four non-magic skills migrated
[Per-skill migration notes: which entry points changed,
which failure branches were routed through the helper]

## Phase D — Stealth collapse
[How CmdHide now routes; legacy immediate-XP path removed]

## Phase E — Empathy gating
[Active is_empath identified at line N, gate added there;
duplicate definition at line M flagged for followup]

## Phase F — Tests
[Test file count, all-passing confirmation, including
existing tests still passing]

## Phase G — Live verification
[Per-skill verbatim outputs from fixture verification]

## Phase H — Documentation
[Doc location, magic deferral note included]

## Final state
"MT-515 v1 shipped. Helper formalized. Four non-magic skills
migrated. Stealth dual-path collapsed. Empathy guild-gated.
Pattern documented. Magic skills (arcana, attunement)
deferred to MT-515-magic with design questions named. Ready
for player verification."
```

## Verification checklist

1. Phase A context confirmed; helper API validated as stable
2. Four non-magic skills migrated using the helper
3. Stealth dual-path collapsed; CmdHide routes through
   deferred recorder
4. Empathy guild-gated at active is_empath; duplicate
   surfaced for followup
5. All test files pass; existing tests still pass
6. Live verification per migrated skill captures verbatim
   output
7. Documentation in place with magic deferral note
8. Validation artifact in place
9. No code outside in-scope list modified
10. Foraging unchanged
11. Helper unchanged unless migration surfaced a real bug
12. Magic skills untouched
13. Duplicate is_empath not removed (only flagged)

## Stop conditions

- Edit only:
  - `typeclasses/characters.py` (per-skill migrations,
    empathy gate at active is_empath)
  - `typeclasses/abilities_perception.py` (perception)
  - `commands/cmd_hide.py` (stealth collapse)
  - `commands/cmd_diagnose.py`,
    `commands/cmd_study_anatomy.py`,
    `commands/cmd_mark.py`, `commands/cmd_recall.py`,
    `commands/cmd_assessstance.py` (per migration owners)
  - Test files for migrations + stealth + empathy
  - `docs/architecture/skill_attempts.md` (new)
  - `exports/mt515_validation.md` (new)
- Do NOT touch the helper unless a migration surfaces a
  real bug
- Do NOT migrate magic skills
- Do NOT fix the duplicate is_empath
- Stop and report on unexpected gating dependencies, test
  breakage, or spell visibility regressions
- Do NOT extend the migration roster
- Do NOT declare SHIPPED until live verification confirms

## Required artifacts

1. Updated character methods for four migrations
2. Updated `commands/cmd_hide.py` (stealth collapse)
3. Updated other command files per migration roster
4. Empathy guild gate at active is_empath
5. New test files for migrations + stealth + empathy
6. New `docs/architecture/skill_attempts.md`
7. New `exports/mt515_validation.md`

## Followup queue

- **MT-515-magic — Magic skill migrations:** arcana,
  attunement, and the magic skill family. Requires locked
  design decisions about what "skill too low" means for:
  - charge_luminar (charge magnitude vs arcana rank)
  - prepare_spell (prep mana level vs attunement rank)
  - center_empath_self (centering depth vs attunement rank)
  - Non-targeted spell casts (cast difficulty vs category
    rank)
  These are gameplay design decisions, not code migrations.
  Needs Gary's input on how low-rank casting should feel
  before drafting.

- **Duplicate `is_empath` cleanup:** characters.py contains
  two definitions; the later shadows the earlier. Small
  followup to remove the dead one. Surfaced by MT-515 audit;
  flagged again by this dispatch.

- **MT-515b — Combat weapon failure XP:** Migrate weapon
  skills to use the helper at 10% multiplier (lower than
  non-combat 25%). Combat is high-frequency; multiplier
  compounds. Includes weapon misses awarding small XP,
  defender evasion training on defended attempts.

- **MT-515c — Armor passive training:** Add training hooks
  where wearing armor under combat trains armor skills at
  appropriate multipliers.

- **MT-515d — Remaining general skill migrations:** The ~20
  skills with attempt paths not covered by v1.

- **MT-515e — Storage layer consolidation:** Resolve
  `db.skills` legacy + `exp_skill_state` newer dual
  representation.

- **MT-515f — Training path consolidation:** Resolve the
  three parallel training paths.

- **MT-515g — `primary_magic` resolution:** Add to registry
  as synthesized derived value, OR refactor spell metadata
  to use category skills.

- **Forage migration to helper** (cleanup): Migrate forage
  to consume the v1 helper, eliminating duplication.

- **Manual trial zone build:** Becomes feasible after MT-515
  v1 ships and the trial zone author has confidence in skill
  attempt + failure learning UX.
```