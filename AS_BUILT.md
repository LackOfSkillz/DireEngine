# Dragons Ire As-Built

## Purpose

This document is the current implementation snapshot for the running game and supporting toolchain in this repository.

Use it to answer:

- what is live today beyond stock Evennia
- where the major systems live in the codebase
- how the server currently boots and runs
- which areas are implemented, partially implemented, or scaffolding-first

## Build Summary

- Base platform: Evennia on Python 3.11
- Web stack: Django through Evennia
- Primary player surface: custom browser client
- Secondary client surface: Godot client workspace with websocket bridge
- World target: DragonRealms-inspired text gameplay with modern client support, structured state updates, and map-assisted play

## Webclient Lifecycle Snapshot

- The live browser client is a DireEngine-owned template and static override on top of Evennia's stock webclient routing, not a stock Evennia shell.
- Loopback web navigation is now canonicalized to `localhost` from both the website base template and the webclient base template so dev browsing does not split Django session cookies across `127.x` variants.
- Disconnected browser state now suppresses the draggable right rail before the reconnect controls render, which keeps the reconnect surface reachable in the narrow attached-browser viewport used for dispatch verification.
- Browser-side recovery no longer depends on a JS console call. The client now treats the authenticated `/play` route as the canonical session recovery seam when reconnect attempts stall, which preserves the selected-character bridge used by the website dashboard and auto-puppet hooks.
- DRG-WEBCLIENT-002 hardens that recovery seam: `sendCommand()` now guards on `Evennia.isConnected()`, queues disconnected user commands instead of fake-echoing them as sent, and drains queued user input only after reconnect succeeds.
- Bootstrap refresh now follows the same transport discipline: `requestInitialRefresh()` defers through `initialRefreshPending` while disconnected, only latches `initialRefreshSent` when the bootstrap commands are actually delivered, and drains bootstrap before queued user commands on `connection_open`/`logged_in`.
- Manual reconnect on recovered `/play` sessions is now verified across repeated full `startWeb.bat` restarts; any remaining live browser smoke failures after reconnect are no longer handshake defects by default and should be treated as downstream runtime issues unless the connection state regresses.

## Current Architecture

The active architecture is no longer just `commands -> typeclasses`.

Current direction:

- `commands/` is the command-entry layer
- `engine/services/` owns orchestration and mutation authority for newer systems
- `domain/` owns pure rules and data helpers where extraction has already happened
- `typeclasses/` remains the live Evennia object layer, persistence surface, and compatibility bridge
- `world/` contains professions, system modules, AreaForge, bootstrap code, and broader gameplay helpers

Current extracted service/domain areas include:

- `engine/services/combat_service.py`
- `engine/services/state_service.py`
- `engine/services/skill_service.py`
- `engine/services/rexp_service.py`
- `engine/services/injury_service.py`
- `engine/services/pulse_service.py`

## Magic Runtime Snapshot

