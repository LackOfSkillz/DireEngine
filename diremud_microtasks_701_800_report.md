# DireMUD Microtasks 701-800 Report

## Scope

This report tracks implementation of MT 701-800 from [MT 701 - 800.md](c:/Users/gary/dragonsire/MT%20701%20-%20800.md), adapted to the current Evennia codebase.

Implementation rule used for this batch:
- When the document conflicts with an existing repo system, the document is treated as the source of truth.
- When the document assumes a new system that overlaps an existing repo system, the existing system is brought into line instead of creating a duplicate subsystem.

Current progress in this report:
- Completed MT 701-800

## Implemented

### MT 701-720
- Added a deployable trap-device workflow on top of the existing box-trap system instead of creating a second unrelated trap subsystem.
- Added [typeclasses/trap_device.py](c:/Users/gary/dragonsire/typeclasses/trap_device.py) with support for:
  - active/armed trap state
  - enemy-only trigger checks
  - hidden-room placement
  - expiration handling
- Extended [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py) with trap rework and deployment helpers:
  - `get_deployable_trap_device()`
  - `rework_trap()`
  - `deploy_trap()`
  - `detect_traps_in_room()`
  - `check_room_traps_for_enemy()`
- Added trap-state persistence on characters for reworking harvested/disarmed traps:
  - `last_disarmed_trap`
  - `last_disarmed_trap_difficulty`
  - `last_disarmed_trap_source`
- Updated the locksmithing/disarm/harvest flow so disarmed traps can be converted into room-deployed devices.
- Added [commands/cmd_rework.py](c:/Users/gary/dragonsire/commands/cmd_rework.py) and [commands/cmd_settrap.py](c:/Users/gary/dragonsire/commands/cmd_settrap.py).
- Registered the new trap commands in [commands/default_cmdsets.py](c:/Users/gary/dragonsire/commands/default_cmdsets.py).
- Hooked trap detection into movement and perception verbs:
  - movement via `Character.at_post_move()`
  - `search`
  - `observe`
- Hooked trap triggering into combat-start pressure in [commands/cmd_attack.py](c:/Users/gary/dragonsire/commands/cmd_attack.py).
- Hooked trap expiration into the global status tick in [server/conf/at_server_startstop.py](c:/Users/gary/dragonsire/server/conf/at_server_startstop.py).

### MT 721-740
- Added Lore skills to the registry in [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py):
  - `appraisal`
  - `scholarship`
  - `tactics`
  - `trading`
- Seeded starter Lore skills so new characters begin with:
  - `appraisal = 1`
  - `trading = 1`
- Added coins as a persisted character resource to support the first economy loop.
- Added appraisal and comparison helpers in [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py):
  - `get_item_value()`
  - `describe_weapon()`
  - `describe_armor()`
  - `appraise_target()`
  - `compare_items()`
- Added a minimal vendor system with [typeclasses/vendor.py](c:/Users/gary/dragonsire/typeclasses/vendor.py).
- Added vendor-facing character helpers:
  - `is_vendor_target()`
  - `get_nearby_vendor()`
  - `sell_item()`
- Added [commands/cmd_appraise.py](c:/Users/gary/dragonsire/commands/cmd_appraise.py), [commands/cmd_compare.py](c:/Users/gary/dragonsire/commands/cmd_compare.py), [commands/cmd_sell.py](c:/Users/gary/dragonsire/commands/cmd_sell.py), and [commands/cmd_spawnvendor.py](c:/Users/gary/dragonsire/commands/cmd_spawnvendor.py).
- Registered the new Lore commands in [commands/default_cmdsets.py](c:/Users/gary/dragonsire/commands/default_cmdsets.py).
- Hooked `tactics` into combat accuracy in [commands/cmd_attack.py](c:/Users/gary/dragonsire/commands/cmd_attack.py).
- Hooked `scholarship` into learning gain scaling through `use_skill()`.

### MT 741-760
- Expanded appraisal into tier-based output in [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py) with:
  - `get_appraisal_tier()`
  - tier-aware weapon descriptions
  - tier-aware armor descriptions
  - tier-aware value descriptions
- Added trading contest and haggling support:
  - `trading_contest()`
  - `haggle_with()`
  - one-shot `haggle_bonus` consumption in `sell_item()`
- Added teaching support in [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py):
  - `start_teaching()`
  - `get_teaching_strength()`
  - `process_teaching_pulse()`
- Added tactical stance assessment with `assess_stance()` and one-shot `tactics_prep` state.
- Added [commands/cmd_haggle.py](c:/Users/gary/dragonsire/commands/cmd_haggle.py), [commands/cmd_teach.py](c:/Users/gary/dragonsire/commands/cmd_teach.py), [commands/cmd_endteach.py](c:/Users/gary/dragonsire/commands/cmd_endteach.py), and [commands/cmd_assessstance.py](c:/Users/gary/dragonsire/commands/cmd_assessstance.py).
- Registered the advanced Lore commands in [commands/default_cmdsets.py](c:/Users/gary/dragonsire/commands/default_cmdsets.py).
- Extended [server/conf/at_server_startstop.py](c:/Users/gary/dragonsire/server/conf/at_server_startstop.py) so the learning tick also processes active teaching relationships.
- Updated [commands/cmd_attack.py](c:/Users/gary/dragonsire/commands/cmd_attack.py) so `tactics_prep` is consumed during attack resolution.

