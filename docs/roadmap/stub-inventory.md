# DRG-022 Stub Inventory Walk

Purpose: current-state audit of DireEngine before any Phase 4 overhaul work.

How to read this document:

- Entries are grouped by the Phase 4 bundle order defined in `docs/roadmap/direngine-phase-4.md`.
- Each entry describes what the code does today, which eventual DRG-011 bundle it maps to, how close it appears to GSL/canon alignment, and whether the current implementation is already extension-friendly or still hardcoded in the engine.
- Hardcoded-knowledge violations are intentionally called out even when the current feature works. DRG-022.5 uses this document as its work surface for extension-point design.

Master references:

- Phase 4 master roadmap: `docs/roadmap/direngine-phase-4.md`
- As-built implementation snapshot: `AS_BUILT.md`
- Phase 4 audit note: `DATA-GAP-AUDIT.md`

Sample canon validation performed during this walk:

- `canon_skills`: 63 rows
- `canon_stats`: 10 rows
- `canon_races` Human/Elf rows: 2
- `profession_spells`: Ranger 37, Cleric 49, Empath 37, Moon Mage 59
- `profession_abilities`: Ranger 13, Cleric 8, Empath 4, Moon Mage 22
- `map.rooms` area matches for Crossing: `The Crossing` 218, `Crossing` 48, plus Crossing subareas that bring the local total into the roadmap's expected 266-room range

## Foundation Phase

**System / Module:** Foundation orchestration and command/runtime plumbing
**Primary location:** `commands/command.py`
**Companion files:** `commands/default_cmdsets.py`, `commands/__init__.py`, `typeclasses/objects.py`, `typeclasses/rooms.py`, `typeclasses/exits.py`, `engine/services/state_service.py`, `world/systems/scheduler.py`, `world/systems/time_model.py`, `world/systems/tick_audit.py`, `server/conf/at_server_startstop.py`
**Current behavior:** The engine already has a functional command-entry layer, Evennia typeclass hierarchy, mutable state/effect handling, and scheduled runtime work. `engine/services/state_service.py` owns newer mutation paths for statuses, roundtime, fatigue, and some combat-adjacent effects; `typeclasses/objects.py` and `typeclasses/rooms.py` remain the main persistence and presentation surface; `world/systems/scheduler.py` and `server/conf/at_server_startstop.py` split timed work into scoped pulses instead of the older heavy sweep.
**Bundle assignment:** `T0-VERB-DISPATCH`, `T0-OBJECT-SYSTEM`, `T0-VARFIELDS`, `T0-EFFECTS`, `T0-TIME`, `T0-COMMS`, `T0-UTIL`
**Canon mappings:** `gsl.scripts` foundation cluster, `canon_effects`, scheduler/time semantics from GSL lifecycle scripts, no single DireLore registry yet for object/typeclass layout
**GSL alignment:** `pre_gsl_math_overhaul`
**Extension-API status:** `not_applicable`
**Dependencies:** none
**Estimated overhaul size:** `large (>800 LOC)`
**Hardcoded-knowledge violations:**
- `server/conf/at_server_startstop.py:69` hardcodes `LANDING_AREA_ID = "new_landing"`
- `server/conf/at_server_startstop.py:1942` primes explicit zone IDs `new_landing`, `empath-guild-map`, and `ranger-guild-map`
- state/effect keys remain engine-owned string constants in `engine/services/state_service.py`
**Notes:** This phase is infrastructure-heavy rather than content-heavy, but it still contains named-zone assumptions that will matter once zone bundles become installable/removable.

## Player State Phase

**System / Module:** Character state, vitals, position, stance, wounds, and encumbrance
**Primary location:** `typeclasses/characters.py`
**Companion files:** `commands/cmd_stance.py`, `engine/services/injury_service.py`, `domain/wounds/constants.py`, `domain/wounds/models.py`, `domain/wounds/rules.py`, `world/systems/wounds.py`
**Current behavior:** `typeclasses/characters.py` is the live state container for stats, resources, profession, race, equipment, injuries, transient states, and compatibility helpers. Position/stance/vitals are persisted directly on the Character object, while wound handling is increasingly routed through `engine/services/injury_service.py` and `domain/wounds/`. Encumbrance and resource side effects are still largely computed from character-held data structures.
**Bundle assignment:** `T0-POSITION`, `T0-STANCE`, `T0-ENGAGEMENT`, `T0-VITALS`, `T0-WOUNDS`, `T0-ENCUMBRANCE`
**Canon mappings:** `canon_stats`, `canon_effects`, GSL posture/engagement/wound scripts (`S00003`, `S00005`, `S00028`, `S00029`, `S00047`, `S00048`), future DireLore-driven wound/healing tuning
**GSL alignment:** `pre_gsl_math_overhaul`
**Extension-API status:** `not_applicable`
**Dependencies:** foundation phase, scheduler/time paths
**Estimated overhaul size:** `large (>800 LOC)`
**Hardcoded-knowledge violations:**
- `typeclasses/characters.py:615` hardcodes `DEFAULT_EQUIPMENT` slot names
- `typeclasses/characters.py:509` hardcodes starter and guild-locked skill visibility inside the Character layer
- `typeclasses/characters.py` uses fixed wound/body-part ordering through `BODY_PART_ORDER` and imported wound constants rather than a registry-driven surface
**Notes:** This is one of the largest consolidation surfaces in the repo. It is foundational for later service extraction but currently mixes engine substrate with profession/race/content assumptions.

