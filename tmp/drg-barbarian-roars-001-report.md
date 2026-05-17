# DRG-BARBARIAN-ROARS-001 report

## Outcome

Implemented the canonical Barbarian roar foundation on a dedicated service seam and replaced the placeholder Warrior-only `roar` command path. The dispatch ships the first two canonical roars only: `Kuniyo's Spirit` and `Everild's Rage`.

## Canon decisions

- Authority: `S03088`, `S03089`, `S03281`, `S03468`, `S11807`, `S11808`, and `S12052`.
- Architecture: `engine/services/roar_service.py` owns preflight, slot accounting, `spellbook1` knowledge checks, and dispatch; `engine/services/vocal_damage_service.py` owns vocal strain totals, tiers, and effect-code state.
- Storage: learned roars persist through `spellbook1` bits; slots follow `((circle + 5) / 10)` with integer division.
- Auto-learn: bounded local implementation teaches `Kuniyo's Spirit` at circle `>= 5` when no roars are already known.
- Runtime state: target-side live markers `effect_2077001`, `effect_11808001`, and `effect_11808002`; actor-side vocal strain under `3089001` / `3089002`-aligned state.
- Combat seam: Everild penalties feed the existing EDF/parry/shield calculations in place instead of opening a new combat subsystem.

## Files changed

- `engine/services/vocal_damage_service.py`
- `engine/services/roar_service.py`
- `domain/abilities/roars/__init__.py`
- `domain/abilities/roars/registry.py`
- `domain/abilities/roars/kuniyo_spirit.py`
- `domain/abilities/roars/everild_rage.py`
- `commands/cmd_roar.py`
- `engine/services/circle_service.py`
- `typeclasses/characters.py`
- `domain/combat/resolution.py`
- `tests/services/test_vocal_damage_service.py`
- `tests/services/test_roar_service.py`
- `tests/commands/test_cmd_roar.py`
- `tests/domain/test_kuniyo_spirit.py`
- `tests/domain/test_everild_rage.py`
- `CHANGELOG.md`

## Validation

- Focused ROARS slice: `26 passed`
- Exact documented preservation batch: `314 passed, 153 subtests passed`
- Reconstructed Ranger-adjacent regression: `92 passed, 138 subtests passed`
- Direct runtime smoke: `7/7`

## Scope notes

1. This dispatch does not widen into inspirations, Bloodthirst, full T'Kiel teaching chains, or room-`3202` world modeling.
2. `S03468` was re-verified directly; it informed the teaching model, but the local bounded implementation deliberately keeps only the first auto-learned roar live for now.
3. The live smoke initially failed on a harness-side `dict` assertion because Evennia returned mapping-backed state objects; the runtime behavior itself was correct and the smoke passed after the harness was made mapping-safe.
