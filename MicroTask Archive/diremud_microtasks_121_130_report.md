## Report — Microtasks 121-130

### MT121 - Add weapon type taxonomy
- Added `WEAPON_TYPES` to `typeclasses/weapons.py` as the canonical weapon skill/type list:
	- `brawling`
	- `light_edge`
	- `heavy_edge`
	- `blunt`
	- `polearm`
	- `short_bow`
	- `long_bow`
	- `crossbow`
- Result: PASS

### MT122 - Normalize weapon skill mapping
- Updated `Weapon.at_object_creation()` so weapons default to a concrete skill mapping.
- Added `Weapon.get_weapon_skill()` with a `brawling` fallback.
- Result: PASS

### MT123 - Route skill usage from attack
- Updated `commands/cmd_attack.py` to resolve the active weapon skill from the equipped weapon profile.
- Routed combat through `self.caller.use_skill(skill_name, apply_roundtime=False, emit_placeholder=False, require_known=False)` so attacks now seed skill usage without replacing the existing combat path.
- Result: PASS

### MT124 - Add skill data structure expansion
- Expanded `self.db.skills` in `typeclasses/characters.py` to store per-skill dicts of the form `{"rank": 1, "mindstate": 0}`.
- Added normalization logic so existing characters are upgraded safely when accessed.
- Updated `learn_skill()` to preserve and normalize mapping-shaped skill data.
- Result: PASS

### MT125 - Add skill rank getter
- Added `get_skill_rank(skill_name)` to `typeclasses/characters.py`.
- Included a persistence-safe normalization fix so stored Evennia mapping-backed entries are read correctly instead of resetting to defaults.
- Result: PASS

### MT126 - Add skill gain stub
- Updated `use_skill()` so using a known or routed combat skill increments that skill's `mindstate` by `1`.
- No caps or pulse conversion were added in this batch.
- Result: PASS

### MT127 - Add hit bonus from skill
- Updated `commands/cmd_attack.py` so attack accuracy now includes `skill_rank`:
	- `accuracy = 50 + reflex + agility + skill_rank`
- Result: PASS

### MT128 - Add random body-part targeting
- Updated `commands/cmd_attack.py` to choose a random body part from the target injury map before applying damage.
- Replaced fixed chest damage with location-based `target.apply_damage(location, damage)`.
- Result: PASS

### MT129 - Add hit location messaging
- Updated combat messaging so both attacker and defender see the struck body location in hit messages.
- Result: PASS

### MT130 - Full system validation
- Reloaded Evennia successfully after implementation.
- Validated weapon taxonomy and weapon skill mapping:
	- `WEAPON_TYPES` returned the expected canonical list.
	- `Weapon.get_weapon_skill()` returned `light_edge` for the training sword test weapon.
- Validated combat skill hook and mindstate gain:
	- A forced hit with a `light_edge` weapon increased `light_edge` mindstate from `0` to `1`.
- Validated skill-rank hit bonus:
	- With the same forced roll of `60`, a `brawling` rank of `1` missed at `Chance:51`.
	- With the same forced roll of `60`, a `brawling` rank of `20` hit at `Chance:70`.
- Validated random body-part targeting and messaging:
	- Forced location targeting applied damage to `left_arm` and produced the expected location-specific hit messages for attacker and defender.
- Validated weapon-driven combat properties:
	- Forced-weapon tests confirmed weapon damage values are used.
	- Forced-weapon tests confirmed weapon roundtime is applied.
	- Forced-weapon tests confirmed weapon fatigue cost is applied.
- Validated bleed behavior after random location hits:
	- A forced `12` damage hit to `left_arm` increased `left_arm` bleed to `1`.
	- `is_bleeding()` returned `True` and bleed state updated to `light`.
- Validated NPC loop stability:
	- Player attacks still engaged NPCs correctly.
	- NPC retaliation still used the shared attack path and respected the updated location-based combat flow.
- Result: PASS

## Batch Outcome

- Weapon identity is now formalized through a shared taxonomy and weapon-to-skill mapping.
- Attacks now contribute to skill usage and mindstate gain without splitting the combat architecture into competing paths.
- Combat now varies by hit location, while still feeding the existing injury and bleed systems.
- Skill rank now directly influences combat accuracy, creating the first working combat-to-progression bridge.

## Notes

- During validation, a persistence bug was found in skill normalization: nested Evennia mapping-backed skill entries were being treated as non-dicts and reset to defaults.
- This was fixed by normalizing against `collections.abc.Mapping` rather than plain `dict`, which restored correct skill-rank reads and mindstate persistence.