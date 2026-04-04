# Timing Inventory

This document is the live-code inventory for Phase 1.

It records current timing paths by subsystem, timing primitive, and authority model.

DireTest coverage for completed timing migrations now lives in `docs/architecture/diretest-timing-coverage.md`.

Phase 1 constraint:

- timestamp state remains authoritative where it already exists
- scheduler usage in Phase 1 standardizes execution and metadata, not authoritative ownership
- no migration decisions are finalized here beyond candidate identification

## Classification Legend

- `ONE_SHOT`: direct one-off delay
- `SCHEDULED_EXPIRY`: keyed scheduler event
- `CONTROLLER`: Script-based orchestration or repeat-driven state holder
- `SHARED_TICKER`: shared Evennia ticker callback
- `INVALID`: timing path should not remain in its current shape long-term

## Direct Delay Usage

| Subsystem | Classification | Authority | File | Entry Point | Notes |
| --- | --- | --- | --- | --- | --- |
| Death emote follow-up | `ONE_SHOT` | event-local | `typeclasses/characters.py` | `die()` | Uses `delay(1.0, room.msg_contents, ...)` to separate death messaging from immediate death processing. |
| Observe awareness reset | `ONE_SHOT` | callback-local | `typeclasses/abilities_perception.py` | `ObserveAbility.execute()` | Uses `delay(10, clear_observe)` to clear temporary observing state. |
| Telnet handshake timeout | `ONE_SHOT` | protocol-local | `server/conf/telnet.py` | `NoMCCPTelnetProtocol.connectionMade()` | Uses `delay(2, callback=self.handshake_done, timeout=True)` for protocol setup. |

## Scheduler Usage

| Subsystem | Classification | Authority | File | Entry Point | Notes |
| --- | --- | --- | --- | --- | --- |
| Roundtime expiry | `SCHEDULED_EXPIRY` | `db.roundtime_end` timestamp | `typeclasses/characters.py` | `set_roundtime()`, `_expire_roundtime()` | Scheduler handles keyed expiry execution; `roundtime_end` remains the authoritative state check. |
| Thief roundtime expiry | `SCHEDULED_EXPIRY` | `db.roundtime_end` timestamp | `typeclasses/characters.py` | `apply_thief_roundtime()` | Extends the same keyed expiry model for stacked thief RT. |
| Scheduler execution surface | `SCHEDULED_EXPIRY` | scheduler registry | `world/systems/scheduler.py` | `schedule()`, `cancel()`, `reschedule()`, `flush_due()`, `get_scheduler_snapshot()` | Phase 0 surface already exists and is the baseline for Phase 1 metadata and key normalization. |

## Dual-Mode Timing Systems

Some systems currently use timestamp authority plus scheduler enforcement.

These are transitional by design and must not be converted to scheduler-owned authoritative state in Phase 1.

| Subsystem | Authority Model | Enforcement Model | File | Notes |
| --- | --- | --- | --- | --- |
| Roundtime | `db.roundtime_end` timestamp | keyed scheduler expiry callback | `typeclasses/characters.py` | Canonical Phase 0 hybrid model; gameplay checks read the timestamp while scheduler expiry clears state when due. |
| Thief-applied roundtime | `db.roundtime_end` timestamp | keyed scheduler expiry callback | `typeclasses/characters.py` | Uses the same hybrid authority model as base RT and inherits the same Phase 1 no-migration rule. |

## Shared Ticker Usage

| Subsystem | Classification | Authority | File | Entry Point | Dependency Risk | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Global status tick | `SHARED_TICKER` | mixed per-subsystem state | `server/conf/at_server_startstop.py` | `at_server_start() -> process_status_tick()` | `HIGH` | Registered every 1 second as `global_status_tick`; heavily state-gated but still carries many responsibilities. |
| Global learning tick | `SHARED_TICKER` | skill and teaching state | `server/conf/at_server_startstop.py` | `at_server_start() -> process_learning_tick()` | `LOW` | Registered every 10 seconds as `global_learning_tick`; separated from combat/status work. |
| Trap expiration | `SCHEDULED_EXPIRY` | trap `placed_time` + `expire_time` timestamp authority | `typeclasses/trap_device.py`, `typeclasses/characters.py` | `deploy_trap() -> schedule_expiry()` | `LOW` | PH1-016 migrated trap expiry from the status ticker to a keyed scheduler event while keeping timestamp authority on the trap object. |

### Shared Ticker Responsibilities