## World Interaction Phase

**System / Module:** Movement, inventory, equipment, containers, and perception
**Primary location:** `commands/cmd_go.py`
**Companion files:** `commands/navigation.py`, `commands/cmd_inventory.py`, `commands/cmd_get.py`, `commands/cmd_drop.py`, `commands/cmd_wear.py`, `commands/cmd_remove.py`, `commands/cmd_wield.py`, `commands/cmd_draw.py`, `commands/cmd_stow.py`, `commands/cmd_open.py`, `commands/cmd_look.py`, `commands/cmd_observe.py`, `commands/cmd_perceive.py`, `typeclasses/weapons.py`, `typeclasses/wearables.py`, `typeclasses/sheaths.py`, `typeclasses/wearable_containers.py`, `typeclasses/box.py`
**Current behavior:** The repo has a live inventory/equipment loop with nested containers, wield/wear/remove flows, improvised-weapon fallback behavior, and look/perception commands that already coordinate with room/object presentation. Movement clears transient combat state and interacts with stealth/interest/onboarding systems, but traversal behavior is still spread across command modules and typeclass helpers.
**Bundle assignment:** `T0-MOVEMENT`, `T0-INVENTORY`, `T0-EQUIPMENT`, `T0-CONTAINERS`, `T0-PERCEPTION`
**Canon mappings:** GSL equipment/inventory scripts (`S00023`-`S00027`), `canon_items`, `canon_effects`, zone room/exit data from `map.rooms` and `map.exits`
**GSL alignment:** `pre_gsl_math_overhaul`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** player state phase, foundation phase
**Estimated overhaul size:** `large (>800 LOC)`
**Hardcoded-knowledge violations:**
- `typeclasses/characters.py:615` embeds wearable slot taxonomy inside engine code
- `typeclasses/weapons.py` and `typeclasses/wearables.py` still assume engine-owned item semantics instead of bundle-registered item families
- perception/display behavior still keys directly off room/object state rather than bundle-registered presentation traits
**Notes:** The substrate is live and reusable, but item-family knowledge is still owned by engine code. This phase will need extension points for item templates before paid trade bundles land cleanly.

## Skill Phase

**System / Module:** Skill registry, rank tracking, mindstate, and learning conversion
**Primary location:** `typeclasses/characters.py`
**Companion files:** `world/systems/skills.py`, `engine/services/skill_service.py`, `engine/services/pulse_service.py`, `commands/cmd_skills.py`, `commands/cmd_mindstate.py`, `commands/cmd_train.py`, `world/systems/exp_pulse.py`
**Current behavior:** Skill learning is live and performance-sensitive. `typeclasses/characters.py` hardcodes the main skill registry, starter baselines, and some guild-locked visibility, while `world/systems/skills.py` provides mindstate names, pulse timing, drain math, and event weighting. `engine/services/skill_service.py` and `world/systems/exp_pulse.py` handle mutation and delayed learning conversion.
**Bundle assignment:** `T0-SKILLS`
**Canon mappings:** `canon_skills` (spot-checked at 63 rows), `canon_stats` (10 rows), profession-specific skill visibility from future registry wiring
**GSL alignment:** `gsl_canon_data_missing`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** foundation phase, player state phase
**Estimated overhaul size:** `medium (200-800 LOC)`
**Hardcoded-knowledge violations:**
- `typeclasses/characters.py:509` hardcodes `SKILL_REGISTRY`
- `world/systems/skills.py:30` hardcodes `SKILL_GROUPS`
- `world/systems/skills.py:41` hardcodes first/second/third-wave EXP skill lists
- `engine/services/pulse_service.py:1` imports `SKILL_GROUPS` directly from `world.systems.skills`
**Notes:** The learning loop itself is usable. The main gap is that skill identity and grouping are still engine constants rather than canon-fed registry data.

## Combat Phase

**System / Module:** Combat core, attack resolution, weapon/armor handling, hit areas, and defense
**Primary location:** `engine/services/combat_service.py`
**Companion files:** `domain/combat/rules.py`, `domain/combat/resolution.py`, `engine/services/combat_xp.py`, `engine/services/state_service.py`, `engine/services/injury_service.py`, `commands/cmd_attack.py`, `commands/cmd_advance.py`, `commands/cmd_retreat.py`, `commands/cmd_disengage.py`, `typeclasses/weapons.py`, `typeclasses/armor.py`
**Current behavior:** Combat is live, service-driven, and already split away from some Character methods, but the math is still pre-GSL. `engine/services/combat_service.py` handles target validation, engagement, ranged/ammo flow, post-resolution state, and combat XP. `domain/combat/resolution.py` and `domain/combat/rules.py` resolve hit/miss/damage/critical outcomes. Defense, hit-area, and roundtime behavior are functional today but do not yet reflect the GSL endroll model called for in Phase 4.
**Bundle assignment:** `T0-COMBAT-CORE`, `T0-WEAPONS`, `T0-ARMOR`, `T0-HIT-AREA`, `T0-DAMAGE`, `T0-ATTACK-VERBS`, `T0-DEFENSE`
**Canon mappings:** `gsl.scripts` `S00031`-`S00037`, `S00039`-`S00046`, `S00047`, `S00048`; `canon_items` for weapons/armor; future DireLore item-property import paths
**GSL alignment:** `pre_gsl_math_overhaul`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** player state, world interaction, skills
**Estimated overhaul size:** `large (>800 LOC)`
**Hardcoded-knowledge violations:**
- `engine/services/combat_service.py:11` imports `RANGER_SNIPE_CONFIG` directly from `world.systems.ranger`
- `engine/services/combat_service.py:172`-`176` reads ranger-specific state keys directly during attack context assembly
- `domain/combat/rules.py` owns fixed hit locations and damage assumptions in engine code
- `typeclasses/weapons.py`/`typeclasses/armor.py` still encode engine-owned class/profile behavior instead of item-family registration
**Notes:** This is the first large visible overhaul after DRG-022.5/023. The service/domain split is valuable, but it still contains direct profession coupling that the extension architecture must remove.