### MT 761-780
- Completed the final Lore layer in [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py):
  - `recall_knowledge()`
  - `study_item()`
  - `create_vendor_inventory_item()`
  - `buy_item()`
- Added [typeclasses/study_item.py](c:/Users/gary/dragonsire/typeclasses/study_item.py) for repeatable study objects/books.
- Added [commands/cmd_recall.py](c:/Users/gary/dragonsire/commands/cmd_recall.py), [commands/cmd_study.py](c:/Users/gary/dragonsire/commands/cmd_study.py), and [commands/cmd_buy.py](c:/Users/gary/dragonsire/commands/cmd_buy.py).
- Registered those commands in [commands/default_cmdsets.py](c:/Users/gary/dragonsire/commands/default_cmdsets.py).
- Added diminishing returns for study items through `study_uses` tracking.
- Added buy-side trading influence so vendor buying is no longer a sell-only economy loop.
- Refined teaching so it:
  - stops when teacher and student are separated
  - slows near skill parity
  - gives periodic feedback to both participants
- Refined appraisal so Perception gates appraisal detail without creating a duplicate appraisal subsystem.

### MT 781-800
- Added the core Magic skillset in [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py):
  - `attunement`
  - `arcana`
  - `augmentation`
  - `debilitation`
  - `warding`
  - `utility`
  - `targeted_magic`
- Added starter seeding for:
  - `attunement = 1`
  - `arcana = 1`
- Added attunement resource support in [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py):
  - `attunement`
  - `max_attunement`
  - `regen_attunement()`
  - `spend_attunement()`
- Hooked attunement regeneration into [server/conf/at_server_startstop.py](c:/Users/gary/dragonsire/server/conf/at_server_startstop.py).
- Added [typeclasses/luminar.py](c:/Users/gary/dragonsire/typeclasses/luminar.py) as the first Radiance storage item.
- Added luminar interaction helpers in [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py):
  - `charge_luminar()`
  - `invoke_luminar()`
- Added [commands/cmd_charge.py](c:/Users/gary/dragonsire/commands/cmd_charge.py) and registered it.
- Added the first prepare/cast path in [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py):
  - `prepare_spell()`
  - `cast_spell()`
  - `resolve_spell()`
- Added [commands/cmd_prepare.py](c:/Users/gary/dragonsire/commands/cmd_prepare.py) and [commands/cmd_cast.py](c:/Users/gary/dragonsire/commands/cmd_cast.py), and registered them.
- Added the first example spell, `flare`, as a stubbed but functional targeted-magic release.

## Validation

Validated outcomes for MT 701-720:
- Trap rework creates a deployable trap device from a disarmed trap.
- Trap deployment moves the device into the room and enforces owner-bound room placement.
- Trap detection works through movement and perception verbs.
- Enemy-only triggering works at combat initiation.
- Expired trap devices are cleaned up by the global tick.

Validated outcomes for MT 721-740:
- New characters seed `appraisal = 1` and `trading = 1`.
- Selling to a vendor grants coins and removes the sold item.
- `appraise` and `compare` run without crashes and train the intended Lore skill path.
- Scholarship scaling applies to the shared learning system.
- Tactics contributes to combat accuracy.

Validated outcomes for MT 741-760:
- Haggle bonuses are created and consumed correctly.
- Teaching pulses grant learning progress.
- `assessstance` sets tactical preparation state and that state is consumed in combat.
- Advanced Lore command registrations and imports validated cleanly.

Validated outcomes for MT 761-780:
- `recall` scales output by Scholarship instead of relying on hardcoded encyclopedia data.
- `study` only works on study items, respects difficulty, and hits diminishing returns.
- `buy` works through vendor inventory and uses Trading-adjusted prices.
- Teaching now clears correctly on separation and slows near parity.
- Appraisal/perception refinement works without crashing and remains tied to the existing appraisal system.

Validated outcomes for MT 781-800:
- Starter magic skills seed correctly for `attunement` and `arcana`.
- Attunement drains on prepare and regenerates through the shared tick path.
- Luminar charging stores attunement correctly and can be invoked during casting.
- `prepare flare 10` and `cast` run without crashes.
- `flare` releases an outward flash message and uses the new magic foundation instead of a duplicate combat subsystem.

## Notes

- This report is intentionally scoped only to MT 701-800.
- Post-800 follow-up work, including later guild-aware magic gating and appraisal roundtime/polish changes, is not part of this report range.