Detailed keep/migrate/remove decisions for each shared ticker responsibility now live in `docs/architecture/ticker-responsibility-audit.md`.

`process_status_tick()` in `server/conf/at_server_startstop.py` currently drives or gates all of the following:

- balance, fatigue, and attunement recovery
- magic state expiration and cyclic processing
- bleed and wound condition processing
- passive perception and combat range updates
- subsystem state updates through `tick_subsystem_state()`
- soul decay and resurrection recovery processing
- justice tick processing
- thief tick processing
- warrior tick processing
- NPC `ai_tick()` execution

`process_learning_tick()` currently drives:

- `process_learning_pulse()`
- `process_teaching_pulse()`

## Script-Based Timing

Detailed controller/poller/mixed classification now lives in `docs/architecture/script-usage-audit.md`.

| Subsystem | Classification | Authority | File | Entry Point | Notes |
| --- | --- | --- | --- | --- | --- |
| `BleedTicker` | `INVALID` | none | `typeclasses/scripts.py` | `BleedTicker.at_repeat()` | Deprecated script path; invalidated and deleted on server start. |
| Corpse decay controller | `CONTROLLER` | `corpse.db.memory_time`, `devotional_vigil_until`, condition state | `typeclasses/scripts.py` | `CorpseDecayScript.at_start()`, `CorpseDecayScript.at_repeat()` | Script now handles corpse condition decay, memory fade processing, and reload-time re-arming of corpse expiry scheduling. |
| Grave maintenance polling | `CONTROLLER` | `grave.db.expiry_time` | `typeclasses/scripts.py` | `GraveMaintenanceScript.at_repeat()` | Polls every 2 hours for warning, expiry, and grave wear updates. |
| Onboarding roleplay | `CONTROLLER` | onboarding state timestamps and script-local prompt cache | `typeclasses/onboarding_scripts.py` | `OnboardingRoleplayScript.at_repeat()` | Mixed controller plus prompt-spacing checks; emits nudges when characters idle. |
| Onboarding invasion | `CONTROLLER` | script-local `stage_started_at` and onboarding progression state | `typeclasses/onboarding_scripts.py` | `OnboardingInvasionScript.at_repeat()` | Multi-stage orchestration with timed stage progression every 6 seconds. |

### Script Attachment Sites

- `typeclasses/characters.py`: `corpse.scripts.add("typeclasses.scripts.CorpseDecayScript")`
- `typeclasses/corpse.py`: `grave.scripts.add("typeclasses.scripts.GraveMaintenanceScript")`
- `server/conf/at_server_startstop.py`: tutorial NPCs and rooms attach `OnboardingRoleplayScript` and `OnboardingInvasionScript`

## Manual Timestamp-Authoritative Timing Paths

