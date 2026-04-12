# Timing Map

This document is the Stage 7 execution map for active timing paths.

It complements the broader inventory in `docs/architecture/timing-inventory.md` and focuses on where timed execution is now routed through the scheduler contract.

## Roundtime

- `engine/services/combat_service.py` -> `StateService.apply_roundtime()`
- `engine/services/state_service.py` -> `Character.set_roundtime()` / `Character.apply_thief_roundtime()`
- `typeclasses/characters.py` -> `schedule_event(key="roundtime_end", owner=character, callback="combat:clear_roundtime")`
- authority remains `character.db.roundtime_end`

## Skill Pulse

- `world/systems/skills.py` -> pool gain and pulse math
- `engine/services/pulse_service.py` -> per-character pulse execution
- `world/systems/exp_pulse.py` -> global pulse controller and reschedule boundary
- `world/systems/scheduler.py` -> `schedule_event(key="global_exp_pulse_tick", owner="global-exp-pulse", callback="skills:process_pulse")`

## Cooldowns

- `typeclasses/abilities_perception.py` -> `ObserveAbility.execute()` schedules `observe_reset`
- current combat and ritual state expiries still store timestamp authority in object state and are documented as remaining hybrid/manual paths in `docs/architecture/timing-inventory.md`

## Delayed Effects

- `typeclasses/characters.py` -> cleric ritual completion and revive cleanup
- `world/systems/fishing.py` -> bite, nibble timeout, struggle, borrowed-gear cleanup
- `world/systems/guards.py` -> guard clump exit
- `systems/onboarding.py` -> pending scene progression
- `systems/aftermath.py` -> orderly idle prompt
- `server/conf/telnet.py` -> handshake timeout

## Remaining Timestamp-Authoritative Paths

- effect and state expiry timestamps such as `expires_at`, `next_pulse_at`, and similar fields remain authoritative where live gameplay reads them directly
- those paths are inventoried in `docs/architecture/timing-inventory.md`
- Stage 7 normalizes execution routing, keys, and metadata; it does not rewrite every timestamp-owned subsystem