- The structured spell registry in `domain/spells/spell_definitions.py` now distinguishes prototype fixtures from canonical catalog entries through `canon_status`, and spell data now carries explicit `mana_min`, `mana_max`, `min_prep_time`, and `expiry_window` metadata instead of relying on timing-only bridge defaults.
- Cast resolution now follows the GSL Magic v2.1 control-versus-difficulty model in `domain/mana/backlash.py`: primary magic is scaled internally, total difficulty scales from `base_difficulty` plus `diff_per_extra_mana`, and failed casts now distinguish clean fizzles from true backlash by comparing scaled control against base and total difficulty rather than by the older heuristic strain model.
- The follow-up profession correction keeps that canon math honest: the GSL `MANADIFF` caller-context branch is treated as an effective-skill penalty, so commoner/barbarian casters now resolve at 50% scaled skill and thief/trader at 80% instead of receiving an inverted buff.
- Prepared spell state now preserves the full cast-math profile through `typeclasses/characters.py` and `engine/services/mana_service.py`, including `mana_min`, `mana_max`, `diff_per_extra_mana`, and per-spell `provenance`, so the live cast seam no longer drops canonical scaling inputs before resolution.
- Canonical spell definitions now also carry `slot_cost` and `apprentice_until_circle`, so permanent memorization cost and derived apprentice access live in the registry rather than in ad hoc command logic.
- DRG-024.5a's lifecycle remains authoritative: `prepare` forms the pattern without spending attunement, `cast` spends intended mana and any released harnessed mana, full-prep and prepared-expiry still run through the scheduler-backed `ManaService` seams, and `typeclasses/characters.py` continues to sync the player-facing prepared state from mana-state authority.
- Four canonical Analogous Patterns starter spells are now live in the registry: `burden` (debilitation), `gauge_flow` (utility), `strange_arrow` (targeted magic), and `manifest_force` (warding).
- Those four starter spells are now treated as a narrow repo-canon exception set rather than as generic 2004 GSL spell promotions: their live effects remain intact, their registry entries are recalibrated to low starter-style base difficulty, and each carries explicit `provenance="magic_3_0_design"` so the grandfathered exception is visible in code.
- The Analogous Patterns registrations now match canon instead of the earlier provisional model: Burden, Strange Arrow, and Manifest Force derive apprentice access through circle 10, Gauge Flow no longer does, and the four seeded spells currently in repo carry slot costs of 1/2/1/1 respectively.
- Debilitation effects can now carry stat debuffs and encumbrance modifiers through the existing `active_effects["debilitation"]` model, so Burden reduces Strength and increases carried burden without introducing a parallel debuff store.
- Utility effects can now carry capability-flag payloads through `engine/services/state_service.py`, which DRG-024.5b uses for Gauge Flow's `gauge_flow_active` state while the downstream magical-research system remains deferred.
- Targeted magic now supports mixed typed damage payloads in `engine/services/spell_contest_service.py`, so Strange Arrow resolves as puncture plus electrical damage while still routing wound application through the existing typed damage path.
- Physical warding now distinguishes magic-only and physical-only barriers inside the shared state model: Manifest Force stores `absorbs_physical`, mirrors into `physical_barrier`, and is consumed in `domain/combat/resolution.py` after armor reduction but before wound shaping, while existing prototype wards remain magic-only.
- `engine/services/slot_service.py` now owns the generic `db.magic_slot_pool` surface. Max slots are derived from profession magic-skillset placement and circle, allocations are keyed by category, and spells are only the first consumer of the shared pool ahead of deferred magical feats.
- DRG-RUNTIME-001 adds a bootstrap safety rule to that slot service: slot-pool max computation reads persisted `db.circle` directly inside `SlotService._get_circle()` rather than calling `Character.get_circle()`, so legacy magic users with `magic_slot_pool=None` can self-heal their pool on first access without re-entering `ensure_core_defaults()` and recursing.
- DRG-024.5d-2 is now live on that shared pool: `domain/feats/feat_definitions.py` registers a dedicated feat catalog, `engine/services/feat_training_service.py` allocates learned feats into `allocations["feats"]`, and profession-granted feats remain slot-free in `db.feats["granted"]`.
- Eight magical feats are now implemented end-to-end: the original starter set (`deep_attunement`, `efficient_harnessing`, `focused_preparation`, `faster_battle_preparations`, `faster_matrices`, `cautious_casting`, and `efficient_channeling`) plus `raw_channeling` as the first capability-unlock feat in the catalog.
- Passive feat modifiers are threaded through the existing live seams rather than through a parallel buff system: attunement regeneration, harness/cast attunement spend, prepared expiry, prep-time metadata, cyclic upkeep drain, and backlash vitality loss all now consult `engine/services/feat_service.py` and preserve identity behavior when no feats are known.
- DRG-024.5d-3a corrects cyclic upkeep to the canon sustain model: active cyclic payloads now carry `sustain_source` and optional `sustain_ref`, cyclic casts prefer held harnessed mana by default, attunement-direct sustain only becomes legal through Raw Channeling, and cambrinth sustain is schema-supported but currently returns a clean deferred-subsystem error until the item-side subsystem lands.
- Cyclic upkeep no longer routes through generic attunement spend. `ManaService.consume_mana_for_cyclic()` now dispatches by sustain source, applies Efficient Channeling regardless of source, applies Efficient Harnessing only for attunement-direct sustain, and collapses cyclic effects with source-specific reasons when held mana, attunement, or Raw Channeling availability runs out.
- The live cyclic runtime now enforces canon's single-active-cyclic rule. Starting a second cyclic fails privately before cast-time mana spend or prepared-state clearing, and explicit `release cyclic` remains the authority surface for changing sustained patterns.
- Live smoke fixtures now need to be normalized through the EXP-skill persistence seam rather than the older `Character.update_skill()` helper when the target skills are EXP-backed. For `SmokeClericLive` and `SmokeEmpathLive`, durable browser-smoke rebalancing used the EXP handler plus `_persist_exp_skill_state(...)` to pin `cyclic`, `attunement`, `arcana`, `debilitation`, `targeted_magic`, `healing`, and `scholarship` at rank 50.
- The skill/learning registry now covers the runtime magic skills that browser smoke exercises directly: `cyclic` and `healing` are first-class `magic` skills in `SKILL_REGISTRY`, and `Character.get_skill_entries()` now sorts legacy uncategorized positive-rank rows safely instead of crashing `health`/`stats` on mixed `None`/`str` category data.
- Deterministic wound setup for browser healing smoke now exists through `commands/cmd_woundadmin.py`: `@wound <target> <part> <external> <internal> <bleed>` writes a body-part injury, recomputes the summary vitality/bleeding buckets used by `health`, updates bleed state, and syncs client state.
- Recovered `/play` browser smoke is now live-green on the current maintenance matrix: `spells`, `slots`, and `feats` render cleanly, Gauge Flow, Manifest Force, and Strange Arrow complete end-to-end, wounded Regenerate now sustains and heals correctly on `SmokeEmpathLive`, and Burden applies correctly on a living target after fixture normalization. The earlier local `/auth/login` failure was traced to stale in-memory Account cache after shell-side password changes; a clean Evennia restart is the required recovery step for that operational seam.
- Player-facing feat surfaces are now live: `feats` lists learned, granted, and currently available feats; `learn feat <name>` and `forget feat <name>` transact through the first Landing feat trainer, `Instructor Sariel`, in `The Hall of Arcane Refinement` off Town Green NE.
- Permanent spell learning is now slot-gated in `engine/services/spellbook_service.py`, while `engine/services/spell_access_service.py` derives apprentice access fresh from profession plus circle plus spell metadata instead of persisting apprentice spells into `db.spellbook`.
- Circle advancement now recomputes slot maxima and privately communicates apprentice transitions: magic users receive a circle-10 warning for unmemorized apprentice spells and lose derived access at circle 11 unless the spell was permanently memorized.
- Player-facing slot visibility now exists through `slots` and `spells`: `commands/cmd_slots.py` reports max/used/available pool state and per-category allocations, and `commands/cmd_spellbook.py::CmdSpells` distinguishes permanent memorization from apprentice access.
- Existing prototype spells such as `flare` and `storm_field` remain in place as regression fixtures and are now explicitly distinguishable from the canonical seed catalog rather than being silently treated as equivalent content.

