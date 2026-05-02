# DireEngine Foraging System Design

## Status

- Version: 0.1 (design)
- Author: MT-514c-design
- Implementation: Pending MT-514c-impl
- Last review: 2026-05-01

## Overview

DireEngine currently has two adjacent resource-gathering loops: a universal `forage` ability backed by a small hardcoded table, and a Ranger-only visible-room-resource loop backed by `room.db.ranger_resources`. In parallel, the repo now includes a richer content catalog at `world/builder/content/forage_catalog.yaml` with terrain, season, time-of-day, indoor, skill-rank, and healing metadata for 139 items. That catalog is not yet used by the live engine.

This design defines the target system for MT-514c-impl: a unified, catalog-driven `forage` flow that consumes terrain, skill rank, calendar season, calendar time-of-day, weather, invasion state, and indoor/outdoor classification. Terrain and catalog metadata drive filtering. Weather and invasion remain engine-side consumption rules rather than item-schema extensions. Ranger gather is folded into the same system as profession-aware bonuses rather than maintained as a separate gathering mechanic.

The design is intentionally implementation-facing rather than exhaustive. It specifies the rule shape, composition order, merge strategy, and migration path. It does not set exact tuning values, redesign bundle/braid, or modify the content schema.

## Worldbuilding Decisions (Locked)

- Weather and invasion behavior stays in engine rules rather than new catalog fields.
- `forage` and Ranger `gather` merge into one unified foraging system.
- Invasion affects yield in v1 and does not block forage or trigger combat.
- `bundle` and `braid` remain separate Ranger crafting commands operating on gathered materials.

## Current State (Phase A)

### Current forage behavior

The player-facing command is `forage` in `commands/cmd_forage.py`. It takes no arguments and delegates directly to `execute_ability_input("forage")`.

The live behavior is in `typeclasses/abilities_survival.py` as `ForageAbility`.

Current characteristics:

- Visible and usable at Outdoorsmanship rank 1 or higher.
- Uses a contest roll of `outdoorsmanship + wisdom + intelligence` against `room.db.forage_difficulty`, defaulting to 35 when unset.
- Emits room messaging before resolution.
- On failure, returns nothing.
- On partial/success/strong-success, assigns a quality tier and base yield amount.
- Adds a Ranger profession bonus of `+1` yield.
- Adds `outdoorsmanship // 10` to yield.
- Trains Outdoorsmanship on meaningful attempts.
- Increments `db.forage_uses`.

The live item table is still hardcoded and tiny:

- `grass tuft`
- `stick bundle`
- `wild herb`

Selection is weighted by `random.random()` and does not consult terrain, season, time-of-day, weather, invasion, climate, or the catalog.

### Current Ranger gather behavior

Ranger gather is implemented separately from forage.

Command surfaces in `commands/cmd_rangercraft.py`:

- `gather <material>`
- `bundle <material>`
- `braid <material>`

Runtime behavior lives in `typeclasses/characters.py`.

Current characteristics:

- Room data model: `room.db.ranger_resources` is a list of resource keys.
- Only Rangers can see available resources through `get_available_ranger_resources()`.
- Current resource set is small and fixed by `RANGER_RESOURCE_PROFILES`:
  - `grass`
  - `stick`
- Resources render in room appearance as visible lines such as `a patch of tall grass` and clickable actions such as `gather grass`.
- Gathering is deterministic once the room resource is present.
- Gathered resources are tracked as consumed per-character per-room in non-persistent `ndb.ranger_resource_state`.
- Gathered items carry `ranger_resource_kind` and `forage_kind` metadata.
- `bundle` transforms `stick` into `bundle`.
- `braid` transforms `grass` into `braided grass`.

Behaviorally, this differs from forage in two important ways:

- It is visible and explicit rather than hidden and contest-rolled.
- It depends on room-authored resource presence rather than a derived candidate pool.

This is the main system split MT-514c-impl will close.

### Catalog

The catalog lives at `world/builder/content/forage_catalog.yaml`. It is already richer than the engine surface.

Observed schema fields per item:

- `display_name`
- `category`
- `skill_ranks`
- `healing`
- `seasonal`
- `time_of_day`
- `terrain`
- `indoor`
- `restrictions`
- `crafting_tags`
- `healed_part`
- `heal_route`
- `heal_type`
- `notes`

