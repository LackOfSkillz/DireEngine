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