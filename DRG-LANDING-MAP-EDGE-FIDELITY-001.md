# DRG-LANDING-MAP-EDGE-FIDELITY-001 — Map Edge Filter Tightening

## Purpose

The parent repair dispatch DRG-LANDING-MAP-PRIMARY-IMAGE-FILTER-001 reduced the zone-map render set to the 202 dominant-image rooms and applied a Manhattan-distance edge filter at threshold 200. The visible map is still spaghetti in production. Direct edge-data analysis against `data/canon/map-1777858104.json` shows the threshold was too lax and that a separate population of edges (non-compass navigation commands) was never filtered.

This dispatch tightens both filters in a single bounded change.

Halt sensitivity LOW. The surface is a single helper in `world/area_forge/map_api.py` and one constant. Production line ceiling 150. Test budget separate.

## Pre-flight context

- Parent dispatches DRG-LANDING-V2-MANIFEST-AND-MAP-FILTER-001 and DRG-LANDING-MAP-PRIMARY-IMAGE-FILTER-001 closed cleanly against their stated targets; this dispatch is a tuning fix on top of them.
- HARDEN-001 proxy invariant must hold across dispatch 22.
- FIXTURE-SAFETY-001 guards remain LOAD-BEARING.
- Locked anchors must stay green: preservation 315/153, Ranger-adjacent 92/138.

## Root cause

### Two populations of remaining spaghetti

Direct analysis of the 480 edges among the 202 dominant-image canonical Landing rooms:

```
Manhattan bucket    Count   Disposition under current filter (threshold=200)
       <=10            0    keep
     11-20             2    keep
     21-50           325    keep
     51-100          121    keep
    101-200           28    keep  ← visibly long, should drop
       >200            4    drop  ← already dropped
```

The 32 edges at Manhattan 101+ are the visible spaghetti in the post-parent-dispatch render. Of those:

- **Non-compass named exits** (40 total across all distances; the biggest are 200+): `go bridge` (5 occurrences, ~342 units each — these cross the river), `go ramp` (4, ~287 units — level change between Hodierna Way and Bazaar Walkway), `go arch` (1, ~152 units), `go gate` (6), `climb stair` (2), `go path/pier/dock/bazaar/square` (singletons). These are navigation commands, not spatial adjacency. They should not render as edges on a spatial map.

- **Long compass exits** (legitimate compass directions, but spanning multiple blocks): `south` between Kertigen Road segments (158 units), `south` between Ustial Road and Stevedore's Wend (153 units), `southeast` between Mongers' Square and Mongers' Bazaar (152 units), and similar. These are real compass exits but they jump big chunks of geography — same street name continuing across a gap, or a long thoroughfare.

### Direction abbreviation aliasing

The canonical data uses both full-name and single-letter forms of compass directions: 6 `"e"`, 5 `"s"`, 3 `"w"`, 2 `"n"` in addition to 100+ `"east"`, `"south"`, etc. A naive non-compass filter would treat the abbreviations as non-compass and drop them, breaking real adjacency. Direction normalization is required ahead of the compass check.

Direction aliasing is already defined in `web/views.py:BUILDER_DIRECTION_ALIASES`. Reuse or mirror.

### Zero compass-direction-inconsistent edges

Across all 480 dominant-image edges, zero compass exits have geometry that contradicts their direction name (e.g., a `"north"` exit going south). A directional-consistency filter would catch nothing the threshold doesn't, so it is not part of this dispatch. Documented as a tested-and-discarded option in case it surfaces later.

## Step 0 — Live state probes (MANDATORY)

### Step 0a — Confirm the live edge distribution matches the JSON analysis

Run the same edge-bucket distribution probe against the live DB (rooms with `db.is_canonical_crossing=True` AND `db.canonical_image == LANDING_PRIMARY_IMAGE`). Expected results within rounding of the analysis above (480 total, 32 over 100, 4 over 200). If wildly different, halt and surface — the live data has drifted from the JSON in a way that invalidates the threshold choice.

### Step 0b — Confirm the existing parent-dispatch filter state

Read the current `world/area_forge/map_api.py` and locate the existing Manhattan threshold constant. Confirm it is 200 (or whatever value the parent dispatch set). The new threshold replaces it; surface the old value in the closeout for completeness.

### Step 0c — Enumerate non-compass direction names actually present

