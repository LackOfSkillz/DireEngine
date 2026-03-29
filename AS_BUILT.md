# Dragonsire As-Built

## Purpose

This document summarizes the custom gameplay systems currently implemented on top of stock Evennia in this repository.

It is intended to answer three questions:

- What has been added beyond the base Evennia scaffold?
- Where does each system live in the codebase?
- What are the current behaviors, assumptions, and known design constraints?

## Base Platform

- Engine: Evennia
- Project root: `dragonsire`
- Core game focus so far: lightweight DragonRealms-inspired combat, injuries, bleeding, roundtime, skills, NPC combat, weapons, and delayed skill progression

## High-Level Custom Systems

The following systems have been added on top of default Evennia behavior.

### 1. Character Combat State

Primary file:

- `typeclasses/characters.py`

Implemented behavior:

- HP and max HP tracking
- alive/defeated state checks
- combat target tracking
- in-combat state tracking
- defensive combat-state cleanup when target links or room state drift out of sync
- movement lock while in combat

Current behavior summary:

- Characters can engage targets through `attack`
- Defeated characters cannot attack
- Targets at `0` HP cannot be attacked again
- Combat clears when a target is defeated, disengaged, or leaves the room
- Limbo now contains a persistent `training dummy` NPC for retaliation-capable sparring tests after restart

### 1a. Character Presentation Layer

Primary file:

- `typeclasses/characters.py`

Implemented behavior:

- default character description field (`desc`)
- condition helper derived from HP ratio
- overridden `return_appearance()`
- wielded-weapon visibility in `look`

Current behavior summary:

- looking at a character now shows:
  - name
  - description
  - wielded weapon, if any
  - current condition

### 2. Roundtime System

Primary files:

- `typeclasses/characters.py`
- `commands/cmd_attack.py`
- `commands/cmd_disengage.py`
- `commands/cmd_tend.py`

Implemented behavior:

- `roundtime_end` persistent attribute
- `is_in_roundtime()`
- `get_remaining_roundtime()`
- `set_roundtime()`
- `msg_roundtime_block()`

Commands using roundtime:

- `attack`
- `disengage`
- `tend`
- `use <skill>` via shared skill executor
- `health` / `hp` are available as convenience aliases for `stats`

Current behavior summary:

- Actions are blocked while roundtime is active
- successful attacks apply roundtime
- missed attacks also apply roundtime
- disengage applies roundtime
- tend applies roundtime
- blocked-action messaging now reports roundtime with two decimal places instead of truncating to `0 seconds`

### 3. Injury Model

Primary files:

- `typeclasses/characters.py`
- `commands/cmd_injuries.py`
- `commands/cmd_tend.py`

Canonical injury schema per body part:

- `external`
- `internal`
- `bleed`
- `max`
- `vital`

Current tracked body parts:

- `head`
- `chest`
- `abdomen`
- `back`
- `left_arm`
- `right_arm`
- `left_hand`
- `right_hand`
- `left_leg`
- `right_leg`

Implemented behavior:

- per-body-part injury storage
- body-part lookup and normalization helpers
- per-body-part damage application
- healing of body-part external damage
- vital body-part destruction checks
- human-readable body-part formatting for player-facing messages

Current behavior summary:

- attacks apply damage to specific body parts
- `injuries` reports body-part injury severity and bleeding state
- `tend` distinguishes invalid part, uninjured part, not bleeding, and success

### 4. Bleeding and Bleed UX

Primary files:

- `typeclasses/characters.py`
- `server/conf/at_server_startstop.py`
- `commands/cmd_stats.py`

Implemented behavior:

- bleed accumulation on sufficiently strong hits
- total bleed aggregation across body parts
- bleed severity ladder:
  - `none`
  - `light`
  - `moderate`
  - `severe`
  - `critical`
- `bleed_state` persistence
- state-change messaging without per-tick spam
- bleed damage processing in the global ticker
- bleed exposure in `stats`