## Learning Runtime Snapshot

- Live EXP persistence remains the existing `SkillState` plus `Character.db.exp_skill_state` seam; newer learning work does not introduce a parallel `db.skill_states` model.
- The canonical 20-second EXP pulse still flows through `world/systems/exp_pulse.py` into `engine/services/pulse_service.py`, now with sleep-aware handling: Light Sleep continues absorption, Deep Sleep suspends pulse drain, and rested EXP can triple a draining group's absorption rate when banked time is available.
- `engine/services/rexp_service.py` owns rested EXP banking, the 4-hour cap, the 23.5-hour consumption cycle, and static offline drain on login via `Character.at_post_puppet()` / `at_post_unpuppet()` timestamps.
- Player-facing sleep state now lives on `Character.db.sleep_state` with `sleep` and `awake` commands, automatic wake-on-action for most commands, and rested EXP visibility on the `experience` command.
- `typeclasses/characters.py::SKILL_REGISTRY` is now the authoritative live skill-identity table: every entry carries `category`, `visibility`, `display_name`, `description`, and `starter_rank`, with lowercase underscore keys used as the runtime skill IDs.
- Defense learning identities now exist as first-class skills: `shield_usage`, `parry_ability`, and `multiple_engaged_opponent` live under the `defense` category and drain through the canonical pulse rotation like other non-guild-locked skills.
- `domain/learning/skill_aliases.py` and `domain/learning/skill_groups.py` are aligned against that registry, so pulse groups no longer silently no-op on missing skill IDs and group 9 is intentionally reserved empty for future profession-specific skill dispatches.
- `engine/services/stat_training_service.py`
- `engine/services/circle_service.py`
- `engine/services/messaging.py`
- `engine/services/result.py`
- `engine/services/errors.py`
- `engine/contracts/combat_result.py`
- `domain/combat/hit_area.py`
- `domain/combat/damage.py`
- `domain/combat/armor.py`
- `domain/combat/wounds.py`
- `domain/combat/cleanup.py`
- `domain/combat/rules.py`
- `domain/wounds/constants.py`
- `domain/wounds/models.py`
- `domain/wounds/rules.py`
- `domain/learning/skill_aliases.py`
- `domain/learning/mindstate.py`
- `domain/learning/skill_groups.py`
- `domain/learning/pool_size.py`
- `domain/learning/tdp_cost.py`

