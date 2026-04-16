# Guard Patrol Stabilization Notes

Updated: 2026-04-14

## Scheduler Inventory

- Evennia ticker owner wiring: `server/conf/at_server_startstop.py::at_server_start()` via `_run_guard_ticker_tick()`.
- Persistent global script owner wiring: `typeclasses/scripts.py::GlobalGuardPatrolScript.at_repeat()`.
- Status fallback owner wiring: `server/conf/at_server_startstop.py::process_status_tick()`.
- Reactor fallback owner wiring: `server/conf/at_server_startstop.py::_schedule_guard_reactor_tick()`.

Current stabilization rule:

- `GUARD_PATROL_OWNER` is the single authoritative owner switch.
- Allowed values in this slice: `global_script`, `ticker`, `disabled`.
- Current selected owner: `global_script`.
- Status and reactor fallback are intentionally fail-closed in this slice and do not co-own patrol.

## Current Execution Reality

- The patrol owner loop is still centralized around `world/systems/guards.py::process_guard_tick()`.
- The global loop now exists only to iterate active guards and call `process_guard_behavior_tick(guard, stats=...)`.
- The actual guard brain already lives in per-guard functions, especially:
  - `process_guard_behavior_tick(guard, stats=None)`
  - `guard_movement_tick(guard, stats=None)`
  - `decay_suspicion(guard, ...)`
  - `_process_guard_enforcement(guard, actor)`
  - `_get_valid_guard_exits(guard, room)`
  - `_select_guard_exit(guard, exits, force_move=False)`
  - `_select_targeted_exit(guard, exits)`
  - `_guard_patrol_move_to(guard, destination)`

## Idle Optimization Reality

- There is no true sleep or dormancy system yet.
- Guards are still considered every patrol pass.
- Existing throttles are limited to movement and flavor cadence, mainly:
  - `GUARD_MOVE_COOLDOWN`
  - `GUARD_IDLE_MAX`
- `GUARD_DWELL_THRESHOLD`
- `GUARD_MOVE_CHANCE`
- `GUARD_MESSAGE_COOLDOWN`
  - `last_move_time`
  - `last_idle_time`
  - idle-look cooldown logic
- `last_room_id`
- per-guard last-message tracking

## Temporary Stabilization Findings

- The chosen temporary owner is the persistent `global_guard_patrol` script.
- A re-entrancy guard now prevents nested `process_guard_tick()` execution in-process.
- Per-tick instrumentation now records:
  - candidate guard count
  - active guard count
  - duplicate/inactive skips
  - enforcement count
  - patrol reached count
  - idle count
  - moved count
  - message count
  - no-exit count
  - failed preconditions
  - failed move-helper count
  - completed moves
  - exception count
  - estimated moves per minute
  - estimated idle cycles per minute
  - estimated messages per minute
  - total duration in ms

Manual validation snapshot after instrumentation:

- active guards: 15
- patrol reached: 15
- moved: 7
- re-entrant invocation: skipped as expected

## Per-Guard Migration Shape

Target future shape for `GuardBehaviorScript`:

- attaches to one guard
- owns one timer
- calls existing per-guard brain helpers
- does not iterate other guards globally

Future migration mode placeholder:

- `GUARD_PATROL_MODE = global | per_guard`
- extended current values: `global | hybrid | per_guard`
- current default value: `hybrid`
- current rollout mechanism: first `N` guards by ascending guard id via `GUARD_PER_GUARD_ROLLOUT_COUNT`

## Per-Guard Ownership Implementation

- `typeclasses.scripts.GuardBehaviorScript` now exists as the per-guard owner.
- The script is:
  - persistent
  - repeating
  - object-attached through `self.obj`
  - jittered on creation via `GUARD_PER_GUARD_JITTER`
- The script does not iterate all guards.
- The script validates `self.obj`, checks whether the guard should currently use per-guard ownership, and then calls `process_guard_behavior_tick(guard, source=...)`.

