# MT-514c-design validation

Status: SHIPPED

Deliverable: `docs/design/foraging_design.md`

Phase A: Repo audit complete. Documented current forage behavior, Ranger gather split, catalog schema, runtime state query surfaces, and existing scenario coverage.

Phase B: Merge design complete. `forage` is the authoritative unified flow, `gather` is treated as a migration alias, Ranger bonuses move inside the shared system, and `bundle`/`braid` remain acknowledged but out of scope.

Phase C: Consumption rules documented for terrain, skill, season, time-of-day, weather, invasion, indoor/outdoor, and composition order.

Phase D: Migration plan documented per Option A. Legacy `forage_difficulty` fallback remains for terrain-unset rooms; `ranger_resources` is deprecated over a coexistence period rather than removed abruptly.

Phase E: 7 open questions surfaced for user resolution before MT-514c-impl drafts.

Phase F: Design document checked in.

Phase G: This artifact.

Next: User reviews `docs/design/foraging_design.md`, resolves open questions, then MT-514c-impl is drafted.