Current behavior summary:

- bleed damage is processed over time
- bleed messaging is state-change based, not spammed every tick
- tending can stop bleed on a specific body part

### 5. Tend / Field Treatment Flow

Primary file:

- `commands/cmd_tend.py`

Implemented behavior:

- natural-language body-part parsing, including phrases like `my right hand`
- body-part validation
- distinction between unsupported anatomy, uninjured parts, non-bleeding injuries, and bleeding wounds
- stopping bleed on a body part
- small healing amount to external injury
- room messaging

Current behavior contract:

- invalid part: `Invalid body part.`
- valid but uninjured: `Your <part> is uninjured.`
- injured but not bleeding: `Your <part> is not bleeding.`
- bleeding: `You stop bleeding on your <part>.`

### 6. Skills Scaffold

Primary files:

- `typeclasses/characters.py`
- `commands/cmd_skills.py`
- `commands/cmd_use.py`

Implemented behavior:

- central `use_skill()` execution path
- `has_skill()`
- `learn_skill()`
- skill storage as structured dictionaries:
  - `rank`
  - `mindstate`
- starter skills seeded for characters:
  - `brawling`
  - `light_edge`
  - `attack`
  - `tend`
  - `disengage`

Current behavior summary:

- `skills` lists known skills with rank and mindstate label
- `use <skill>` routes through the shared skill executor
- attack-driven learning now flows through weapon skill mapping instead of generic `attack`

### 7. Mindstate and Learning Pulse

Primary files:

- `typeclasses/characters.py`
- `server/conf/at_server_startstop.py`
- `commands/cmd_skills.py`
- `commands/cmd_attack.py`

Implemented behavior:

- mindstate ladder from `clear` to `mind locked`
- `get_mindstate_label()`
- mindstate cap at `110`
- `process_learning_pulse()`
- learning pulse hook in the global ticker
- simple rank gain and mindstate drain on pulse
- light improvement messaging on pulse rank gain

Current behavior summary:

- successful meaningful attacks increase mindstate
- misses do not grant learning
- trivial attacks are gated by a temporary heuristic: no learning when final hit chance is `95` or higher
- ticker pulses convert mindstate into rank over time
- Intelligence increases learning capacity through a dynamic mindstate cap
- Wisdom increases pulse drain speed through a dynamic learning drain
- higher stored mindstate produces larger pulse rank gains
- attack learning now also uses a difficulty curve based on the target's `reflex + agility`
- current learning bands are:
  - `trivial`
  - `easy`
  - `optimal`
  - `hard`
  - `too_hard`
- trivial targets provide no learning, parity targets provide the strongest learning, and much stronger targets provide reduced learning

Current simplifications:

- no XP system
- no instant level-up model
- pulse conversion is still intentionally simple, but no longer flat
- mindstate gain is currently a flat `+1` when granted
- temporary pulse debug output is still enabled
- temporary attack-side learning-band debug output is still enabled

### 8. Probabilistic Combat Resolution

Primary files:

- `commands/cmd_attack.py`
- `typeclasses/characters.py`

Implemented behavior:

- hit roll using `random.randint(1, 100)`
- attacker accuracy based on:
  - base `50`
  - `reflex`
  - `agility`
  - active combat skill rank
- defender evasion based on:
  - `reflex`
  - `agility`
- minimum and maximum hit-chance clamps
- explicit miss branch before damage application

Current behavior summary:

- combat is probabilistic rather than deterministic
- misses still consume fatigue and roundtime
- skill rank now directly affects hit chance
- attack messaging is layered across actor, target, and room observers
- combat phrasing is now weapon-aware and quality-aware through helper-driven verbs and hit-result text

Debug note:

- the attack command currently still emits debug lines for roll/chance and weapon/damage during testing

### 9. Balance and Fatigue

Primary files:

- `typeclasses/characters.py`
- `server/conf/at_server_startstop.py`
- `commands/cmd_attack.py`
- `commands/cmd_stats.py`

Implemented behavior:

- `balance` / `max_balance`
- `fatigue` / `max_fatigue`
- getters, setters, and clamping
- recovery through the global ticker
- attack costs applied through the active weapon profile
- attack block at zero balance

Current behavior summary:

- attacks spend balance and add fatigue
- ticker recovers balance upward and fatigue downward
- `stats` exposes current values

### 10. Weapons and Improvised Wielding

Primary files:

- `typeclasses/weapons.py`
- `typeclasses/characters.py`
- `commands/cmd_wield.py`
- `commands/cmd_spawnweapon.py`

Implemented behavior:

- base `Weapon` typeclass
- weapon fields:
  - `weapon_type`
  - `damage_min`
  - `damage_max`
  - `roundtime`
  - `balance_cost`
  - `fatigue_cost`
  - `skill`
  - `damage_type`
- canonical weapon taxonomy:
  - `brawling`
  - `light_edge`
  - `heavy_edge`
  - `blunt`
  - `polearm`
  - `short_bow`
  - `long_bow`
  - `crossbow`
- `get_weapon_skill()` on weapons
- wield command
- training weapon spawn command

Current behavior summary:

- weapon profile drives damage, fatigue cost, balance cost, roundtime, and active combat skill
- any object may be wielded
- non-weapon objects are normalized through a safe improvised/default profile rather than rejected

### 11. NPC Combat Loop

Primary files:

- `typeclasses/npcs.py`
- `server/conf/at_server_startstop.py`
- `commands/cmd_spawnnpc.py`

Implemented behavior:

- NPC typeclass inheriting from Character
- `is_npc` flag
- `npc_combat_tick()` AI hook
- NPC spawn command for test combatants
- ticker-driven retaliation and combat continuation

Current behavior summary:

- NPCs enter combat when attacked because the shared attack path establishes mutual targeting
- NPCs attack through the same `attack` command path used by players
- NPCs respect roundtime
- NPCs stop when target is dead, absent, or combat is broken

### 12. Global Ticker-Orchestrated Systems

Primary file:

- `server/conf/at_server_startstop.py`

Current global ticker responsibilities:

- recover balance
- recover fatigue
- process bleed
- update bleed state
- process learning pulse
- run NPC combat ticks

The ticker is currently the main periodic orchestrator for character-state progression.

### 12a. Visibility / Messaging Layer

Primary files:

- `typeclasses/characters.py`
- `commands/cmd_attack.py`
- `commands/cmd_disengage.py`
- `commands/cmd_tend.py`

Implemented behavior:

- layered hit messaging for actor, target, and room observers
- layered miss messaging for actor, target, and room observers
- room-visible disengage messaging
- room-visible tend messaging

Current behavior summary:

- combat actions are now visible to uninvolved observers in the room
- `disengage` produces room-facing exit text
- `tend` produces room-facing treatment text

### 13. Legacy Character Backfill / Migration Safety

Primary files:

- `typeclasses/characters.py`
- `server/conf/at_server_startstop.py`
- `typeclasses/scripts.py`

Implemented behavior:

- centralized `ensure_core_defaults()` migration path
- smaller `ensure_*` helpers inside Character for maintainability
- automatic backfill on puppet and on runtime access paths
- startup backfill for Characters/NPCs
- retirement of legacy script-based bleed tickers

Current behavior summary:

- older characters created before later systems were added are upgraded in-place when accessed
- startup no longer depends on the old per-object persistent `BleedTicker` scripts

Covered legacy fields currently include:

- stats
- HP
- balance/fatigue
- bleed state
- roundtime
- injuries
- combat flags
- equipped weapon slot
- structured skill storage and starter skills

## Custom Commands Currently Available

Registered in the Character cmdset:

- `attack`
- `disengage`
- `injuries`
- `skills`
- `spawnnpc`
- `spawnweapon`
- `stats`
- `tend`
- `use`
- `wield`