Current catalog summary:

- 139 total items
- 9 categories
- 34 healing herbs
- 13 indoor-allowed items
- 129 items available at all times of day
- 10 items marked day-only
- 0 items currently marked night-only

Current category counts:

- `wood`: 6
- `indoor_misc`: 9
- `seashell`: 9
- `fauna_part`: 5
- `flora`: 47
- `mineral_misc`: 5
- `food`: 23
- `healing_herb`: 34
- `mushroom`: 1

Representative entries:

- `branch`: no-skill, outdoor, always available, general wood pickup
- `berries`: outdoor, spring/summer/autumn only
- `cattail`: freshwater wetland, day-only, non-winter
- `Nemoih root`: healing herb, rank 60, multiple cultivated/steppe terrains
- `Sufil sap`: healing herb, rank 120, day-only, chaparral/coastal/scrub-and-thorn

The catalog is currently consumed by builder/scoring surfaces in `web/views.py` and `world/builder/scoring/zone_scorer.py`, not by the live forage engine.

### Related runtime state surfaces

Relevant query paths already exist and are cheap enough for per-attempt use.

Terrain and room classification:

- Rooms expose `get_terrain_type()` in `typeclasses/rooms.py`.
- Rooms expose `db.terrain_type` and infer terrain when unset.
- Rooms expose environment through `get_environment_type()`.
- Legacy forage difficulty still exists as `room.db.forage_difficulty`.
- Ranger-only room resources still exist as `room.db.ranger_resources`.

Calendar:

- `world.calendar.get_current_season()` returns one of `spring`, `summer`, `autumn`, `winter`.
- `world.calendar.get_current_time_of_day()` returns one of `night`, `morning`, `afternoon`, `evening`.
- Season is real-world anchored; time-of-day is game-time anchored.

Weather:

- `world.weather.get_current_weather(zone_id)` returns the zone weather state.
- Weather state is script-cached and safe for frequent reads.

Invasion:

- `world.invasion.get_current_invasion(zone_id)` returns the current invasion type.
- `world.invasion.is_zone_invaded(zone_id)` is available for boolean checks.

Skill rank:

- The forage ability currently reads skill via `user.get_skill("outdoorsmanship")`.
- Outdoorsmanship is already documented in character skill mappings as the shared survival skill for `forage` and `gather`.

Room indoor/outdoor:

- The design should keep indoor/outdoor checks aligned with the room/environment classification already used elsewhere rather than inventing a second interpretation.

Zone identity:

- Weather and invasion operate per zone, so implementation will need a stable way to resolve the current room's zone id before calling those systems.
- This design assumes that zone resolution already exists somewhere in room or area metadata; MT-514c-impl must use the existing path rather than invent a duplicate zone resolver.

### Tests

There are currently no focused `tests/test_forage.py` unit tests in the repo.

Existing automated coverage is scenario-oriented in `diretest.py`:

- `ranger-forage-scaling`
  - asserts that `forage` creates inventory items and scales above a minimal threshold in an easy room
- `ranger-forage-variation`
  - asserts multiple `forage_kind` values can appear across repeated attempts
- `ranger-resource-visibility`
  - asserts Rangers can see `room.db.ranger_resources` while non-Rangers cannot
- `ranger-resource-sell-loop`
  - asserts gathered Ranger resources can be transformed and sold

Current coverage gaps relative to the target design:

- no focused tests for terrain-driven selection
- no focused tests for season filters
- no focused tests for time-of-day filters
- no focused tests for indoor gating
- no focused tests for weather modifiers
- no focused tests for invasion modifiers
- no focused tests for unified forage/gather migration behavior
- no bounded-time forage test

## Merge Design (Phase B)

### Unified command surface

`forage` remains the universal player-facing command.

Design choice for v1 migration:

- `forage` becomes the authoritative runtime gather command.
- `gather` remains temporarily available as a Ranger-facing shortcut during migration.
- During the coexistence period, `gather <resource>` should redirect into the unified forage logic when the requested resource is one of the room's legacy Ranger resources.
- Once migration is complete and content no longer depends on `room.db.ranger_resources`, `gather` becomes a deprecated alias rather than a separate mechanic.

Rationale:

- This preserves player familiarity while eliminating the split in underlying logic.
- It avoids breaking existing Ranger room interactions during Option A coexistence.
- It keeps the long-term command surface aligned with DragonRealms research: one foraging system with profession differences inside it.

`COLLECT` remains a future feature, not part of MT-514c-impl.

### Ranger bonuses inside the unified system

Rangers stay better at foraging, but within the same core rules as everyone else.

For v1, Ranger advantages should be:

- lower effective difficulty or higher effective skill during the forage contest
- modest bonus to output quantity or quality after a successful roll
- access advantage for a small subset of special materials without requiring a separate command path

Because the current catalog has no explicit guild-gating field and schema extension is out of scope, the design adopts the following approach:

- v1 does not require a formal new catalog field for Ranger-only items
- MT-514c-impl may maintain an engine-side allowlist of special slugs if a small number of Ranger-exclusive materials are needed immediately
- otherwise, the safer default is to model Ranger advantage primarily through roll efficiency and output quality rather than hard exclusivity

This keeps the user's no-schema-extension decision intact while avoiding a fake sense of catalog support that does not yet exist.

Cosmetic messaging differences are deferred.

Ranger companion bonuses, including any Raccoon-related behavior, are deferred.

### Bundle/braid relationship

`bundle` and `braid` remain separate Ranger crafting verbs that transform items already in inventory.

The merged forage system should preserve the assumptions those commands currently make:

- raw grass-like material can still become braided output
- raw stick-like material can still become bundle output
- item metadata needed for recipe matching should still be present on produced items

The merge should not redesign recipe logic. It only needs to ensure the unified forage output still provides compatible inputs for the existing transforms.

### Item categorization

Catalog categories are treated primarily as organizational and rule-grouping metadata, not as standalone player-facing modes.

Design role by category:

- `food`, `flora`, `wood`, `seashell`, `mineral_misc`, `fauna_part`, `indoor_misc`:
  - general forage outputs
- `healing_herb`:
  - high-value outputs with stronger skill-gating and terrain specificity
- `mushroom`:
  - valid general category with likely higher weather affinity in implementation rules

Categories may influence weather weighting and future rarity weighting, but they do not create separate commands.

## Consumption Rules (Phase C)

### Terrain

Terrain is the primary selector for the candidate pool.

Rule shape:

- Start from the room's normalized terrain type.
- Include all catalog entries whose `terrain` list contains that terrain.
- For generic tags such as `outdoor` or `indoor`, include those entries when the room classification matches.

Multi-terrain rooms:

- If a room exposes both primary and secondary terrain in the future or via existing metadata, both pools may contribute.
- Primary terrain should dominate weighting.
- Secondary terrain should expand the pool but at reduced weight.

Legacy rooms with no terrain set:

- Option A remains locked.
- If terrain cannot be resolved, the engine falls back to the legacy `forage_difficulty` placeholder path rather than forcing the catalog path.

### Skill rank (Outdoorsmanship)

Skill rank is both a hard filter and a soft scaler.

Hard rule:

- Items with `skill_ranks: N` are unavailable below effective rank `N`.

Soft rule:

- Higher rank improves success chance, output quality, and access to broader variety after thresholds are met.

Effective skill:

- base Outdoorsmanship rank
- plus any implementation-side contest bonus from Ranger profession

Low-skill experience:

- Very low ranks should still be able to find a narrow pool of low-tier items often enough to learn.
- The catalog already supports this with tier-0 and low-tier items.
- Implementation should preserve a viable beginner loop rather than making early foraging mostly empty failures.

### Calendar season

Season is a strict availability filter.

Rule shape:

- `seasonal: [all]` means always eligible
- any specific seasonal list means the item is unavailable outside those seasons

Season is global because the current calendar season is global.

### Calendar time-of-day

Time-of-day is also a strict availability filter.

Rule shape:

- `time_of_day: [all]` means always eligible
- `time_of_day: [day]` means only available during `morning` and `afternoon`
- `time_of_day: [night]` means only available during `night`

`evening` is the one ambiguous slot because the catalog currently uses `day` and `night` rather than the calendar's four exact labels.

Design choice:

- For v1, treat `evening` as night-adjacent for filtering purposes only if the implementation needs a binary day/night reduction.
- This should be called out explicitly in MT-514c-impl and surfaced in player messaging only when relevant.

### Weather

Weather behavior stays in engine rules, not catalog schema.