This is still a transitional architecture. Not every gameplay surface has been extracted yet, but combat, state mutation, and wound handling now have a formal service/domain path.

Combat now routes its post-penetration path through source-backed hit-area, damage, armor, wound, and cleanup helpers aligned to the verified GSL scripts for DRG-024a.
Combat verb routing now also follows a canonical shared table in `domain/combat/verbs.py`, with command-layer dispatch flowing through `engine/services/attack_verb_service.py` into `CombatService.attack()`.
Defensive stance routing now mirrors that pattern: `parry` and `dodge` flow through `commands/cmd_defense_verbs.py` and `engine/services/defense_verb_service.py`, persist canonical maneuver IDs on `Character`, and feed the S09449 defender-scaling table used by `domain/combat/resolution.py`.

## Combat Test Infrastructure

- `commands/cmd_spawndummy.py` adds an in-band combat smoke helper for live browser validation.
- `spawndummy` creates an unarmored training dummy in the caller's room.
- `spawndummy armored` creates an armored dummy using the existing `NPC` and `Armor` typeclasses, avoiding cross-process shell staging for browser combat tests.
- Use these in live web-client validation instead of `python -m evennia shell` object creation when the goal is to verify browser-visible world state.
- `commands/cmd_combatreset.py` adds `combatreset <character>` as an admin combat-state reset helper for dev testing.
- `combatreset` resets a character to a clean combat baseline through `Character.combat_reset_state()`, clearing combat flags, wounds, roundtime, dead-state metadata, and linked corpse references.
- `combatreset` now finishes through `Character.sync_state_to_client()`, an explicit wrapper over the existing structured browser sync path.
- The permanent `drginfraadmin` account and `InfraAdmin` character exist as a secondary dev actor for cases where the primary browser session is impaired and cannot safely drive its own recovery commands.
- Use `InfraAdmin` for in-band admin actions such as `combatreset`, `spawndummy`, and other out-of-band smoke control from a second session; keep the credential in private repo notes rather than public-facing docs.
- The authoritative live sync path is `CombatService` and `StateService` mutating Character state through setters that call `Character.sync_client_state()`, which sends structured `character` and `subsystem` payloads consumed by the browser client.
- Browser dead-state command gating is enforced by `Character.execute_cmd()` and `Character.can_execute_while_dead()`, so `combatreset` and `cmbreset` are allowlisted there as well as in the command base.
- Live validation confirmed a dead browser session could be reset back to clean alive presentation in the same session, with no logout required, and could immediately execute `look` afterward.

## DRG-024c - Player Defense Commands (Parry, Dodge)

- Canonical maneuver IDs now live in `domain/combat/maneuvers.py`, including the S09449 defender scaling table keyed by the actor's persisted `last_maneuver`.
- `Character` now persists `last_maneuver` across combat actions, and both attack and defense verb services update it when a maneuver is committed.
- `parry` and `dodge` now exist as first-class combat commands with the canon-specific duplicate-stance guard messages and 3-4 second defensive positioning RT.
- Combat resolution now applies defender last-maneuver scaling to evasion, parry, and shield calculations instead of treating those defenses as stance-agnostic.
- Defense XP now follows the canonical defense identities instead of the older bridge: parry results train `parry_ability`, shield results train `shield_usage`, and opportunistic multi-opponent pressure trains `multiple_engaged_opponent` off the transient `incoming_attackers` counter while preserving the existing combat messaging and attacker miss-XP behavior.