| Subsystem | Classification | Authority | File | Entry Point | Notes |
| --- | --- | --- | --- | --- | --- |
| Roundtime state checks | `SCHEDULED_EXPIRY` | `db.roundtime_end` | `typeclasses/characters.py` | `is_in_roundtime()`, `get_remaining_roundtime()` | Hybrid model: timestamp-authoritative with scheduler expiry callback. |
| Death sting | `INVALID` | `db.death_sting_end` | `typeclasses/characters.py` | `apply_death_sting()`, `refresh_death_sting()` | Passive timestamp cleanup with no scheduler-backed expiry yet. |
| Corpse decay to grave transition | `SCHEDULED_EXPIRY` | `corpse.db.decay_time` | `typeclasses/corpse.py` | `schedule_decay_transition()`, `_expire_decay_to_grave()` | One-shot corpse expiry now runs as a keyed scheduler event while the timestamp remains authoritative. |
| Corpse memory fade | `INVALID` | `corpse.db.memory_time` | `typeclasses/corpse.py`, `typeclasses/scripts.py` | corpse remaining-time helpers, `CorpseDecayScript.at_repeat()` | Memory loss is still discovered by periodic script processing. |
| Grave expiry | `INVALID` | `grave.db.expiry_time` | `typeclasses/grave.py`, `typeclasses/scripts.py` | expiry helper, `GraveMaintenanceScript.at_repeat()` | Poll-driven warning and deletion flow. |
| Tend minimum window and reopen logic | `INVALID` | per-body-part `tend.min_until` and `duration` | `typeclasses/characters.py` | `is_tended()`, `get_tend_duration()`, bleed processing paths | Mixed integer countdown plus timestamp gate. |
| Justice timers | `INVALID` | plea deadline, stocks message timestamps, jail timer, fine timestamps | `typeclasses/characters.py`, `utils/crime.py` | `process_justice_tick()` and crime helpers | Shared ticker decrements and polls multiple independent justice windows. |
| Thief timed states | `INVALID` | assorted per-state timestamps | `typeclasses/characters.py` | `process_thief_tick()` | Mark expiry, khri collapse/drain, slip/intimidation/rough/stagger windows, position and attention decay, recent action, post-ambush grace. |
| Warrior temporary states | `INVALID` | `states[*]["expires_at"]` | `typeclasses/characters.py`, `typeclasses/abilities_warrior.py` | `process_warrior_tick()` and ability application | Shared ticker clears multiple one-shot warrior expirations by timestamp polling. |
| Magic temporary states and cooldown flags | `INVALID` | `states[*]["expires_at"]` | `typeclasses/characters.py` | `process_magic_states()`, `set_state()` call sites | Timestamp-driven buff/debuff/cooldown expiration. |
| Empath links and unity windows | `INVALID` | link `expires_at` timestamps | `typeclasses/characters.py` | empath link helpers | Timed relationship/state windows are stored as timestamps and checked lazily or via shared processing. |
| Onboarding prompt spacing and idle reminders | `INVALID` | onboarding state timestamps | `systems/onboarding.py`, `typeclasses/onboarding_scripts.py` | `prompt_spacing_active()`, `remind_objective_if_idle()`, onboarding scripts | Prompt cadence and idle reminder behavior are timestamp-authoritative and script-polled. |
| Capture / plea deadlines | `INVALID` | `ndb.plea_deadline` | `commands/cmd_capture.py`, `utils/crime.py`, `typeclasses/characters.py` | capture command and `process_justice_tick()` | One-shot case resolution currently depends on justice tick polling. |
| Trap expiration | `SCHEDULED_EXPIRY` | placed-time timestamps | `typeclasses/trap_device.py`, `typeclasses/characters.py` | `deploy_trap()`, `schedule_expiry()`, `_expire_if_due()` | Per-trap expiry now executes through a keyed scheduler event while the object timestamp remains authoritative. |

## Mixed or Transitional Timing Areas

| Subsystem | Current Shape | Why It Is Transitional |
| --- | --- | --- |
| Roundtime | timestamp authority + scheduler expiry | Explicitly documented hybrid model from Phase 0; scheduler is execution, not source of truth. |
| Tend states | integer duration + timestamp minimum window | Two parallel representations exist and should be classified before migration. |
| Onboarding scripts | controller scripts + manual prompt spacing timestamps | These likely remain controller-based, but their one-shot nudges should be separated from pure polling logic. |

## Candidate Expiry Paths (PH1-014 Eligible)

These are low-risk one-shot expiry candidates that can migrate execution without changing authoritative ownership of roundtime-like systems.

| Candidate | Current Implementation | Target Primitive | Why It Is Low Risk | Primary Files |
| --- | --- | --- | --- | --- |
| Corpse decay to grave transition | scheduler-backed expiry from `corpse.db.decay_time` | `SCHEDULED_EXPIRY` | Migrated in Phase 1 as the reference low-risk one-shot expiry path | `typeclasses/corpse.py`, `typeclasses/characters.py`, `diretest.py` |
| Grave expiry warning and deletion | `GraveMaintenanceScript` polls `expiry_time` | `SCHEDULED_EXPIRY` | Informational warning plus one deletion boundary | `typeclasses/scripts.py`, `typeclasses/grave.py`, `typeclasses/corpse.py` |
| Death sting auto-expiry | passive timestamp cleanup | `SCHEDULED_EXPIRY` | Isolated debuff expiry with no combat-loop ownership questions | `typeclasses/characters.py` |
| Thief mark expiry | per-second polling inside `process_thief_tick()` | `SCHEDULED_EXPIRY` | Simple cleanup path and clear expiry timestamp | `typeclasses/characters.py` |
| Plea deadline resolution | justice tick polls `plea_deadline` | `SCHEDULED_EXPIRY` | One-shot resolution event currently hidden inside shared ticker work | `typeclasses/characters.py`, `utils/crime.py`, `commands/cmd_capture.py` |

## Review Stop

This inventory intentionally stops before migration work.

Phase 1 review gate:

- review this document before PH1-014 begins
- finalize stable key rules before adding new scheduler-backed paths
- confirm which `INVALID` entries should remain ticker/controller driven and which should migrate to explicit scheduler events