## Death and Healing Phase

**System / Module:** Death, wounds, natural recovery, herbs, corpse handling, and resurrection
**Primary location:** `engine/services/injury_service.py`
**Companion files:** `commands/cmd_death.py`, `commands/cmd_die.py`, `commands/cmd_depart.py`, `commands/cmd_tend.py`, `commands/cmd_heal.py`, `commands/cmd_resurrect.py`, `commands/cmd_restore.py`, `commands/cmd_bind.py`, `typeclasses/corpse.py`, `typeclasses/grave.py`, `world/systems/death.py`, `world/systems/wounds.py`
**Current behavior:** The repo has a live death/corpse/recovery loop with bleeding, stabilization, treatment, corpse persistence, and some cleric/empath-facing restoration verbs. `engine/services/injury_service.py` owns scheduled wound/bleed effects; `typeclasses/corpse.py` stores corpse wounds and prep totals; resurrection/recovery flows are exposed through dedicated commands.
**Bundle assignment:** `T0-DEATH`, `T0-WOUND-HEALING`, `T0-EMPATH-INFRA`, `T0-HERBS`, `T0-RESURRECTION`
**Canon mappings:** `canon_effects`, herb/corpse/death GSL scripts, future `canon_items` herb rows, profession spells/abilities for Empath and Cleric healing surfaces
**GSL alignment:** `pre_gsl_math_overhaul`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** player state, combat, magic
**Estimated overhaul size:** `large (>800 LOC)`
**Hardcoded-knowledge violations:**
- `typeclasses/corpse.py:13` hardcodes `DEFAULT_CORPSE_EMPATH_WOUNDS`
- `typeclasses/corpse.py:29` hardcodes `CORPSE_SINGLE_EMPATH_PREP_CAP = 55`
- `commands/cmd_bind.py:18` gates the verb with direct `caller.is_profession("cleric")`
- `commands/cmd_resurrect.py:23` and `commands/cmd_restore.py:18` embed cleric-only assumptions in command logic
**Notes:** Healing and resurrection infrastructure already exists, but profession-specific rules are interwoven directly into commands and corpse handling.

## Magic Phase

**System / Module:** Spell registry, spell access, casting, mana, spell duration, and contest effects
**Primary location:** `domain/spells/spell_definitions.py`
**Companion files:** `engine/services/spell_access_service.py`, `engine/services/spellbook_service.py`, `engine/services/spell_effect_service.py`, `engine/services/spell_contest_service.py`, `engine/services/mana_service.py`, `domain/mana/constants.py`, `domain/mana/rules.py`, `domain/mana/backlash.py`, `commands/cmd_prepare.py`, `commands/cmd_cast.py`, `commands/cmd_stopcast.py`
**Current behavior:** Mana handling, prep/harness/cast flow, cyclic drain, backlash scaffolding, and spellbook access are all present, but spell content is intentionally thin and profession coupling is still direct. `domain/spells/spell_definitions.py` currently hardcodes a small spell registry and a fixed list of spellcasting professions. `engine/services/mana_service.py` contains several profession-specific branches for cleric, moon mage, empath, and warrior mage behavior.
**Bundle assignment:** `T0-SPELL-CIRCLES`, `T0-CASTING`, `T0-SPELL-DURATION`, `T0-SPELL-CATEGORIES`
**Canon mappings:** `canon_spells`, `profession_spells`, `profession_abilities`, `gsl.spells`, GSL casting/backlash script family, `canon_effects`
**GSL alignment:** `pre_gsl_math_overhaul`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** foundation, skills, player state
**Estimated overhaul size:** `large (>800 LOC)`
**Hardcoded-knowledge violations:**
- `domain/spells/spell_definitions.py:31` hardcodes `SPELLCASTING_PROFESSIONS`
- `domain/spells/spell_definitions.py` hardcodes `SPELL_REGISTRY` entries and allowed profession lists
- `engine/services/mana_service.py:301`, `304`, `355`, `758`, `791`, `818` branch directly on specific professions
- `engine/services/spell_effect_service.py:138` uses explicit empath profession checks
**Notes:** Spot-checks confirmed strong canon coverage in DireLore: Ranger 37 spells, Cleric 49, Empath 37, Moon Mage 59. The infrastructure is substantial, but the content and profession model are not bundle-ready yet.

## NPC Infrastructure Phase

