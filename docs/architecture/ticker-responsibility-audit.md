# Shared Ticker Responsibility Audit

This document satisfies PH1-015 by breaking shared ticker work into concrete responsibilities and recording whether each responsibility should stay on a shared ticker, migrate to a more explicit primitive, or be removed.

Phase 1 scope reminder:

- this is an audit, not a mass migration plan
- timestamp-authoritative systems remain timestamp-authoritative in Phase 1
- `keep` means the shared cadence is still justified
- `migrate` means the responsibility should move out of the shared ticker in a later microtask
- `remove` means the responsibility is legacy or should disappear rather than move elsewhere

## Live Shared Ticker Registrations

| Ticker | Interval | System | File | Registration Site | Reason |
| --- | --- | --- | --- | --- | --- |
| `global_status_tick` | 1s | `world.status_tick` | `server/conf/at_server_startstop.py` | `at_server_start()` | State-gated global status processing for recovery, subsystem state, justice/thief/warrior updates, and AI. |
| `global_learning_tick` | 10s | `world.learning_tick` | `server/conf/at_server_startstop.py` | `at_server_start()` | Frequency-separated learning and teaching pulse processing. |

## Status Tick Responsibilities

`process_status_tick()` currently mixes genuinely shared cadence work with several hidden one-shot expiry scans. The table below records the Phase 1 decision for each responsibility.

| Responsibility | Current Entry Point | Decision | Execution-Order Dependency | Shared-State Reliance | Notes |
| --- | --- | --- | --- | --- | --- |
| Balance, fatigue, and attunement recovery | `process_status_tick()` -> `recover_balance()`, `recover_fatigue()`, `regen_attunement()` | `KEEP` | Low. Recovery runs after combat-range refresh and before later subsystem consumers, but the order is not tightly coupled to another ticker responsibility. | Medium. Reads per-character combat, fatigue, and attunement state and is already heavily state-gated. | This is still a legitimate grouped cadence: many active actors recover on the same 1-second boundary. Keep on the shared ticker unless recovery becomes individualized deadlines later. |
| Combat range upkeep | `process_status_tick()` -> `process_combat_range_tick()` | `KEEP` | Medium. Runs before later status consumers so combat state is fresh for the rest of the tick. | High. Depends on live combat state across actors in the same encounter. | Shared cadence remains justified because combat positioning is not a one-shot expiry. |
| Passive perception / awareness cleanup | `process_status_tick()` -> `process_passive_perception()` and awareness resets | `KEEP` | Medium. Uses current stealth/awareness state and should happen after state-gating but before the tick ends. | High. Depends on room occupants, hidden observers, and combat/awareness state. | This is ambient world perception work, not an isolated deadline. Shared cadence is appropriate. |
| Bleed processing and wound conditions | `process_status_tick()` -> `process_bleed()`, `update_bleed_state()`, `process_wound_conditions()` | `KEEP` | Medium. Bleed application and state refresh intentionally run together in the same tick. | High. Reads and mutates injury state and ongoing condition state. | Ongoing damage-over-time and condition progression are genuine recurring work. Keep grouped for now. |
| Magic state upkeep | `process_status_tick()` -> `process_magic_states()` | `MIGRATE` | Medium. Currently ordered before cyclic and subsystem updates, but most of the risky work is timestamp expiry cleanup rather than cadence-driven simulation. | Medium. Reads shared `states` data but primarily clears one-shot buff/debuff windows. | The one-shot expiry pieces should leave the shared ticker. If a smaller recurring magic cadence remains after extraction, reassess separately. |
| Cyclic magic sustain | `process_status_tick()` -> `process_magic_states()` -> `process_cyclic_effects()` | `KEEP` | Medium. Runs inside shared magic-state upkeep so cyclic processing sees the current effect container before other expiry cleanup. | High. Depends on active cyclic effect state and attunement pools. | Structured cyclic upkeep is recurring simulation work and stays on the shared ticker through the unified magic-state path. |
| Profession subsystem pulse | `process_status_tick()` -> `tick_subsystem_state()` | `KEEP` | Medium. Runs after core recovery and before profession-specific post-processing. | High. Uses profession controller state cached on the character and may update subsystem snapshots. | This is effectively a shared recurring profession-resource pulse. Keep, but watch for one-shot expiry logic hidden inside subsystem controllers. |
| Soul and resurrection recovery | `process_status_tick()` -> `process_soul_tick()`, `process_resurrection_recovery_tick()` | `KEEP` | Low. These are late-tick consumers of death/recovery state and do not currently gate other responsibilities. | Medium. Depends on death-state and recovery-state flags on the character. | The cadence is state-driven and recurring rather than a simple deadline. Keep unless later profiling shows they need their own controller. |
| Justice timers and custody messaging | `process_status_tick()` -> `process_justice_tick()` | `MIGRATE` | Low inside the ticker, but internally mixes unrelated timers. | Medium. Reads warrants, plea deadline, stocks message timestamps, and jail timers from the character. | This is an anti-pattern cluster: plea resolution is a one-shot expiry, stocks messaging is periodic messaging, and jail/fine handling are separate concerns. Split and migrate the one-shot paths out of the shared ticker. |
| Thief timed states | `process_status_tick()` -> `process_thief_tick()` | `MIGRATE` | Low. The ticker only provides a wake-up loop; the method itself polls multiple unrelated timestamps. | Medium. Uses many per-character timestamp fields such as mark, slip, intimidation, stagger, position, attention, and grace windows. | This is mostly hidden expiry cleanup. It should be decomposed into explicit scheduled expiries plus any truly recurring resource-drain cadence that remains. |
| Warrior temporary states and sustain | `process_status_tick()` -> `process_warrior_tick()` | `MIGRATE` | Medium. The method combines sustained combat exhaustion with timestamp expiry cleanup for temporary states and roars. | High. Reads combat state, exhaustion, tempo, berserk data, roar effects, and multiple `expires_at` entries. | This is mixed. The sustain pieces may stay recurring later, but the expiry cleanup portion should leave the shared ticker. Audit decision is `MIGRATE` because the method is not a clean shared-cadence unit today. |
| NPC AI wake-up loop | `process_status_tick()` -> `ai_tick()` | `MIGRATE` | Low at the ticker level. Each NPC immediately does its own `next_ai_tick_at` timestamp gate. | High. Reads target, surprise, combat timer, pursuit state, and per-NPC transient state. | This is a classic hidden per-object time check inside a global loop. The shared ticker is only acting as a poller. Plan extraction to scheduler/controller ownership later. |
| Trap sweep and trap expiration | Formerly `process_status_tick()` -> trap `at_tick()` sweep gated by `_TRAP_TICK_STATE["next_sweep_at"]`; now `deploy_trap()` -> `schedule_expiry()` | `MIGRATED` | Low. The extracted path no longer relies on ticker ordering. | Low. Authority remains on each trap's own placed-time and expire-time fields. | PH1-016 extracted this responsibility to keyed scheduler expiry in `typeclasses/trap_device.py`. |