## Runtime Boot Behavior

Primary file:

- `server/conf/at_server_startstop.py`

Current startup behavior includes:

- enabling scoped periodic server work instead of a single heavy legacy sweep
- startup and bootstrap of live world content for The Landing
- Brookhollow justice configuration and lawful-space setup
- guard-space and enforcement-space preparation
- training-space maintenance for local testing
- wound scheduling bootstrap through `InjuryService`
- zone map cache priming support via AreaForge map APIs

Key runtime settings in `server/conf/settings.py`:

- `AT_SERVER_STARTSTOP_MODULE = "server.conf.at_server_startstop"`
- custom account and character typeclasses
- custom telnet protocol class with MCCP disabled
- Godot websocket portal plugin enabled
- Godot websocket port `4008`

## Code Layout

- `commands/`: player verbs, admin/debug commands, onboarding commands, combat entries, and profession-facing verbs
- `typeclasses/`: characters, rooms, exits, objects, corpses, graves, NPCs, weapons, armor, spells, containers, and behavior integration
- `engine/`: service-layer orchestration and typed contracts
- `domain/`: pure combat and wound rules
- `world/`: professions, races, languages, law, systems, world bootstrap, AreaForge, and area support
- `systems/`: onboarding and tutorial scripting
- `web/`: custom browser client templates and static assets
- `godot/`: Godot client workspace and websocket-facing client experiments
- `tests/`: focused service/domain tests and other coverage
- `tools/`: architecture audit, simulation suites, and maintenance utilities
- `artifacts/`: stored DireTest and scenario outputs

## Player-Facing Systems

### Character State And Presentation

Primary file:

- `typeclasses/characters.py`

Current state:

- centralized persistent-field backfill through `ensure_core_defaults()` and related helpers
- stats, skills, resources, profession, death, injury, and subsystem state stored on Character
- spendable TDP progression now persists on Character, with `grant_tdp()` for rank and circle rewards and `spend_tdp()` for stat training
- custom condition, equipment, and character-state presentation
- structured sync hooks for browser and client state updates

### Learning, Stat Training, And Circle Projection

Primary files:

- `commands/cmd_experience.py`
- `commands/cmd_stat_info.py`
- `commands/cmd_train.py`
- `commands/cmd_study.py`
- `engine/services/stat_training_service.py`
- `engine/services/circle_service.py`
- `domain/learning/skill_aliases.py`

Current state:

- the direct stat commands (`strength`, `stamina`, `agility`, `reflex`, `charisma`, `discipline`, `wisdom`, `intelligence`) now expose current stat value, racial training modifier, next-rank TDP cost, and a short gameplay-facing effect summary
- `train` and `study` are now location-sensitive learning verbs: in The Landing stat trainer rooms they consult and commit TDP-based stat raises, while at active guild leaders they project and commit circle advancement
- trainer consults, trainer commits, guildleader circle previews, and circle commits now emit explicit room-visible observer lines through the shared action-messaging helper instead of staying actor-only
- `experience` remains the authoritative learning surface and now supports `exp <skill>` detail lookups plus `exp circle` projection
- the live EXP runtime now consumes canonical learning helpers: the full 35 mindstates in `domain/learning/mindstate.py`, the canonical 10 pulse groups in `domain/learning/skill_groups.py`, and the modern pool-size plus wisdom helpers in `domain/learning/pool_size.py`
- the live skill identity layer now routes `exp` display through registry-backed `display_name` metadata, so merged abstractions such as `light_edge` present as `Light Edged Weapons` and defense aliases resolve to dedicated defense skills instead of the older combat bridge
- profession metadata now carries the authoritative primary/secondary/tertiary skillset placement tables in `world/professions/professions.py`, and transient EXP tier routing now consumes those tables directly instead of the older override-first fallback
- the old 10-second global learning ticker has been reduced to teaching-only work in `server/conf/at_server_startstop.py`; the retired `process_learning_pulse()` branch is no longer invoked during server startup wiring
- EXP pulses now run on the canonical 10-group 200-second rotation, private mindstate milestone notifications fire at higher absorption thresholds, and mind-locked skills reject new XP while still draining through the normal pulse
- `exp parry`, `exp shield`, and `exp moe` now resolve to `parry_ability`, `shield_usage`, and `multiple_engaged_opponent`, and live combat resolution plus combat XP routing now feed those same canonical defense identities directly
- circle advancement currently uses explicit placeholder requirements keyed to total skill ranks plus `db.coins`; the service is structured so canon per-guild requirement tables can replace the placeholder math without changing command routing

