## Report — Microtask 101

- File modified: [typeclasses/characters.py](/c:/Users/gary/dragonsire/typeclasses/characters.py)
- Added `Character.get_stat(self, name)` to centralize stat access for combat calculations and return `0` safely when a named stat is missing.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed live stat access through a fresh Character object, including `get_stat("reflex") == 10`.
- Result: MT101 PASS.

## Report — Microtask 102

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Imported `random` and added `hit_roll = random.randint(1, 100)` inside the attack resolution path.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed the roll is generated and surfaced through the required debug line, for example `[DEBUG] Roll:7 Chance:50`.
- Result: MT102 PASS.

## Report — Microtask 103

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Added attacker accuracy calculation using `50 + reflex + agility` from the attacker's stats.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed the attacking Character's stat values were read through `get_stat()` and incorporated into the debug-reported hit chance.
- Result: MT103 PASS.

## Report — Microtask 104

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Added defender evasion calculation using the target's `reflex + agility`.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed defender stats were read from the target and contributed to the computed hit chance.
- Result: MT104 PASS.

## Report — Microtask 105

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Added the miss branch before damage resolution so a failed hit roll now emits `You miss <target>.` / `<attacker> misses you.` and exits before HP loss or injury application.
- Engagement is still established first, matching the task requirement that combat mutates only as far as engagement on a miss.
- Reload result: `evennia reload` completed successfully with no errors.
- Forced-miss runtime verification confirmed:
	- caller output: `[DEBUG] Roll:99 Chance:50`, `You miss <target>.`
	- target output: `<attacker> misses you.`
	- target HP stayed at `100`
	- target chest bleed stayed at `0`
	- both combatants still targeted each other after the miss
- Result: MT105 PASS.

## Report — Microtask 106

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Adjusted attack ordering so validation and hit resolution happen before damage, injury, and hit messaging.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification covered both paths:
	- on hit, the caller saw `You engage ...` and `You hit ... for 10 damage.` only after the debug line and hit check
	- on miss, no damage or hit messaging was emitted
- Result: MT106 PASS.

## Report — Microtask 107

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Added the minimum hit-chance clamp with `final_chance = max(10, accuracy - evasion)`.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed the combat path uses the clamped `final_chance` value exposed by the debug output.
- Result: MT107 PASS.

## Report — Microtask 108

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Added the maximum hit-chance clamp with `final_chance = min(95, final_chance)`.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed the final chance reported in debug output is the fully clamped value used for hit/miss resolution.
- Result: MT108 PASS.

## Report — Microtask 109

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Added the required temporary debug output: `self.caller.msg(f"[DEBUG] Roll:{hit_roll} Chance:{final_chance}")` immediately before hit/miss resolution.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed the debug line is visible in both shell-driven command tests and live telnet sessions.
- Result: MT109 PASS.

## Report — Microtask 110

- No additional code change was required beyond MT101–109; MT110 is a full validation task for the new probabilistic combat layer.
- Reload result: `evennia reload` completed successfully with no errors.
- Repeated live command-path validation against an NPC confirmed mixed outcomes without crashes:
	- some attempts emitted hit messages and changed HP
	- some attempts emitted miss messages and left HP unchanged
	- observed examples included `[DEBUG] Roll:3 Chance:50` with a hit and `[DEBUG] Roll:93 Chance:50` with a miss
- Additional manual telnet-session validation was completed against the live server on port `4000` using a disposable account:
	- `spawnnpc` created `corl`
	- first live attack showed a miss with debug output: `[DEBUG] Roll:61 Chance:50` followed by `You miss corl.`
	- later live attack showed a hit with debug output: `[DEBUG] Roll:34 Chance:50` followed by `You engage corl.` and `You hit corl for 10 damage.`
	- the NPC retaliation loop remained intact and itself produced misses/hits, including `corl misses you.` and `corl hits you for 10 damage.`
	- `disengage` still broke the loop cleanly
- Cleanup note: the disposable manual test account/character and spawned `corl` NPC were deleted after validation.
- Confirmation: combat is now probabilistic, stats influence the outcome, debug output is visible for this validation batch, NPC retaliation still works, and the system remained stable with no duplicate messaging or crashes.
- Result: MT110 PASS.

## Correction Note — Post-MT110 Miss Costs

- Combat rule clarification applied after MT110: missed attacks should still incur roundtime and fatigue.
- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- The miss branch now applies `self.caller.set_fatigue(self.caller.db.fatigue + 5)` and `self.caller.set_roundtime(3)` before returning.
- Reload result: `evennia reload` completed successfully with no errors.
- Forced-miss runtime verification confirmed the corrected behavior:
	- attacker fatigue changed from `0/100` to `5/100`
	- attacker entered roundtime
	- target HP remained `100`
	- target bleed remained `0`
	- miss messaging remained correct