**System / Module:** NPC templates, dialog, AI, patrol, and loot-adjacent behavior
**Primary location:** `typeclasses/npcs.py`
**Companion files:** `typeclasses/_guard_npc_impl.py`, `world/systems/guards.py`, `commands/cmd_talk.py`, `server/systems/direlore_npc_import.py`, `world/worlddata/services/import_zone_service.py`
**Current behavior:** The repo has working NPC typeclasses, specialized guards, talk-facing interactions, vendor support, and zone-spawn integration. Guard assist/patrol behavior is live. Dialog and quest handling exist as local patterns rather than a single formal registry.
**Bundle assignment:** `T0-NPC-TEMPLATES`, `T0-DIALOG`, `T0-QUEST-FLAGS`, `T0-CRITTER-AI`, `T0-LOOT`
**Canon mappings:** `canon_shops`, `canon_room_pois`, `entities`, `facts`, future DireLore NPC import paths
**GSL alignment:** `unclear_needs_audit`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** foundation, combat, economy, zone content
**Estimated overhaul size:** `medium (200-800 LOC)`
**Hardcoded-knowledge violations:**
- `typeclasses/npcs.py:675` applies ranger-specific handling inside generic NPC logic
- `typeclasses/npcs.py:731` applies cleric-specific handling inside generic NPC logic
- guard/patrol role semantics remain hardcoded in specialized classes rather than a registry surface
**Notes:** This is a mixed maturity surface: guard AI is live, but generalized dialog/quest/content registration still needs architectural work.

## Economy Phase

**System / Module:** Currency, banking, shopping, lockers, and exchange
**Primary location:** `typeclasses/vendor.py`
**Companion files:** `commands/cmd_shop.py`, `commands/cmd_buy.py`, `commands/cmd_sell.py`, `commands/cmd_haggle.py`, `commands/cmd_appraise.py`, `commands/cmd_deposit.py`, `commands/cmd_withdraw.py`, `commands/cmd_store.py`, `commands/cmd_retrieve.py`, `world/worlddata/vendor_profiles/`
**Current behavior:** Shopping, buy/sell/haggle/appraise, banking, and locker flows exist and are used by live gameplay. Vendor specialization is already more data-driven than most other content surfaces because profile YAML can filter and weight stock, but the core currency and shop contracts remain engine constants.
**Bundle assignment:** `T0-CURRENCY`, `T0-BANKING`, `T0-EXCHANGE`, `T0-SHOPPING`, `T0-LOCKERS`, `T0-MAIL`
**Canon mappings:** `canon_shops`, shop inventory/operator tables, `canon_items`, economy-related GSL scripts, future mail data if present
**GSL alignment:** `pre_gsl_math_overhaul`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** world interaction, NPC infrastructure
**Estimated overhaul size:** `medium (200-800 LOC)`
**Hardcoded-knowledge violations:**
- currency names and denomination handling remain engine-owned in shopping/banking commands
- vendor contract still assumes `db.inventory` and `price_map` rather than a formal bundle registry
- locker semantics are command/typeclass conventions rather than a bundle-neutral service contract
**Notes:** This phase is farther along than crafting, but not yet registry-driven enough for paid trade bundles to plug in safely.

## Crafting Infrastructure Phase

**System / Module:** Crafting registration, recipes, materials, and workstations
**Primary location:** `commands/cmd_rangercraft.py`
**Companion files:** crafting-adjacent helpers are sparse; no unified `world/systems/crafting.py` or recipe registry was found
**Current behavior:** There are scattered profession/trade-adjacent verbs, but no complete shared crafting substrate yet. Tailoring, armor, weapons, alchemy, and fletching are still mostly planning-level concepts from the roadmap rather than implemented systems.
**Bundle assignment:** `T0-CRAFTING-INFRA`
**Canon mappings:** `canon_recipes` family, `canon_items`, trade-specific GSL scripts, future tool/workstation data
**GSL alignment:** `scaffolding_only`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** economy, world interaction, skills
**Estimated overhaul size:** `large (>800 LOC)`
**Hardcoded-knowledge violations:**
- crafting/trade names appear in isolated command surfaces instead of a shared registry
- no extension surface yet exists for free vs paid trades to register recipes/materials/tools
**Notes:** This is one of the clearest examples of a roadmap-defined bundle family that is still mostly absent in code.

## Outdoorsmanship Phase

**System / Module:** Foraging, hunting, skinning, harvesting, fishing, and ranger wilderness actions
**Primary location:** `commands/cmd_forage.py`
**Companion files:** `commands/cmd_hunt.py`, `commands/cmd_harvest.py`, `commands/cmd_skin.py`, `commands/cmd_fishing.py`, `world/systems/fishing.py`, `world/systems/fishing_economy.py`, `world/systems/ranger/instinct.py`, `typeclasses/abilities_survival.py`
**Current behavior:** Outdoorsmanship exists as a cluster of live but uneven systems. Forage/harvest/skin/fishing verbs are present, and the Ranger bundle already owns wilderness-facing mechanics like instinct, companion, snipe, and beseech. Some of this is gameplay-complete enough for current use, but it is still mixed together with profession-specific behavior and pre-GSL math.
**Bundle assignment:** `T0-OUTDOORSMANSHIP`
**Canon mappings:** foraging/hunting/skinning GSL script family, `canon_items` harvestable materials, ranger profession spells/abilities, future recipe/material registration
**GSL alignment:** `pre_gsl_math_overhaul`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** skills, world interaction, combat
**Estimated overhaul size:** `medium (200-800 LOC)`
**Hardcoded-knowledge violations:**
- `world/systems/ranger/instinct.py:77` hardcodes `RANGER_SNIPE_CONFIG`
- `typeclasses/characters.py:15765`-`15777` consumes ranger config directly in generic Character methods
- outdoors/survival loot and reward logic remain engine-owned rather than trade/profession registered
**Notes:** This is partly a Tier 0 substrate problem and partly an early Tier 1 Ranger bundle already baked into engine code.