### Combat And Action Pacing

Primary files:

- `commands/cmd_attack.py`
- `commands/cmd_attack_verbs.py`
- `commands/cmd_advance.py`
- `commands/cmd_retreat.py`
- `commands/cmd_disengage.py`
- `commands/cmd_target.py`
- `commands/cmd_combatreset.py`
- `domain/combat/verbs.py`
- `engine/services/attack_verb_service.py`
- `engine/services/combat_service.py`
- `engine/services/state_service.py`
- `domain/combat/rules.py`
- `engine/presenters/combat_presenter.py`

Implemented behavior:

- target-based combat flow
- range and engagement handling
- roundtime pacing
- canonical attack verbs for `thrust`, `lunge`, `slice`, `chop`, `sweep`, `feint`, and `jab`
- verb-specific base roundtimes from S00031-S00037 threaded through `CombatService.attack()`
- slice pre-hit defender hook support through `on_attack_attempt(..., verb="slice")`
- chop terrain guard for `trees` and `vines` when no choppable room target exists
- feint fallback to the caller's current engagement target when no explicit target is supplied
- NPC combat behavior follows `event -> set target -> ai_tick acts on target`, where room-entry presence and damage hooks establish targets and the existing global NPC tick drives continued attacks and disengage cleanup
- same-room guard assist is event-driven as well: assist-capable NPCs join when a nearby guard acquires a player target, then the existing target state and ai tick handle the rest
- NPC threat tracking is layered on top of that same loop as runtime combat state: damage and assist add threat, ai tick can switch to the top valid threat, and threat is cleared when combat fully disengages
- action-facing combat messaging now uses a shared three-audience helper for command and presenter surfaces, so actor, defender, and observers can receive intentionally distinct lines without duplicating room-broadcast plumbing
- presenter miss messaging now distinguishes full parries, full shield blocks, evasions, and generic misses; hit narration also adds observer-visible armor mitigation and higher-force impact lines

### Vendors And Stock Generation

Current state:

- vendors still sell through the existing `db.inventory` and `price_map` contract used by `shop` and `buy`
- vendor specialization is now profile-driven through `world_data/vendor_profiles/`
- item YAML supports `weapon_class`, `tags`, and `level_band`, allowing one generator to produce guild-specific stock without duplicating vendor logic
- vendor profiles can filter and weight weapon classes while still feeding the current shop interface and purchase flow
- weapon-profile-driven offense
- fatigue and balance pressure
- NPC retaliation and combat cleanup
- service-driven damage application into HP and wound consequences

Current state:

- live and central to moment-to-moment gameplay
- partially consolidated into the new service layer

### Wounds, Bleeding, And Treatment

Primary files:

- `engine/services/injury_service.py`
- `domain/wounds/`
- `commands/cmd_injuries.py`
- `commands/cmd_tend.py`
- `typeclasses/characters.py`

Implemented behavior:

- body-part injury tracking
- trauma severity and bleed-state handling
- wound-aware combat consequences
- scheduled bleed and natural recovery support
- stabilization and tending flows
- player-facing injury display lines and penalties

Current state:

- live and integrated into combat and recovery
- newly consolidated under a formal wound domain and service layer

### Death, Corpses, Graves, Favor, And Recovery

Primary files:

- `commands/cmd_depart.py`
- `commands/cmd_death.py`
- `commands/cmd_resurrect.py`
- `commands/cmd_stabilize.py`
- `commands/cmd_restore.py`
- `commands/cmd_bind.py`
- `typeclasses/corpses.py`
- `typeclasses/graves.py`
- `typeclasses/characters.py`

Implemented behavior:

- alive, dead, and departed state handling
- corpse creation and corpse recovery flow
- grave creation and grave recovery support
- favor-tracked recovery pressure
- depart-mode handling
- resurrection-facing command flow and recovery fragility

Current state:

- live core loop, not placeholder-only
- still open to tuning and further balance depth