The design keeps weather effects intentionally small and legible for v1.

Conceptual rules:

- `clear`, `cloudy`: baseline behavior
- `light_rain`: minor category-weight boost toward damp-growth materials such as mushrooms, wetland flora, and sap-like finds where appropriate
- `heavy_rain`: stronger damp-growth weighting and mild yield penalty
- `storm`: strong yield penalty; may hard-block only if implementation testing shows the action feels better blocked than heavily penalized
- `fog`: mild success or visibility penalty, not a hard block
- `light_snow`, `heavy_snow`, `blizzard`: stronger penalties on open-ground forage, with cold-weather regions still able to produce some valid results rather than universally zeroing the pool
- `sandstorm`: harsh penalty or hard block in exposed arid terrain, depending on implementation playtest feel

Important constraint:

- Weather should not require per-item special cases beyond a few category-oriented or terrain-oriented affinity rules.
- If implementation discovers that weather needs item-level tagging to feel coherent, that is a revisit signal for a future schema-extension discussion rather than a silent change in MT-514c-impl.

### Invasion

Invasion is a yield modifier only in v1.

Rule shape:

- `none`: no effect
- any active invasion type: reduce resulting yield after item selection and base quality are determined

Invasion does not:

- block item eligibility
- create invasion-themed forage items
- trigger risk or combat
- vary by invasion type in v1

This keeps the first consumer use of invasion simple and consistent with the user's lock.

### Indoor/outdoor

Indoor/outdoor classification is a hard filter.

Rule shape:

- `indoor: true` items are allowed indoors
- default outdoor-only items require an outdoor-eligible room

The implementation should use the same room/environment interpretation already used elsewhere in the game rather than introducing a bespoke forage-only notion of indoors.

### Composition order

The order of rule application is architecturally important and should be preserved.

1. Resolve room zone id and room terrain/context.
2. Determine whether the room has resolved terrain for catalog mode.
3. If terrain is unresolved, use Option A legacy fallback.
4. Build candidate pool from terrain matches.
5. Filter by indoor/outdoor eligibility.
6. Filter by seasonal eligibility.
7. Filter by time-of-day eligibility.
8. Filter by effective skill threshold.
9. Apply any weather hard-block rule if one exists for the current state.
10. Apply weather-driven weighting adjustments.
11. Roll item selection from the weighted pool.
12. Calculate base success, quality, and quantity from contest plus skill.
13. Apply weather yield modifier.
14. Apply invasion yield modifier.
15. Apply Ranger profession modifier.
16. Create output item(s), mark metadata, and train skill.

Rationale:

- Terrain and metadata filters decide what is possible.
- Weather and invasion then shape probability and output feel.
- Ranger advantage lands late enough to feel like profession competency rather than schema bypass.
- Yield modifiers apply after a valid item is found so invasion reduces output rather than erasing content.

## Migration Plan (Phase D)

### Existing rooms with `forage_difficulty`

Option A is the migration rule.

- Rooms with no resolved terrain continue to use the legacy hardcoded forage path.
- Rooms with resolved terrain use the new catalog-driven path.
- This allows terrain migration and forage refactor to coexist safely.
- `forage_difficulty` remains meaningful only for the legacy path during migration.

Long-term direction:

- Once terrain coverage is reliable, the legacy fallback can become exceptional rather than normal.
- Removal of the fallback is not part of MT-514c-impl.

### Existing rooms with `ranger_resources`

`room.db.ranger_resources` becomes a deprecated transition surface.

Migration rule:

- During the transition period, legacy Ranger resources remain readable.
- The unified forage path may treat those resources as additive or guaranteed candidates for compatibility when `gather` is used.
- New authored content should move toward terrain-driven catalog forage rather than explicit `ranger_resources` authoring.

Long-term direction:

- Deprecate `ranger_resources` once the unified forage flow and content coverage are sufficient.
- Do not remove it in MT-514c-impl unless the migration can be shown to be fully backward-compatible.

### Existing forage tests

Scenario coverage in `diretest.py` should remain green.

MT-514c-impl should add focused tests alongside the scenario coverage, ideally in `tests/test_forage.py`, covering:

- terrain-driven selection
- legacy fallback behavior
- season filters
- time-of-day filters
- indoor gating
- weather yield modifier
- invasion yield modifier
- Ranger profession bonus behavior
- bounded-time attempt cost