## Governance and Time Phase

**System / Module:** Justice, law, climate/weather, calendar/time, and GM/admin controls
**Primary location:** `world/systems/justice.py`
**Companion files:** `world/law.py`, `world/weather.py`, `world/calendar.py`, `world/systems/time_model.py`, `commands/cmd_justice.py`, `commands/cmd_payfine.py`, `commands/cmd_weather.py`, admin/debug command modules
**Current behavior:** Justice, fines, and guard coordination exist today, and weather/calendar systems are already fairly substantial. `world/weather.py` stores per-zone weather state and seasonal transitions; `world/calendar.py` and `world/systems/time_model.py` connect runtime time to the Elanthian calendar. GM/debug/admin commands exist across `commands/`.
**Bundle assignment:** `T0-JUSTICE`, `T0-CLIMATE`, `T0-PLANETARY`, `T0-GM-TOOLS`
**Canon mappings:** justice-related GSL script family, climate/weather/calendar scripts, future Moon Mage planetary references, zone climate metadata
**GSL alignment:** `unclear_needs_audit`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** foundation, NPC infrastructure, social/lifecycle
**Estimated overhaul size:** `medium (200-800 LOC)`
**Hardcoded-knowledge violations:**
- `world/law.py:1` begins a law mode constant surface with no external registry
- `world/weather.py:53` hardcodes `WEATHER_STATES`
- lawful-zone and justice assumptions are still local code/config knowledge rather than bundle-registered governance metadata
**Notes:** Governance is live enough to matter but still under-documented compared with combat and wounds. Planetary/lunar behavior is notably underbuilt for future Moon Mage support.

## Familiars Phase

**System / Module:** Familiar/companion infrastructure
**Primary location:** `commands/cmd_companion.py`
**Companion files:** `world/systems/ranger/companion.py`, `typeclasses/npcs.py`
**Current behavior:** The repo has Ranger companion behavior and commands, but not a generic familiar species/control/behavior framework that matches the Phase 4 bundle plan.
**Bundle assignment:** `T0-FAMILIARS`
**Canon mappings:** familiar-related GSL script family (`S00049`-`S00056`), future species/template data
**GSL alignment:** `scaffolding_only`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** NPC infrastructure, outdoorsmanship
**Estimated overhaul size:** `small (<200 LOC)`
**Hardcoded-knowledge violations:**
- Ranger companion handling is the de facto familiar implementation rather than a bundle-neutral familiar registry
**Notes:** This is a small but clear DRG-022.5 target: split generic familiar infrastructure from current Ranger-owned companion behavior.

## Social and Lifecycle Phase

**System / Module:** Social verbs, onboarding, login/logout lifecycle, and early-room flow
**Primary location:** `typeclasses/accounts.py`
**Companion files:** `systems/first_area.py`, `commands/cmd_say.py`, `commands/cmd_whisper.py`, `commands/cmd_channel.py`, `commands/cmd_ask.py`, `commands/cmd_onboarding.py`, `server/conf/at_server_startstop.py`
**Current behavior:** Social verbs are live and standard. Lifecycle/onboarding behavior is customized through account hooks, onboarding commands, and first-area state tracking. Early tutorial/threshold flows are real runtime systems rather than placeholders.
**Bundle assignment:** `T0-SOCIAL-VERBS`, `T0-LIFECYCLE`
**Canon mappings:** social/lifecycle GSL scripts, onboarding/tutorial content is local rather than canon-backed
**GSL alignment:** `unclear_needs_audit`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** foundation, world interaction
**Estimated overhaul size:** `medium (200-800 LOC)`
**Hardcoded-knowledge violations:**
- `systems/first_area.py:5`-`7` hardcodes `OUTER_YARD`, `MARKET_APPROACH`, and `SIDE_PASSAGE`
- `systems/first_area.py` hardcodes named tutorial vendor/item keys like `Street Vendor`, `trail bread`, and `wayfinder token`
- lifecycle/onboarding rooms are embedded as engine assumptions rather than zone-registered tutorial metadata
**Notes:** This is a live content-bearing slice that will need a clean separation between engine lifecycle hooks and bundle-owned onboarding spaces.

## Tier 1 Free Content

**System / Module:** Crossing zone bundle surface
**Primary location:** `worlddata/zones/crossingV2.yaml`
**Companion files:** `worlddata/zones/crossingV2_seeded.yaml`, `worlddata/zones/crossingV2_builder_target.yaml`, `world/worlddata/services/import_zone_service.py`, `server/systems/direlore_item_import.py`, `server/systems/direlore_npc_import.py`
**Current behavior:** The Crossing is already represented as live/importable zone content via YAML worlddata and runtime zone import services. It is the clearest existing free-zone candidate, but it is not yet expressed as a standalone installable bundle module.
**Bundle assignment:** `T1-ZONE-CROSSING`
**Canon mappings:** `map.rooms`, `map.exits`, `canon_room_pois`, `canon_shops`, `gsl.scripts`; sample validation found `The Crossing` 218 rooms and `Crossing` 48 rooms in `map.rooms`, which aligns with the roadmap's combined 266-room target once Crossing subareas are included
**GSL alignment:** `gsl_canon_data_missing`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** foundation, world interaction, NPC infrastructure, economy
**Estimated overhaul size:** `medium (200-800 LOC)`
**Hardcoded-knowledge violations:**
- zone content is stored in repo-local YAML and startup/import conventions rather than a formal zone registration API
- `builderdebug` and AreaForge paths still assume landing/crossing-specific world modules in places
**Notes:** Crossing is the best candidate to prove the future zone-bundle registration surface.

