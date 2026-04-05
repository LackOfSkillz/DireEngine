# Second-Wave Skill Research

This report covers the next requested skill batch:

- Shield Usage
- Parry Ability
- Athletics
- Locksmithing
- Debilitation
- Small Edged

The goal is to capture everything already present in the repo and live Evennia database that can help implement or bridge these skills into the current systems.

## Executive Summary

There are really three different states in this batch:

1. Athletics, Locksmithing, and Debilitation already exist as first-class skills in code and in persisted character skill payloads.
2. Small Edged does not exist under that name, but the repo already has a practical equivalent: `light_edge`.
3. Shield Usage and Parry Ability do not currently exist as skills in the registry, database, or combat resolution pipeline.

The repo is therefore not starting from a blank slate. The real work is split between:

- EXP bridge work for existing skills that still learn through legacy hooks or not at all.
- nomenclature and migration work for `Small Edged` versus `light_edge`.
- fresh combat-system design work for `Shield Usage` and `Parry Ability`.

## Live Database Findings

Source queried: `server/evennia.db3`

The live Evennia attribute table confirms that `skills` is a persisted character attribute and is currently populated on live objects.

Persisted skill findings from decoded `skills` payloads:

- `athletics`: present on 266 linked objects, rank greater than 0 on 266 of them, current observed distribution is entirely rank 1 starter seeding.
- `locksmithing`: present on 266 linked objects, rank greater than 0 on 0 of them, current observed distribution is entirely rank 0.
- `debilitation`: present on 175 linked objects, rank greater than 0 on 0 of them, current observed distribution is entirely rank 0.
- `light_edge`: present on 266 linked objects, rank greater than 0 on 164 of them.
- `shield_usage`: not present in decoded skill payloads.
- `parry_ability`: not present in decoded skill payloads.
- `small_edged`: not present in decoded skill payloads.

Interpretation:

- `athletics` is already fully seeded into live characters.
- `locksmithing` and `debilitation` are structurally present in live character skill dicts but have not yet been meaningfully trained in the sampled DB state.
- `light_edge` is the only existing persisted candidate for `Small Edged`.
- `shield_usage` and `parry_ability` would require both code introduction and DB migration/backfill.

## Existing Skill Registry And EXP Constraints

The current canonical skill registry lives in `typeclasses/characters.py`.

Relevant entries already exist there:

- `athletics`: survival, shared, starter rank 1.
- `locksmithing`: survival, shared, starter rank 0.
- `debilitation`: magic, guild-locked, starter rank 0.
- `light_edge`: combat, shared, starter rank 0.

Relevant current registry gaps:

- no `shield_usage`
- no `parry_ability`
- no `small_edged`

The transient EXP system in `world/systems/skills.py` currently recognizes only the first-wave template batch. Current EXP template skills are:

- `evasion`
- `stealth`
- `perception`
- `brawling`
- `targeted_magic`
- `appraisal`

The repo memory already calls out this exact batch as the recommended next EXP bridge phase.

Important implication:

- Athletics, Locksmithing, Debilitation, and any future Small Edged bridge work still need explicit inclusion in `SKILL_GROUPS`, `TEMPLATE_EXP_SKILLS`, and the gameplay hook paths that call `award_exp_skill(...)`.

## Skill-By-Skill Findings

## 1. Shield Usage

### Current Status

- No skill registry entry.
- No live DB skill payloads.
- No combat resolution path that treats shield use as a distinct defensive skill.
- The only meaningful `shield` hit in the codebase right now is the spell name `shielding` in `typeclasses/spells.py`, which is unrelated to physical shield combat.

### What Already Exists That You Can Reuse

- `commands/cmd_attack.py` already has a multi-stage attack and defense contest structure.
- The current defense lane is primarily built around `evasion`, stance, awareness, hindrance, surprise, debilitation, and profession-state modifiers.
- Equipment and wielded-weapon patterns already exist, including `equipped_weapon` persistence and weapon profile handling.

### What Is Missing

