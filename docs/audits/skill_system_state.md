# DireEngine Skill System Audit

**Date:** 2026-05-02
**Author:** MT-515-audit
**Purpose:** Inventory current skill system state to inform MT-515-impl scope.

## Executive Summary

The current codebase exposes one explicit skill registry with 38 named skills, but the runtime training surface is not unified. Training currently flows through three overlapping patterns: `Character.use_skill()` into `SkillService.award_practice()`, direct difficulty-mode XP awards through `SkillService.award_xp()`, and legacy wrappers like `Character.award_skill_experience()` that now delegate into `SkillService.award_xp()`. The character persistence model also keeps both the old `db.skills` structure and the newer `exp_skill_state` / `SkillHandler` model alive at the same time.

The audit found a split between skills that already model failure outcomes explicitly and skills that either train only on success or have no concrete attempt path in code. Outdoorsmanship already has a low-rank failure-learning path in forage and fishing. Guild/profession gating exists in multiple places: ability `guilds`, spell `allowed_professions`, spell min-circle / min-skill checks, and ad hoc `is_profession(...)` conditionals inside character methods.

This is not a small skill surface. The registry contains 38 skills, several attempt paths are dynamic rather than literal-string keyed, and there are at least two parallel storage/training layers coexisting. The gap analysis below classifies current observed behavior without recommending migration order or implementation strategy.

## Skill Inventory (Phase A)

Canonical registry source: `typeclasses/characters.py`, `SKILL_REGISTRY`.

| Skill | Display | Category | Visibility | Starter Rank | Registry Source |
| --- | --- | --- | --- | ---: | --- |
| appraisal | Appraisal | lore | shared | 1 | `typeclasses/characters.py` `SKILL_REGISTRY` |
| arcana | Arcana | magic | shared | 1 | same |
| athletics | Athletics | survival | shared | 1 | same |
| attack | Attack | combat | shared | 0 | same |
| attunement | Attunement | magic | shared | 1 | same |
| augmentation | Augmentation | magic | guild_locked | 0 | same |
| backstab | Backstab | survival | guild_locked | 0 | same |
| blunt | Blunt | combat | shared | 0 | same |
| brawling | Brawling | combat | shared | 0 | same |
| brigandine | Brigandine | armor | shared | 0 | same |
| chain_armor | Chain Armor | armor | shared | 0 | same |
| combat | Combat | combat | shared | 0 | same |
| debilitation | Debilitation | magic | guild_locked | 0 | same |
| disengage | Disengage | combat | shared | 0 | same |
| empathy | Empathy | magic | shared | 0 | same |
| evasion | Evasion | survival | shared | 1 | same |
| first_aid | First Aid | survival | shared | 0 | same |
| heavy_edge | Heavy Edge | combat | shared | 0 | same |
| instinct | Instinct | survival | guild_locked | 0 | same |
| light_armor | Light Armor | armor | shared | 0 | same |
| light_edge | Light Edge | combat | shared | 0 | same |
| locksmithing | Locksmithing | survival | shared | 0 | same |
| mechanical_lore | Mechanical Lore | lore | shared | 0 | same |
| outdoorsmanship | Outdoorsmanship | survival | shared | 0 | same |
| perception | Perception | survival | shared | 1 | same |
| plate_armor | Plate Armor | armor | shared | 0 | same |
| polearm | Polearm | combat | shared | 0 | same |
| scholarship | Scholarship | lore | shared | 0 | same |
| skinning | Skinning | survival | shared | 0 | same |
| stealth | Stealth | survival | shared | 0 | same |
| tactics | Tactics | lore | shared | 0 | same |
| targeted_magic | Targeted Magic | magic | guild_locked | 0 | same |
| thanatology | Thanatology | survival | guild_locked | 0 | same |
| theurgy | Theurgy | magic | guild_locked | 0 | same |
| thievery | Thievery | survival | guild_locked | 0 | same |
| trading | Trading | lore | shared | 1 | same |
| utility | Utility | magic | guild_locked | 0 | same |
| warding | Warding | magic | guild_locked | 0 | same |

### Registry Divergence Observed

