## Report — Microtasks 261-280

### MT261 - Add stance system to Character
- Added stance state to `Character.at_object_creation()` in `typeclasses/characters.py`:
	- `self.db.stance = {"offense": 50, "defense": 50}`
- Added legacy-safe initialization through `ensure_combat_defaults()` so older characters also gain stance state.
- Result: PASS

### MT262 - Add stance normalization
- Added `normalize_stance()` to `typeclasses/characters.py`.
- Stance now normalizes offense/defense splits so they always total `100`.
- Result: PASS

### MT263 - Add set_stance method
- Added `set_stance(offense=None, defense=None)` to `typeclasses/characters.py`.
- Stance values are now clamped to valid bounds and normalized automatically.
- Result: PASS

### MT264 - Create stance command
- Added `commands/cmd_stance.py`.
- `stance` with no arguments now reports the current offense/defense split.
- `stance <0-100>` now sets offense directly and derives defense from the remainder.
- Registered the command in `commands/default_cmdsets.py`.
- Result: PASS

### MT265 - Apply stance to hit chance
- Updated `commands/cmd_attack.py`.
- Attacker offense stance now increases accuracy through:
	- `accuracy += stance["offense"] * 0.2`
- Result: PASS

### MT266 - Apply stance to defense
- Updated `commands/cmd_attack.py`.
- Defender defense stance now increases evasion through:
	- `evasion += target_stance["defense"] * 0.2`
- Result: PASS

### MT267 - Add positioning state
- Added position state to `Character.at_object_creation()` in `typeclasses/characters.py`:
	- `self.db.position = "standing"`
- Added legacy-safe initialization through `ensure_combat_defaults()`.
- Result: PASS

### MT268 - Add position modifiers
- Added `get_position_modifiers()` to `typeclasses/characters.py`.
- Position modifiers now resolve as:
	- `prone`: offense `-30`, defense `-20`
	- `kneeling`: offense `-10`, defense `+5`
	- `standing`: no modifier
- Result: PASS

### MT269 - Apply position to combat
- Updated `commands/cmd_attack.py`.
- Attacker and defender position modifiers now affect:
	- attack accuracy
	- target evasion
- Result: PASS

### MT270 - Add body part targeting
- Added targeted-body-part state to `Character.at_object_creation()` in `typeclasses/characters.py`:
	- `self.db.target_body_part = None`
- Added legacy-safe initialization through `ensure_combat_defaults()`.
- Added `resolve_targeted_body_part()` to map abstract targets like `arm` and `leg` to actual injury locations.
- Result: PASS

### MT271 - Create target command
- Added `commands/cmd_target.py`.
- `target <part>` now supports:
	- `head`
	- `chest`
	- `arm`
	- `leg`
- Registered the command in `commands/default_cmdsets.py`.
- Result: PASS

### MT272 - Apply targeting penalties
- Updated `commands/cmd_attack.py`.
- Targeting now applies accuracy penalties for harder locations:
	- `head`: `-20`
	- `arm` / `leg`: `-10`
- Result: PASS

### MT273 - Apply targeting bonuses
- Updated `commands/cmd_attack.py`.
- Targeting now applies damage bonuses for more precise attacks:
	- `head`: `+2`
	- `arm`: `+1`
- Result: PASS

### MT274 - Add target reset on disengage
- Updated `commands/cmd_disengage.py`.
- Disengaging now clears:
	- current combat target
	- `target_body_part`
- Result: PASS

### MT275 - Improve combat messaging (body part)
- Updated hit messaging in `commands/cmd_attack.py`.
- Successful attacks now explicitly mention the struck body part in actor, target, and room messaging.
- Result: PASS

### MT276 - Add critical hit chance (basic)
- Updated `commands/cmd_attack.py`.
- Added a basic `5%` critical-hit roll that doubles damage.
- Critical hits are reflected in the hit message text.
- Result: PASS

### MT277 - Add stun effect (basic)
- Updated `commands/cmd_attack.py`.
- Head hits now have a basic `10%` chance to set the target as stunned.
- Result: PASS

### MT278 - Add stunned block
- Added stunned state to `Character` combat defaults.
- Added stunned blocking to combat-relevant commands:
	- `attack`
	- `disengage`
	- `stance`
	- `target`
	- `use`
	- `wield`
- Blocked actions now emit `You are stunned!`.
- Implemented `consume_stun()` so the basic stun effect acts as a temporary action block rather than a permanent lock.
- Result: PASS

### MT279 - Validate full combat loop
- Performed deterministic live validation in Evennia shell using disposable characters, a disposable weapon, and mocked combat rolls.
- Validated:
	- `stance 70` normalized to offense `70` / defense `30`
	- `target head` set targeted body part correctly
	- targeted head attack applied the expected damage bonus
	- hit messaging included the struck body part
	- combat engagement state set correctly
	- disengage cleared both combat targeting and body-part targeting
	- stunned state blocked the next action and then cleared
- Result: PASS

### MT280 - Full system validation
- Reloaded Evennia successfully after implementation.
- Confirmed:
	- stance works
	- position modifiers are integrated into attack math
	- targeting works
	- critical hit and stun hooks are present
	- disengage cleanup works
	- combat remained stable during deterministic validation
- Result: PASS

## Batch Outcome

- Combat now has a tactical decision layer through stance, position, and targeted attacks.
- The system supports higher-risk precision attacks with meaningful tradeoffs.
- Basic critical and stun hooks are now in place for future combat depth.
- The combat layer is now positioned for future armor and mitigation work.

## Validation Summary

- Reloaded Evennia successfully after implementation.
- Performed deterministic live validation in Evennia shell with disposable characters and a disposable weapon.
- Used mocked random rolls so the validation covered the intended stance/targeting path rather than relying on chance.
- Confirmed:
	- stance normalization worked
	- targeted head attacks applied the expected bonus
	- body-part hit messaging appeared correctly
	- disengage cleared combat and targeting state
	- stunned state blocked a follow-up action and then cleared
- Deleted all disposable validation objects after the test completed.