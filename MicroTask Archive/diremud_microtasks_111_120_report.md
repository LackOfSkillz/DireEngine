## Report — Microtask 111

- File created: [typeclasses/weapons.py](/c:/Users/gary/dragonsire/typeclasses/weapons.py)
- Added the base `Weapon` typeclass with default combat fields:
    - `weapon_type`
    - `damage_min`, `damage_max`
    - `roundtime`
    - `balance_cost`, `fatigue_cost`
    - `skill`
    - `damage_type`
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed spawned weapons initialize with the expected defaults before customization.
- Result: MT111 PASS.

## Report — Microtask 112

- File modified: [typeclasses/characters.py](/c:/Users/gary/dragonsire/typeclasses/characters.py)
- Added `self.db.equipped_weapon = None` in `Character.at_object_creation()`.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed fresh Characters start with no equipped weapon.
- Result: MT112 PASS.

## Report — Microtask 113

- File modified: [typeclasses/characters.py](/c:/Users/gary/dragonsire/typeclasses/characters.py)
- Added `Character.get_weapon(self)` to centralize equipped-weapon lookup.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed the helper returns `None` before wielding and the equipped object after wielding.
- Result: MT113 PASS.

## Report — Microtask 114

- File modified: [typeclasses/characters.py](/c:/Users/gary/dragonsire/typeclasses/characters.py)
- Added `Character.get_weapon_profile(self)` with an unarmed fallback profile and a wielded-weapon profile derived from the equipped weapon's attributes.
- The unarmed fallback now provides:
    - damage `1–3`
    - roundtime `3`
    - balance cost `10`
    - fatigue cost `5`
    - skill `brawling`
    - damage type `impact`
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed both paths:
    - unarmed Characters returned the fallback profile
    - wielding a training sword returned the customized weapon profile with `damage_min = 3`, `damage_max = 6`, and `skill = light_edge`
- Result: MT114 PASS.

## Report — Microtask 115

- Files created/modified:
    - [commands/cmd_wield.py](/c:/Users/gary/dragonsire/commands/cmd_wield.py)
    - [commands/default_cmdsets.py](/c:/Users/gary/dragonsire/commands/default_cmdsets.py)
- Added `CmdWield` and registered it in the character cmdset so players can equip an object with `wield <item>`.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed a successful wield updates `equipped_weapon` and emits `You wield training sword.`.
- Result: MT115 PASS.

## Report — Microtask 116

- Files created/modified:
    - [commands/cmd_spawnweapon.py](/c:/Users/gary/dragonsire/commands/cmd_spawnweapon.py)
    - [commands/default_cmdsets.py](/c:/Users/gary/dragonsire/commands/default_cmdsets.py)
- Added `CmdSpawnWeapon` and registered it in the character cmdset so `spawnweapon` creates a test `training sword` with a customized combat profile:
    - damage `3–6`
    - roundtime `3`
    - balance cost `10`
    - fatigue cost `5`
    - skill `light_edge`
    - damage type `slice`
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed `spawnweapon` emitted `Weapon spawned.` and created a `training sword` in the caller's location.
- Result: MT116 PASS.

## Report — Microtask 117

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Replaced flat attack damage with profile-driven damage:
    - `profile = self.caller.get_weapon_profile()`
    - `damage = random.randint(profile["damage_min"], profile["damage_max"])`
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed wielded weapon damage varies inside the configured range; a training-sword hit produced `6` damage and reduced target HP from `100` to `94`.
- Result: MT117 PASS.

## Report — Microtask 118

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Replaced hardcoded attack resource costs with weapon-profile values on the hit path:
    - balance cost from `profile["balance_cost"]`
    - fatigue cost from `profile["fatigue_cost"]`
    - roundtime from `profile["roundtime"]`
- Preserved the clarified combat rule that misses still incur costs by moving the miss path to use the weapon profile's fatigue and roundtime values as well.
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed:
    - training-sword hit changed balance from `100/100` to `90/100` and fatigue from `0/100` to `5/100`
    - forced miss changed fatigue from `5/100` to `10/100`, entered roundtime, and left target HP unchanged
- Result: MT118 PASS.

## Report — Microtask 119

- File modified: [commands/cmd_attack.py](/c:/Users/gary/dragonsire/commands/cmd_attack.py)
- Added the required temporary weapon debug line:
    - `self.caller.msg(f"[DEBUG] Weapon:{profile.get('skill')} DMG:{damage}")`
- Reload result: `evennia reload` completed successfully with no errors.
- Runtime verification confirmed the line is emitted on successful hits, for example `[DEBUG] Weapon:light_edge DMG:6`.
- Result: MT119 PASS.

## Report — Microtask 120

- No additional code change was required beyond MT111–119; MT120 is a full validation task for the new weapon-driven combat layer.
- Reload result: `evennia reload` completed successfully with no errors.
- Shell-driven validation confirmed:
    - unarmed fallback profile returns `brawling` and damage range `1–3`
    - spawned training sword profile returns `light_edge` and damage range `3–6`
    - wielding the training sword changes the active combat profile
    - a controlled training-sword hit produced debug lines `[DEBUG] Roll:10 Chance:50` and `[DEBUG] Weapon:light_edge DMG:6`
    - the hit reduced target HP from `100` to `94`
    - miss path still consumed fatigue and roundtime while leaving target HP unchanged
- Additional manual in-game telnet validation was completed with a disposable account and character:
    - `spawnweapon` returned `Weapon spawned.`
    - explicit `wield training sword-2` returned `You wield training sword.`
    - successful live attack emitted `[DEBUG] Weapon:light_edge DMG:6` and `You hit corl for 6 damage.`
    - NPC retaliation still worked after the weapon-equipped attack
    - `disengage` still broke the combat loop cleanly
- Cleanup note: the disposable test account, its character, the spawned `corl` NPC, and all spawned `training sword` test objects were deleted after validation.
- Confirmation: combat is now weapon-driven, damage varies by profile, debug output shows both roll/chance and weapon/damage, roundtime and costs follow the active profile, NPC combat still works, and misses still incur roundtime/fatigue.
- Result: MT120 PASS.