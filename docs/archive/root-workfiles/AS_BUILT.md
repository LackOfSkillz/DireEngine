# Dragonsire As-Built

## Purpose

This document summarizes the gameplay, world, client, and server systems currently implemented on top of the stock Evennia game scaffold in this repository.

It is intended to answer four questions:

- What has been added beyond base Evennia?
- Which systems are currently live and player-facing?
- Where do the important systems live in the codebase?
- What architectural choices now define the running server?

## Base Platform

- Engine: Evennia
- Language/runtime: Python 3.11
- Web stack: Django through Evennia
- Project root: `dragonsire`
- Game target: browser-first, DragonRealms-inspired text gameplay with modern client support

## What Is No Longer Stock Evennia

This repository is no longer a thin Evennia tutorial game. It now includes:

- a custom browser client and structured server-to-client payloads
- a custom world bootstrap path for The Landing and supporting spaces
- custom character, room, exit, object, corpse, grave, NPC, weapon, armor, trap, and vendor typeclasses
- a large custom command surface replacing basic stock play with domain-specific verbs
- custom progression, combat, injury, survival, justice, profession, magic, and death systems
- AreaForge map and world-building support

## Runtime Startup Behavior

Primary file:

- `server/conf/at_server_startstop.py`

Current startup behavior includes:

- installation of a lightweight `1s` global status ticker
- installation of a separate `10s` learning ticker
- legacy Character/NPC backfill through `ensure_core_defaults()` at startup
- cleanup of legacy bleed ticker scripts
- creation/maintenance of the Limbo training complex and training dummy
- automatic build/bootstrap of The Landing content
- Brookhollow justice-region configuration

Current design intent:

- the server should start into a usable game world without requiring manual world bootstrap steps
- periodic game work should be split into small, state-gated loops rather than a monolithic every-character sweep

## Code Layout

- `typeclasses/`: core game rules and persistent object behavior
- `commands/`: player verbs, admin/debug verbs, and movement/combat interaction entry points
- `world/`: profession systems, map/world APIs, content builders, justice helpers, and game subsystems
- `world/area_forge/`: map ingestion, payload generation, graph building, and client-facing map APIs
- `web/templates/webclient/`: custom browser client template
- `web/static/webclient/`: client JavaScript and CSS
- `server/conf/`: startup hooks and configuration

## Core Character Layer

Primary file:

- `typeclasses/characters.py`

Implemented behavior:

- centralized persistent-character migration/backfill through `ensure_core_defaults()` and related helpers
- persistent stats, resources, injuries, equipment, combat, profession, magic, death, and state fields
- custom `return_appearance()` and player-facing condition/equipment presentation
- structured client-sync hooks for character and map updates

Important architectural rule:

- any new persistent Character field must be added through the default/backfill helpers so older characters remain valid

## Browser Client and Structured APIs

Primary files:

- `web/templates/webclient/`
- `web/static/webclient/`
- `world/area_forge/character_api.py`
- `world/area_forge/map_api.py`

Implemented behavior:

- custom browser-first web client rather than the stock Evennia shell alone
- structured character payload updates
- structured subsystem updates
- structured map payloads
- click-to-move support through clickable exits and map interactions
- local and zone map rendering support
- fullscreen/pan/fit/center map UX in the web client

Current behavior summary:

- movement, state, and map data are pushed to the browser client in structured form
- map-assisted navigation is a first-class supported play mode

## World Bootstrap and Content Pipeline

Primary files:

- `world/the_landing.py`
- `world/area_forge/`
- `server/conf/at_server_startstop.py`

Implemented behavior:

- automatic bootstrap of The Landing world content at server start
- AreaForge support for graph/map-driven world creation and payload generation
- auto-maintained Limbo training space for test combat and equipment workflows
- justice-region assignment for Brookhollow-related areas

Current behavior summary:

- the running server is built around authored and generated/custom-processed world spaces, not just stock Evennia test rooms

## Combat and Action Pacing

Primary files:

- `typeclasses/characters.py`
- `commands/cmd_attack.py`
- `commands/cmd_advance.py`
- `commands/cmd_retreat.py`
- `commands/cmd_disengage.py`
- `utils/contests.py`

