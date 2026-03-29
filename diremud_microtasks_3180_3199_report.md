# DireMUD Microtasks 3180-3199 Report

## Scope

Integration patch only. Existing systems were extended in place.

## 3180-3183 Skill System Hook

- Live learning integration remains in `Character.use_skill()` in `typeclasses/characters.py`.
- Profession-weighted learning now happens there before mindstate is applied:
  - resolve `skillset` from current skill metadata category
  - read profession weight with `get_skill_weight(skillset)`
  - scale learning amount before `update_skill(..., mindstate=...)`
- The result is clamped so positive gains cannot drop below `1`.
- Debug output added:
  - `[XP] <character> <skillset> x<weight>`
- Rank gain remains in the existing `process_learning_pulse()` path, so the profession hook affects rank indirectly through existing mindstate accumulation rather than a new XP system.

## 3184-3186 Ability System Injection

- Existing ability resolution remains in `typeclasses/abilities.py` and `Character.use_ability()`.
- Added `PROFESSION_ABILITY_MAP` to the same registry module.
- Added `get_ability_map(character=None)` to merge profession abilities into the existing ability map.
- Merge is non-destructive:
  - profession abilities are inserted with `setdefault(...)`
  - existing abilities keep priority unless an override is made intentionally later
- `Character.use_ability()` and `Character.get_visible_abilities()` now resolve through the merged map.

## 3187-3189 Subsystem Lifecycle

- Added `Character.get_subsystem()` as the session-persistent subsystem accessor using `ndb`.
- On character creation and login:
  - `get_subsystem()` now runs in `at_object_creation()` and `at_post_puppet()`.
- On profession change:
  - `set_profession()` clears `ndb.subsystem`
  - then rebuilds it immediately through `get_subsystem()`
- Session persistence remains `ndb` only, as requested.

## 3190-3192 Client Message Pipeline

- Added `send_subsystem_update()` in `world/area_forge/character_api.py`.
- All subsystem updates now use structured message type `subsystem`.
- `Character.sync_client_state()` now sends subsystem updates alongside existing map and character updates.
- Added live browser handler in `web/static/webclient/js/dragonsire-browser-v2.js`:
  - `Evennia.emitter.on("subsystem", ...)`
  - logs `SUBSYSTEM:` to the browser console
- Browser-console arrival was wired end to end in code, but not manually verified in a live browser session during this pass.

## 3193-3195 NPC Trainer Integration

- Existing NPC base in `typeclasses/npcs.py` now has:
  - `db.is_trainer = False`
  - `db.trains_profession = None`
- Added trainer detection helper on `Character`:
  - `get_room_trainer()` uses `next(...)` over `room.contents` and checks `obj.db.is_trainer`
- Added trainer profession validation helper on `Character`:
  - denies when `trainer.db.trains_profession != caller.db.profession`

## 3196-3197 Guild Location Alignment

- Existing room system in `typeclasses/rooms.py` now initializes `room.db.guild_tag`.
- Added one profession-to-guild-tag mapping table in `typeclasses/characters.py`:
  - `PROFESSION_TO_GUILD`
- Added `Character.get_profession_guild_tag()` to consume that one mapping table.

## 3198-3199 Stealth System Extension

- Existing detection function remains `Character.can_perceive()`.
- Added profession-aware detection modifiers there:
  - thieves get `stealth_bonus += 10`
  - empaths get `perception_bonus += 5`
- Existing hidden-state, stealth total, perception total, and awareness logic were left intact.

## Result

- Skills are profession-weighted through the current learning path.
- Abilities still resolve through one registry path, now with a profession extension seam.
- Subsystems now exist as session state and are sent through the structured client pipeline.
- Trainers use the existing NPC structure.
- Rooms now carry a guild-tag alignment field.
- Stealth detection is profession-aware without replacing the current system.
