# MT-514c-impl — Catalog-driven foraging with runtime state consumption

## Background

MT-514c-design produced `docs/design/foraging_design.md` with seven
open questions. The user resolved all seven:

1. **Item rarity:** uniform within pool for v1; explicit rarity
   weighting deferred to v2 if needed.
2. **Ranger exclusivity:** no ranger-only forage items in v1.
   Ranger advantage is contest, quality, and quantity bonuses only.
3. **Evening classification:** the evening time-of-day block counts
   as day for foraging purposes.
4. **Weather hard-blocks:** none in v1. Storm, blizzard, and
   sandstorm produce severe penalties only.
5. **Multi-terrain weighting:** 70% primary terrain pool, 30%
   secondary terrain pool when both are present.
6. **Failure messaging:** three-tier context-aware messages —
   skill-too-low, weather-blocked-or-penalized, generic-no-result.
7. **Legacy gather migration:** `gather` remains as a temporary
   alias to `forage` during the coexistence period. Deprecation
   queued as a follow-up after MT-514c-impl ships.

This dispatch implements the unified foraging system per the design
doc and the locked decisions. It refactors `ForageAbility` to
consume the catalog and runtime state, merges ranger gather into
the unified flow, preserves backward compatibility via Option A
fallback (rooms without terrain use the legacy hardcoded path),
and ships focused tests.

The architectural patterns from the MT-514 arc apply throughout:
- ScriptDB fallback for any new singletons (none expected here)
- Bounded-time test from day one
- Production-shape verification before closing
- One dispatch ships one focused change; do not chain follow-ups

## Architectural guardrails (READ FIRST)

This is the largest implementation dispatch in the MT-514 arc.
The biggest risk is scope drift — getting curious about adjacent
systems while implementing.

The second-biggest risk is over-engineering the consumption rules.
The design doc specifies the rules; impl should encode them
faithfully without adding "while I'm here" sophistication.

**Frozen scope:**

1. Phase A: Read `docs/design/foraging_design.md` end to end.
   This is the authoritative spec. The dispatch defers to the
   design doc on any conflict between dispatch text and design
   text.
2. Phase B: Refactor `ForageAbility` to consume the catalog and
   runtime state. Implement the consumption rules in the
   composition order specified in the design.
3. Phase C: Implement the legacy fallback path (Option A). Rooms
   without terrain use the existing hardcoded table.
4. Phase D: Wire the unified forage flow to handle ranger guild
   bonuses inline. Remove the ranger gather code path; alias
   `gather` to `forage` for backward compatibility.
5. Phase E: Implement the three-tier failure messaging.
6. Phase F: Tests at `tests/test_forage.py` — focused unit tests
   parallel to weather/invasion patterns, including bounded-time
   regression and consumption-rule coverage.
7. Phase G: Existing scenario tests in `diretest.py` continue to
   pass against the new implementation.
8. Phase H: Live verification in production — forage in a
   terrain-set room, verify catalog-driven behavior; forage in a
   legacy room, verify fallback.
9. Phase I: Validation artifact at
   `exports/mt514c_impl_validation.md`.

**Frozen what-not-to-do list:**

- DO NOT modify `docs/design/foraging_design.md`. The design is
  locked. If implementation reveals a design flaw, stop and
  report rather than silently amending the design.
- DO NOT extend the catalog schema. The locked decision was
  engine rules over schema extension. Per-item weather and
  invasion behavior live in code, not data.
- DO NOT add new fields to existing catalog items. The 139 items
  ship as-is; gaps in coverage are content tasks, not impl tasks.
- DO NOT redesign or modify bundle/braid mechanics. They stay as
  separate ranger crafting commands operating on inventory items
  produced by the unified forage flow.
- DO NOT add a COLLECT command. That's a future feature noted in
  the design doc's followup queue.
- DO NOT add ranger-only forage items. Locked decision #2.
- DO NOT add hard-blocks for any weather state. Locked decision
  #4. Severe penalties only.
- DO NOT add explicit rarity weighting per item. Locked decision
  #1. Uniform within pool.
- DO NOT modify weather, invasion, calendar, or terrain modules.
  Foraging consumes them; this dispatch should not touch them.
- DO NOT modify foraging-adjacent systems: lumberjacking, mining,
  skinning, animal lore. Out of scope.