Implemented behavior:

- target-based combat state
- engagement/range state and range transitions
- roundtime-based action pacing
- probabilistic contest-driven combat resolution
- explicit hit, miss, damage, defense, and messaging branches
- movement restrictions while in combat
- target cleanup when combat links drift or break

Current behavior summary:

- combat is no longer stock Evennia command handling; it is a custom stateful combat loop with range, accuracy, defense, damage, and resource pressure

## Injuries, Bleeding, and Condition

Primary files:

- `typeclasses/characters.py`
- `commands/cmd_injuries.py`
- `commands/cmd_tend.py`
- `server/conf/at_server_startstop.py`

Implemented behavior:

- per-body-part injuries
- external/internal/bruise/bleed tracking
- bleed-state summarization and over-time bleed processing
- body-part injury display and severity formatting
- tend-based bleeding treatment
- character condition text derived from current state

Current tracked body regions include:

- head
- chest
- abdomen
- back
- arms
- hands
- legs

Current behavior summary:

- injury and bleeding are central gameplay state, not flavor-only messaging
- bleeding progresses over time and can be stabilized rather than trivially ignored

## Balance, Fatigue, Resources, and Recovery

Primary files:

- `typeclasses/characters.py`
- `server/conf/at_server_startstop.py`
- `commands/cmd_stats.py`

Implemented behavior:

- HP and max HP
- balance and max balance
- fatigue and max fatigue
- attunement and max attunement
- profession-specific resource bridges such as Inner Fire, Focus, and Transfer Pool
- ticker-driven passive recovery for appropriate states

Current behavior summary:

- actions create persistent pressure on resources, and the server recovers those resources over time based on activity state

## Weapons, Equipment, Inventory, and Containers

Primary files:

- `typeclasses/characters.py`
- `typeclasses/weapons.py`
- `typeclasses/wearable_containers.py`
- `typeclasses/sheaths.py`
- `commands/cmd_inventory.py`
- `commands/cmd_wear.py`
- `commands/cmd_remove.py`
- `commands/cmd_wield.py`
- `commands/cmd_unwield.py`
- `commands/cmd_draw.py`
- `commands/cmd_stow.py`
- `commands/cmd_slots.py`

Implemented behavior:

- slot-based worn equipment
- wielded weapon handling
- sheaths and wearable containers
- inventory and slot display
- unified carried-weight calculation including coins, worn gear, nested container contents, and carry limits
- encumbrance state calculation with overload movement blocking
- weighted container capacity checks and container weight/capacity display
- permissive wielding of non-weapon objects through improvised/default weapon profiles
- armor-type handling and armor-derived hindrance/effects

Current behavior summary:

- equipment handling is custom and deeply tied into combat, appearance, and movement/combat penalties

## Skills, Mindstate, XP, and Learning

Primary files:

- `typeclasses/characters.py`
- `commands/cmd_skills.py`
- `commands/cmd_use.py`
- `commands/cmd_mindstate.py`
- `server/conf/at_server_startstop.py`

Implemented behavior:

- central skill registry across combat, survival, lore, armor, and magic
- per-skill rank and mindstate storage
- `use_skill()` as the shared skill-learning/action hook
- learning pulse conversion over time
- difficulty-band-based learning logic
- total XP and unabsorbed XP support
- experience debt support tied to the death system

Current behavior summary:

- the game now has delayed progression behavior rather than instant one-shot advancement
- learning is connected to real action use and post-action progression pulses

## Professions and Subsystems

Primary files:

- `typeclasses/characters.py`
- `world/professions.py`
- `world/systems/warrior/`
- `world/systems/ranger/`

Implemented behavior:

- profession identity and guild mapping
- profession rank/circle concepts
- subsystem controllers and per-profession subsystem state
- profession-aware commands, unlocks, bonuses, and UI exposure
- cleric devotion subsystem support with structured subsystem/UI state

Current live profession-facing systems include:

- Warrior systems
- Ranger systems
- Empath systems
- Thief-facing systems and khri hooks
- Cleric devotion, commune, and death/favor-facing support
- spellcasting guild access hooks

