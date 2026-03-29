## Report — Microtask 81

- File modified: [typeclasses/characters.py](/c:/Users/gary/dragonsire/typeclasses/characters.py)
- Added the default Character flag `self.db.is_npc = False` in `Character.at_object_creation()` so player-controlled Characters and NPCs can be distinguished cleanly.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification on a fresh Character object confirmed `char.db.is_npc == False`.
- Result: MT81 PASS.

## Report — Microtask 82

- File modified: [typeclasses/npcs.py](/c:/Users/gary/dragonsire/typeclasses/npcs.py)
- Added the basic `NPC` typeclass inheriting from `Character`, with `at_object_creation()` setting `self.db.is_npc = True`.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification on a spawned NPC confirmed `npc.db.is_npc == True`.
- Result: MT82 PASS.

## Report — Microtask 83

- Files modified:
	- [commands/cmd_spawnnpc.py](/c:/Users/gary/dragonsire/commands/cmd_spawnnpc.py)
	- [commands/default_cmdsets.py](/c:/Users/gary/dragonsire/commands/default_cmdsets.py)
- Added `CmdSpawnNPC` and registered it in the character cmdset so `spawnnpc` creates a test NPC named `corl` in the caller's room.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed `spawnnpc` emitted `NPC spawned.` and created `corl` in the caller's location.
- Result: MT83 PASS.

## Report — Microtask 84

- No code change was required.
- Audit result: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py) already performs mutual engagement with `self.caller.set_target(target)` followed by `target.set_target(self.caller)`, so NPCs automatically target the attacker when attacked.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed that after a player attacked an NPC, the NPC target became the player and `npc.db.in_combat` was `True`.
- Result: MT84 PASS.

## Report — Microtask 85

- File modified: [typeclasses/npcs.py](/c:/Users/gary/dragonsire/typeclasses/npcs.py)
- Added `NPC.npc_combat_tick()` as the basic AI hook for combat behavior.
- The hook exits cleanly when the NPC is not in combat, has no target, has a dead target, or the target has left the room; otherwise it attacks via `self.execute_cmd(f"attack {target.key}")`.
- Reload result: `evennia reload` completed successfully with no errors.
- Result: MT85 PASS.

## Report — Microtask 86

- File modified: [server/conf/at_server_startstop.py](/c:/Users/gary/dragonsire/server/conf/at_server_startstop.py)
- Extended the existing global ticker loop so it includes both Character and NPC typeclass paths and calls `npc_combat_tick()` for NPCs.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification through the actual ticker hook confirmed that after a player engaged an NPC, one call to `process_bleed_tick()` caused the NPC to attack back, reducing player HP to `90`.
- Result: MT86 PASS.

## Report — Microtask 87

- File modified: [typeclasses/npcs.py](/c:/Users/gary/dragonsire/typeclasses/npcs.py)
- Added the roundtime guard at the top of `npc_combat_tick()` so NPC AI respects the same pacing rules as players.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification called `npc_combat_tick()` twice back to back on an engaged NPC; after the first attack the NPC entered roundtime, and the second immediate tick produced `0` new hit messages and no additional HP loss.
- Result: MT87 PASS.

## Report — Microtask 88

- File modified: [typeclasses/npcs.py](/c:/Users/gary/dragonsire/typeclasses/npcs.py)
- Added dead-target protection inside `npc_combat_tick()` so NPCs clear target and stop combat when their target is no longer alive.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed that when an NPC was pointed at a defeated Character and `npc_combat_tick()` ran, the NPC cleared its target and left combat.
- Result: MT88 PASS.

## Report — Microtask 89

- No code change was required; MT89 is a combat-messaging verification task.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed both sides of the message flow in the live combat loop:
	- player attack path produced the expected player-facing `You hit ...` message
	- NPC retaliation through the ticker produced the expected player-facing `<npc> hits you for 10 damage.` message
- Result: MT89 PASS.

## Report — Microtask 90

- No additional code change was required beyond MT81–88; MT90 is a full combat-loop validation task.
- Reload result: `evennia reload` completed successfully with no errors.
- Full flow validated in deterministic Evennia scenarios:
	- `spawnnpc` produced a live test NPC in-room
	- player `attack` engaged the NPC and caused the NPC to target the player
	- the global ticker triggered NPC retaliation and respected roundtime pacing
	- immediate repeat NPC ticks during roundtime produced no extra hit messages
	- `disengage` cleared combat for both sides, and a subsequent NPC combat tick produced no new hits and no HP loss
- Confirmation: bidirectional combat works, roundtime is respected, `disengage` breaks the loop, and the NPC loop ran without crashes or message spam.
- Additional manual telnet-session validation was completed against the live server on port `4000` using a disposable account:
	- connected successfully with `connect <username> <password>`
	- `spawnnpc` returned `NPC spawned.`
	- `look` showed `corl` present in the room
	- `attack corl` produced `You engage corl.`, `You hit corl for 10 damage.`, and live retaliation `corl hits you for 10 damage.`
	- after waiting, the NPC attacked again through the live ticker
	- `disengage` returned `You disengage from combat.`
	- a final wait produced no further NPC attack messages, confirming the loop stopped in an actual client session
- Result: MT90 PASS.