## Learning Tick Responsibilities

`process_learning_tick()` is much narrower than the status tick and currently remains justified as a shared cadence.

| Responsibility | Current Entry Point | Decision | Execution-Order Dependency | Shared-State Reliance | Notes |
| --- | --- | --- | --- | --- | --- |
| Skill learning pulse | `process_learning_tick()` -> `process_learning_pulse()` | `KEEP` | Low. It only needs to run before the teaching pulse if both happen in the same pass. | Medium. Reads and mutates per-character skill mindstate tables. | This is a legitimate grouped 10-second cadence and already separated from the 1-second status loop. |
| Teaching pulse | `process_learning_tick()` -> `process_teaching_pulse()` | `KEEP` | Medium. Should follow the character's active learning state lookup in the same pass. | High. Depends on room co-location, teacher identity, and active `learning_from` state. | This remains valid shared cadence work because many learners can share the same coarse interval and it is not a one-shot deadline. |

## Legacy And Removal Notes

| Item | Decision | Notes |
| --- | --- | --- |
| `global_bleed_tick` legacy ticker ids removed during server start | `REMOVE` | These are cleanup guards for stale registrations, not live responsibilities. Keep the defensive unregister logic until confidence is high that no old registrations remain. |
| `BleedTicker` script deleted during server start | `REMOVE` | This script is already treated as deprecated invalid timing and should not return as a shared ticker replacement. |

## Dependency Risk Summary

Highest dependency-risk shared ticker work:

- combat range upkeep, passive perception, bleed progression, and subsystem pulses because they react to live actor state rather than isolated deadlines
- teaching pulses because they depend on teacher and student co-location at the time of execution

Highest extraction-value shared ticker work:

- justice timers
- thief timed states
- warrior temporary-state expiry cleanup
- NPC AI polling
- timestamp-driven magic-state expiry cleanup

## Phase 1 Outcome

PH1-015 conclusion:

- keep the shared learning ticker as-is for Phase 1
- keep only genuinely recurring status responsibilities on the 1-second status ticker
- treat justice, thief, warrior-expiry, AI polling, and magic-expiry cleanup as the main remaining extraction candidates after the PH1-016 trap-expiry migration