## Warrior Systems

Primary files:

- `world/systems/warrior/`
- `typeclasses/characters.py`
- Warrior-related command modules in `commands/`

Implemented behavior:

- warrior circles/ranks
- war tempo and tempo-state logic
- berserk and roar systems
- exhaustion/recovery hooks
- warrior-specific combat abilities and passives
- `recover` fallback for warrior exhaustion when grave recovery is not applicable

## Ranger Systems

Primary files:

- `world/systems/ranger/`
- `typeclasses/abilities_survival.py`
- `typeclasses/characters.py`
- ranger-related commands in `commands/`

Implemented behavior:

- wilderness bond
- terrain/environment-aware bonuses
- trail creation and reading
- tracking/hunting support
- stealth and movement support such as hide, sneak, stalk, pounce, snipe, cover tracks, and related flow
- companion support hooks
- beseech and environment-derived bonuses

## Empath Systems

Primary files:

- `typeclasses/characters.py`
- empath-related commands in `commands/`

Implemented behavior:

- empath wound model and wound transfer foundations
- empath links
- empath shock/load behavior
- stabilization of living bleeding targets
- corpse stabilization support for the death system
- poison/disease wound-condition processing

## Magic Systems

Primary files:

- `typeclasses/spells.py`
- `typeclasses/characters.py`
- `commands/cmd_prepare.py`
- `commands/cmd_charge.py`
- `commands/cmd_cast.py`
- `commands/cmd_stopcast.py`

Implemented behavior:

- spell preparation
- charge/release flow
- spell schools/categories including targeted, augmentation, debilitation, warding, and utility
- cyclic-ready support hooks
- guild-aware spell access foundations

Current behavior summary:

- magic is no longer a placeholder command shell; it has a real stateful prepare/cast pipeline even if the content breadth is still growing

## Stealth, Survival, and Exploration Verbs

Primary files:

- `typeclasses/abilities_stealth.py`
- `typeclasses/abilities_survival.py`
- `typeclasses/abilities_perception.py`
- related commands in `commands/`

Implemented behavior:

- hide
- sneak
- stalk
- ambush
- observe
- search
- analyze
- forage
- harvest
- skin
- climb
- swim
- passage discovery and travel

Current behavior summary:

- room movement and exploration are tied into stealth, tracking, trails, terrain, and survival skill use rather than plain stock exit traversal

## Economy, Vendors, and Appraisal

Primary files:

- `typeclasses/vendor.py`
- `typeclasses/characters.py`
- `typeclasses/items/gem.py`
- `typeclasses/items/gem_pouch.py`
- `typeclasses/box.py`
- `typeclasses/rooms.py`
- `commands/cmd_buy.py`
- `commands/cmd_sell.py`
- `commands/cmd_loot.py`
- `commands/cmd_unlock.py`
- `commands/cmd_deposit.py`
- `commands/cmd_withdraw.py`
- `commands/cmd_balance.py`
- `commands/cmd_store.py`
- `commands/cmd_retrieve.py`
- `commands/cmd_haggle.py`
- `commands/cmd_appraise.py`
- `commands/cmd_compare.py`

Implemented behavior:

- typed loot generation for NPCs: coins, gems, and boxes
- strict gem schema, deterministic gem value tables, and gem pouch auto-storage
- corpse search before loot extraction, with separate one-time coin, gem, and box recovery
- strict box generation, unlock/open flow, and capped box contents
- specialized vendor types: general, gem buyer, and pawn
- vendor acceptance and payout rules, including `sell all`
- vendor inventory sink behavior that prevents buy/sell loops
- buying and selling
- haggle flow
- appraisal and comparison support
- coin tracking on characters and corpses/graves
- banked coin storage via `deposit`, `withdraw`, and `balance`
- vault item storage via `store` and `retrieve`
- location-gated bank and vault support through room flags
- Brookhollow bank/vault rooms marked explicitly and The Landing room generation now classifies bank/vault service rooms from generated POI labels and descriptions
- coin weight and carry-weight pressure integrated into the economy loop

Current behavior summary:

- the economy is now a multi-step loop with typed loot, specialized sinks, bank/vault safety, Landing-aware service locations, and carry-weight pressure rather than a flat buy/sell coin counter

## Traps, Locksmithing, and Devices

Primary files:

- `typeclasses/trap_device.py`
- `typeclasses/box.py`
- `typeclasses/lockpick.py`
- `typeclasses/characters.py`
- related commands in `commands/`

Implemented behavior:

- traps and concealed devices
- trap deployment and detection
- boxes, locks, and lock difficulty
- lockpick spawning and use
- inspect/open/pick/disarm/rework flows

## Justice, Crime, and Bounties

Primary files:

- `utils/crime.py`
- `typeclasses/npcs.py`
- `typeclasses/characters.py`
- justice/bounty commands in `commands/`

Implemented behavior:

- law-region support
- crime flags, warrants, fines, stocks/jail state hooks
- guards/capture flows
- bounty boards and bounty acceptance/review commands
- justice-facing commands such as `justice`, `bribe`, `capture`, `surrender`, `plead`, `payfine`, and `laylow`

Current behavior summary:

- justice is an active game system with command/UI consequences, not a planned placeholder

## Death, Favor, Resurrection, Corpses, and Graves

Primary files:

- `typeclasses/characters.py`
- `typeclasses/corpse.py`
- `typeclasses/grave.py`
- `typeclasses/scripts.py`
- `typeclasses/objects.py`
- `commands/cmd_depart.py`
- `commands/cmd_perceive.py`
- `commands/cmd_prepare.py`
- `commands/cmd_preserve.py`
- `commands/cmd_sensesoul.py`
- `commands/cmd_resurrect.py`
- `commands/cmd_death.py`
- `commands/cmd_corpse.py`
- `commands/cmd_recover.py`
- `commands/cmd_stabilize.py`
- `commands/cmd_rejuvenate.py`
- `commands/cmd_uncurse.py`
- `commands/cmd_consent.py`
- `commands/cmd_deathinspect.py`
- `commands/cmd_decaycorpse.py`
- `commands/cmd_res.py`
- `commands/cmd_die.py`

Implemented behavior:

- life-state model: alive, dead, departed
- Favor-based death-state modeling
- dead-state command gating in `Character.execute_cmd()`
- Death's Sting penalties
- experience debt on death, stacking on repeated death, and partial recovery on resurrection
- corpse creation on death
- explicit soul-state creation on death with per-character recoverability and strength
- corpse condition tiers and condition-based description
- owner-aware corpse presentation for named versus anonymous dead
- corpse memory timer/state parallel to physical decay
- soul decay over time on dead characters through the active status tick
- corpse stabilization by Empaths
- cleric corpse perception with resurrection-state readout
- cleric soul sensing through `sense soul`
- cleric memory preservation through `preserve`
- cleric corpse preparation stacks through `prepare`
- corpse decay into owner-visible graves
- corpse/grave stored coin handling
- grave item-damage metadata with time-based grave damage growth
- grave expiry timers and owner-facing expiry warnings
- grave item and coin recovery
- depart paths based on available Favor profile
- region-aware recovery-point resolution for depart destinations
- room-level no-resurrection, dangerous-zone, and safe-zone death flags
- resurrection favor requirement and favor consumption on success
- favor-threshold-based resurrection quality scaling
- favor-based soul durability and no-favor resurrection lockout
- cleric-driven resurrection from corpse
- resurrection quality tiers: perfect, stable, fragile, flawed
- post-resurrection fragility/instability penalties on weak returns
- cleric devotion as a separate profession resource from Favor
- cleric ritual support through `pray`, with tiered devotion gain and ritual cooldowns
- first commune set through `commune solace`, `commune ward`, and `commune vigil`
- Theurgy as a cleric guild skill trained by rituals, communes, corpse rites, and resurrection
- devotion drift toward baseline through the active status tick
- devotion-aware resurrection cost, failure pressure, and recovery quality adjustments
- devotion-aware cleric spell preparation stability and spell power scaling
- resurrection gating on corpse state, memory state, and soul recoverability together
- failed resurrection attempts damage corpse condition and soul strength and can make a corpse irrecoverable
- `uncurse` support for reducing or clearing Death's Sting
- recovery metadata tracking for depart versus resurrection
- corpse/grave recovery permissions and player consent
- consent listing, expiry windows, and consent-use notification messaging
- new-player death protection that softens sting/debt and upgrades early depart outcomes
- randomized death emote variants with a delayed room beat
- ghost-state messaging and a persistent dead-command banner
- refined Death's Sting severity labels and expiry messaging
- occasional combat feedback while Death's Sting remains active
- player-facing `death` status command
- player-facing `corpse` status command
- preview and confirmation flow for favor-spending `depart` paths
- anti-duplication protections for corpse and grave creation
- orphan corpse/grave cleanup, death event hooks, and per-character death analytics
- admin `@deathinspect`, `@decaycorpse`, and `@res` commands for testing and intervention
- admin `die` command for testing

