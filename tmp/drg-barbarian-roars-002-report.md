# DRG-BARBARIAN-ROARS-002 report

## Outcome

Implemented the next six canonical Barbarian intimidation roars on the existing roar-service seam: `Trothfang's Butchery`, `Tempestuous Fury`, `Death's Embrace`, `Death's Lullaby`, `Death's Shriek`, and `Magic's Bane`.

## Canon decisions

- Authority: `S03089`, `S11809`, `S11810`, `S11811`, `S11812`, `S11813`, `S11814`, and `S12052`.
- Classification: `B`. The repo already had the owning roar, position, roundtime, combat, and spell-difficulty seams needed to ship a bounded implementation.
- Architecture: each roar remains a dedicated definition under `domain/abilities/roars/`; `engine/services/roar_service.py` owns learning prerequisites and target-side state cleanup; no Warrior placeholder subsystem was reused.
- Prerequisite chain: `Death's Shriek` requires the learned `Death's Embrace` bit, matching the directly re-verified `S12052` teaching chain.
- Combat seam: Tempestuous Fury and Death's Embrace feed the existing OF/damage calculations; Trothfang uses existing stat reads; Magic's Bane uses existing skill/effect reads; Death's Lullaby and Death's Shriek stay on existing roundtime/position state.

## Files changed

- `engine/services/roar_service.py`
- `domain/abilities/roars/registry.py`
- `domain/abilities/roars/trothfang_butchery.py`
- `domain/abilities/roars/tempestuous_fury.py`
- `domain/abilities/roars/deaths_embrace.py`
- `domain/abilities/roars/deaths_lullaby.py`
- `domain/abilities/roars/deaths_shriek.py`
- `domain/abilities/roars/magics_bane.py`
- `typeclasses/characters.py`
- `domain/combat/resolution.py`
- `tests/services/test_roar_service.py`
- `tests/domain/test_barbarian_intimidation_roars.py`
- `tests/combat/test_resolution.py`
- `CHANGELOG.md`

## Validation

- Focused ROARS-002 slice: `50 passed`
- Exact documented preservation batch: launched, but the terminal runner did not flush a final summary before closeout
- Reconstructed Ranger-adjacent regression: launched, but the terminal runner did not flush a final summary before closeout

## Scope notes

1. Death's Shriek shipped on the bounded fear/kneel seam rather than reopening the older commented-out bodily-function branch from `S11813`.
2. Warrior placeholder references were inventoried for later cleanup, not reconciled in this dispatch.
3. No live `/play` smoke was completed in this session.