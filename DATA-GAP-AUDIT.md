# Data Gap Audit

## DireEngine Phase 4

DireLore foundation complete; DireEngine Phase 4 begins per `docs/roadmap/direngine-phase-4.md`.

**Bundle catalog authority:** DireLore's `docs/architecture/BUNDLE-CATALOG.md` (built by DRG-011) is canonical.

**Connection:** DireLore Postgres on `127.0.0.1:5432`, db `direlore`, user `user`. Config in `world/systems/canon_seed.py`.

**Sequence summary:**

1. DRG-022 - Stub inventory walk
2. DRG-022.5 - Bundle extension point architecture (prerequisite for all bundles)
3. DRG-023 - Foundational data wiring
4. DRG-024+ - Tier 0 overhauls (combat, magic, economy, crafting, outdoorsmanship)
5. DRG-025-030 - Tier 1 free bundles (Ranger, Cleric, Empath, Human, Elf, Crossing, Tailoring)
6. DRG-031-047 - Tier 2 paid bundles (Moon Mage first; then other 7 profs, 9 races, 11+ zones, 4 trades, 1 combined)
7. DRG-048 - Tier 3 premium (festivals, auction, CHE)

**Per-system pattern:** audit -> cross-reference DRG-011 + canon -> flag GSL deltas -> overhaul in place -> register through extension API -> test against GSL -> record bundle membership.

**Architectural prime directive:** bundle extension points required. Paid bundles ship as standalone Python modules. Someone without the Moon Mage bundle should never see Moon Mage code on disk.

**Filing note:** `DATA-GAP-AUDIT.md` did not previously exist in this repository; this file was created during the Phase 4 roadmap filing so the audit note has a canonical location.

## DRG-022 - Stub Inventory Walk

Filed: `docs/roadmap/stub-inventory.md`

Audit summary:

- Systems audited: 18
- GSL-aligned: 0
- Pre-GSL math overhaul required: 9
- Scaffolding only: 7
- Hardcoded-knowledge violations surfaced: 20+ primary hotspots across profession, race, skill, spell, zone, and onboarding surfaces
- Estimated total overhaul size (LOC): approximately 13k-17k LOC blended across the current grouped surfaces

Key findings for DRG-022.5 (extension API design):

- `world/professions/professions.py` hardcodes all free and paid professions in `PROFESSION_PROFILES`
- `world/races/definitions.py` hardcodes all free and paid races in `RACE_DEFINITIONS`
- `typeclasses/characters.py` and `world/systems/skills.py` hardcode skill identity, starter baselines, and groupings
- `domain/spells/spell_definitions.py` and `engine/services/mana_service.py` still embed spellcasting-profession knowledge in shared engine code
- `engine/services/combat_service.py`, `typeclasses/characters.py`, and multiple commands import or branch on Ranger/Cleric/Empath directly
- `server/conf/at_server_startstop.py`, `world/the_landing.py`, and `systems/first_area.py` hardcode named zone and onboarding content that should eventually register via zone/content APIs

## DRG-022.5 - Bundle Extension Point Architecture

Filed: `docs/architecture/bundle-extension-api.md`
Implementation: `engine/bundles/`

Summary:

- 8 registries shipped: profession, race, zone, trade, content, skill, stat, spell_circle
- Bundle manifest format defined (`bundle.toml`)
- Bundle loader implemented with discovery, validation, ordering, and failure handling
- Graceful absence verified in tests: loader handles zero bundles and missing dependencies without crashing
- Proof-of-concept migration: stats now load from `public.canon_stats` via `stat_registry`; they fall back to hardcoded defaults if DireLore is unreachable

Remaining hardcoded-knowledge violations awaiting per-system migration:

- `PROFESSION_PROFILES` in `world/professions/professions.py` (DRG-025+ per-profession dispatches)
- `RACE_DEFINITIONS` in `world/races/definitions.py` (DRG-028)
- `SKILL_REGISTRY` and related group metadata in `world/systems/skills.py` (DRG-023)
- `SPELL_REGISTRY` and profession magic branching in `domain/spells/spell_definitions.py` / `engine/services/mana_service.py` (DRG-024.5)
- Direct profession imports in commands, services, and onboarding code
- Named-zone hardcoding in `world/the_landing.py`, `systems/first_area.py`, and related area bootstraps
- Engine-owned content constants like `LAW_STANDARD` and `WEATHER_STATES` that still need Tier 0 canon-backed migration

