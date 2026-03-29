# diremud microtasks 341-380 report

## scope

Completed the MT 341-380 batch from `MT 341 - 380.md`.

This batch added contested combat distance, ranged-weapon handling, aiming, basic perception-vs-stealth visibility, stealth-aware movement messaging, and lightweight NPC pursuit and retreat behavior.

## implemented

### range state and combat awareness

- Added `RANGE_BANDS = ["melee", "reach", "missile"]` in `typeclasses/characters.py`.
- Added persistent combat range tracking on characters:
  - `db.combat_range`
  - `db.range_break_ticks`
  - `db.aiming`
- Added helpers on `Character` for:
  - `get_range()`
  - `set_range()`
  - `clear_range()`
  - `clear_aim()`
  - `get_pressure()`
  - `process_combat_range_tick()`
- Extended combat-state cleanup so ending combat also clears aim and per-target range state.

### commands

- Added `advance` in `commands/cmd_advance.py`.
  - Re-engages the current target at melee range.
  - Uses player-favored direct re-entry with no contest roll.
- Added `retreat` in `commands/cmd_retreat.py`.
  - Retreat is contested instead of automatic.
  - Uses agility, reflex, pressure, fatigue, balance, and a small player advantage.
  - Supports full retreat to `missile` and partial retreat to `reach`.
  - Applies retreat roundtime.
- Added `aim` in `commands/cmd_aim.py`.
  - Stores the current target id as the aiming target.
- Registered all three commands in `commands/default_cmdsets.py`.

### attack integration

- Updated `commands/cmd_attack.py` to enforce melee-only attacks for non-ranged weapons when targets are outside melee.
- Added ranged-weapon support:
  - ranged weapons may attack outside melee
  - ranged attacks suffer an accuracy penalty at melee range
- Added aim bonus application when the attacker is aiming at the current target.
- Clears aim after an actual attack attempt.
- Added distinct ranged combat messaging for hit and miss results.

### perception and stealth

- Added `get_perception()` on `Character` using intelligence.
- Added `get_stealth()` on `Character` using the stealth skill.
- Added `can_detect()` and routed `can_perceive()` through it.
- Updated room character display in `typeclasses/rooms.py` so undetected characters are omitted from room look output.

### movement presentation

- Added stealth-aware movement presentation through:
  - `typeclasses/exits.py`
  - `typeclasses/characters.py`
- Exits now record the traversed direction.
- Stealthy movers emit `You move quietly to the <direction>.`
- Observers only receive the quiet movement message if they can detect the mover.

### ranged weapon data

- Added `db.is_ranged = False` default on weapons in `typeclasses/weapons.py`.
- Extended `spawnweapon` with a true ranged example weapon:
  - `bow`
- The spawned training bow carries:
  - `is_ranged = True`
  - missile-range profile data
  - puncture-weighted damage distribution
  - attack-skill scaling tiers

### NPC pursuit and retreat

- Extended `typeclasses/npcs.py` with:
  - `is_winning()`
  - `attempt_pursue()`
  - `attempt_retreat()`
- NPCs now:
  - pursue when they are winning and range opens up
  - may retreat when badly hurt
  - respect roundtime when pursuing or fleeing
- Updated the status tick in `server/conf/at_server_startstop.py` so in-combat characters always process range-state updates.

### disengage persistence

- Added a lightweight combat persistence break:
  - if both sides remain at missile range for consecutive combat ticks, combat is broken automatically
- This gives retreat room to matter without making escape immediate or free.

## validation

### command and import validation

- `commands.default_cmdsets` imports cleanly after the new commands were added.
- File-level error checks found no relevant syntax or type issues introduced by this batch.

### direct shell validation

Validated the new systems with isolated temporary objects while the server was stopped to avoid SQLite lock conflicts.

Confirmed:

- default combat range resolves to `melee`
- explicit range updates to `missile`
- `aim` stores the current target id
- high-stealth targets are hidden from room look output
- visible targets reappear once stealth drops below perception
- NPC pursuit can pull range back to `melee`
- wounded NPCs can retreat to `missile`
- ranged weapons report `is_ranged = True`

Validated retreat and combat-persistence loop:

- `retreat` moved the pair to `missile`
- after roundtime reset, `advance` returned the pair to `melee`
- two consecutive missile-range combat ticks broke combat cleanly

Validated ranged attack path:

- ranged attack from missile range succeeded
- aim was cleared after the attack
- target HP dropped from the attack
- attacker received roundtime from the ranged attack

## result

MT 341-380 is complete in the current workspace.

Combat now supports contested distance, ranged pressure, basic stealth-based visibility, and state-aware NPC pursuit/escape behavior without adding a new heavy global loop.