**System / Module:** Human and Elf race profiles
**Primary location:** `world/races/definitions.py`
**Companion files:** `world/races/descriptors.py`, `world/races/hooks.py`, `world/races/utils.py`
**Current behavior:** Races are currently defined in a single hardcoded Python mapping with aliases, stat modifiers, caps, learning modifiers, size categories, and descriptions. Human and Elf are present as starter races, but they live in the same engine registry as all paid races.
**Bundle assignment:** `T1-RACE-HUMAN`, `T1-RACE-ELF`
**Canon mappings:** `canon_races` (spot-checked Human/Elf rows: 2), race feature/descriptor GSL scripts, later language/appearance canon
**GSL alignment:** `gsl_canon_data_missing`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** player state, skills
**Estimated overhaul size:** `medium (200-800 LOC)`
**Hardcoded-knowledge violations:**
- `world/races/definitions.py:65` hardcodes `RACE_DEFINITIONS`
- `world/races/definitions.py` embeds all paid races in the same engine file as free races
**Notes:** This is a direct extension-API target. Free and paid races need to register through the same surface.

**System / Module:** Ranger profession implementation
**Primary location:** `world/systems/ranger/__init__.py`
**Companion files:** `world/systems/ranger/instinct.py`, `world/systems/ranger/companion.py`, `world/systems/ranger/beseech.py`, `commands/cmd_aim.py`, `commands/cmd_blend.py`, `commands/cmd_track.py`, `commands/cmd_mark.py`, `commands/cmd_companion.py`, `engine/services/combat_service.py`, `typeclasses/rooms.py`, `typeclasses/characters.py`
**Current behavior:** Ranger is one of the deepest profession implementations in the repo. It owns wilderness bond/focus, companion handling, snipe/aim/mark behavior, track/follow-trail verbs, and room/combat hooks that already affect core systems.
**Bundle assignment:** `T1-PROF-RANGER`
**Canon mappings:** `profession_spells` (37 rows for Ranger), `profession_abilities` (13 rows for Ranger), ranger GSL scripts, `canon_skills` survival/magic hooks
**GSL alignment:** `pre_gsl_math_overhaul`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** skills, combat, outdoorsmanship, magic
**Estimated overhaul size:** `large (>800 LOC)`
**Hardcoded-knowledge violations:**
- `typeclasses/characters.py:108`-`132` imports ranger modules directly into the Character typeclass
- `engine/services/combat_service.py:11` imports ranger config directly
- `typeclasses/rooms.py:21` imports ranger systems directly and `typeclasses/rooms.py:330` branches on ranger profession
- many commands branch directly on `caller.is_profession("ranger")`, including `cmd_aim.py:33`, `cmd_mark.py:41`, and `cmd_track.py:24`
**Notes:** Ranger is the clearest example of a content bundle currently embedded throughout the engine. DRG-022.5 must account for both module registration and the removal of direct profession imports.

**System / Module:** Cleric profession scaffolding and holy-specialized hooks
**Primary location:** `commands/cmd_commune.py`
**Companion files:** `commands/cmd_bind.py`, `commands/cmd_preserve.py`, `commands/cmd_rejuvenate.py`, `commands/cmd_restore.py`, `commands/cmd_resurrect.py`, `commands/cmd_selfreturn.py`, `commands/cmd_uncurse.py`, `engine/services/mana_service.py`, `typeclasses/characters.py`
**Current behavior:** Cleric has a visible command surface and several specialized mana/devotion/recovery hooks, but much of the profession still lives as gating branches and helper methods rather than a clean subsystem package like Ranger.
**Bundle assignment:** `T1-PROF-CLERIC`
**Canon mappings:** `profession_spells` (49 rows for Cleric), `profession_abilities` (8 rows for Cleric), `canon_professions`, holy/theurgy GSL scripts
**GSL alignment:** `scaffolding_only`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** magic, death/healing, governance
**Estimated overhaul size:** `medium (200-800 LOC)`
**Hardcoded-knowledge violations:**
- command gating is hardcoded across many files: `cmd_commune.py:20`, `cmd_bind.py:18`, `cmd_preserve.py:18`, `cmd_restore.py:18`, `cmd_resurrect.py:23`, `cmd_uncurse.py:18`
- `engine/services/mana_service.py` contains cleric-only devotion/holy realm branches
- `typeclasses/characters.py` contains many direct cleric checks and cleric-specific helper paths rather than a standalone profession module
**Notes:** Cleric is more implemented than a pure placeholder, but it is not yet structured like a content bundle.

