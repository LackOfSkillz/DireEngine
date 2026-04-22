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
- `engine/services/injury_service.py`
- `engine/services/pulse_service.py`
- `engine/services/result.py`
- `engine/services/errors.py`
- `engine/contracts/combat_result.py`
- `domain/combat/rules.py`
- `domain/wounds/constants.py`
- `domain/wounds/models.py`
- `domain/wounds/rules.py`

This is still a transitional architecture. Not every gameplay surface has been extracted yet, but combat, state mutation, and wound handling now have a formal service/domain path.

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
- custom condition, equipment, and character-state presentation
- structured sync hooks for browser and client state updates

### Combat And Action Pacing

Primary files:

- `commands/cmd_attack.py`
- `commands/cmd_advance.py`
- `commands/cmd_retreat.py`
- `commands/cmd_disengage.py`
- `engine/services/combat_service.py`
- `engine/services/state_service.py`
- `domain/combat/rules.py`

Implemented behavior:

- target-based combat flow
- range and engagement handling
- roundtime pacing
- NPC combat behavior follows `event -> set target -> ai_tick acts on target`, where room-entry presence and damage hooks establish targets and the existing global NPC tick drives continued attacks and disengage cleanup
- same-room guard assist is event-driven as well: assist-capable NPCs join when a nearby guard acquires a player target, then the existing target state and ai tick handle the rest
- NPC threat tracking is layered on top of that same loop as runtime combat state: damage and assist add threat, ai tick can switch to the top valid threat, and threat is cleared when combat fully disengages

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
- XP debt support
- skill math tests and active-set pulse behavior

Current state:

- live and used by gameplay loops
- learning cadence is now treated as a performance-sensitive runtime system

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