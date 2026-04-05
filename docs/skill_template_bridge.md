# Skill Template Bridge

This document tracks the live skill templates being migrated from legacy `use_skill(...)` learning into the transient EXP system.

## Scope

These are template integrations, not the final rollout of all skills and spells.

The purpose of this bridge work is to replace or bridge the old learning destination for the highest-value live behavior templates:

- Evasion -> passive defense in combat and targeted-magic defense
- Stealth -> `hide`, `sneak`, `stalk`, `ambush`
- Perception -> `search`, `observe`, anti-stealth detection
- Brawling -> unarmed attack loop
- Targeted Magic -> `prepare` and `cast` on offensive spell resolution
- Appraisal -> `appraise` command branches
- Athletics -> `attempt_climb()` and `attempt_swim()` terrain actions
- Locksmithing -> box and trap workflow
- Debilitation -> debuff spell resolution
- Light Edge -> armed melee success path for the live small-edged equivalent

## Legacy Status

Before this bridge work, most of these behaviors still awarded learning through legacy `use_skill(...)` hooks and updated persistent `db.skills[*].mindstate` rather than the transient `exp_skills` pools.

That older path is still present elsewhere in the repo for unrelated skills and systems, but these bridged behaviors now route into the new EXP system through the canonical helper in `world/systems/skills.py`.

## Canonical Bridge

The canonical gameplay bridge is:

```python
def award_exp_skill(char, skill_name, difficulty, success=True):
    skill = char.exp_skills.get(skill_name)
    return train(skill, difficulty, success=success)
```

Gameplay hooks should call this helper instead of duplicating EXP math inside commands or abilities.

## Template Map

| Skill | Action Source | Legacy-Only Before | Bridged Now | DireTest Coverage |
| --- | --- | --- | --- | --- |
| Evasion | passive physical defense, targeted-magic defense | no real new-EXP hook | yes | `exp-evasion-passive`, `exp-command-visibility` |
| Stealth | `hide`, `sneak`, `stalk`, `ambush` prep | yes | yes | `exp-stealth-bridge`, `exp-stealth-perception-dual`, `exp-command-visibility` |
| Perception | `search`, `observe`, anti-stealth checks | yes | yes | `exp-stealth-perception-dual` |
| Brawling | unarmed `attack` success path | yes | yes | `exp-brawling-bridge` |
| Targeted Magic | offensive cast resolution | yes | yes | `exp-targeted-magic-bridge`, `exp-command-visibility` |
| Appraisal | gem, item, weapon, armor, creature appraisal | yes | yes | `exp-appraisal-loop`, `exp-command-visibility` |
| Athletics | climb and swim terrain actions | yes | yes | `exp-athletics-bridge` |
| Locksmithing | inspect, disarm, pick, analyze, harvest, rework | yes | yes | `exp-locksmithing-bridge`, `exp-second-wave-command-visibility` |
| Debilitation | hindering spell resolution | yes | yes | `exp-debilitation-bridge`, `exp-second-wave-command-visibility` |
| Light Edge | armed melee `attack` success path | yes | yes | `exp-light-edge-bridge`, `exp-second-wave-command-visibility` |

## Bridge Audit

### Stealth

- Legacy hooks previously lived in `typeclasses/abilities_stealth.py` and the sneak-move continuation hook in `typeclasses/characters.py`.
- New EXP bridge now lives in those same behavior points through `award_exp_skill(...)`.
- Legacy path still remains in parallel temporarily: no, not for the bridged stealth actions.

### Perception

- Legacy hooks previously lived in `typeclasses/abilities_perception.py` for `search` and `observe`.
- New EXP bridge now lives in those same ability executions.
- Legacy path still remains in parallel temporarily: no, not for the bridged perception actions.

### Appraisal

- Legacy hooks previously lived in `typeclasses/characters.py` inside `appraise_target()` and `compare_items()`.
- New EXP bridge now lives in those same appraisal branches.
- Legacy path still remains in parallel temporarily: no, not for the bridged appraisal actions.

### Targeted Magic

- Legacy hook previously lived in `cast_spell()` after spell resolution for category learning.
- New EXP bridge now lives in `resolve_targeted_spell()` and `resolve_room_targeted_spell()` so hits and misses can both train through EXP.
- Legacy path still remains in parallel temporarily: no, not for targeted-magic resolution.

### Brawling

- Legacy hook previously lived in `commands/cmd_attack.py` for meaningful successful hits.
- New EXP bridge now lives in that same hit-resolution path, but only when the resolved combat skill is `brawling`.
- Legacy path still remains in parallel temporarily: no, not for brawling success cases.

### Evasion

- Legacy hook previously did not exist as a real EXP bridge point.
- New EXP hook now lives in physical attack resolution and targeted-magic defense resolution.
- Legacy path still remains in parallel temporarily: not applicable, because this is new hook creation rather than replacement.

### Athletics

- Legacy hooks previously lived in `typeclasses/characters.py` inside `attempt_climb()` and `attempt_swim()`.
- New EXP bridge now lives in those same terrain-action methods through `award_exp_skill(...)` with success-sensitive gain.
- Legacy path still remains in parallel temporarily: no, not for climb and swim learning.

### Locksmithing

- Legacy hooks previously lived in `typeclasses/characters.py` inside the box and trap workflow helpers.
- New EXP bridge now lives in `inspect_box()`, `disarm_box()`, `pick_box()`, `analyze_trap()`, `harvest_trap()`, and `rework_trap()`.
- Legacy path still remains in parallel temporarily: no, not for the bridged locksmithing actions.

### Debilitation

- Legacy hook previously did not route offensive debuff learning through transient EXP.
- New EXP bridge now lives in `resolve_debilitation_spell()` so both resisted and successful casts train the same skill through outcome-sensitive gain.
- Legacy path still remains in parallel temporarily: no, not for debilitation spell resolution.

### Light Edge

- Legacy hook previously fell through the generic combat-learning path in `commands/cmd_attack.py`.
- New EXP bridge now lives in that same hit-resolution path, but only when the resolved combat skill is `light_edge`.
- Legacy path still remains in parallel temporarily: yes, for other weapon families that are outside this batch; no, for `light_edge` itself.

## Brawling Decision Note

- Current repo behavior: brawling learns on meaningful successful attacks.
- Current repo behavior: brawling does not learn on miss.
- DR-style target behavior may want miss-learning later.
- That change is deferred to a later balance pass so this bridge stays behaviorally conservative.

## Naming And Deferred Work

- The live repo skill key for planned Small Edged behavior is `light_edge`.
- This bridge batch deliberately does not add a duplicate `small_edged` live skill.
- `parry_ability` and `shield_usage` remain deferred future work because they need dedicated combat hooks instead of a direct bridge swap.