**System / Module:** Empath profession implementation and healing/link mechanics
**Primary location:** `world/systems/empath_unlocks.py`
**Companion files:** `commands/cmd_circle.py`, `commands/cmd_channel.py`, `commands/cmd_center.py`, `commands/cmd_diagnose.py`, `typeclasses/corpse.py`, `engine/services/spell_effect_service.py`, `engine/services/state_service.py`, `engine/services/mana_service.py`, `typeclasses/characters.py`
**Current behavior:** Empath is the other deeply implemented starter profession. It has wound transfer, shock/channel/link/unity/circle behavior, corpse prep interactions, and healing modifier hooks that reach into core services.
**Bundle assignment:** `T1-PROF-EMPATH`
**Canon mappings:** `profession_spells` (37 rows for Empath), `profession_abilities` (4 rows for Empath), empath/healing GSL scripts, `canon_effects`
**GSL alignment:** `pre_gsl_math_overhaul`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** death/healing, magic, player state
**Estimated overhaul size:** `large (>800 LOC)`
**Hardcoded-knowledge violations:**
- `commands/cmd_circle.py:53` hardcodes empath-only circle behavior in command logic
- `commands/cmd_channel.py:21` branches on `is_empath()` directly
- `engine/services/spell_effect_service.py:138` and `engine/services/state_service.py:528`-`541` have explicit empath hooks in shared services
- `typeclasses/corpse.py` embeds empath-specific corpse wound handling
**Notes:** Empath already justifies its own bundle, but it currently leaks into generic services and corpse mechanics.

**System / Module:** Tailoring trade surface
**Primary location:** no dedicated tailoring module found
**Companion files:** clothing/equipment flows live under `typeclasses/wearables.py` and `typeclasses/characters.py`; no formal tailoring recipe registry was found
**Current behavior:** Tailoring exists as roadmap scope, not as a finished system. Clothing/equipment support exists, but recipe/material/tool/workstation behavior does not yet appear as a standalone trade implementation.
**Bundle assignment:** `T1-TRADE-TAILORING`
**Canon mappings:** `canon_recipes` family, `canon_items`; spot-check on `canon_items` found zero `item_type='clothing'` rows, which suggests Tailoring canon coverage likely sits in recipe/material tables rather than the current item snapshot
**GSL alignment:** `scaffolding_only`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** crafting infrastructure, economy, world interaction
**Estimated overhaul size:** `medium (200-800 LOC)`
**Hardcoded-knowledge violations:**
- clothing support exists only as item/equipment behavior, not as a registered trade module
**Notes:** Tailoring is mostly a planned free bundle at this point; DRG-022.5 should not assume an existing trade registry.

## Tier 2 Paid Content Scaffolding

**System / Module:** Paid profession registry and profession-coupled command/service surfaces
**Primary location:** `world/professions/professions.py`
**Companion files:** `typeclasses/characters.py`, `engine/services/mana_service.py`, `commands/cmd_berserk.py`, `commands/cmd_roar.py`, `commands/cmd_recover.py`, `commands/cmd_khri.py`, `world/khri.py`, `world/systems/warrior/`
**Current behavior:** All paid professions are already present in the runtime profession registry, and some paid/proto-paid surfaces exist through warrior and thief-adjacent mechanics. However, there is no bundle registration layer, and several professions exist only as names plus scattered command gating.
**Bundle assignment:** `T2-PROF-MOONMAGE`, `T2-PROF-PALADIN`, `T2-PROF-BARBARIAN`, `T2-PROF-WARMAGE`, `T2-PROF-BARD`, `T2-PROF-THIEF`, `T2-PROF-TRADER`, `T2-PROF-NECROMANCER`
**Canon mappings:** `canon_professions`, `profession_spells`, `profession_abilities`; sample validation confirmed Moon Mage 59 spells and 22 abilities in DireLore
**GSL alignment:** `scaffolding_only`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** DRG-022.5 extension architecture, magic, combat, economy
**Estimated overhaul size:** `large (>800 LOC)`
**Hardcoded-knowledge violations:**
- `world/professions/professions.py:16` hardcodes all professions, including paid ones, in `PROFESSION_PROFILES`
- `engine/services/mana_service.py:304` and `355` already know about `warrior mage` and `moon mage`
- `commands/cmd_berserk.py:23`, `cmd_roar.py:24`, `cmd_recover.py:44`, and `cmd_thug.py:68` gate profession-specific behavior directly in commands
**Notes:** This is the biggest DRG-022.5 work surface. Paid professions are present on disk today even though the Phase 4 directive forbids that end state.

**System / Module:** Paid race registry scaffolding
**Primary location:** `world/races/definitions.py`
**Companion files:** `world/races/hooks.py`, `world/races/descriptors.py`
**Current behavior:** Paid races are already defined alongside starter races with stats, caps, carry modifiers, and descriptions, but there are no paid-race modules or extension points yet.
**Bundle assignment:** `T2-RACE-HALFELF`, `T2-RACE-DWARF`, `T2-RACE-GNOME`, `T2-RACE-HALFLING`, `T2-RACE-SKRAMUR`, `T2-RACE-PRYDAEN`, `T2-RACE-RAKASH`, `T2-RACE-KALDAR`, `T2-RACE-GORTOG`
**Canon mappings:** `canon_races`, future language/appearance/culture canon
**GSL alignment:** `gsl_canon_data_missing`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** player state, skill registry, extension architecture
**Estimated overhaul size:** `medium (200-800 LOC)`
**Hardcoded-knowledge violations:**
- `world/races/definitions.py:65` puts all paid race definitions in engine code
- race aliases are hardcoded in the same module instead of a registry input layer
**Notes:** This is structurally simpler than professions, but it is still a direct bundle-boundary violation.

