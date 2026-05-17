# DRG-BARBARIAN-BERSERK-001 report

## Outcome

Implemented the canonical Barbarian `BERSERK` verb on a dedicated service seam and replaced the placeholder Warrior command path. The repo-level cached Berserk SAF aftermath bug was corrected from flat `+115` to the directly re-verified `S00523` formula:

`(discipline * 3) - stamina - charisma + 75`

## Canon decisions

- Authority: DireLore `S00523`.
- Architecture: dedicated `engine/services/berserk_service.py` plus in-place `commands/cmd_berserk.py` repoint.
- Auto-learn: circle 2 through `collect_circle_advancement_private_messages(...)`.
- Runtime state: shared existing character state storage with stored Berserk payload and effect markers `1740001` / `1740004`.

## Files changed

- `engine/services/barbarian_saf_service.py`
- `engine/services/berserk_service.py`
- `commands/cmd_berserk.py`
- `engine/services/circle_service.py`
- `typeclasses/characters.py`
- `tests/services/test_barbarian_saf_service.py`
- `tests/services/test_berserk_service.py`
- `tests/commands/test_cmd_berserk.py`
- `CHANGELOG.md`

## Validation

- Focused Berserk + Barbarian foundation slice: `46 passed`
- Exact documented preservation batch: `314 passed, 153 subtests passed`
- Reconstructed Ranger-adjacent regression: `92 passed, 138 subtests passed`
- Direct runtime smoke: `6/6`

## Live-only defects found and fixed before closeout

1. Evennia mapping-backed state payloads were initially rejected because the service only accepted plain `dict` state.
2. Berserk expiry cleanup initially recursed through `set_hp(...)` because the HP accessor now consults active Berserk state.

Both defects were repaired and revalidated before report closeout.
