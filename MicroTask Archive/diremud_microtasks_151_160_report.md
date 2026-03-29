## Report — Microtasks 151-160

### MT151 - Add difficulty helper
- Reused the existing `get_skill_rank()` helper in `typeclasses/characters.py` as the central rank lookup for difficulty-based learning.
- No behavioral change to rank lookup semantics was required.
- Result: PASS

### MT152 - Add difficulty calculation
- Added `calculate_difficulty_ratio(skill_name, difficulty)` to `typeclasses/characters.py`.
- The helper returns `2.0` for non-positive difficulty values so those cases are treated as trivial.
- Result: PASS

### MT153 - Add difficulty band resolver
- Added `get_difficulty_band(ratio)` to `typeclasses/characters.py`.
- The helper resolves difficulty into the bands `trivial`, `easy`, `optimal`, `hard`, and `too_hard`.
- Result: PASS

### MT154 - Map band to learning gain
- Added `get_learning_gain(band)` to `typeclasses/characters.py`.
- The current mapping is:
	- `trivial -> 0`
	- `easy -> 1`
	- `optimal -> 3`
	- `hard -> 2`
	- `too_hard -> 1`
- Result: PASS

### MT155 - Add difficulty entry point
- Added `get_learning_amount(skill_name, difficulty)` to `typeclasses/characters.py`.
- The helper now returns `(gain, band)` as the unified learning decision point.
- Result: PASS

### MT156 - Integrate difficulty into use_skill
- Updated `use_skill()` in `typeclasses/characters.py` to use difficulty-aware learning instead of a flat `+1` mindstate gain.
- The method now:
	- reads `difficulty` from kwargs
	- resolves `(gain, band)` through `get_learning_amount()`
	- applies no learning for trivial outcomes
	- caps resulting mindstate with `get_mindstate_cap()`
- Added an optional `return_learning=True` mode so callers can receive `(gain, band)` for tuning/debug purposes without breaking existing call sites.
- Result: PASS

### MT157 - Pass difficulty from attack
- Updated `commands/cmd_attack.py` so attack-driven learning difficulty is derived from the target:
	- `difficulty = target.get_stat("reflex") + target.get_stat("agility")`
- Attack now passes that value into `use_skill()`.
- Result: PASS

### MT158 - Add debug output for tuning
- Updated `commands/cmd_attack.py` to capture the returned learning band from `use_skill(..., return_learning=True)`.
- Added temporary debug output:
	- `[DEBUG] Learning band: <band>`
- Result: PASS

### MT159 - Prevent learning on extreme failure
- Confirmed the miss branch in `commands/cmd_attack.py` still does not call `use_skill()`.
- Misses continue to consume fatigue and roundtime, but they do not grant learning.
- Result: PASS

### MT160 - Full validation
- Reloaded Evennia successfully after implementation.
- Validated helper-level difficulty behavior with `brawling` rank `20`:
	- `difficulty = 10` -> `(0, 'trivial')`
	- `difficulty = 16` -> `(1, 'easy')`
	- `difficulty = 22` -> `(3, 'optimal')`
	- `difficulty = 35` -> `(2, 'hard')`
	- `difficulty = 60` -> `(1, 'too_hard')`
- Validated real attack-path learning against different targets:
	- weak target produced `Learning band: trivial` and `mindstate = 0`
	- equal target produced `Learning band: optimal` and `mindstate = 3`
	- strong target produced `Learning band: too_hard` and `mindstate = 1`
- Validated combat stability after integration:
	- attacks still resolved normally
	- roundtime still applied
	- NPC retaliation still functioned
	- no crashes occurred during reload or runtime tests
- Additional stability confirmation:
	- a live player-vs-NPC test showed `Learning band: too_hard`, mindstate gain still occurred correctly, NPC combat remained active, and roundtime stayed enforced.
- Result: PASS

## Batch Outcome

- Learning now follows a difficulty curve instead of a flat success reward.
- Trivial targets no longer teach.
- Parity targets now provide peak learning.
- Overwhelming targets still teach, but at a reduced rate.
- The attack path now produces tuning-visible learning-band output without changing the core combat architecture.