- `SKILL_REGISTRY` is the canonical visible registry.
- Character storage still mirrors rank data into legacy `db.skills` while also persisting `db.exp_skill_state` and an in-memory `SkillHandler`/`SkillState` layer.
- `world/systems/skills.py` only templates a smaller EXP subset (`evasion`, `stealth`, `perception`, `brawling`, `targeted_magic`, `appraisal`, then later `athletics`, `locksmithing`, `light_edge`, `debilitation`, `empathy`, `first_aid`, `scholarship`). That EXP template list is narrower than the full registry.

## Per-Skill Attempt-And-Train Paths (Phase B)

Observed attempt / train behavior below is based on static reads only.

| Skill | Attempt Path(s) | Eligibility Gates | Training Trigger | XP Path | Failure Handling |
| --- | --- | --- | --- | --- | --- |
| appraisal | `Character.appraise_target`, `Character.compare_items`, `CmdMark.func` | target presence; `mark` has thief/ranger branch logic but no appraisal rank gate | success-path actions | direct difficulty XP via `award_skill_experience` or `SkillService.award_xp` | no appraisal-specific failure-XP path found; `mark` awards success XP only |
| arcana | `Character.charge_luminar` | needs luminar, available attunement, charge caps | successful charge | `use_skill("arcana")` -> `award_practice` | charge can fail from no focus / destabilization with no observed failure XP |
| athletics | climb / swim / burglary movement | climb/swim state checks; burglary entry validation | both success and failure in climb/swim and burglary movement | direct difficulty XP in climb/swim; direct difficulty XP in burglary movement helper | climb/swim and burglary movement explicitly award failure XP via `success=False` |
| attack | warrior ability prerequisite skill; also present as registry row | warrior abilities require `attack` rank for visibility/use | no direct `attack` training call found | none found | no concrete failure handling found |
| attunement | `Character.prepare_spell`, `Character.center_empath_self` | spell access checks for prepare; empath/self state checks for centering | successful prepare / centering | `use_skill("attunement")` -> `award_practice` | mana or state failures do not award observed failure XP |
| augmentation | structured spell cast for augmentation spells | spell `allowed_professions`, known spell, circle, spell min-skill checks | successful non-targeted cast | dynamic `use_skill(category)` where category is spell metadata | no explicit failure-XP path found |
| backstab | no concrete backstab attempt path found in live code | registry only; thief docs/research exist outside runtime slice | none found | none found | none found |
| blunt | dynamic combat attack through weapon profile `skill_name` | weapon selection / combat readiness | successful hits only when weapon skill resolves to `blunt` | `CombatXP.award` -> `award_practice` for non-`brawling`/`light_edge` skills | no direct failure-XP path for attacker; defender still may train `evasion` |
| brawling | dynamic combat attack through weapon profile | combat readiness | successful hits | `CombatXP.award` -> direct `award_xp` success path | no direct attacker failure-XP path |
| brigandine | passive armor skill reference only | armor worn / armor type mapping | no direct training call found | none found | none found |
| chain_armor | passive armor skill reference only | armor worn / armor type mapping | no direct training call found | none found | none found |
| combat | registry-only general combat row | none found beyond metadata | none found | none found | none found |
| debilitation | structured debilitation spells | spell access (`allowed_professions`, known spell, circle, `min_skill`) | spell contest always resolves caster/target award call | `award_skill_experience("debilitation", ..., success=hit)` | miss still awards difficulty XP with `success=False` through wrapper |
| disengage | registry-only combat row | none found | none found | none found | none found |
| empathy | `CmdDiagnose`, anatomy study, empath helper `award_empathy_experience` | diagnose needs character target; empath body systems add profession-specific checks in owning methods | success-path diagnose/use-skill, anatomy study, empath body interactions | mixed: `use_skill("empathy")` and direct `award_skill_experience` | diagnose path uses generic practice and has no explicit failure XP; anatomy/body helpers mostly success-only |
| evasion | combat defense, targeted-magic defense | being attacked / targeted | successful or failed defense depending on attacker outcome | direct difficulty XP via `CombatXP.award` and spell contest wrapper | combat and spell contests both award on defend attempt; combat uses `success=not hit` |
| first_aid | tending / stabilize corpse / anatomy study | wound/corpse/state checks in owning methods | success-path tend/stabilize/study hooks | direct `award_skill_experience` in helpers; study path direct | no explicit low-rank failure-learning path found in observed first-aid methods |
| heavy_edge | dynamic combat attack through weapon profile | combat readiness | successful hits only | `CombatXP.award` -> `award_practice` | no attacker failure-XP path found |
| instinct | registry-only guild-locked placeholder | none found | none found | none found | none found |
| light_armor | passive armor skill reference only | armor worn / armor type mapping | no direct training call found | none found | none found |
| light_edge | dynamic combat attack through weapon profile | combat readiness | successful hits only | `CombatXP.award` -> direct difficulty XP success path | no attacker failure-XP path found |
| locksmithing | inspect/analyze/disarm/harvest/rework/pick box; burglary entry | target box / trap / burglary validation | success and failure in several locksmithing contests | direct difficulty XP via `award_skill_experience` or `SkillService.award_xp` | burglary explicitly distinguishes catastrophic / fail / partial / success; locksmithing gets failure XP there. Box helpers also award success/failure by outcome |
| mechanical_lore | fishing rig / untangle; fishing economy path | needs pole/hook/line state | both success and failure on rigging and untangling; success path in economy helper | direct `SkillService.award_xp`; one legacy wrapper in fishing economy | rig/untangle explicitly award failure XP with low multiplier |
| outdoorsmanship | forage ability, fishing, ranger resource transform | forage has no rank gate; fishing requires gear/location state; ranger transform requires recipe/material | success in forage/fishing/transform; low-rank failure in forage and some fishing outcomes | mixed `use_skill("outdoorsmanship")` and direct `SkillService.award_xp` | forage skill-too-low explicitly awards 25% failure XP; fishing junk/event/failure outcomes also award fractional failure/partial XP |
| perception | search/observe abilities, trap detection, mark, stealth observer detection | ability rank gates on `search`/`observe`; target/room state checks | search/observe and mark success paths; trap detection; observer detection | mixed direct `award_xp` and `use_skill("perception")` | no explicit skill-too-low failure-learning path found; `search`/`observe` always award after execution |
| plate_armor | passive armor skill reference only | armor worn / armor type mapping | no direct training call found | none found | none found |
| polearm | dynamic combat attack through weapon profile | combat readiness | successful hits only | `CombatXP.award` -> `award_practice` | no attacker failure-XP path found |
| scholarship | recall knowledge, study item, study anatomy | study item checks item flags and difficulty; recall depends on owning method context | success-path recall/study | direct `award_skill_experience`; some dynamic `use_skill(normalized_skill)` fallback for non-scholarship study items | study item below-skill failure returns message with no XP |
| skinning | `Character.skin_target`, `Character.skin_fish_target` | corpse/fish presence, knife, state checks | completion of skinning contest regardless of outcome bucket | `use_skill("skinning")` -> `award_practice` | result messaging varies by fail/partial/success/strong, but training call itself does not carry explicit outcome/failure semantics |
| stealth | hide/sneak/stalk/ambush ability family, legacy `CmdHide`, burglary movement | ability rank gates; hidden-state prerequisites for sneak/stalk/ambush; thief roundtime in command path | ability path defers XP to scheduled `finalize_stealth_learning`; legacy command awards immediately; burglary movement awards directly | mixed scheduled `award_skill_experience`, direct `SkillService.award_xp`, and direct command award | ability path has margin-based partial/failure modifiers; legacy `CmdHide` awards only success XP; burglary awards success/failure XP |
| tactics | `Character.assess_stance` | valid combat target | successful assessment use | `use_skill("tactics")` -> `award_practice` | low-skill messaging changes, but no explicit failure-XP path |
| targeted_magic | structured targeted spells | spell access (`allowed_professions`, known spell, circle, `min_skill`) and valid target checks | spell contest always awards caster/target training | direct `award_skill_experience` in `SpellContestService.resolve_targeted_magic` | miss still awards caster training with `success=False`; target evasion also trains |
| thanatology | registry-only guild-locked placeholder | none found | none found | none found | none found |
| theurgy | cleric corpse rites, rituals, communes, prepare/cast cleric spell adjunct, resurrection flows | strong ad hoc profession checks (`is_profession("cleric")`), ability/state/corpse prerequisites in owning methods | successful cleric actions after gate pass | `use_skill("theurgy")` -> `award_practice` | wrong profession hard-fails in owning methods; no explicit failure-XP path after allowed attempt found |
| thievery | theft system | theft contest setup, target/container validity, justice/shop context | every theft attempt resolves one XP award | direct `SkillService.award_xp` with success/partial/failure outcome | caught theft uses `success=False`, `outcome="failure"`; unseen failed theft uses partial |
| trading | haggle / sell item / sell all / pending purchase accept | vendor / inventory / transaction-state checks | success-path merchant actions | `use_skill("trading")` -> `award_practice` | no explicit failure-learning path found |
| utility | structured utility spells | spell access (`allowed_professions`, known spell, circle, `min_skill`) | successful non-targeted cast | dynamic `use_skill(category)` where category is spell metadata | no explicit failure-XP path found |
| warding | structured warding spells; debilitation defense | spell access for casting; defend-side spell contest when targeted by debilitation | defend contest always awards; successful non-targeted warding cast also uses dynamic `use_skill(category)` | direct `award_skill_experience` on defense; dynamic `use_skill("warding")` on warding spell casts | debilitation miss still gives defense-side warding XP with `success=True` because defense succeeded |

