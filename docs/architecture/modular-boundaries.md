# Modular Boundaries

Purpose: current Phase 4 ownership map for major engine substrates that must stay modular, testable, and bundle-safe.

## T0-COMBAT-CORE

Bundle: Tier 0 combat substrate

Status: DRG-024 combat core complete

Owning code:

- `domain/combat/resolution.py`: pure combat resolution math and compatibility result assembly
- `domain/combat/rng.py`: S00265-shaped combat RNG helper
- `engine/services/combat_service.py`: authoritative combat mutation/orchestration path
- `engine/services/combat_xp.py`: offense/defense XP interpretation of combat results
- `engine/presenters/combat_presenter.py`: player-facing presentation only

Boundary rules:

- combat math lives in `domain/combat/`; callers pass actors and context, but do not reimplement hit or damage logic in commands, typeclasses, or bundles
- `engine/services/combat_service.py` is the only authoritative mutation path for attack execution and post-resolution side effects
- presenters consume structured combat results and never decide outcomes themselves
- bundle code may register content that affects combat inputs, but bundles do not own the combat-resolution algorithm
- compatibility fields on `AttackResolution.details` are part of the boundary until all downstream callers migrate to the richer combat-state payload

Canon sources for the current core:

- S00041 offensive factor
- S00042 evasion defense factor
- S00043 parry
- S00046 shield
- S00091 and S00092 subtractive orchestration
- S00265 combat RNG

Deferred follow-up boundaries:

- DRG-024a: hit area, damage tier, armor reduction, and wound-depth parity
- DRG-024b: attack verb routing and verb-specific GSL parity
- DRG-024c: richer equipment and defense metadata once weapon force/power and shield inputs are surfaced cleanly

Integration note:

- combat consumes registry-backed skill identity from DRG-023, but no bundle is allowed to bypass `CombatService` or inject parallel combat math paths