- A shield item/typeclass concept that can be equipped in a way combat resolution can see.
- A `shield_usage` skill definition and migration path.
- A defensive resolution layer for shield block chance, shield mitigation, or both.
- Messaging for blocked or partially blocked attacks.
- Any EXP or legacy learning hook for shield-based defense.

### Recommended Implementation Shape

- Add `shield_usage` to `SKILL_REGISTRY` as a combat or survival-adjacent defensive skill. Combat is the cleaner fit with the current repo structure.
- Add explicit equipment support for shields rather than overloading generic armor.
- Insert shield resolution into `commands/cmd_attack.py` after attack accuracy is computed and before raw damage lands.
- Keep the first implementation simple: use shield skill plus reflex plus shield profile to reduce hit quality or convert some hits into blocks.
- Delay advanced DR-style shield templates until a real shield object model exists.

### EXP Bridge Readiness

- Not bridge-ready yet because the underlying gameplay loop does not exist.

## 2. Parry Ability

### Current Status

- No skill registry entry.
- No live DB skill payloads.
- No explicit parry contest or parry state in combat resolution.

### What Already Exists That You Can Reuse

- Weapons already expose skill, balance, range band, and damage profile through `typeclasses/weapons.py` and `Character.get_weapon_profile()` usage in combat.
- The attack loop in `commands/cmd_attack.py` already computes a single `evasion` defense total that can be split or layered.
- Wielded weapon state already exists, so a parry system could be weapon-dependent from day one.

### What Is Missing

- A `parry_ability` skill definition.
- A combat defense lane that depends on having an eligible wielded weapon.
- Any distinction between unarmed, weapon, and shield defense beyond the current evasion-heavy model.
- No parry messaging or parry-specific failure cases.

### Recommended Implementation Shape

- Add `parry_ability` to `SKILL_REGISTRY` and persistent backfill.
- In `commands/cmd_attack.py`, split defense into at least two stages: evasion and parry, with parry requiring a wielded melee-capable weapon.
- Use current weapon balance and suitability as parry modifiers.
- Keep `evasion` as the universal defense and make parry additive or conditional rather than replacing it.
- Avoid making `parry_ability` a hidden alias for weapon skill; use weapon skill as a modifier, not the skill itself.

### EXP Bridge Readiness

- Not bridge-ready yet because the gameplay hook does not exist.

## 3. Athletics

### Current Status

- Fully present in `SKILL_REGISTRY`.
- Shared visibility, description, starter rank 1.
- Present in live DB skills on all sampled linked characters at rank 1.
- Survival training hooks already map it to `climb`, `swim`, and `traversal`.

### Existing Gameplay Hooks

Athletics already has real behavior hooks in `typeclasses/characters.py`:

- `climb` contest path uses `athletics + agility + strength`.
- `swim` contest path uses `athletics + stamina + agility`.

The 601-700 work also explicitly documented that:

- `climb` and `swim` were added as athletics verbs.
- unsupported terrain fails gracefully.

### What Is Missing

- Athletics is not currently in the first-wave EXP template list.
- No second-wave EXP bridge appears to be wired yet.
- The current live DB state suggests only starter seeding, not demonstrated training growth.

### Recommended Implementation Shape

- Keep the existing survival-verb architecture.
- Bridge athletics learning at the actual climb and swim resolution points using `award_exp_skill(self, 'athletics', difficulty, success=...)`.
- Add `athletics` to `SKILL_GROUPS` and the second-wave EXP integration docs.
- Add DireTest scenarios for at least:
  - athletics success learning
  - athletics failure learning
  - athletics visibility in `experience`
  - athletics ticker drain and rank gain behavior

### EXP Bridge Readiness

- High. The gameplay hooks already exist.

## 4. Locksmithing

### Current Status

- Fully present in `SKILL_REGISTRY`.
- Shared visibility, description, starter rank 0.
- Present in live DB skills on all sampled linked characters, but currently rank 0 across the sample.

### Existing Gameplay Hooks

