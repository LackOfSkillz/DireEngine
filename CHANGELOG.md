# Changelog

## 2026-05-12

- Added the DireEngine Phase 4 master roadmap at `docs/roadmap/direngine-phase-4.md` as the canonical planning reference for Phase 4 dispatches.
- Added `DATA-GAP-AUDIT.md` with the Phase 4 audit note and sequencing summary.
- Recorded the current validation snapshot for DireLore connectivity, canon table counts, authority architecture, and profession registry coverage in the roadmap.
- Added the DRG-022 stub inventory at `docs/roadmap/stub-inventory.md` and recorded the grouped hardcoded-content violations driving Phase 4 migration work.
- Added the bundle extension architecture contract at `docs/architecture/bundle-extension-api.md` and implemented the initial `engine/bundles/` registry and loader package.
- Migrated Character stat defaults to the new `stat_registry`, backed by DireLore `public.canon_stats` on port `5432` with a logged fallback path when DireLore is unavailable.
- Wired `skill_registry` from DireLore `public.canon_skills` through `engine/bundles/builtin_skills.py` and replaced `SKILL_GROUPS` pulse metadata reads with registry-backed helpers.
- Added focused tests for skill registry population and pulse-service integration, and verified live Evennia boot both with canon available and with DireLore temporarily unavailable.
- Replaced the pre-GSL flat hit-chance combat resolver with the canon-correct OF minus EDF subtractive contest from S00041/S00042/S00043/S00046/S00091/S00092, backed by a new S00265-style combat RNG helper in `domain/combat/rng.py`.
- Preserved the existing `AttackResolution.details` compatibility surface while adding canonical combat state fields such as offensive factor, evasion defense factor, leftover OF, force of impact, parry, shield, and combat outcome.
- Updated `engine/services/combat_service.py` and `engine/services/combat_xp.py` to consume the new combat core without breaking legacy callers, then added focused combat tests plus regression coverage for ammo depletion and bundle wiring.
- Followed up DRG-024 with resolver hardening for placeholder criticals, injected RNG determinism, and fallback hit-location selection so valid targets without initialized injury maps no longer crash the damage path.
- Verified Evennia restarts cleanly after DRG-024 via `startWeb.bat` and `evennia status`; live shell smoke reached the new resolver path, with remaining harness friction isolated to thin test dummy methods rather than the combat core itself.