## DRG-DE-PHASE-4-AMEND-001 — Modernization principle

Filed: amendment to `docs/roadmap/direngine-phase-4.md`

Principle: GSL is source of truth for math/mechanics/algorithms/thresholds.
DireEngine architecture is modern Python/Evennia idioms.
Every Phase 4 dispatch from DRG-022.5 onward inherits this principle.

Test discipline: numerical parity tests cite GSL scripts; implementation
structure is free to refactor.

## DRG-023 - Foundational Data Wiring (Skills)

Filed: skill catalog migration via `engine/bundles/builtin_skills.py`

Summary:

- `skill_registry` now boots from `public.canon_skills` through the DRG-022.5 extension API
- Verified canon row count: 63 skills loaded when DireLore is reachable
- Verified fallback subset size: 12 skills when DireLore is unreachable
- `world/systems/skills.py` no longer exposes `SKILL_GROUPS`; registry-backed helpers now provide canonical lookup, group listing, and pulse metadata access
- Direct migrated consumers: `engine/services/pulse_service.py`, `commands/cmd_experience.py`
- `MINDSTATE_MAX = 34` preserved unchanged

Live verification:

- Evennia restarted cleanly with normal DireLore config after DRG-023 changes
- Runtime `boot_bundles()` verification returned `skill_source=canon`, `stat_source=canon`, and `skill_count=63`
- Live fallback path verified by temporarily changing DireLore port away from `5432`; Evennia still booted cleanly, demonstrating registry fallback does not block server startup

Canon caveat discovered during wiring:

- `public.canon_skills` currently exposes columns `id`, `gsl_id`, `name`, `skillset`, `description`, `source_entity_id`, `confidence`, `created_at`
- Only a minority of rows currently have resolved names; many rows are placeholder keys like `unknown_0`
- Group metadata is sparse. DRG-023 wires canon exactly as present today and marks unresolved skill rows explicitly instead of fabricating richer canon data

## DRG-024 - Combat Resolution Core (OF minus EDF subtractive contest)

Filed: `domain/combat/resolution.py`, `domain/combat/rng.py`, `docs/architecture/modular-boundaries.md`

Authority verified directly from `gsl.scripts`:

- S00041: offensive factor builder; S00265 combat RNG is applied inside OF
- S00042: evasion defense factor builder
- S00043: parry sub-contest thresholds and partial/full parry behavior
- S00046: shield sub-contest
- S00091 and S00092: canonical subtractive flow `v1 = v1 - v2`, with penetration only when leftover OF is positive
- S00265: 4d50 open-roll combat RNG loop

Implementation summary:

- `domain/combat/resolution.py` no longer decides hits through flat `hit_roll <= final_chance` math
- `domain/combat/rng.py` now provides a dedicated `CombatRng` helper that mirrors the S00265 loop shape
- combat resolution now computes offensive factor, evasion defense factor, leftover OF, force of impact, parry, and shield in a canon-shaped order
- `AttackResolution` compatibility stayed intact, and the legacy `details` keys (`accuracy`, `evasion`, `hit_roll`, `final_chance`) were preserved for downstream callers while new keys were added for the migrated combat state
- immediate consumers were updated in place: `engine/services/combat_service.py` now treats positive `leftover_of` as pressure, and `engine/services/combat_xp.py` supports both the new OF/EDF fields and the legacy `final_chance` fallback

Validation:

- focused combat slice passed: `python -m unittest tests.combat.test_rng tests.combat.test_resolution tests.services.test_combat_xp`
- broader regression slice passed: `python -m unittest tests.test_ammo_depletion tests.bundles.test_registry tests.bundles.test_manifest tests.bundles.test_loader tests.bundles.test_stat_registry tests.bundles.test_skill_registry tests.services.test_pulse_service`
- editor/static diagnostics on touched combat files returned no errors
- Evennia restarted cleanly after DRG-024 (`startWeb.bat`, `evennia status`)

Known deferred scope for DRG-024a and later:

- hit area parity from S00047 is still placeholder-driven
- damage tier parity from S00048 is still placeholder-driven
- armor reduction and wound-depth parity from later combat scripts remain to be migrated
- current FOI, parry, and shield inputs bridge through the existing object model because explicit weapon `force` / `power` and richer defense metadata are not yet fully exposed