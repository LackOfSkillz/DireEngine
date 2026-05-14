# Progression Loop

This document is the current architecture note for learning progression after DRG-LEARN-001, DRG-LEARN-002a, DRG-LEARN-002b, DRG-LEARN-003b, DRG-LEARN-004, and DRG-SKILL-001.

## Current loop

1. Skill ranks accumulate through the existing skill and experience systems.
2. The global EXP pulse in `world/systems/exp_pulse.py` advances on the canonical 20-second cadence and routes one of the 10 canonical skill groups each tick into `engine/services/pulse_service.py`.
3. Each skill pulse uses profession-driven skillset placement, canonical pool sizing, canonical wisdom helpers, and normalized mindstate weighting from `world/systems/skills.py`.
4. Sleep state now gates the live pulse loop: Light Sleep keeps draining existing pools, Deep Sleep suppresses drain entirely, and banked Rested EXP can multiply a draining group's absorption when available.
5. Online idle and Deep Sleep characters bank Rested EXP through the 60-second ticker in `server/conf/at_server_startstop.py`, while logout/login transitions apply static offline drain and offline banking through `engine/services/rexp_service.py` plus `typeclasses/characters.py` puppet hooks.
6. New XP grants route through `engine/services/skill_service.py`, which now rejects gain attempts while the character is asleep and surfaces a rate-limited actor-only warning.
7. Each actual rank gained calls `world/systems/skills.py::process_rank()`, which forwards to `Character.on_skill_rank_gained()` and grants TDP progress through the hidden 200-point pool.
8. Spendable TDPs persist on `Character.db.tdp`.
9. Players inspect training state through three command surfaces:
   - `experience` / `exp` for skill learning, skill detail, and circle projection
   - `sleep` / `awake` for rest-state control
   - direct stat verbs (`strength`, `stamina`, `agility`, `reflex`, `charisma`, `discipline`, `wisdom`, `intelligence`) for per-stat costs and effects
10. At stat trainers, `train` and `study` route through `engine/services/stat_training_service.py`:
   - consult computes the next-rank TDP cost using `domain/learning/tdp_cost.py`
   - commit spends TDPs through `Character.spend_tdp()` and raises the trained stat by 1
11. At guild leaders, `train` and `study` route through `engine/services/circle_service.py`:
   - projection reports placeholder circle requirements based on total skill ranks and `db.coins`
   - commit deducts coins, raises `db.circle`, and grants a circle TDP award

## Current authority boundaries

- `typeclasses/characters.py` owns persisted progression state (`tdp`, `tdp_pool`, `stats`, `circle`, `coins`, `exp_skill_state`).
- `typeclasses/characters.py::SKILL_REGISTRY` now also owns the canonical runtime skill identity surface: lowercase underscore keys, registry-backed `display_name`, and the live `defense` identities required by later defense-learning work.
- `domain/learning/tdp_cost.py` owns TDP spend math.
- `domain/learning/skill_aliases.py` owns deterministic player-facing alias resolution.
- `domain/learning/mindstate.py` now owns the full 35-band canonical mindstate table used by player-facing naming helpers.
- `domain/learning/skill_groups.py` now owns the canonical 10-group, 200-second pulse grouping consumed by the live EXP pulse runtime.
- `domain/learning/skill_groups.py` also preserves group 9 as an intentionally empty profession-reserved surface; non-guild-locked live skills are expected to belong to exactly one of groups 0-8.
- `domain/learning/pool_size.py` now owns the canonical pool-size and wisdom pulse utility formulas consumed by the live EXP pulse runtime.
- `world/professions/professions.py` now owns per-profession primary/secondary/tertiary skillset placement data consumed by live EXP tier routing.
- `engine/services/stat_training_service.py` owns trainer-room consult/commit behavior.
- `engine/services/circle_service.py` owns guildleader projection/commit behavior.
- `engine/services/rexp_service.py` owns rested EXP banking, consumption, display shaping, and offline drain helpers.
- `commands/cmd_experience.py`, `commands/cmd_stat_info.py`, `commands/cmd_train.py`, `commands/cmd_study.py`, `commands/cmd_sleep.py`, and `commands/cmd_awake.py` are thin routing and presentation surfaces.

## Known non-canon placeholders

- defense skill identity and field-XP routing are now aligned: combat resolution reads `parry_ability` and `shield_usage` directly, defense results train `parry_ability`, `shield_usage`, and opportunistic `multiple_engaged_opponent`, and the remaining combat-learning follow-ons are tuning and broader canon distribution work rather than identity bridging.
- circle requirements are placeholders, not canon per-guild tables.
- circle costs currently consume `db.coins` because that is the live persisted currency field in the repo; older `silver` references are not authoritative here.
- the legacy 10-second learning ticker has been reduced to teaching-only processing; retired per-character learning pulses are no longer invoked from server startup wiring.
- mindstate milestone notifications are intentionally sparse and actor-only; only higher absorption thresholds and mind lock currently surface explicit player notifications.
- rested EXP currently uses the live pulse cadence and existing `SkillState` persistence bridge rather than a brand-new detached learning storage layer.