### Skills, Mindstate, XP, And Learning

Primary files:

- `world/systems/skills.py`
- `engine/services/skill_service.py`
- `commands/cmd_skills.py`
- `commands/cmd_mindstate.py`
- `commands/cmd_use.py`
- `world/systems/exp_pulse.py`

Implemented behavior:

- central skill registry
- skill rank and mindstate tracking
- delayed learning conversion
- modern DR TDP persistence with a shared hidden 200-point pool
- rank-up TDP accrual wired at the authoritative `process_rank()` seam
- player-facing `tdp` command plus TDP totals shown in `experience`
- XP debt support
- skill math tests and active-set pulse behavior

Current state:

- live and used by gameplay loops
- learning cadence is now treated as a performance-sensitive runtime system
- current TDP scope now includes infrastructure as well as foundation: rank-gain accrual, persistence, display, the parallel eight-stat racial TDP modifier table, TDP cost utilities, a Landing trainer hub, and a guildhall locator registry are live; player-facing stat-training spend, circling, and death-side TDP pool loss remain follow-on work

Stat Training Infrastructure snapshot:

- `world/races/definitions.py` now carries `RACIAL_TDP_MODIFIERS` as a parallel eight-stat training-cost table instead of extending the existing six-stat `RACE_STATS` balance model
- `domain/learning/tdp_cost.py` provides the canonical integer-math helpers for single-step and projected TDP spend
- `world/areas/the_landing/stat_trainers/build.py` bootstraps eight dedicated trainer rooms off the Landing hub, each tagged with `region_name = "The Landing"` and `stat_trainer:<stat>`
- `typeclasses/npcs.py` now exposes `StatTrainerNPC` and a fresh `GuildLeaderNPC` base for future profession dispatches, while the current Empath, Cleric, and Ranger guildleaders remain untouched
- `engine/services/guildhall_locator.py` is the forward registry for profession guildhall lookups; today it resolves Empath, Cleric, and Ranger only, and future profession dispatches extend it as their guildhalls ship

### Equipment, Inventory, And Item Handling

Primary files:

- `commands/cmd_inventory.py`
- `commands/cmd_wear.py`
- `commands/cmd_remove.py`
- `commands/cmd_wield.py`
- `commands/cmd_draw.py`
- `commands/cmd_stow.py`
- `typeclasses/weapons.py`
- `typeclasses/wearable_containers.py`
- `typeclasses/sheaths.py`

Implemented behavior:

- slot-based equipment
- wield and unwield flows
- sheaths and wearable containers
- carry weight and encumbrance calculation
- nested container handling
- improvised and default weapon-profile fallback for non-weapon wielded objects

Current state:

- live and broadly integrated with combat and movement pressure

### Stealth, Theft, Justice, And Enforcement

Primary files:

- `world/systems/theft.py`
- `world/systems/justice.py`
- `world/systems/guards.py`
- `world/khri.py`
- `commands/cmd_mark.py`
- `commands/cmd_contact.py`
- `commands/cmd_khri.py`

Implemented behavior:

- hide, stalk, and sneak support through command and state systems
- mark and theft support plus theft memory and awareness hooks
- shop heat and justice pressure
- contacts support
- lawful-zone enforcement logic
- guardhouse, jail, pillory, and enforcement scenario coverage

Current state:

- materially implemented, not just design notes
- still expanding toward fuller thief and guild identity depth

### Economy, Vendors, And Banking

Primary files:

- trade and banking command modules in `commands/`
- vendor and economy helpers in `world/systems/`

Implemented behavior:

- buy, sell, haggle, and appraisal flows
- bank balance and deposit flows
- test coverage through DireTest economy and bank scenarios

Current state:

- live and test-covered
- economy balancing remains an ongoing area rather than a closed system

### Races, Languages, And Profession Identity

Primary files:

- `world/races/`
- `world/languages/`
- `world/professions/professions.py`
- `world/professions/subsystems.py`
- `typeclasses/characters.py`

Implemented behavior:

- race profiles and stat, carry, and learning modifiers
- language, accent, and comprehension systems
- profession registry and profession display/social identity
- profession subsystem scaffolding and active resource bridges

Current registry includes:

- commoner
- barbarian
- bard
- cleric
- empath
- moon mage
- necromancer
- paladin
- ranger
- thief
- trader
- warrior
- warrior mage

Current state:

- registry coverage is broader than fully implemented profession gameplay coverage
- warrior, ranger, empath, thief-facing, and cleric-facing systems are the deepest live profession surfaces today

### Deepest Profession Systems

Warrior:

- tempo resource
- berserks
- roars
- exhaustion and recovery logic

Ranger:

- wilderness bond
- terrain-aware bonuses
- trails and tracking
- companion hooks
- beseech hooks

Empath:

- healing-facing systems
- links and unity hooks
- shock and strain handling
- wound-transfer-facing support

Thief-facing support:

- khri command surface and active-state hooks
- mark and theft support
- burglary and justice DireTest scenarios
- contacts support

Cleric-facing support:

- devotion subsystem support
- commune command surface
- recovery, corpse, and resurrection-facing support

## Clients, Maps, And Navigation

### Browser Client

Primary files:

- `web/templates/webclient/`
- `web/static/webclient/`

Implemented behavior:

- custom browser-first client rather than stock Evennia presentation alone
- structured updates for character and subsystem state
- structured map payload integration
- interactive map controls and click movement

### Godot Client

Primary files:

- `godot/DireMudClient/`
- `server/conf/settings.py`

Implemented behavior:

- Godot workspace in-repo
- portal websocket support enabled for the Godot client path
- map and navigation iteration in the Godot client codebase

Current state:

- active secondary client surface
- browser client remains the primary documented player interface

### AreaForge And Map Payloads

Primary files:

- `world/area_forge/`
- `world/area_forge/map_api.py`
- `world/area_forge/character_api.py`

Implemented behavior:

- graph and map-driven area tooling
- map payload generation for clients
- zone map caching and payload support
- local fallback map behavior for non-authored spaces

Current state:

- live support path for client navigation and world-building tooling
- `world/area_forge/character_api.py::_get_cooldowns()` now treats persisted Evennia nested attrs as generic mappings instead of builtin `dict` only, so `_SaverDict` spell cooldown entries serialize cleanly into browser payloads without raising `TypeError` during `send_character_update()`.
- Structured character payload generation is now verified against both persisted spell cooldowns and transient `ndb.cooldowns`; malformed cooldown values degrade to `0` in the payload instead of tearing down the `/play` character update.

## World Bootstrap And Tutorial Flow

Primary files:

- `world/the_landing.py`
- `systems/onboarding.py`
- onboarding command modules in `commands/`

Implemented behavior:

- automatic Landing bootstrap at startup
- onboarding step and state handling
- guided tutorial beats for movement, equipment, combat, trade, and breach escalation
- mentor, gremlin, and tutorial scripting plus state transitions

Current state:

- live onboarding path
- under continued iteration as content and pacing are tuned

## Testing, Diagnostics, And Tooling

Primary files:

- `diretest.py`
- `tests/services/test_injury_service.py`
- `tests/services/test_service_contracts.py`
- `tests/domain/test_wound_rules.py`
- `tests/domain/test_skill_math.py`
- `tools/architecture_audit.py`
- `tools/full_death_to_res_suite.py`
- `tools/resurrection_sim_suite.py`

Implemented behavior:

- DireTest scenario registration and CLI runner
- artifact writing and replay support
- lag metrics and baseline compare and save flows
- focused domain and service unit coverage for newer extracted systems
- simulation tools for death, resurrection, and empath maintenance

Current state:

- strong repo-local validation support exists
- test coverage is uneven across the full codebase but materially better than stock manual-only validation

## Current Partial Or Scaffolding-First Areas

These areas exist in code but are not all equally deep:

- full profession parity across the entire registry
- long-form guild progression and content breadth
- some magic and guild systems beyond current command and state scaffolding
- broader integration coverage for every legacy system now being pulled under services and domain
- richer world and content coverage compared to the underlying engine and subsystem breadth

## Canonical Docs To Pair With This File

- `README.md`: public overview and quickstart
- `docs/architecture/authority-matrix.md`: ownership direction
- `docs/architecture/engine-contract.md`: service-layer contract direction
- `docs/architecture/timing-map.md`: timing and scheduler inventory
- `docs/architecture/timing-rules.md`: timing ownership rules