### Catalog readiness

The catalog is broadly ready for engine consumption.

Strengths:

- strong terrain coverage for common outdoor types
- healing herb data is already rich
- season and time-of-day fields already exist

Observed limitations:

- no explicit night-only items at present
- no explicit guild-gating field
- weather and invasion behavior are not represented in data by design
- some categories, especially mushroom, are sparse enough that weighting must be careful to avoid over-promising variety

These are not blockers for MT-514c-impl, but they should inform tuning and follow-up content tasks.

### Performance

The unified forage system should remain cheap per attempt.

Expected hot-path components:

- terrain/environment lookup: cheap
- calendar lookup: cheap
- weather lookup: cached and cheap
- invasion lookup: cached and cheap
- catalog filtering: in-memory and cheap

Design target:

- one forage attempt should complete in low milliseconds under normal conditions
- focused bounded-time validation in implementation should target no worse than 50ms to 100ms per attempt on warmed paths

## Open Questions (Phase E)

- Item rarity weighting: should rare materials be explicitly less likely than common materials within a valid pool, or is threshold-gating enough for v1?
- Ranger exclusivity: should v1 include any truly Ranger-only forage outputs, or should Ranger advantage remain purely contest, quality, and quantity based until a future schema pass can represent guild gating cleanly?
- Evening classification: should `evening` count as day or night for `time_of_day` filtering when catalog entries only express `day` or `night`?
- Weather hard-block policy: should `storm`, `blizzard`, or `sandstorm` ever fully block foraging, or should they always remain severe penalties only?
- Multi-terrain weighting: if a room supplies both primary and secondary terrain, what default ratio should favor the primary terrain pool over the secondary one?
- Failure messaging: should empty results distinguish between no valid pool, low skill, and hostile weather, or is a generic failure acceptable in v1?
- Legacy Ranger migration: should `gather` remain as a temporary alias throughout the full coexistence period, or should it be deprecated as soon as unified forage can consume legacy `ranger_resources` internally?

## Acceptance Criteria For MT-514c-impl

- Foraging consumes terrain, skill rank, season, time-of-day, weather, invasion, and indoor/outdoor classification.
- Catalog data, not the current hardcoded 3-item table, drives item selection on terrain-resolved rooms.
- Ranger profession advantage exists inside the unified forage system rather than through a separate gather mechanic.
- Option A fallback is preserved for rooms without resolved terrain.
- Existing scenario coverage continues to pass.
- Focused tests cover terrain, season, time-of-day, weather, invasion, Ranger bonus, and legacy fallback behavior.
- Forage attempts stay within the agreed bounded-time budget.
- `bundle` and `braid` continue to function against produced materials without redesign.

## Appendix: Catalog Schema Reference

Compact schema reference for `world/builder/content/forage_catalog.yaml`:

```yaml
<tier_or_group>:
  <slug>:
    display_name: <string>
    category: <wood|indoor_misc|seashell|fauna_part|flora|mineral_misc|food|healing_herb|mushroom>
    skill_ranks: <int>
    healing: <bool>
    seasonal: [all] | [spring, summer, autumn, winter]
    time_of_day: [all] | [day] | [night]
    terrain: [<terrain tags>]
    indoor: <bool>
    restrictions: <string>
    crafting_tags: [<foraging-related tags>]
    healed_part: <body part|null>
    heal_route: <internal|external|internal/external|null>
    heal_type: <wounds|scars|null>
    notes: <string>
```

Example entries:

```yaml
general:
  branch:
    display_name: branch
    category: wood
    skill_ranks: 0
    healing: false
    seasonal: [all]
    time_of_day: [all]
    terrain: [outdoor]
    indoor: false
```

```yaml
tier_20:
  scallion:
    display_name: scallion
    category: food
    skill_ranks: 20
    healing: false
    seasonal: [spring, summer, autumn]
    time_of_day: [day]
    terrain: [rural_cultivated]
    indoor: false
```

```yaml
tier_120:
  sufil_sap:
    display_name: Sufil sap
    category: healing_herb
    skill_ranks: 120
    healing: true
    seasonal: [all]
    time_of_day: [day]
    terrain: [chaparral, coastal, scrub_and_thorn]
    indoor: false
```