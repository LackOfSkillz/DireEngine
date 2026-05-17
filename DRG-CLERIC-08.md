# DRG-CLERIC-08 — Canonical Cleric Utility Sub-Book

Scope: ship only the bounded Cleric utility slice for Spirit Beacon and Uncurse.

Deliverables:
- Add canonical registry rows for Spirit Beacon (`202006` / `S04170`) and Uncurse (`203003` / `S01976`) in `domain/spells/spell_definitions.py`.
- Route Spirit Beacon through the existing favor/departure seam without widening into held-mana or self-return mechanics.
- Route Uncurse through the structured effect-removal path, preserving Death's Sting relief from the legacy command surface.
- Keep three-audience messaging in the structured presenter.
- Add focused tests for prep/cast/effect/profession enforcement.
- Run the preservation batch and one live `/play` smoke on `SmokeClericLive`.
- Update `CHANGELOG.md`, `/mnt/user-data/outputs/DRG-CLERIC-08-report.md`, and the Cleric deferred-mechanics tracker.

Explicit defers:
- Centering
- Persistence of Mana
- Shield of Light
- Phelim's Sanction
- Soul Attrition

Implementation notes:
- Spirit Beacon may ship as state-setting only if broader discoverability UX would widen scope.
- Spirit Beacon must not anchor while the caster still has favor remaining for non-forced departure handling.
- Uncurse may ship as generic negative-effect removal when curse-specific granularity would widen scope.