Locksmithing is already one of the deepest implemented systems in the repo.

Current helpers in `typeclasses/characters.py` include:

- `describe_lock_difficulty()`
- `inspect_box()`
- `locksmith_contest()`
- `disarm_box()`
- `trigger_box_trap()`
- `apply_box_trap_effect()`
- `get_active_lockpick()`
- `has_lockpick()`
- `analyze_trap()`
- `harvest_trap()`
- `rework_trap()`
- `deploy_trap()`
- `pick_box()`
- `open_box()`

Related implemented infrastructure already exists:

- box typeclass
- lockpick typeclass
- analyze and harvest commands
- deployable trap device workflow
- loot spill and box content generation
- trap component generation

The 601-700 and 701-800 reports already describe this as a complete DR-style box, trap, and tool loop foundation.

### What Is Missing

- No evidence that locksmithing has been bridged into the transient EXP system yet.
- Current hooks still use the older `use_skill('locksmithing', ...)` path.
- No locksmithing-specific EXP DireTest scenarios were found in the existing artifact naming.

### Recommended Implementation Shape

- Treat locksmithing as a clean second-wave bridge target rather than a new feature build.
- Replace or bridge the current `use_skill('locksmithing', ...)` calls in:
  - `inspect_box()`
  - `disarm_box()`
  - `analyze_trap()`
  - `harvest_trap()`
  - `pick_box()`
- Use difficulty values already present on box lock and trap fields rather than inventing new EXP difficulty math.
- Preserve the current multi-step workflow. Do not collapse box handling into a single command.

### EXP Bridge Readiness

- Very high. The gameplay loop already exists and exposes clean difficulty values.

## 5. Debilitation

### Current Status

- Present in `SKILL_REGISTRY` as a magic skill.
- Guild-locked to `SPELLCASTING_GUILDS`.
- Present in live DB skill payloads on 175 linked objects, all currently at rank 0 in the sampled data.
- Present in profession seeding for Necromancer in `systems/character/creation.py`.
- Present in spell definitions via `hinder` in `typeclasses/spells.py`.

### Existing Gameplay Hooks

The spell system already has a real debilitation path in `typeclasses/characters.py`:

- `resolve_spell()` routes `category == 'debilitation'` into `resolve_debilitation_spell()`.
- `resolve_debilitation_spell()` already uses:
  - `get_multi_skill_factor('debilitation', 'attunement')`
  - offensive power scaling
  - target `warding` plus discipline defense
  - magic resistance
  - debuff application through `target.set_state('debilitated', ...)`
  - repeat-cast dampening
  - `exposed_magic` follow-up state application

Combat also already consumes the resulting debuff state in `commands/cmd_attack.py`:

- attacker-side accuracy can be reduced by an active `debilitated` state
- defender-side evasion can be reduced when the debuff type is `evasion`

### What Is Missing

- No evidence that debilitation is in the transient EXP template bridge yet.
- The spell path still appears to rely on the older category learning route for non-targeted magic.
- No current second-wave EXP scenario names for debilitation were found in the artifact set.

### Recommended Implementation Shape

- Keep `resolve_debilitation_spell()` as the canonical gameplay hook.
- Bridge learning there instead of in generic `cast_spell()`.
- Use the resolved offense-versus-defense contest ratio to decide EXP success versus reduced-success cases.
- Add `debilitation` to the transient EXP config and keep the category-specific bridge at spell resolution, not at prepare time.
- Add at least these scenarios:
  - resisted debilitation still gives reduced learning
  - successful debilitation trains normally
  - repeat debilitation respects diminished potency without breaking EXP awards

### EXP Bridge Readiness

- High. The contest and difficulty information already exist.

## 6. Small Edged

### Current Status

- The exact name `small_edged` does not exist in the skill registry, live DB, or combat resolution.
- The repo uses `light_edge` instead.
- `light_edge` is already a core weapon skill in code and the live DB.
- `light_edge` is also used in profession seeds and starter weapons.

