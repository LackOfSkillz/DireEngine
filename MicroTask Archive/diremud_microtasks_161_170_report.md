## Report — Microtasks 161-170

### MT161 - Add character description field
- Added `self.db.desc = "An unremarkable person."` to `Character.at_object_creation()` in `typeclasses/characters.py`.
- Added legacy-safe defaulting for `desc` through the existing identity/default backfill path.
- Result: PASS

### MT162 - Add condition helper
- Added `get_condition()` to `typeclasses/characters.py`.
- Condition now resolves from HP ratio into these states:
	- `dead`
	- `near death`
	- `badly wounded`
	- `wounded`
	- `bruised`
	- `in good shape`
- Result: PASS

### MT163 - Override return_appearance
- Added `return_appearance(looker)` to `typeclasses/characters.py`.
- The appearance now includes:
	- character name
	- description text
	- current condition
- Result: PASS

### MT164 - Add wield display
- Extended `return_appearance()` so wielded weapons appear in look output when present.
- Result: PASS

### MT165 - Add combat messaging helpers
- Added the following helpers to `typeclasses/characters.py`:
	- `get_attack_verb()`
	- `get_hit_result(damage)`
	- `get_attack_phrases(weapon_name)`
- These now drive layered combat phrasing for actor, target, and room messaging.
- Result: PASS

### MT166 - Replace attack messaging
- Updated `commands/cmd_attack.py` hit messaging to use layered DR-style output.
- Actor now receives two lines.
- Target now receives two lines.
- Room observers now receive one line.
- Result: PASS

### MT167 - Replace miss messaging
- Updated `commands/cmd_attack.py` miss messaging to use actor, target, and room lines instead of the earlier flat miss text.
- Result: PASS

### MT168 - Add disengage room messaging
- Updated `commands/cmd_disengage.py` to send room-visible combat exit messaging:
	- `<name> steps back from the fight.`
- Result: PASS

### MT169 - Standardize tend messaging tone
- Updated `commands/cmd_tend.py` room messaging to:
	- `<name> tends to their <part>.`
- Added generic limb aliases through body-part normalization so `arm`, `hand`, and `leg` resolve to tracked body parts instead of failing immediately.
- Result: PASS

### MT170 - Full visibility validation
- Reloaded Evennia successfully after implementation.
- Validated `look`/appearance output:
	- observed output included name, description, wielded weapon, and condition
	- example observed appearance:
		- `Jekar`
		- `A scarred veteran with a steady gaze.`
		- `They are wielding training sword.`
		- `They are wounded.`
- Validated hit messaging structure:
	- actor saw layered output including an attack line and a hit-result line
	- target saw layered output including the attack line and `You are hit!`
	- room observer received one room-facing combat line
- Validated miss messaging structure:
	- actor saw the miss line
	- target saw the miss line
	- room observer received one room-facing miss line
- Validated disengage visibility:
	- room observers received `Aedan steps back from the fight.`
- Validated tend visibility:
	- using `tend arm` succeeded through generic-limb alias resolution
	- room observers received `Aedan tends to their left arm.`
- Stability confirmation:
	- no crashes during reload or runtime probes
	- no duplicate command-side failures were introduced
- Result: PASS

## Batch Outcome

- Characters now have a minimal descriptive presentation layer through `look`.
- Combat text is now layered across actor, target, and observers instead of relying on a single flat line.
- Weapon visibility is now exposed in both appearance and combat phrasing.
- Disengage and tend now produce room-visible action text that fits the broader DR-style presentation layer.

## Post-Batch Performance Incident Note

- A later live regression produced severe command lag after restart:
	- `connect` commonly delayed by roughly `3s` to `10s`
	- simple live commands like `look`, `north`, and `south` delayed by roughly `5s` to `8s`
- Confirmed non-causes during investigation:
	- command/body rendering logic in `return_appearance()` was not the active root cause
	- telnet MCCP compression was hard-disabled and verified absent from the live handshake, but lag still reproduced
	- command execution itself remained fast once the server actually began processing the command
- Confirmed root cause:
	- the old `global_bleed_tick` in `server/conf/at_server_startstop.py` ran every second
	- each tick iterated all Character/NPC objects in the database (about `185` objects during diagnosis)
	- for each object it could call balance recovery, fatigue recovery, bleed processing, bleed-state updates, learning pulses, and NPC combat actions
	- those methods repeatedly touched default-normalization paths and, in some cases, emitted messages or executed commands, which blocked the Evennia reactor and stalled all live command handling
- Isolation proof:
	- temporarily disabling the ticker dropped movement latency from multi-second delays to about `0.04s` to `0.06s`
	- that established the ticker loop, not telnet compression, as the decisive cause of the lag
- Permanent fix applied:
	- retained hard MCCP-disable protection in `server/conf/settings.py`, `server/conf/telnet.py`, and `server/conf/mssp.py`
	- replaced the old monolithic 1-second global sweep with:
		- a lightweight `process_status_tick()` every `1s`
		- a separate `process_learning_tick()` every `10s`
	- skipped idle characters entirely
	- only processed balance/fatigue recovery, bleed work, learning pulses, and NPC combat when each object actually needed that work
	- removed per-pulse debug spam from `process_learning_pulse()`
- Verified post-fix live timings after full restart with the optimized tickers enabled:
	- `connect`: about `0.78s`
	- `look`: about `0.02s`
	- `look jekar`: about `0.10s`
	- room movement commands: about `0.55s` or better in the first post-fix pass, and near-instant once settled
- If this symptom ever returns, check these first:
	- `server/conf/at_server_startstop.py` for accidental reintroduction of a full-object 1-second sweep
	- any new periodic loop that iterates all characters/NPCs and calls default-normalization or command execution on each pass
	- live timing before and after temporarily disabling the global status/learning tickers