Lifecycle helpers now in `world/systems/guards.py`:

- `ensure_guard_behavior_script(guard)`
- `remove_guard_behavior_script(guard)`
- `sync_guard_execution_mode(guard)`
- `sync_all_guard_behavior_scripts()`
- `guard_has_per_guard_ownership(guard)`
- `should_guard_use_per_guard_execution(guard)`

These helpers enforce the rule that one guard may have at most one `GuardBehaviorScript` attached.

## Hybrid Cutover Rules

- In `hybrid` mode, only the rollout subset receives `GuardBehaviorScript` ownership.
- The global owner loop still runs for non-migrated guards.
- The global loop now explicitly skips guards that currently have per-guard ownership, preventing double-driving.
- Tick summaries now record:
  - `global_owned_count`
  - `per_guard_owned_count`
  - `skipped_per_guard_owned_count`

## Uniqueness And Lifecycle Rules

- One guard may have at most one patrol behavior script of the future per-guard type.
- Future attach points:
  - guard spawn
  - guard bootstrap/repair
  - explicit guard creation tools
- Future detach points:
  - guard deletion
  - guard deactivation/disable
  - migration cleanup/repair

## Builder Compatibility Note

- Builder does not depend on the global patrol loop specifically.
- Builder only needs stable authoritative location updates.
- A future per-guard script model remains compatible with Builder real-time polling as long as guards continue updating live room location normally.

Runtime validation after the per-guard migration slice:

- Hybrid startup sync after reload attached exactly one per-guard behavior script with rollout count `1`.
- Global patrol summary after reload reported:
  - `global_owned_count = 14`
  - `per_guard_owned_count = 1`
  - `skipped_per_guard_owned_count = 1`
- Rollback validation succeeded:
  - switching mode to `global` removed the attached per-guard script cleanly
  - switching back to `hybrid` restored one attached script
- Manual per-guard Builder visibility check succeeded:
  - guard `24568`
  - exported room id changed from `4376` to `4387`
  - `process_guard_behavior_tick(..., source='per_guard_manual_validation')` returned `moved`
- Automatic 30-second export monitor under hybrid mode still showed `changed_npc_count = 0`.

Current interpretation:

- Per-guard ownership, dedupe, hybrid filtering, and rollback are working.
- Builder can observe per-guard-owned room changes when that guard executes behavior.
- Autonomous runtime cadence still needs further validation and may still be affected by the broader scheduler/logging issue already identified earlier.

## Current Cadence Rules

- Guards now persist `last_room_id` separately from the older `previous_room_id` compatibility field.
- Normal patrol exit selection excludes exits that lead directly back to `last_room_id` when any other valid exit exists.
- If every valid exit leads back to `last_room_id`, the guard is allowed to backtrack instead of freezing.
- Patrol movement now respects a minimum dwell gate via `last_move_time` and `GUARD_DWELL_THRESHOLD`.
- Even after dwell is satisfied, non-targeted patrol movement is probabilistic through `GUARD_MOVE_CHANCE`, which reduces mechanical every-tick marching.
- Movement-decision debug logs now explicitly distinguish dwell skips, random skips, completed moves, and forced fallback backtracks when the guard patrol debug flag is enabled.

## Current Atmosphere Rules

- Patrol flavor is now split into independent `arrival`, `idle`, and `departure` message pools.
- Each guard persists `last_message_type`, `last_message_id`, and `last_message_time`.
- Immediate repetition of the same message within the same category is blocked when that category has more than one variant.
- Message output is gated by `GUARD_MESSAGE_COOLDOWN`, with arrival messaging allowed to bypass the same-move departure cooldown so one successful patrol step can still produce both a departure and an arrival line.
- Idle messaging only runs during non-movement cycles and remains probabilistic through `GUARD_IDLE_MESSAGE_CHANCE`.
- The low-level patrol helper no longer emits the generic announce-move spam for patrol steps; the atmosphere pool now owns patrol enter/leave flavor.

