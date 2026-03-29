## Report — Microtask 91

- File modified: [typeclasses/characters.py](/c:/Users/gary/dragonsire/typeclasses/characters.py)
- Added the base `stats` dictionary in `Character.at_object_creation()` with defaults for `strength`, `stamina`, `agility`, `reflex`, `discipline`, `intelligence`, `wisdom`, and `charisma`, all set to `10`.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification on a fresh Character object confirmed `char.db.stats["strength"] == 10`.
- Result: MT91 PASS.

## Report — Microtask 92

- File modified: [typeclasses/characters.py](/c:/Users/gary/dragonsire/typeclasses/characters.py)
- Added derived combat-resource pools in `Character.at_object_creation()`:
	- `balance = 100`, `max_balance = 100`
	- `fatigue = 0`, `max_fatigue = 100`
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification on a fresh Character object confirmed the expected starting values existed.
- Result: MT92 PASS.

## Report — Microtask 93

- File modified: [typeclasses/characters.py](/c:/Users/gary/dragonsire/typeclasses/characters.py)
- Added safe balance and fatigue accessors/setters:
	- `get_balance()` / `set_balance()`
	- `get_fatigue()` / `set_fatigue()`
- The implementation also includes `ensure_resource_defaults()` so legacy Characters/NPCs without the new fields are initialized safely when accessed instead of breaking runtime systems.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed setter clamping and normal getter output, for example `(50, 100)` for balance and `(10, 100)` for fatigue.
- Result: MT93 PASS.

## Report — Microtask 94

- File modified: [typeclasses/characters.py](/c:/Users/gary/dragonsire/typeclasses/characters.py)
- Added `Character.recover_balance()` to regenerate balance by `2` per recovery tick until the maximum is reached.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification through the live ticker callback confirmed balance changed from `50/100` to `52/100` after one recovery cycle.
- Result: MT94 PASS.

## Report — Microtask 95

- File modified: [typeclasses/characters.py](/c:/Users/gary/dragonsire/typeclasses/characters.py)
- Added `Character.recover_fatigue()` to reduce fatigue by `2` per recovery tick until it reaches `0`.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification through the live ticker callback confirmed fatigue changed from `10/100` to `8/100` after one recovery cycle.
- Result: MT95 PASS.

## Report — Microtask 96

- File modified: [server/conf/at_server_startstop.py](/c:/Users/gary/dragonsire/server/conf/at_server_startstop.py)
- Extended the existing global ticker loop so it now calls `character.recover_balance()` and `character.recover_fatigue()` before bleed processing and NPC AI handling.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification via the live `process_bleed_tick()` callback confirmed both resources updated in one ticker cycle: balance `50 -> 52`, fatigue `10 -> 8`.
- Result: MT96 PASS.

## Report — Microtask 97

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Added the attack balance cost so successful attacks now call `self.caller.set_balance(self.caller.db.balance - 10)`.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification through the real attack command path confirmed attacker balance dropped from `100/100` to `90/100` after one successful attack.
- Result: MT97 PASS.

## Report — Microtask 98

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Added the attack fatigue cost so successful attacks now call `self.caller.set_fatigue(self.caller.db.fatigue + 5)`.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification through the real attack command path confirmed attacker fatigue rose from `0/100` to `5/100` after one successful attack.
- Result: MT98 PASS.

## Report — Microtask 99

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Added the balance gate near the top of `CmdAttack.func()` so a caller with `balance <= 0` is blocked with `You are too off balance to attack.`.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed that after forcing attacker balance to `0`, `attack` emitted the expected block message and did not proceed.
- Result: MT99 PASS.

## Report — Microtask 100

- File modified: [commands/cmd_stats.py](/c:/Users/gary/dragonsire/commands/cmd_stats.py)
- Extended `stats` output to show the new combat-resource fields:
	- `Balance: <current>/<max>`
	- `Fatigue: <current>/<max>`
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed `stats` output now includes lines such as `Balance: 0/100` and `Fatigue: 5/100`.
- Additional validation confirmed NPCs inherit the same resource logic through their shared attack path: an NPC attack reduced NPC balance from `100/100` to `90/100`, increased fatigue from `0/100` to `5/100`, and damaged the victim to `90` HP.
- Additional manual telnet-session validation was completed against the live server on port `4000` using a disposable account:
	- pre-combat `stats` showed `HP: 100/100`, `Balance: 100/100`, `Fatigue: 0/100`
	- after a successful live `attack corl-3`, `stats` showed `HP: 90/100`, `Balance: 92/100`, `Fatigue: 3/100`, reflecting both attack costs and one recovery interval already having occurred in-session
	- after waiting through live ticker recovery, `stats` showed `Balance: 100/100` and `Fatigue: 0/100`, confirming the resources recover in a real client session as well
- Result: MT100 PASS.