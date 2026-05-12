# Skill Attempts and Failure Learning

## Overview

General skills can be attempted at any rank when the owning action already exposes a local `skill_too_low` boundary. Successful attempts award full difficulty XP. Failed attempts award failure XP only when the failure reason is `skill_too_low`, using the shared helper and a default `0.25` multiplier.

Guild-gated empathy routes are a separate rule. Non-empaths hard-fail with no XP. Empaths can still attempt at rank `0`, and empathy-only training surfaces now route low-rank outcomes through the same failure-learning helper.

MT-515 v1 covers the non-magic migration roster only:

- `scholarship`: `study_item`, `recall_knowledge`
- `first_aid`: anatomy-study item paths that already expose a clean local difficulty check
- `tactics`: `assess_stance`
- `perception`: `detect_traps_in_room`, `SearchAbility`, `ObserveAbility`, `CmdMark`
- `stealth`: `CmdHide` now records deferred stealth learning instead of awarding immediate XP
- `empathy`: non-empath hard-fail and low-rank empath failure learning on diagnosis and anatomy study

## Helper API

Shared helper: `world/helpers/skill_attempts.py`

```python
attempt_with_failure_learning(
    character,
    skill_name,
    difficulty,
    *,
    success,
    failure_reason="skill_too_low",
    success_multiplier=1.0,
    failure_multiplier=0.25,
    event_key=None,
    source_mode="difficulty",
)
```

Behavior:

- Normalizes the skill name and verifies the skill exists in `SKILL_REGISTRY`
- Awards full difficulty XP on `success=True`
- Awards failure XP only when `success=False` and `failure_reason == "skill_too_low"`
- Returns metadata describing the attempted skill, difficulty, outcome, and awarded amount

Example:

```python
attempt_with_failure_learning(
    caller,
    "scholarship",
    15,
    success=False,
    failure_reason="skill_too_low",
    event_key="study",
)
```

## When To Use The Helper

Use the helper when all of the following are true:

- The skill is a general or empathy-only skill in the current roster
- The owning code already has a local `skill_too_low` branch or equivalent low-rank outcome
- The action should still count as an attempt even though it did not fully succeed
- The desired result is difficulty-mode XP with consistent success/failure metadata

Current examples:

- `Character.study_item(...)` when the study difficulty exceeds `scholarship` or `first_aid`
- `Character.recall_knowledge(...)` when scholarship only supports vague or empty recall
- `Character.assess_stance(...)` when tactics is too low for a reliable read
- `detect_traps_in_room(...)` when active traps are present but perception is insufficient
- `CmdMark`, `SearchAbility`, and `ObserveAbility` when the action completes but perception rank is still too low to count as a full success
- Empath-only diagnosis and anatomy-study routes when the caller is an empath but lacks the empathy rank to fully train on the action

## When Not To Use The Helper

Do not use the helper for:

- Wrong-guild hard-fail paths that should award no XP
- Combat weapon training, which remains queued for `MT-515b`
- Armor/passive training, which remains queued for `MT-515c`
- Magic-family skills that do not yet expose a clean local skill-threshold boundary
- Generic action failures such as missing items, missing resources, invalid state, or unrelated blockers

## Failure Reason Taxonomy

- `skill_too_low`: awards failure XP at the configured failure multiplier; default is `0.25`
- `generic`, `no_resource`, `weather_blocked`, and other non-threshold reasons: no XP by default
- `unknown_skill`: helper blocks and logs a warning instead of awarding

## Perception Hot-Path Note

Perception is high-frequency, so the migration avoids firing the helper on every raw check. The current rule is one helper call per actionable owner path:

- `detect_traps_in_room(...)` fires only when active traps exist and none were detected
- `SearchAbility` and `ObserveAbility` fire once per action after their room scan completes
- `CmdMark` fires once per completed mark attempt

That keeps the migration bounded and avoids turning each observer comparison into an unconditional XP event.

## First Aid Scope Note

The audit listed tend, corpse stabilization, and anatomy study under `first_aid`. In the current character layer, corpse and tend flows expose wound/state checks but not a clean local `first_aid < difficulty` threshold. MT-515 v1 therefore only migrates the anatomy-study surfaces that already carry an explicit study difficulty.

This was intentional. The followup did not invent new corpse or tending thresholds.

## Empathy Gating Note

`typeclasses/characters.py` still contains duplicate `is_empath` definitions. The later definition is the active one by Python resolution; the earlier definition is dead code. MT-515 v1 uses the active behavior at the call sites and leaves duplicate cleanup for a separate followup.

## Deferred To MT-515-magic

`arcana`, `attunement`, and the rest of the magic-family training paths remain deferred.

Reason:

- current spell and mana code fails on access, resource, room, circle, preparation, or destabilization conditions
- the character layer does not currently define a local `skill_too_low` threshold for those systems
- inventing those thresholds would be gameplay design work, not a bounded migration

`MT-515-magic` must first lock what low-rank failure means for:

- `charge_luminar`
- `prepare_spell`
- `center_empath_self`
- non-targeted spell casts that currently train through category skills

## Future Migration Queue

- `MT-515b`: combat weapon failure XP
- `MT-515c`: armor passive training
- `MT-515d`: remaining general skill migrations
- `MT-515-magic`: magic-family threshold design and migration
- duplicate `is_empath` cleanup