Across the dominant-image edge set, list every distinct exit `key` (direction name). Confirm the set decomposes into:

- Compass full-name: `north south east west northeast northwest southeast southwest up down`
- Compass abbreviations: `n s e w ne nw se sw u d` (subset; whichever are actually present in live data)
- Non-compass: `go X` patterns, `climb X` patterns, bare nouns like `arch`/`gate`/`path`

If a direction name appears that doesn't fit any of these three buckets, surface for operator decision before Section B's classifier ships.

### Step 0d — Confirm the live max-rendered-Manhattan after parent dispatch

Re-run the agent's earlier metric probe. Confirm current state matches what the parent dispatch reported (`max_rendered_manhattan = 159`, `edge_count = 476`). If the count has drifted, surface — the threshold tuning must be informed by current state, not stale state.

### Step 0e — Partial-failure recovery plan

This dispatch is a single-seam tuning change with no destructive operations. Rollback is reverting the two-line constant change and the helper function. No transaction needed.

## Section A — Direction normalization helper

**Target:** `world/area_forge/map_api.py`.

**Change:** Introduce `_normalize_exit_direction(direction: str) -> str` that lowercases, strips whitespace, and maps abbreviated forms to canonical full names. Reuse or mirror `web/views.py:BUILDER_DIRECTION_ALIASES`; if not reusable as-is, define a local mapping table for `n→north, s→south, e→east, w→west, ne→northeast, nw→northwest, se→southeast, sw→southwest, u→up, d→down`. Return the input unchanged if no normalization applies (so non-compass names pass through for Section B's classifier).

Add a module constant `_COMPASS_DIRECTIONS = frozenset({"north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest", "up", "down"})`.

Add `_exit_is_compass_adjacency(exit_obj)` that returns True iff `_normalize_exit_direction(exit_obj.key)` is in `_COMPASS_DIRECTIONS`. Used by Section B's edge filter.

**Estimate:** 25-40 production lines including the alias table.

## Section B — Tighten edge-rendering predicate

**Target:** `world/area_forge/map_api.py` — wherever the parent dispatch's Manhattan filter currently lives (likely `_get_cached_zone_template` and/or `_collect_room_edges` / `get_local_map`).

**Change:** Replace the existing single-condition Manhattan threshold check with a two-condition predicate:

1. The exit must be a compass adjacency: `_exit_is_compass_adjacency(exit_obj)` returns True. If False, drop the edge.
2. The edge's Manhattan distance must be at or below `LANDING_MAP_EDGE_MAX_MANHATTAN = 80`. If above, drop the edge.

Both conditions must pass for the edge to render. Lower the existing threshold constant from 200 to 80.

If the parent dispatch's filter currently lives in only one of the two map paths (zone vs. local), apply the new predicate consistently to both. The same predicate function should be called from both call sites.

**Estimate:** 30-50 production lines including the constant change, the predicate call sites, and any plumbing to thread the predicate through cached-template signature computation (so cache invalidation works correctly when the constant changes).

## Section C — Tests

Extend `tests/world/test_landing_v2_manifest_and_map_filter.py` with:

- `test_compass_direction_normalization_handles_abbreviations` — `_normalize_exit_direction("e")` returns `"east"`, `_normalize_exit_direction("ne")` returns `"northeast"`, `_normalize_exit_direction("east")` returns `"east"`, `_normalize_exit_direction("go gate")` returns `"go gate"` unchanged.
- `test_zone_map_drops_non_compass_named_exits` — create rooms with a `"go bridge"` exit between them, assert the edge does not appear in the zone-map template.
- `test_zone_map_keeps_compass_abbreviation_exits` — create rooms with an `"e"` exit between them at Manhattan distance < 80, assert the edge IS in the zone-map template (regression against the abbreviation aliasing fix).
- `test_zone_map_drops_long_compass_edges_over_threshold` — create rooms with a `"south"` exit at Manhattan distance 100, assert the edge does not appear.
- `test_zone_map_keeps_compass_edges_at_threshold` — create rooms with a `"south"` exit at Manhattan distance 80, assert the edge IS present (boundary check; threshold is inclusive).
- `test_local_map_applies_same_predicate` — same scenarios against `get_local_map`; assert behavior matches zone-map.

**Estimate:** 80-130 test lines.

## Halts

1. Production line ceiling 150. Test budget separate.
2. Halt sensitivity LOW. This is a single-seam tuning change with no destructive surface.
3. NO modification to the canonical importer.
4. NO modification to FIXTURE-SAFETY-001 guards.
5. The new compass-adjacency predicate MUST normalize direction abbreviations before the compass check. Halt and surface if Step 0c reveals direction names outside the documented three buckets.
6. The new Manhattan threshold MUST be informed by Step 0a's live edge distribution. If live data shows materially different distribution from the JSON analysis (e.g., 50+ edges at 51-80 distance suggesting the threshold should be higher, or zero edges at 21-50 suggesting the threshold should be lower), surface for operator decision before shipping.
7. Both filters MUST apply consistently to zone-map AND local-map renders. The same predicate function from both call sites.
8. Cache invalidation for the zone-map template MUST account for the new constant. If the parent dispatch's signature computation didn't include the threshold, this dispatch must add it.
9. Locked anchors stay green: preservation 315/153, Ranger-adjacent 92/138.
10. HARDEN-001 proxy invariant must hold across dispatch 22.
11. Closeout MUST include a fresh V2 builder zone-map screenshot showing no edges spanning more than ~10% of the canvas in any direction.

## Decisions

1. Threshold value 80 chosen from the bucket distribution: keeps the 121 edges in 51-100 (legitimate long streets) and drops the 32 edges in 101+ (visible spaghetti). Boundary inclusive (80 keeps, 81 drops). Documented for future tuning if live observation suggests adjustment.
2. Non-compass named exits dropped entirely from zone-map rendering, not visually downweighted. Rationale: `go bridge`, `go ramp` etc. are navigation commands across geographic discontinuities (rivers, level changes). They have no spatial adjacency meaning on a 2D map. Players still use them in-game; they just don't show as line connectors on the map.
3. Direction normalization mirrors `web/views.py:BUILDER_DIRECTION_ALIASES` rather than refactoring to a shared module. Rationale: avoid scope creep; the duplication is small and documented. A future refactor dispatch can consolidate if more callers need the same normalization.
4. No directional-consistency check (e.g., assert `"north"` exits actually go north). Rationale: zero such inconsistencies exist in the canonical data per Step 0c-equivalent analysis. Adding the check would only fire on data corruption, which has its own surface.
5. Threshold applies AFTER non-compass filter, not as part of a single composite check. Rationale: keeps the two failure modes distinguishable in logs and tests; if the threshold needs future tuning, the non-compass behavior is unaffected.

## Drop order if budget pressure

Nothing droppable. All three sections (normalization helper, predicate change, tests) are interdependent. If budget tightens, narrow Section C's test cases first — six tests can become four if needed, but the core normalization and predicate work must ship together.

## Expected outcome

- V2 builder zone map at `/builder/` shows the 202 dominant-image canonical Crossing rooms with only short-range compass-adjacency edges rendered.
- In-game zone map shows the same.
- The upper-left orphan node and the long diagonal/horizontal/vertical lines visible in the post-parent-dispatch screenshot are gone.
- ~408 edges render (down from current 476): all 40 non-compass named exits dropped, all 32 compass edges over distance 80 dropped.
- `go bridge`, `go ramp`, `go gate` etc. remain functional in-game; they just don't appear as map connectors.
- Locked anchors green; HARDEN-001 holds across dispatch 22.

## Closeout report MUST document

- Step 0a/0c/0d numbers (live edge distribution, direction-name inventory, current max-Manhattan).
- Section A's direction alias table contents.
- Final rendered edge count after both filters apply.
- Fresh V2 builder zone-map screenshot showing the clean render.
- In-game zone-map screenshot from a primary-image room confirming the same.
- Confirmation that abbreviated-direction exits ("e", "n", "s", "w") are still rendered when at short Manhattan distance.
- The threshold value chosen (default 80; document any deviation and why).

## Lessons captured

**Lesson 8** (new): When tuning filter thresholds against data, validate against the actual distribution, not a defensive default. The parent dispatch's threshold of 200 was a defensible-looking guess; the actual edge distribution made it obvious that 80 was the right cut once we looked at the data. Future filter-tuning dispatches should require a Step 0 distribution probe before the threshold is chosen.

Carries forward into all future dispatch closeouts under the "Validation" heading alongside Lessons 5, 6, 7.