Command roles:

- `attack`: combat resolution entry point
- `disengage`: leaves combat and clears mutual combat state when linked
- `injuries`: shows body-part injury severity and bleed visibility
- `skills`: shows known skills with rank and mindstate label
- `spawnnpc`: creates a test NPC combatant
- `spawnweapon`: creates a test training sword
- `stats`: shows HP, combat status, bleed state, balance, and fatigue
- `tend`: field-treats a body part
- `use`: executes a skill through the shared skill executor
- `wield`: equips an object for combat use

## Current Design Constraints and Locks

These constraints are already reflected in code and should be preserved unless intentionally changed.

- There should be one authoritative combat path. `attack` is the primary combat executor; other interfaces should delegate rather than fork combat logic.
- Missed attacks still incur fatigue and roundtime.
- `wield` should remain permissive; profile normalization belongs in `get_weapon_profile()`, not in rigid wield-time type checks.
- Legacy character migration should continue to be handled through the centralized Character backfill helpers whenever persistent fields are added.

## World / Content Notes

Repository-specific custom world content noted so far:

- `world/brookhollow_v3_patched.py` contains Brookhollow map/content construction

Current note:

- Brookhollow does not appear to auto-load on startup through a current startup hook; it appears intended for manual execution/import.

## Known Limitations / In-Progress Areas

This repository is no longer just stock Evennia, but several gameplay systems are still intentionally simplified.

- learning gain is currently flat
- learning pulse conversion is currently flat
- difficulty-based learning has not yet been implemented
- weapon categories exist, but deeper category-specific differentiation is still shallow
- body-part coverage is intentionally limited to the current schema and does not include finer anatomy like eyes or feet
- combat debug messaging is still present
- NPC AI is functional but still simple; it uses the shared combat path and basic pacing checks rather than advanced decision-making

## Suggested Maintenance Rule

Whenever a new persistent Character attribute is added, update the Character backfill helpers in `typeclasses/characters.py` at the same time.

That keeps:

- older characters safe
- ticker-driven systems stable
- new gameplay features compatible with existing accounts/characters

## Performance Regression Note

The most important confirmed live-performance regression so far was not command rendering or telnet compression alone; it was a reactor-blocking periodic gameplay loop.

- Historical symptom pattern:
  - login delayed by several seconds
  - trivial commands like `look` and room movement delayed by roughly `5s` to `8s`
  - once command execution actually started, the command body itself still completed quickly
- Confirmed root cause:
  - the original 1-second global ticker in `server/conf/at_server_startstop.py` iterated every Character/NPC object and ran multiple gameplay maintenance calls on each pass
  - with roughly `185` tracked Character/NPC objects, that full sweep stalled the main Evennia event loop badly enough to delay unrelated commands
- Permanent mitigation now in place:
  - status processing split into a lightweight `1s` status tick and a separate `10s` learning tick
  - idle characters are skipped entirely
  - NPC combat work only runs when the NPC is actually in combat
  - learning pulses only run for characters with meaningful pending mindstate
  - noisy per-pulse debug messaging was removed
  - MCCP is also hard-disabled at the telnet protocol layer, but that was not the decisive fix for the severe multi-second lag
- Fast recognition rule if lag ever reappears:
  - if `connect`, `look`, and simple room movement all become uniformly slow by several seconds, inspect periodic global loops before touching appearance/combat rendering code
  - especially scrutinize any ticker that walks all Character/NPC objects or performs default-normalization work every second

## Summary

As built today, this project has moved from stock Evennia into a functioning lightweight MUD gameplay layer with:

- real combat state
- injuries and bleeding
- roundtime pacing
- balance and fatigue
- weapon-driven attacks
- NPC retaliation
- skill tracking
- mindstate-based delayed progression
- legacy character migration safeguards

The core custom game loop now exists and is testable in live play.