### Skills With No Concrete Attempt Path Found In Static Reads

- `attack`
- `backstab`
- `brigandine`
- `chain_armor`
- `combat`
- `disengage`
- `instinct`
- `light_armor`
- `plate_armor`
- `thanatology`

These skills are present in the registry and may affect visibility, combat/armor calculations, or future systems, but no concrete runtime training entry point was found in the current static audit slice.

### Dynamic / Indirect Attempt Paths Worth Calling Out

- Weapon skills (`blunt`, `brawling`, `heavy_edge`, `light_edge`, `polearm`) are not routed by literal command names. Combat derives `skill_name` from weapon profile in `engine/services/combat_service.py`, then `CombatXP.award()` trains that skill.
- Non-targeted spell skills (`augmentation`, `utility`, some `warding`) are trained through dynamic `category` values in `Character.cast_spell()` rather than literal skill strings at each spell definition.
- Stealth ability learning is deferred through `record_stealth_contest()` / `finalize_stealth_learning()` rather than awarded inline in the ability classes.

## Shared Infrastructure (Phase C)

### SkillService API

Source: `engine/services/skill_service.py`

- `SkillService.calculate_mindstate(pool, capacity)`
- `SkillService.award_xp(character, skill, amount, source=None, success=True, outcome=None, event_key=None, context_multiplier=1.0)`
- `SkillService.award_practice(character, skill, difficulty, learning_multiplier=1.0, source=None)`

