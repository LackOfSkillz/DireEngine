# DRG-LEARN-006 — Defense XP Canon Parity

Type: Closing dispatch for the LEARN arc

Status: In implementation on 2026-05-13

## Goal

Route defense field XP through the canonical defense skills shipped by DRG-SKILL-001 (`parry_ability`, `shield_usage`, `multiple_engaged_opponent`), replace remaining bridged combat-resolution lookups, add shield XP grants, and add opportunistic MOE XP using the existing transient `incoming_attackers` counter.

## Locked findings from pre-flight

- `domain/combat/resolution.py::compute_parry()` still reads the defender's weapon skill instead of `parry_ability`.
- `domain/combat/resolution.py::compute_shield()` still reads raw `shield` instead of `shield_usage`.
- `domain/combat/resolution.py::compute_edf()` already reads `evasion` correctly.
- `engine/services/combat_xp.py` awards parry defense XP to the defender's weapon skill and does not award shield XP at all.
- `engine/services/defense_verb_service.py::_get_parry_skill_name()` still resolves to the weapon skill or `combat`.
- `typeclasses/characters.py::get_skill()` does not alias-resolve, so `get_skill("shield")` is a raw lookup.
- `incoming_attackers` is transient per tick, incremented during attack/spell contest setup and reset in the server tick loop; it is sufficient for opportunistic MOE detection at defense-resolution time.
- Attacker offense XP remains hit-only and is preserved as-is.

## Implementation decisions

- `compute_parry()` reads `parry_ability` directly for defense rank.
- `compute_shield()` reads `shield_usage` directly for defense rank.
- Combat XP routes successful parry outcomes to `parry_ability`.
- Combat XP grants `shield_usage` on `shielded_full` and `shielded_partial` outcomes.
- Combat XP grants `multiple_engaged_opponent` opportunistically when `incoming_attackers > 1` during defense resolution.
- `DefenseVerbService._get_parry_skill_name()` returns `parry_ability` unconditionally.
- No change to combat presenter messaging, attacker miss XP behavior, `award_practice()` math, or the transient/sleep/REXP/TDP plumbing.

## Acceptance targets

- Defense resolution math consults canonical defense skills.
- Defense field XP accumulates on `parry_ability`, `shield_usage`, and opportunistic `multiple_engaged_opponent`.
- Existing evasion defense XP remains intact.
- Existing combat math, messaging, pulse drain, TDP accrual, and sleep XP gates remain preserved.
- LEARN arc marked complete in roadmap/docs after validation.