**System / Module:** Paid zone scaffolding and zone-name assumptions
**Primary location:** `world/the_landing.py`
**Companion files:** `world/area_forge/run.py`, `builderdebug/world/area_forge/run.py`, `systems/aftermath.py`, `server/conf/at_server_startstop.py`, `worlddata/zones/`
**Current behavior:** The repo has live Landing/Crossing-zone assets and builder flows, but not the wider set of paid city/region bundles from the roadmap. The most obvious current zone assumptions are hardcoded around `new_landing`, Crossing YAMLs, and guild-map cache IDs.
**Bundle assignment:** paid zone family beginning with `T2-ZONE-RIVERHAVEN` and extending through the roadmap zone list
**Canon mappings:** `map.rooms`, `map.exits`, `canon_room_pois`, `canon_shops`, area dataset in DireLore
**GSL alignment:** `scaffolding_only`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** extension architecture, zone registration API, NPC/economy subsystems
**Estimated overhaul size:** `large (>800 LOC)`
**Hardcoded-knowledge violations:**
- `world/the_landing.py:476`, `1255`, `1414` hardcode `area_id="new_landing"`
- `server/conf/at_server_startstop.py:69` hardcodes `LANDING_AREA_ID = "new_landing"`
- `world/area_forge/run.py:31` and `58` import `world.the_landing` directly
**Notes:** Zone content already exists in workable forms, but bundle installability/removability will require a proper zone registry and startup indirection.

**System / Module:** Paid trade scaffolding
**Primary location:** no dedicated paid-trade modules found
**Companion files:** trade-adjacent vendor profile YAMLs and general item/equipment systems only
**Current behavior:** Armor, weapons, alchemy, and fletching are roadmap-defined paid trades, but they are not implemented as standalone subsystems yet.
**Bundle assignment:** `T2-TRADE-ARMOR`, `T2-TRADE-WEAPONS`, `T2-TRADE-ALCHEMY`, `T2-TRADE-FLETCHING`
**Canon mappings:** `canon_recipes` family, `canon_items`, trade-specific GSL scripts
**GSL alignment:** `scaffolding_only`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** crafting infrastructure, economy
**Estimated overhaul size:** `large (>800 LOC)`
**Hardcoded-knowledge violations:**
- no shared trade registry exists yet; future paid trades would have to land directly in engine code if implemented today
**Notes:** This family is blocked behind crafting infrastructure and extension-point work.

## Tier 3 Premium

**System / Module:** Premium festivals, auction, and CHE/society systems
**Primary location:** no active implementation surface found
**Companion files:** none identified beyond roadmap/planning references
**Current behavior:** Tier 3 remains planning-only in this repo. No auction subsystem, premium-points system, or festival implementation surfaced during the walk.
**Bundle assignment:** `T3-EVENT-HOLLOWEVE`, `T3-EVENT-DROGOR`, `T3-EVENT-FEAST`, `T3-AUCTION`, `T3-PREMIUM`
**Canon mappings:** event/auction/premium GSL script families, DireLore event/system data when available
**GSL alignment:** `scaffolding_only`
**Extension-API status:** `hardcoded_in_engine`
**Dependencies:** extension architecture, economy, social/lifecycle, governance
**Estimated overhaul size:** `medium (200-800 LOC)`
**Hardcoded-knowledge violations:**
- none in code yet; the violation here is absence of any premium registration surface
**Notes:** Premium work is correctly late in the Phase 4 order; there is no reason to touch it before the extension architecture exists.

## Aggregate Findings

Audit totals:

- Systems audited: 18 grouped entries spanning all Tier 0 phases plus Tier 1, Tier 2, and Tier 3 content surfaces
- `gsl_aligned`: 0
- `gsl_canon_data_missing`: 4
- `pre_gsl_math_overhaul`: 9
- `scaffolding_only`: 7
- `unclear_needs_audit`: 3
- Estimated overhaul sizes: 1 small, 8 medium, 9 large
- Blended total overhaul footprint implied by the current state: approximately 13k-17k LOC across Phase 4 follow-on dispatches

Highest-priority DRG-022.5 findings:

1. `world/professions/professions.py:16` hardcodes all free and paid professions in-engine.
2. `world/races/definitions.py:65` hardcodes all free and paid races in-engine.
3. `typeclasses/characters.py:509` and `world/systems/skills.py:30` hardcode skill identity/grouping instead of reading from canon-fed registries.
4. `domain/spells/spell_definitions.py:31` and `engine/services/mana_service.py` keep spellcasting-profession knowledge inside shared engine code.
5. `engine/services/combat_service.py:11` and multiple command/typeclass files import or branch on Ranger directly, proving profession code still lives in the engine.
6. `server/conf/at_server_startstop.py` and `world/the_landing.py` hardcode named zones (`new_landing`, guild-map IDs), which blocks graceful zone bundle absence.

Likely Phase 4 ordering impact:

- The current roadmap sequence still holds. Nothing in this walk suggests DRG-022.5 should move later; the opposite is true. The number of profession/race/zone assumptions inside generic engine code makes extension-point work a hard prerequisite for almost every visible overhaul.
- DRG-023 remains the correct next step after DRG-022.5 because the skill/race/profession registries are ready to benefit from canon-fed data as soon as the registration surface exists.

No production code was changed during this dispatch.