- DO NOT add a new Outdoorsmanship subskill or new skill. Use
  existing Outdoorsmanship rank.
- DO NOT modify combat, NPC behavior, or quest triggers — these
  are future runtime-state consumers but not this dispatch's
  concern.
- DO NOT pre-implement the deprecation of `gather` as an alias.
  The alias stays in this dispatch; deprecation is a follow-up.
- DO NOT change the `forage` command's player-facing argument
  parsing in ways that break existing scripts or muscle memory.
  Players who type `forage` should still get a forage attempt.
- DO NOT add forage-related admin commands. The system is
  consumed via the existing `forage` command and (aliased)
  `gather`.
- DO NOT add a forage-related YAML loader to a new location. The
  existing catalog loader (currently used by builder UI and zone
  scoring) is the read path; reuse it.
- DO NOT modify zone YAMLs to add forage-related data. Existing
  terrain data is what the system consumes.
- DO NOT skip the bounded-time regression test. Forage attempts
  fire frequently in active play; perf must stay bounded.
- DO NOT skip the legacy fallback path. Rooms without terrain
  set MUST continue to work via the existing hardcoded table
  during the coexistence period.

**Stop-and-report conditions:**

- If reading the design doc reveals an inconsistency between the
  design and the locked decisions, stop and report.
- If the catalog loader currently used by builder UI is not
  suitable for engine-side consumption (e.g., it's tied to UI-
  specific concerns), stop and report. We may need a small
  refactor of the loader as a separate dispatch.
- If the existing `ForageAbility` has dependencies that make
  refactoring hazardous (e.g., it's called from many places with
  inconsistent assumptions), stop and report.
- If the merge with ranger gather requires changes to bundle/braid
  that weren't anticipated, stop and report. Bundle/braid is out
  of scope and shouldn't break.
- If the legacy fallback path can't coexist with the new
  catalog-driven path cleanly (e.g., they fight over the same
  room attribute), stop and report.
- If the bounded-time test reveals the catalog filter chain is
  slow (per-attempt over 50ms), stop and report. The runtime
  state queries are all cached and should be fast; if they're
  not, something has regressed in weather or invasion caching.
- If existing scenario tests in `diretest.py` start failing in
  ways that aren't attributable to the new behavior being
  correctly different from the old behavior, stop and report.
- If live verification in Phase H reveals the new system produces
  unexpected items (wrong terrain, wrong skill threshold,
  weather not respected, etc.), stop and report.
- If the ranger profession bonus produces results that feel
  wrong (rangers getting too much or too little advantage), the
  agent picks a reasonable starting value and notes it for tuning.
  Specific numbers are not blocking.

## Phase A — Read the design

The agent reads `docs/design/foraging_design.md` end to end before
writing any code. The design doc is the authoritative spec. The
agent extracts:

- Composition order (filter → weight → roll → modify → output)
- Per-state-input rule shapes
- Migration plan (Option A: legacy fallback for rooms without
  terrain)
- Acceptance criteria

If anything in this dispatch text conflicts with the design doc,
the design doc wins. If the conflict is structural (not just
phrasing), stop and report.

## Phase B — Implement the unified `ForageAbility`

### B.1 Catalog loading

Reuse the existing catalog loader. The forage path needs:
- Item lookup by category, terrain tag, skill threshold, season,
  time-of-day, indoor flag
- Fast in-memory access (catalog should be loaded once, cached)

If the existing loader is in `world/builder/services/` or similar
and used by builder UI / zone scoring, the engine-side foraging
imports the same loader. No new YAML reads.

If the catalog isn't currently loaded into a long-lived in-memory
structure, add the minimum necessary cache (a module-level dict
populated on first access, cleared on relevant invalidation hooks).

### B.2 Runtime state queries

The forage attempt queries:
- Character's Outdoorsmanship rank (existing skill query path)
- Character's profession (for ranger bonus)
- Room's terrain (primary and secondary)
- Room's outdoor/indoor flag (the same path weather uses for
  broadcast eligibility)
- Zone's climate (existing weather climate resolver)
- Calendar season (existing `world/calendar.py` API)
- Calendar time-of-day (existing API)
- Weather state for the zone (`world.weather.get_current_weather`)
- Invasion state for the zone (`world.invasion.get_current_invasion`)