Observed behavior:

- `award_xp(...)` is the canonical XP mutation path.
- `source={"mode": "difficulty"}` switches the service into difficulty-based learning via `world.systems.skills.train(...)`.
- non-difficulty awards use flat pool addition.
- `award_practice(...)` computes amount from `Character.get_learning_amount(...)`, profession weights, scholarship modifier, race modifier, and debt multiplier, then calls `award_xp(...)` with `track_field_xp=True`.

### Training Paths

Observed training patterns:

1. Generic practice path
   - `Character.use_skill(...)`
   - checks dead / roundtime / optionally `has_skill(...)`
   - calls `SkillService.award_practice(...)`
   - does not pass `success` / `outcome`

2. Explicit difficulty/failure path
   - direct `SkillService.award_xp(..., source={"mode": "difficulty"}, success=..., outcome=..., event_key=..., context_multiplier=...)`
   - used by forage failure XP, fishing, burglary, theft, perception, some combat, some commands

3. Legacy wrapper path
   - `Character.award_skill_experience(...)`
   - wrapper around `SkillService.award_xp(..., source={"mode": "difficulty"})`
   - still used widely in character methods and spell contests

4. Stealth deferred path
   - `record_stealth_contest(...)` stores pending learning
   - `finalize_stealth_learning(...)` later computes context multiplier and calls `award_skill_experience("stealth", ...)`