Current behavior summary:

- death is now a production-ready multi-stage gameplay loop with penalties, rescue/prep support, protected onboarding behavior, corpse/grave logistics, consented recovery, and cleric/empath recovery depth

## NPCs and AI

Primary files:

- `typeclasses/npcs.py`
- `server/conf/at_server_startstop.py`

Implemented behavior:

- NPCs inherit from Character and share most combat/state logic
- roundtime-aware combat AI
- target pursuit/retreat logic
- profession/trade/justice reaction hooks
- startup-maintained training dummy for test combat loops

Current behavior summary:

- NPCs are integrated into the same action model as players rather than using a separate toy combat system

## Commands and Verb Surface

Primary files:

- `commands/default_cmdsets.py`
- `commands/cmd_help.py`

Implemented behavior:

- large custom Character command set covering combat, inventory, professions, stealth, survival, justice, magic, teaching, death, and admin/debug support
- custom help grouping for player and staff commands
- clickable movement wrapper command `__clickmove__` used by the browser client

Current behavior summary:

- moment-to-moment gameplay is driven by a broad custom verb layer rather than the stock Evennia demo surface

## Server Performance Architecture

Primary files:

- `server/conf/at_server_startstop.py`
- `typeclasses/characters.py`
- `typeclasses/rooms.py`

Implemented behavior:

- split status and learning tickers instead of one heavyweight global sweep
- state-gated status work
- room-scoped NPC tick participation near active puppets
- hot-path movement optimizations for state checks and post-move processing
- retirement of earlier expensive periodic patterns

Current behavior summary:

- the running server has already been tuned away from multi-second reactor stalls caused by global gameplay sweeps and expensive move-time default normalization

## Admin, Debug, and Test Utilities

Primary files:

- `commands/default_cmdsets.py`
- admin/debug command modules in `commands/`

Implemented behavior:

- spawn helpers for NPCs, weapons, wearables, lockpicks, vendors, boxes, and other test fixtures
- `renew` reset flows
- `survivaldebug`
- `maptest`
- `die` for forced death testing
- profession/circle test helpers

## Known Architectural Constraints

These are current design rules already reflected in the codebase:

- `typeclasses/characters.py` is the authoritative location for persistent character-state evolution
- dead-state command enforcement lives in `Character.execute_cmd()` because not all commands inherit the custom command base
- shared systems such as contests should remain centralized rather than forked per command
- periodic server work must remain state-gated and should never regress into a full every-object heavy sweep
- move-time hooks must avoid calling full default-normalization paths where direct attribute access is sufficient

## Current State Summary

As built today, Dragonsire is a custom Evennia game server with:

- a custom browser client
- structured character and map APIs
- world bootstrap for The Landing and related content
- custom combat, injuries, bleeding, and pacing
- equipment, weapons, armor, and containers
- progression through skills, mindstate, XP, and profession subsystems
- Ranger, Warrior, Empath, justice/thief-facing, and magic foundations
- vendors, traps, locksmithing, and survival verbs
- a live death/favor/corpse/grave/resurrection system with consent, coin retention, rejuvenation, uncurse, and new-player protection
- server-side performance work to keep all of the above playable in real time

This is no longer a stock Evennia server with a few sample commands. It is a custom gameplay platform with active world, client, profession, death, and map/navigation systems layered over the original Evennia base.