## Validation Snapshot

Focused runtime validation on 2026-04-14 confirmed:

- a forced patrol step from a room with two exits avoided the immediate return path and moved to the alternate room
- a forced patrol step from a dead-end room still backtracked when that was the only valid exit
- a dwell-blocked cycle stayed in place and emitted an idle-vigilance message
- a successful move emitted directionally correct patrol flavor: departure used the traveled exit direction and arrival used the entry direction in the destination room

## Updated 061.5 + 071 Rules

- `GuardBehaviorScript` now rolls a per-guard repeat interval between `25.0` and `45.0` seconds.
- Each per-guard script also rolls a numeric start delay between `0.0` and its current interval so guards do not wake up in lockstep after reboot or repair.
- Healthy per-guard scripts are no longer restarted during sync; repair only occurs when the attached script is missing or has no next repeat scheduled.
- Default guard patrol radius is now `20`, which widens normal wandering without changing Builder-visible location authority.
- Recent-room memory is now kept unique by recency so exit scoring can distinguish truly fresh rooms from recently revisited ones.
- Exit scoring now more strongly rewards unseen destinations, penalizes recently visited destinations, and penalizes rooms that already contain other guards.
- When multiple guards are stacked in the current room, patrol movement gets a small extra push toward dispersal instead of letting the whole group linger.
- Patrol atmosphere is now locked to the exact arrival, idle, and departure message sets approved for this slice.
- Per-guard message repetition tracking now uses `last_message_type`, `last_message_index`, and `last_message_time`.

## Updated Validation Snapshot

Focused runtime validation on 2026-04-14 additionally confirmed:

- a forced selector pick preferred an unseen room over two recently visited options without using the immediate backtrack fallback
- a forced selector pick preferred an empty destination over an otherwise valid room already containing two guards
- patrol flavor emitted the exact approved text set for departure, arrival, and idle lines during deterministic validation

## Updated 091-120 Rules

- Guard exit selection now treats any traversable Evennia exit object with a valid destination as a patrol candidate; it no longer depends on hardcoded direction names.
- Exit messaging now normalizes labels through `get_exit_label(exit_obj)`, which keeps cardinal exits as `north`, `west`, and similar values while exposing non-standard exits as labels like `the gate`, `the path`, or `the walkway`.
- Guards now persist `zone_id` alongside the older `zone` compatibility field.
- Rooms now persist `zone_id` plus the room-level boundary flags `no_npc_wander`, `guild_area`, and `npc_boundary`.
- Patrol filtering now hard-blocks exits whose destinations are outside the guard's `zone_id`, are marked `no_npc_wander`, or are marked `guild_area`.
- Soft patrol preferences still relax recent-room and immediate-backtrack rules when needed, but hard zone and restriction blocks never relax.
- Boundary rooms are allowed as patrol destinations, but when a guard is already on a boundary room the selector now prefers staying on the boundary perimeter over drifting away from it when multiple valid exits remain.
- Builder room creation and export now surface `zone_id`, `no_npc_wander`, `guild_area`, and `npc_boundary`, and Builder-spawned guard-tagged NPC templates now create real `GuardNPC` instances that inherit the room `zone_id`.

## Updated Boundary Validation Snapshot

Focused runtime validation on 2026-04-14 additionally confirmed:

- a boundary-room guard with exits `walkway`, `gate`, and `archway` only retained the in-zone `walkway` exit as patrol-valid
- a forced selector pick from that boundary room chose the non-standard in-zone exit and normalized its message label to `the walkway`
- non-standard patrol messaging produced `leaving through the walkway` and `in from the path` style text without collapsing labels
- Builder-created rooms persisted `zone_id`, `no_npc_wander`, and `npc_boundary`, and Builder-spawned guard-tagged NPCs inherited the destination room `zone_id`