5. Dynamic combat path
   - `CombatService._build_context()` sets `skill_name` from weapon profile
   - `CombatXP.award()` trains the attack skill plus defender `evasion`

### Profession / Guild Helpers

Primary sources: `typeclasses/characters.py`, `world/professions/professions.py`

Observed storage:

- `Character.db.profession`
- `Character.db.guild`
- `Character.db.profession_rank`

Observed helpers:

- `Character.get_profession()`
- `Character.is_profession(key)`
- `Character.get_profession_guild_tag()`
- `Character.get_guild()` / `set_guild()`
- `Character.has_skill_guild_access(skill_name)`
- `Character.passes_guild_check(ability)`
- `SpellAccessService.can_use_spell(...)` for spell profession gating

Observed profession/guild models:

- Skill visibility gating uses registry metadata `guilds` plus `has_skill_guild_access(...)`.
- Ability gating uses `ability.guilds` checked against `Character.get_profession()`.
- Spell gating uses `spell.allowed_professions`, known spellbook membership, circle, and min-skill checks.
- Many cleric / ranger / warrior features also use ad hoc `if not self.is_profession("..."):` hard-fails inside character methods.

No single universal guild-access helper owns all runtime gating.

### Ability Framework Gates

Primary sources: `typeclasses/abilities.py`, `typeclasses/characters.py`

Observed structure:

- Base `Ability` defines `required = {"skill": None, "rank": 0}` and `visible_if = {"skill": None, "min_rank": 0}`.
- `Character.meets_ability_requirements(ability)` only enforces `required.skill` and `required.rank`.
- `Character.passes_guild_check(ability)` enforces `ability.guilds` against profession.
- `Character.can_see_ability(ability)` combines guild check, hidden warrior logic, and `visible_if` rank threshold.

Observed consequences:

- Wrong-guild ability use hard-fails with `"That is not your path."`.
- Rank-gated ability use hard-fails with `"You are not experienced enough."`.
- Ability framework itself does not award XP; training remains in each ability / owning method.

## DR Taxonomy Mapping (Phase D)

This section maps current repo state to the DR taxonomy referenced in the dispatch and in local DR research documents under `docs/archive/root-workfiles` and `docs/research`.

### General Skillsets Present In DireEngine

Observed registry coverage by DR skillset:

- Armor
  - Present: `brigandine`, `chain_armor`, `light_armor`, `plate_armor`
  - Notes: these are defined and referenced in armor calculations, but no direct training hooks were found in this audit slice.

- Weapons
  - Present: `brawling`, `light_edge`, `heavy_edge`, `blunt`, `polearm`
  - Additional combat-adjacent rows: `attack`, `combat`, `disengage`
  - Notes: weapon training is dynamic through combat profile skill resolution.

- Magic
  - Present: `attunement`, `arcana`, `augmentation`, `debilitation`, `targeted_magic`, `utility`, `warding`
  - Also present: `empathy`, `theurgy`
  - Notes: `empathy` is shared in the registry, not guild-locked; `theurgy` is guild-locked to cleric.

- Survival
  - Present: `athletics`, `evasion`, `first_aid`, `locksmithing`, `outdoorsmanship`, `perception`, `skinning`, `stealth`
  - Guild-locked survival rows: `backstab`, `instinct`, `thanatology`, `thievery`

- Lore
  - Present: `appraisal`, `mechanical_lore`, `scholarship`, `tactics`, `trading`

### Guild-Locked Skills Present In DireEngine

Cross-reference against the dispatch’s 11 guild-locked DR skills:

| DR Guild Skill | Current DireEngine Equivalent | Present? | Notes |
| --- | --- | --- | --- |
| Empathy | `empathy` | Yes | Registry marks it shared, not guild_locked; runtime use is strongly empath-themed but not registry-gated to empath only |
| Astrology | none found | No | no `astrology` row in registry |
| Expertise | none found | No | no `expertise` row in registry |
| Scouting | none found | No | ranger systems exist, but no `scouting` skill row |
| Backstab | `backstab` | Yes | registry row exists; no concrete runtime attempt path found |
| Summoning | none found | No | no `summoning` row in registry |
| Bardic Lore | none found | No | no `bardic_lore` row in registry |
| Conviction | none found | No | no `conviction` row in registry |
| Theurgy | `theurgy` | Yes | cleric-gated in registry and runtime methods |
| Thanatology | `thanatology` | Yes | registry row exists; no concrete runtime attempt path found |
| Trading | `trading` | Yes | registry marks it shared rather than guild_locked |

### DireEngine Skills Outside Clean DR Canon Mapping

Observed rows that do not map cleanly to the dispatch’s DR taxonomy names:

- `attack`
- `combat`
- `disengage`
- `instinct`
- `mechanical_lore`
- `thievery`

Notes:

- `mechanical_lore` is explicitly called out in local prior research as a condensed / legacy-style lore skill rather than a modern DR crafting matrix.
- `thievery` appears to represent theft / illicit manipulation, but the registry name does not match the DR guild-skill names listed in the dispatch.

### DR Skills Absent From Current Registry

Based on the dispatch and local DR research files present in the repo, clearly absent named skills include:

- `astrology`
- `expertise`
- `scouting`
- `summoning`
- `bardic_lore`
- `conviction`

Local research files also call out other DR-aligned names not present as current registry rows, including:

- `shield_usage`
- `parry_ability`
- `small_edged`

This audit does not infer a complete external DR skill list beyond the material present in the repo and the dispatch text.

## Gap Analysis Vs MT-515 Principle (Phase E)

Principle under audit:

- general skills: attempts allowed at any rank; low-rank skill failures grant 25% of successful XP for skill-too-low failures
- guild-gated skills: wrong-guild hard-fail with no XP

### Already Correct

- `outdoorsmanship`
  - forage explicitly allows attempt at zero rank, distinguishes `skill_too_low`, and awards failure XP with `FORAGE_FAILURE_XP_MULTIPLIER = 0.25`
- wrong-guild ability use in the ability framework
  - `passes_guild_check(...)` hard-fails with no XP before execution

### Failure-XP Inconsistent

- `stealth`
  - ability path uses delayed margin-sensitive failure modifiers; legacy `CmdHide` awards only immediate success XP
- `locksmithing`
  - burglary and several box/trap paths model failure outcomes explicitly, but not all locksmithing-related paths share one helper or one failure policy
- `mechanical_lore`
  - fishing rig/untangle award explicit failure XP, but the economy-side helper is success-only
- `athletics`
  - climb/swim/burglary movement do award failure XP, but there is no single generalized athletics attempt helper

### Hard-Fail Correct

- `theurgy`
  - cleric-only methods hard-fail wrong-profession characters before training
- ability-level guild-gated skills generally
  - any ability with `guilds` set hard-fails wrong-profession callers via `passes_guild_check(...)`
- spell profession access
  - `SpellAccessService.can_use_spell(...)` hard-fails wrong profession before preparation/cast

### Has Gates But No Failure XP

- `arcana`
- `attunement`
- `skinning`
- `tactics`
- `trading`
- `scholarship`
- `first_aid`
- non-targeted spell categories: `augmentation`, `utility`, successful `warding` casting

These skills have visible attempt prerequisites or action-state checks, but the observed training calls are success-path practice awards rather than explicit failure-learning logic.

### No Failure Handling At All Found

- `attack`
- `backstab`
- `brigandine`
- `chain_armor`
- `combat`
- `disengage`
- `instinct`
- `light_armor`
- `plate_armor`
- `thanatology`

No concrete attempt path was found, so no failure path was observed.

### Unclear / Needs Investigation

- weapon skills other than `brawling` and `light_edge`
  - they do train dynamically in combat, but static reads here did not show whether attacker miss / whiff paths ever grant those weapon skills XP outside successful hits
