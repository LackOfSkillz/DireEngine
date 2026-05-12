# MT-515 v1 validation

Status: SHIPPED (v1 - non-magic)

Ship timestamp: `2026-05-02T08:57:10.6266743-04:00`

## Phase A - Context Confirmed

- Re-read the audit and the shipped helper
- Re-confirmed the active empathy gate is the later `is_empath` definition at `typeclasses/characters.py:8627`
- Re-confirmed the earlier `is_empath` at `typeclasses/characters.py:5600` is shadowed dead code and left untouched

## Phase B - Helper Baseline

- `world/helpers/skill_attempts.py` remained unchanged in this followup
- `tests/test_skill_attempts.py` remained green
- Helper contract still: success awards full difficulty XP, `skill_too_low` awards fractional failure XP, unrelated failures award none

## Phase C - Four Non-Magic Skills Migrated

`scholarship`

- `Character.recall_knowledge(...)` now routes incomplete recall branches through the helper
- `Character.study_item(...)` now routes below-difficulty study failures through the helper

`first_aid`

- `Character.study_item(...)` now routes explicit `first_aid` study-item difficulty failures through the helper
- No new corpse or tending thresholds were invented; those flows remain success-only because the current character layer does not expose a clean local skill-threshold branch there

`tactics`

- `Character.assess_stance(...)` now routes low-rank imprecise reads through the helper
- High-rank message variants and prep-state behavior remain intact

`perception`

- `detect_traps_in_room(...)` now awards failure learning when active traps exist but detection fails
- `SearchAbility` and `ObserveAbility` now award one failure-learning event per action instead of unconditional success-style awards on low-rank outcomes
- `CmdMark` now routes its perception component through the helper while leaving appraisal training unchanged

## Phase D - Stealth Collapse

- `commands/cmd_hide.py` no longer awards immediate stealth XP
- `CmdHide` now records deferred stealth learning through `record_stealth_contest(...)`
- Live fixture verification confirmed:
  - immediate command feedback is still preserved
  - immediate XP delta is `0.0`
  - deferred finalization awards stealth XP on both success and failure

## Phase E - Empathy Gating

- Non-empaths now hard-fail `diagnose` with no empathy XP
- Empaths can still attempt diagnosis and anatomy study at rank `0`
- Low-rank empath outcomes now use helper-based failure learning instead of leaking success-style empathy training
- Empathy-only anatomy-study awards are now gated so non-empaths receive no empathy XP

## Phase F - Tests

Focused test files added:

- `tests/test_skill_attempts_lore.py`
- `tests/test_perception_failure_learning.py`
- `tests/test_hide_deferred_learning.py`
- `tests/test_empathy_gating.py`

Combined validation run:

```text
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m pytest \
  tests/test_skill_attempts.py \
  tests/test_skill_attempts_lore.py \
  tests/test_perception_failure_learning.py \
  tests/test_hide_deferred_learning.py \
  tests/test_empathy_gating.py -q

29 passed in 3.07s
```

## Phase G - Live Verification

Builder launcher health:

- Task `Start Builder Launcher`: already running at `http://127.0.0.1:7777`
- Task `Verify Builder Launcher Health`: `ok=True`, service=`builder_launcher`

Live fixture results were captured against temporary Evennia objects created through the DireTest harness.

`scholarship`

- Command: `study TEST_MT515_FOLIO`
- Messages:
  - `You begin studying TEST_MT515_FOLIO.`
  - `You struggle to make sense of the material.`
  - `You feel your scholarship settling into dabbling.`
- XP delta: `6.5625`

`first_aid`

- Command: `study TEST_MT515_BANDAGE_NOTES`
- Messages:
  - `You begin studying TEST_MT515_BANDAGE_NOTES.`
  - `You struggle to make sense of the material.`
  - `You feel your first_aid settling into dabbling.`
- XP delta: `6.5625`

`tactics`

- Command: `assessstance TEST_MT515_OPPONENT`
- Messages:
  - `You study TEST_MT515_OPPONENT's stance carefully.`
  - `You struggle to read their intentions.`
  - `You feel your tactics settling into dabbling.`
- XP delta: `6.5625`

`perception`

- Command: `mark TEST_MT515_MARK`
- Messages:
  - `You feel your appraisal settling into thoughtful.`
  - `You assess TEST_MT515_MARK. Difficulty: 33`
  - `They seem unsuspecting.`
  - `Attention: idle`
  - `Risk level: 1`
- XP delta: `2.4578`

`empathy` non-empath

- Command: `diagnose TEST_MT515_PATIENT`
- Messages:
  - `You do not know how to diagnose injuries that way.`
- XP delta: `0.0`

`empathy` empath at rank `0`

- Command: `diagnose TEST_MT515_PATIENT`
- Messages:
  - `Vitality: None`
  - `Bleeding: None`
  - `Poison: None`
  - `Disease: None`
  - `You feel your empathy settling into dabbling.`
- XP delta: `6.5625`

`stealth` success via `CmdHide`

- Command: `hide`
- Messages:
  - `You blend into the surroundings.`
- Immediate XP delta: `0.0`
- Deferred XP delta after `finalize_stealth_learning(nonce)`: `2.3152`

`stealth` failure via `CmdHide`

- Command: `hide`
- Messages:
  - `You fail to find a place to conceal yourself.`
- Immediate XP delta: `0.0`
- Deferred XP delta after `finalize_stealth_learning(nonce)`: `0.5788`

## Phase H - Documentation

- Added `docs/architecture/skill_attempts.md`
- Included the non-magic migration roster, helper usage rules, perception hot-path note, first-aid scope note, empathy gating note, and explicit deferral of magic-family skills to `MT-515-magic`

## Final State

MT-515 v1 shipped. The helper remains stable, the four non-magic migration slices are in place, `CmdHide` now uses deferred stealth learning, empathy routes are guild-gated, and the non-magic attempt/failure pattern is documented. Magic-family skills remain deferred to `MT-515-magic` with the unresolved threshold-design questions called out explicitly.

## Followup Queue

- `MT-515-magic`: define low-rank thresholds for `arcana`, `attunement`, and related casting flows
- duplicate `is_empath` cleanup in `typeclasses/characters.py`
- `MT-515b`: combat weapon failure XP
- `MT-515c`: armor passive training
- `MT-515d`: remaining general skill migrations