### Existing Reusable Infrastructure

The weapon system in `typeclasses/weapons.py` already treats `light_edge` as a first-class weapon skill.

Current weapon skill categories are:

- `brawling`
- `light_edge`
- `heavy_edge`
- `blunt`
- `polearm`

The older weapon design notes in `MicroTask Archive/MT 301 -320.md` explicitly describe the DragonRealms concept as `Small Edged (daggers)`, which makes it clear that `light_edge` is this repo's current simplification or rename of that category.

Profession and starter evidence already points at `light_edge` as the active implementation name:

- Thief starts with `light_edge` in `systems/character/creation.py`.
- Paladin, Bard, Warrior, and Warrior Mage also use `light_edge` starter seeding.
- Thief starter weapon is `dagger`, which is exactly the Small Edged fantasy lane.

### What Is Missing

- No canonical decision has been made between keeping `light_edge` or migrating to `small_edged`.
- No alias or migration layer exists.
- No EXP second-wave bridge currently exists for `light_edge` or `small_edged`.

### Recommended Implementation Shape

You need to choose one of two routes before touching EXP:

1. Keep `light_edge` as the canonical internal skill name and treat `Small Edged` as design-language only.
2. Rename `light_edge` to `small_edged` across code, DB migration, profession seeds, weapon definitions, commands, help, and any reporting/tests.

Given current repo state, the safer path is route 1:

- keep `light_edge` as the stored key
- present `Small Edged` as the DR-facing display label if desired
- bridge EXP on `light_edge`

That avoids a large live-data migration and keeps existing weapon/profile code intact.

### EXP Bridge Readiness

- High if you treat it as `light_edge`.
- Low if you insist on renaming the entire repo to `small_edged` first.

## Implementation Recommendations By Priority

### Best Immediate Bridge Targets

These are the cleanest second-wave EXP targets because their gameplay hooks already exist:

1. Athletics
2. Locksmithing
3. Debilitation
4. Light Edge as the Small Edged equivalent

### Fresh Feature Targets

These are not bridge tasks yet. They are new gameplay feature tasks:

1. Shield Usage
2. Parry Ability

## Concrete File Map

These are the highest-value files for this batch:

- `world/systems/skills.py`: transient EXP config, grouping, and bridge helper.
- `docs/skill_template_bridge.md`: current first-wave bridge document and best place to document second-wave scope.
- `docs/expHowTo.md`: player and system-facing EXP source of truth.
- `typeclasses/characters.py`: skill registry, survival hooks, magic resolution, locksmithing system, and legacy skill-use call sites.
- `commands/cmd_attack.py`: combat accuracy and defense resolution, plus any future parry or shield hook points.
- `typeclasses/weapons.py`: weapon skill categories and weapon profile data needed for Small Edged or Parry work.
- `typeclasses/spells.py`: debilitation spell definitions.
- `systems/character/creation.py`: profession starter skill seeds and starter weapon expectations.
- `server/evennia.db3`: live persistence reality check.

## Suggested Build Order

1. Bridge Athletics into transient EXP.
2. Bridge Locksmithing into transient EXP.
3. Bridge Debilitation into transient EXP.
4. Decide whether `Small Edged` means a display alias for `light_edge` or a full rename.
5. Bridge `light_edge` or migrated `small_edged` into transient EXP.
6. Only after that, design `Parry Ability` and `Shield Usage` as new combat systems.

## Bottom Line

This batch is not six equivalent tasks.

- Athletics, Locksmithing, and Debilitation are already implemented systems waiting for EXP integration.
- Small Edged is mostly a naming and compatibility decision because `light_edge` already exists and is live.
- Shield Usage and Parry Ability are not present and should be treated as new combat feature work, not simple bridge work.

If the next implementation pass is meant to mirror the first EXP bridge batch, the clean second-wave set is:

- Athletics
- Locksmithing
- Debilitation
- Light Edge as the current Small Edged equivalent

And the follow-up combat batch should then be:

- Shield Usage
- Parry Ability