- `empathy`
  - registry visibility is shared, but runtime usage is dominated by empath-flavored systems; the exact intended access model is not fully centralized
- spell min-skill gating
  - structured spell definitions use `min_skill={"primary_magic": ...}`, but the visible skill registry does not define `primary_magic`; tests stub it externally, while live character casting uses category skills plus attunement

## Open Questions

- Is `empathy` intended to remain registry-shared, or is the current shared visibility only a transitional state while empath-only systems carry the real gate?
- Should dynamic combat weapon training be treated as one generalized attack-learning family, or as separate per-weapon-skill policies? The current code mixes direct XP for `brawling` / `light_edge` and `award_practice` for other weapon skills.
- Is the spell access layer’s `primary_magic` requirement an intentional abstraction that is resolved elsewhere, or an unresolved mismatch between spell metadata and the character skill registry?
- Are armor skills meant to be passive-only state modifiers for now, or are training hooks simply absent from the current implementation slice?
- For registry-only guild skills (`backstab`, `instinct`, `thanatology`), is “defined but not wired” expected current state or an incomplete implementation boundary?

## Appendix: Code References

### Canonical Skill Registry / Character Skill Storage

- `typeclasses/characters.py`
  - `SKILL_REGISTRY`
  - `AVAILABLE_SKILL_BASELINES`
  - `_sync_exp_skill_state(...)`
  - `_persist_exp_skill_state(...)`
  - `award_skill_experience(...)`
  - `use_skill(...)`
  - `passes_guild_check(...)`
  - `meets_ability_requirements(...)`
  - `has_skill_guild_access(...)`
  - `is_skill_visible(...)`
  - `get_available_skills(...)`
  - `get_skill_detail_entry(...)`

### Shared Training Infrastructure

- `engine/services/skill_service.py`
  - `award_xp(...)`
  - `award_practice(...)`
- `world/systems/skills.py`
  - `train(...)`
  - `award_exp_skill(...)`
  - `SkillState`
  - `SkillHandler`

### Ability Framework / Guild Gates

- `typeclasses/abilities.py`
  - `Ability.required`
  - `Ability.visible_if`
  - `Ability.guilds`
- `typeclasses/abilities_perception.py`
  - `SearchAbility`
  - `ObserveAbility`
- `typeclasses/abilities_stealth.py`
  - `HideAbility`
  - `SneakAbility`
  - `StalkAbility`
  - `AmbushAbility`
- `typeclasses/abilities_survival.py`
  - `_award_forage_skill(...)`
  - `_award_forage_failure_xp(...)`
  - `forage_attempt(...)`
  - `ForageAbility`

### Dynamic Combat / Spell Training

- `engine/services/combat_service.py`
  - `_build_context(...)` sets dynamic `skill_name` from weapon profile
- `engine/services/combat_xp.py`
  - `CombatXP.award(...)`
- `engine/services/spell_contest_service.py`
  - `resolve_targeted_magic(...)`
  - `resolve_debilitation(...)`
- `engine/services/spell_access_service.py`
  - `can_use_spell(...)`
- `typeclasses/characters.py`
  - `prepare_spell(...)`
  - `cast_spell(...)`

### Per-Skill Entry Point Clusters

- Perception: `typeclasses/abilities_perception.py`, `commands/cmd_mark.py`, `typeclasses/characters.py` `detect_traps_in_room(...)`
- Stealth: `typeclasses/abilities_stealth.py`, `commands/cmd_hide.py`, `typeclasses/characters.py` `finalize_stealth_learning(...)`, `world/systems/burglary.py`
- Outdoorsmanship: `typeclasses/abilities_survival.py`, `world/systems/fishing.py`, `typeclasses/characters.py` `transform_ranger_resource(...)`
- Locksmithing: `typeclasses/characters.py` box/trap methods, `world/systems/burglary.py`
- Trading: `typeclasses/characters.py` `haggle_with(...)`, `sell_item(...)`, `sell_all_*`, `accept_pending_purchase(...)`
- Lore study: `typeclasses/characters.py` `study_item(...)`, `recall_knowledge(...)`, `assess_stance(...)`; `commands/cmd_study_anatomy.py`