All of these are already implemented and cached. The forage path
just calls them.

### B.3 Composition order implementation

Per the design doc, in this order:

1. **Determine candidate pool by terrain.**
   - If primary terrain is set, draw from primary pool with 70%
     weight; if secondary is also set, draw from secondary pool
     with 30% weight.
   - If only primary is set, all draws come from primary.
   - If neither is set, fall through to legacy fallback (Phase C).

2. **Filter by indoor/outdoor.**
   - If room is indoor, only items with `indoor: true` remain.
   - If room is outdoor, all items remain (the `indoor` flag is
     about whether the item *can* appear indoors, not whether it
     *requires* indoor).

3. **Filter by season.**
   - Items with `seasonal: [all]` (default) always pass.
   - Items with specific seasons pass only if calendar's current
     season is in the list.

4. **Filter by time-of-day.**
   - Items with `time_of_day: [all]` (default) always pass.
   - Items with `time_of_day: [day]` pass during morning,
     afternoon, AND evening (locked decision #3).
   - Items with `time_of_day: [night]` pass during night only.

5. **Filter by skill threshold.**
   - Items with `skill_ranks: N` pass only if character's
     effective skill rank >= N.
   - Effective skill rank = base Outdoorsmanship rank + ranger
     profession bonus (if applicable).

6. **Apply weather penalty/affinity.**
   - For storm, blizzard, sandstorm: weighting penalty applied
     (severe; specific values agent picks; document the choice).
   - For light rain: minor adjustment, possible affinity boost
     for rain-affinity categories (mushrooms, water-cress
     equivalents). The agent identifies which categories are
     "rain-affinity" based on item names/descriptions in the
     catalog.
   - For heavy rain: more pronounced version of light rain
     adjustments.
   - For fog: minor visibility penalty.
   - For snow / light_snow: cold-region adjustments.
   - For clear, cloudy: baseline; no modifier.
   - These are weighting adjustments; they do NOT remove items
     from the pool entirely.

7. **Roll the item.**
   - Uniform random selection from the weighted pool.

8. **Calculate base yield.**
   - Skill rank vs item's skill threshold determines base
     quantity and quality, per the existing forage success-tier
     logic. The new system replaces the contest against
     `forage_difficulty` with a contest against the rolled
     item's threshold.

9. **Apply weather yield modifier.**
   - Severe penalty in storm, blizzard, sandstorm (e.g., -75%
     yield).
   - Mild penalty in heavy rain, snow.
   - No modifier in clear/cloudy/light rain.
   - Specific values agent picks; document choices.

10. **Apply invasion yield modifier.**
    - If `current_invasion != "none"`: yield reduced.
    - Specific reduction value: agent picks (suggestion: -40%);
      document.

11. **Apply ranger profession bonus.**
    - Quality bonus, quantity bonus, contest bonus.
    - Specific values agent picks; document.

12. **Output: item, quantity, quality.**

### B.4 Failure paths

Three-tier failure messaging per locked decision #6:

- **Skill too low:** the candidate pool after step 5 is empty
  because all items in the terrain/season/time pool exceed the
  character's skill. Message: contextual, hints at skill
  insufficiency. Example: "You search the area but nothing within
  your skill catches your eye."

- **Weather penalty zeroed the result:** the roll succeeded but
  weather penalties drove yield to zero, OR weather is severe
  enough that pool weights effectively prevent meaningful pulls.
  Message: contextual, references the weather. Example: "The
  driving storm makes foraging nearly impossible."

- **Generic no-result:** the roll produced nothing for any other
  reason (bad luck, low quality result rounded to nothing, etc.).
  Message: generic. Example: "You find nothing of value here."

The agent picks the actual message strings; these are
illustrative.

## Phase C — Legacy fallback (Option A)

Rooms with no terrain set continue to use the existing hardcoded
table.

The fallback fires when:
- `room.db.terrain` is unset OR
- The terrain value is not in the recognized terrain vocab OR
- The catalog has no items matching the room's terrain

In any of these cases, the legacy path runs unchanged: contest
against `room.db.forage_difficulty`, roll from the hardcoded
3-item table (grass, sticks, generic herb).

This preserves backward compatibility for rooms that haven't yet
been migrated to terrain-aware data. It is NOT permanent — the
fallback is temporary infrastructure for the coexistence period.

The agent does NOT modify the legacy hardcoded table. Just
preserves the existing path and gates it on terrain-absence.

## Phase D — Merge ranger gather

Per locked decision #7, `gather` becomes an alias to `forage` and
the ranger gather code path is removed.

### D.1 Command surface

- `forage` remains the primary command; behavior is the unified
  flow.
- `gather` is registered as a command alias that resolves to the
  same handler as `forage`. Players who type `gather` get the
  unified forage behavior.

### D.2 Remove the ranger-resources path

- `room.db.ranger_resources` is no longer consumed by the new
  forage path.
- The data is left in place on rooms that have it (no migration
  destroys data) but is ignored.
- Code in `commands/cmd_rangercraft.py` related to `gather`,
  `bundle`, and `braid`:
  - `gather` is removed (the alias to `forage` replaces it).
  - `bundle` and `braid` stay untouched — they consume inventory
    items, not room resources.
- Code in `typeclasses/characters.py` related to ranger resources:
  - Remove gather methods that referenced `ranger_resources`.
  - Keep any methods that bundle/braid depends on.

### D.3 Ranger profession bonus

The ranger advantage is now applied inside the unified forage
flow, per Phase B step 11. Specifically:
- Effective skill rank = base + ranger bonus (e.g., +20 ranks for
  rangers)
- Quality multiplier on result (e.g., 1.2× for rangers)
- Quantity bonus on result (e.g., +1 item per success tier for
  rangers)

Agent picks specific values; documents them.

## Phase E — Failure messaging

Implement the three-tier failure path as designed in Phase B.4.
The agent identifies the right point in the forage flow to detect
each failure mode and emits the corresponding message.

The messages are inline strings in the ability code. They are NOT
loaded from YAML or settings. (Future: could become content-
authored if richness is needed; not v1.)

## Phase F — Focused unit tests

Create `tests/test_forage.py` with at minimum:

### F.1 Catalog-driven selection

- `test_terrain_filters_pool` — primary terrain pool selected
- `test_secondary_terrain_blends` — secondary contributes per
  70/30 ratio
- `test_no_terrain_falls_back` — rooms without terrain use legacy

### F.2 State filters

- `test_season_filter_active` — out-of-season items excluded
- `test_time_of_day_filter_day_includes_evening` — locked
  decision #3
- `test_time_of_day_filter_night_excludes_evening` — counterpart
- `test_indoor_outdoor_filter` — indoor flag respected
- `test_skill_threshold_filter` — items above skill excluded

### F.3 Weather behavior

- `test_clear_weather_baseline` — no modifier
- `test_storm_severe_yield_penalty` — yield reduced significantly
- `test_storm_does_not_hard_block` — locked decision #4; pool
  not zeroed

### F.4 Invasion behavior

- `test_invasion_yield_modifier` — yield reduced when
  `is_zone_invaded` returns True
- `test_no_invasion_no_modifier` — baseline

### F.5 Ranger bonus

- `test_ranger_gets_skill_bonus` — effective rank higher for
  ranger
- `test_ranger_gets_quality_bonus` — output quality higher
- `test_ranger_gets_quantity_bonus` — output quantity higher
- `test_non_ranger_baseline` — no bonus applied

### F.6 Failure messaging

- `test_skill_too_low_message` — three-tier skill failure
- `test_weather_blocked_message` — three-tier weather failure
- `test_generic_failure_message` — three-tier generic

### F.7 Bounded-time regression

```python
def test_forage_attempt_completes_within_bounded_time(self):
    """Forage attempts fire frequently in active play; perf must
    stay bounded.

    Targets: 50ms or less per attempt warm-cache.
    """
    import time
    # Warm path
    forage_attempt(test_character, test_room)
    # Measure
    start = time.monotonic()
    forage_attempt(test_character, test_room)
    elapsed = time.monotonic() - start
    self.assertLess(
        elapsed, 0.050,
        f"forage_attempt() took {elapsed:.3f}s, expected < 0.050s"
    )
```

If 50ms is too tight given test environment overhead, the agent
picks a reasonable production-shape bound (100ms or 200ms) and
documents the choice.

## Phase G — Existing scenario tests

Run the existing forage scenarios in `diretest.py`:
- `ranger-forage-scaling`
- `ranger-forage-variation`
- `ranger-resource-visibility`
- `ranger-resource-sell-loop`

These test end-to-end behavior. Some may need adjustment because
the new system behaves differently than the old (e.g., pool
selection is terrain-driven, not the old hardcoded list).

For each failing scenario:
- If the failure is because the new behavior is correctly
  different from the old, update the scenario to match the new
  expected behavior. Document the update.
- If the failure is because of a bug in the new implementation,
  fix the implementation.
- If the failure is in scope creep that this dispatch shouldn't
  touch (e.g., bundle/braid scenarios), leave the scenario
  alone — bundle/braid is out of scope.

## Phase H — Live verification in production

After implementation, restart the server. Verify in the live game:

### H.1 Terrain-driven forage

1. Connect via webclient or `evennia shell -c` (whichever is
   reliable).
2. Teleport to a room with terrain set (e.g., `@teleport #4213`
   if `new_landing` zone has terrain on its rooms; agent verifies
   which rooms qualify).
3. Set weather to clear, no invasion.
4. Run `forage` 10 times. Capture the items returned.
5. Verify items match terrain (e.g., grass-tagged items in
   grassland terrain, not desert items).
6. Verify items respect skill threshold (test character can use
   admin-grant high skill, or use a low-skill alt).

### H.2 Weather penalty

1. Same outdoor terrain-set room.
2. Set weather to storm.
3. Run `forage` 10 times. Verify yield is significantly reduced
   relative to clear-weather baseline.
4. Verify NO hard-blocks fire (forage attempts succeed at low
   yield, not fail entirely from weather).

### H.3 Invasion penalty

1. Same room.
2. Run `@invasion <zone> goblin_raid`.
3. Run `forage` 10 times. Verify yield is reduced relative to
   non-invasion baseline.
4. Run `@invasion <zone> none` to clear.
5. Verify yield returns to baseline.

### H.4 Legacy fallback

1. Find or designate a room WITHOUT terrain set.
2. Run `forage`. Verify it succeeds with the legacy hardcoded
   items (grass, stick, generic herb), per Option A migration.

### H.5 Gather alias

1. Run `gather` in a terrain-set room.
2. Verify it produces the same kind of unified forage output as
   `forage` would.
3. Verify no `ranger_resources`-specific behavior fires (the old
   path is dead).

### H.6 Bounded time in production

```python
import time
# Pretend to be a character; agent figures out the right shape
character = ...
room = ...
# Warm
forage_attempt(character, room)
# Measure
start = time.monotonic()
forage_attempt(character, room)
elapsed = time.monotonic() - start
print(f"forage_attempt(): {elapsed:.3f}s")
```

Agent reports the production timing. Should be well under 50ms
warm.

## Phase I — Validation artifact

Create `exports/mt514c_impl_validation.md`:

```markdown
# MT-514c-impl validation

Status: SHIPPED  |  BLOCKED  |  PARTIAL

## Phase B-E implementation

[Files modified, key design decisions encoded, specific values
chosen for tunable parameters (weather penalty %, invasion
modifier %, ranger bonus magnitudes), notes on anything the
design didn't fully specify and how the agent decided.]

## Phase F focused tests

[Test counts, all-passing confirmation, bounded-time threshold
chosen and result.]

## Phase G existing scenario tests

[Which scenarios passed, which were updated and why, which were
left alone because they were out of scope (bundle/braid).]

## Phase H live verification

[Verbatim outputs of each verification subphase. Items returned,
yields measured, before/after weather, before/after invasion,
fallback confirmed, alias working, production timing.]

## Tunable values shipped

[Concrete values the agent chose:
- Weather penalty severity per state
- Invasion yield modifier
- Ranger skill bonus
- Ranger quality multiplier
- Ranger quantity bonus
- Multi-terrain primary/secondary ratio (locked at 70/30)
- Bounded-time threshold]

## Migration state

[How many rooms are now terrain-driven vs falling back to legacy.
Catalog gaps surfaced, queued as content tasks.]

## Final state

[One-line: "MT-514c-impl shipped. Foraging is catalog-driven and
runtime-state-aware. Backward compatibility preserved via Option
A fallback. Ready for MT-514d (render-time state diagnostic)."]
```

## Verification checklist

1. Design doc read and followed faithfully.
2. ForageAbility refactored to catalog-driven flow.
3. Composition order implemented per design.
4. All six runtime state inputs (terrain, season, time, skill,
   weather, invasion) consumed correctly.
5. Locked decisions encoded:
   - Uniform within pool (no rarity weighting)
   - No ranger-only items
   - Evening = day for time-of-day
   - No weather hard-blocks
   - 70/30 terrain ratio
   - Three-tier failure messaging
   - Gather alias preserved
6. Legacy fallback works for rooms without terrain.
7. Bundle/braid untouched and still work.
8. Focused tests at `tests/test_forage.py` all pass.
9. Existing scenario tests pass (with documented updates where
   correct behavior diverged).
10. Live verification all six subphases pass.
11. Validation artifact created.
12. No code outside the in-scope list modified.

## Stop conditions

- Edit only:
  - `typeclasses/abilities_survival.py` (refactor ForageAbility)
  - `commands/cmd_forage.py` (if argument parsing changes)
  - `commands/cmd_rangercraft.py` (remove gather, leave bundle/braid)
  - `commands/default_cmdsets.py` (alias gather to forage)
  - `typeclasses/characters.py` (remove dead ranger gather methods)
  - `tests/test_forage.py` (new)
  - `tests/diretest.py` (only scenarios that need updates per
    Phase G; nothing else)
  - `exports/mt514c_impl_validation.md` (new)
  - Possibly a small catalog-loader extraction if needed for
    engine-side consumption — only if absolutely required and
    documented in the validation artifact
- Stop and report on design conflicts.
- Stop and report on catalog loader unsuitability.
- Stop and report on ForageAbility hazardous dependencies.
- Stop and report on bundle/braid breakage.
- Stop and report on legacy fallback / new path coexistence
  conflicts.
- Stop and report on bounded-time perf regression.
- Stop and report on scenario test failures that aren't
  attributable to correct behavioral divergence.
- Stop and report on live verification anomalies.
- Do not chain follow-up fixes within this dispatch.
- Do not modify out-of-scope systems.

## Required artifacts

1. Updated `typeclasses/abilities_survival.py` (refactored
   ForageAbility)
2. Possibly updated `commands/cmd_forage.py`
3. Updated `commands/cmd_rangercraft.py` (gather removed)
4. Updated `commands/default_cmdsets.py` (gather alias)
5. Updated `typeclasses/characters.py` (dead ranger methods
   removed)
6. New `tests/test_forage.py`
7. Updated scenarios in `tests/diretest.py` where appropriate
8. New `exports/mt514c_impl_validation.md`

## Followup queue

- **Catalog content expansion:** Surface any terrain coverage
  gaps found during impl as content tasks. Specifically: which
  terrain tags have fewer than ~5 items in the catalog, making
  forage results monotonous. Content authoring on user's timeline.
- **Gather command deprecation:** After MT-514c-impl ships and
  the unified forage proves stable in playtesting, a small
  follow-up dispatch removes the `gather` alias entirely. Likely
  a one-day dispatch.
- **MT-514d (render-time state diagnostic):** On deck. Diagnoses
  whether the room render path actually evaluates `$state(...)`
  fragments at runtime. Per the invasion dispatch's Phase H, the
  current room display path doesn't appear to support runtime
  state markup, but this needs verification before any
  description-rendering work proceeds.
- **MT-514e (NPC movement perf diagnostic):** Diagnostic-first
  arc for the patrol guard lag problem. Unblocks mobile invasion
  threats eventually.
- **Future runtime-state consumers:** Crafting (cooking, alchemy,
  carving) all consume terrain + season + time + weather.
  Combat AI will eventually consume invasion. NPC behavior will
  consume time of day. Document the runtime-state-driven gameplay
  pattern in `docs/architecture/runtime_state_consumers.md` after
  MT-514c-impl ships, since foraging is the first major consumer
  and proves the pattern.
- **v2 considerations from this dispatch (deferred to playtesting):**
  - Explicit per-item rarity weighting if uniform feels too flat
  - Weather hard-blocks if severe penalties feel too forgiving
  - Ranger-exclusive forage items if bundle/braid proves
    insufficient for guild distinction
  - Per-invasion-type yield modifiers if all-types-equal feels wrong
  - Catalog schema extension with weather/invasion fields if
    engine rules prove too rigid