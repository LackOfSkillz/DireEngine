# MT-514c-impl validation

Status: PARTIAL

## Phase B-E implementation

- Modified `typeclasses/abilities_survival.py` to replace the hardcoded forage path with a catalog-driven `forage_attempt(...)` flow that consumes terrain, season, time-of-day, skill, weather, invasion, and indoor/outdoor state in the design-specified order.
- Added `utils/forage_catalog.py` as a minimal cached engine-safe loader because the only existing catalog readers were duplicated builder/UI helpers, not a reusable engine import surface.
- Modified `commands/cmd_forage.py` so `gather` is a temporary alias of `forage`.
- Removed `CmdGather` from `commands/cmd_rangercraft.py` and command registration from `commands/default_cmdsets.py`.
- Removed the dead ranger room-resource gather/render path from `typeclasses/characters.py` while leaving `bundle` and `braid` support intact through `transform_ranger_resource(...)` and `_match_ranger_resource_item(...)`.
- Updated `diretest.py` forage scenarios to use the unified forage implementation and updated the old ranger-resource scenarios to validate the new behavior instead of the deleted path.

Encoded design decisions and tunables:

- Uniform selection within the post-filter weighted pool; no explicit rarity weighting.
- No ranger-only forage items.
- Evening counts as day in time-of-day filtering.
- No weather hard-blocks for high-skill storm verification; severe weather reduces yield to low-output success.
- Primary/secondary terrain weighting: `0.7 / 0.3`.
- Ranger bonuses: `+20` effective skill, `+1` quality tier, `+1` quantity.
- Invasion yield modifier: `0.6`.
- Weather yield modifiers: `clear/cloudy=1.0`, `light_rain=0.9`, `heavy_rain=0.75`, `fog=0.85`, `storm=0.5`, `light_snow=0.85`, `heavy_snow=0.7`, `blizzard=0.5`, `sandstorm=0.5`.
- Weather weighting modifiers: `light_rain=0.95`, `heavy_rain=0.8`, `fog=0.9`, `storm=0.6`, `light_snow=0.9`, `heavy_snow=0.75`, `blizzard=0.6`, `sandstorm=0.55`.

## Phase F focused tests

- Added `tests/test_forage.py`.
- Result: `25` tests passing via `python -m unittest tests.test_forage` after fix1.
- Covered: terrain filtering, 70/30 secondary weighting, legacy fallback, season filter, day/evening vs night handling, indoor filtering, skill thresholds, clear/storm behavior, invasion behavior, ranger bonuses, gather alias registration, three failure-message tiers, and bounded-time regression in the isolated unit slice.
- Unit bounded-time result: under `0.100s` on the isolated stubbed path.

## Phase G existing scenario tests

Updated scenarios:

- `ranger-forage-scaling`: now exercises the unified forage ability in a terrain-set room.
- `ranger-forage-variation`: now exercises the unified forage ability in a mixed-terrain room.
- `ranger-resource-visibility`: inverted to verify the deleted `ranger_resources` room render/actions no longer appear.
- `ranger-resource-sell-loop`: now seeds compatible forage outputs directly and verifies `bundle`/`braid` plus vendor sale flow without relying on the removed gather path.

Scenario results:

- `ranger-forage-scaling`: PASS
  - detail: `before=0 after=4 items=['high-quality grungy feather', 'high-quality grungy feather', 'high-quality grungy feather', 'high-quality grungy feather']`
- `ranger-forage-variation`: PASS
  - detail: `resource_kinds=['branch', 'broken_shell', 'grass', 'grungy_feather', 'leaf', 'rock', 'root', 'sea_shell', 'torch']`
- `ranger-resource-visibility`: PASS
  - `exit_code: 0`, `lag_status: ok`
- `ranger-resource-sell-loop`: PASS
  - `exit_code: 0`, `lag_status: ok`

## Phase H live verification

Validation method:

- Production-shape shell verification using real Evennia `Room` and `Character` objects created in the live database.
- Weather and invasion were shimmed at the `typeclasses.abilities_survival` import boundary during the shell run so each subphase could be exercised deterministically without modifying the weather or invasion systems themselves.

### H.1 Terrain-driven forage

- Terrain room configuration: `terrain_primary=forest`, `terrain_secondary=coastal`, `terrain_type=forest`.
- High-skill ranger, clear weather, no invasion, 10 attempts:
  - statuses: `success=10`
  - average yield: `4.0`
  - observed items: `rock, moss, leaf, jadice_flower, wood_chip, grass, grungy_feather, twig, root`
  - observed thresholds: `0, 20, 80`
- Low-skill ranger on the same terrain room, 10 attempts:
  - statuses: `success=10`
  - observed thresholds stayed at `0, 10, 20`
  - no higher-skill coastal/forest pulls appeared, confirming threshold filtering at the effective-rank boundary.

### H.2 Weather penalty

- Same terrain room, storm weather, 10 attempts:
  - statuses: `success=10`
  - average yield: `1.0`
  - observed items: `grass, root, leaf, rusty_nail, grungy_feather, jadice_flower, stick, stem, branch`
- Result: storm materially reduced yield from `4.0` to `1.0` while avoiding hard-blocks in the verified high-skill case.

### H.3 Invasion penalty

- Same terrain room, `goblin_raid`, 10 attempts:
  - statuses: `success=10`
  - average yield: `1.9`
  - observed items: `grass, wood_chip, limb, rusty_nail, jadice_flower, bread_crumb`
- Post-clear baseline, 10 attempts:
  - statuses: `success=10`
  - average yield: `3.5`
- Result: invasion penalty reduced yield and baseline recovered after clearing invasion.

### H.4 Legacy fallback

- Legacy room with no terrain fields set, 10 attempts:
  - statuses: `success=9`, `failure=1`
  - average yield: `3.222`
  - observed items: `stick, root, bread_crumb, rock, jadice_flower, stem, wood_chip, branch`
- Result: rooms without terrain still forage successfully via fallback behavior.

### H.5 Gather alias

- Verified `CmdForage.aliases == ['gather']`.
- Direct command invocation with `cmdstring='gather'` on a live ranger character produced unified forage output:
  - messages: `You prepare to forage...`, `You expertly gather high-quality natural materials.`, `You recover high-quality Plovik leaves, high-quality Plovik leaves, high-quality Plovik leaves, and 1 more.`
  - item count created: `4`
- `room.db.ranger_resources = ['grass', 'stick']` did not produce old ranger-room render lines or actions before or after the alias call.

### H.6 Bounded time in production

- Production-shape warm timing on a live ranger character in a terrain room:
  - samples ms: `110, 109, 109, 110, 93, 125, 157, 109, 109, 125`
  - average: `115.6 ms`
  - min/max: `93.0 / 157.0 ms`
- Result: FAIL relative to the dispatch stop threshold (`< 50 ms` warm).
- cProfile of a warm call showed the dominant cost is not catalog filtering. The largest cumulative cost is skill training persistence inside `_award_forage_skill(...) -> Character.use_skill(...) -> skill_service.award_practice/award_xp`, plus Evennia attribute saves. The forage selection/filtering slice is not the main bottleneck.

## Tunable values shipped

- Weather yield modifiers:
  - `clear=1.0`
  - `cloudy=1.0`
  - `light_rain=0.9`
  - `heavy_rain=0.75`
  - `fog=0.85`
  - `storm=0.5`
  - `light_snow=0.85`
  - `heavy_snow=0.7`
  - `blizzard=0.5`
  - `sandstorm=0.5`
- Weather weight modifiers:
  - `light_rain=0.95`
  - `heavy_rain=0.8`
  - `fog=0.9`
  - `storm=0.6`
  - `light_snow=0.9`
  - `heavy_snow=0.75`
  - `blizzard=0.6`
  - `sandstorm=0.55`
- Invasion yield modifier: `0.6`
- Ranger skill bonus: `+20`
- Ranger quality bonus: `+1 tier`
- Ranger quantity bonus: `+1`
- Terrain ratio: `70 / 30`
- Unit bounded-time threshold: `100 ms`
- Production stop threshold from dispatch: `50 ms`

## Migration state

- Production room sample count:
  - total rooms: `855`
  - terrain-driven rooms: `395`
  - legacy fallback rooms: `460`
- Result: fallback remains necessary during coexistence; a large portion of the world is still on the legacy path.

## Final state

MT-514c-impl is functionally shipped but operationally PARTIAL. Foraging is now catalog-driven, runtime-state-aware, and backward-compatible via Option A fallback; `gather` aliases to the unified forage command; bundle/braid compatibility remains intact. The remaining blocker is production-shape warm timing, which currently exceeds the dispatch threshold because skill-award persistence dominates each attempt.

## fix1 — Forage ability gate relaxed and failure XP added

Status: SHIPPED

Problem identified: Rank-0 characters were blocked from foraging before the catalog flow ran. The gate was not in `forage_attempt(...)`; it came from `ForageAbility.required = {"skill": "outdoorsmanship", "rank": 1}` in `typeclasses/abilities_survival.py`, which fed `Character.meets_ability_requirements(...)` in `typeclasses/characters.py` and produced the exact message `You are not experienced enough.`

### Phase A — Diagnosis

- Root cause confirmed locally:
  - `ForageAbility.required` enforced Outdoorsmanship rank `>= 1`
  - `Character.use_ability(...)` called `meets_ability_requirements(...)` before `ability.execute(...)`
  - the failure string originated from the shared requirement gate, not from forage logic
- Effect: rank-0 characters never reached catalog filtering, legacy fallback, or three-tier failure messaging.

### Phase B — Gate relaxed

- Approach taken: local forage-only bypass, no shared ability framework changes.
- Change shipped:
  - `ForageAbility.required = {}`
  - `ForageAbility.visible_if = {}`
- Reasoning: this removes the pre-execution rank gate only for forage, matching the locked universal-forage rule while avoiding MT-515 generalization.

### Phase C — Three-tier messaging

- Verified skill-too-low classification on a live terrain-set steppe room using Jekar at rank 0.
- Result dict now carries `failure_reason` values for precise test/validation coverage:
  - `skill_too_low`
  - `weather_blocked`
  - `generic_no_result`
- Live skill-too-low output for Jekar in a steppe room:
  - `You prepare to forage...`
  - `You search the area but nothing within your skill catches your eye.`

### Phase D — Failure XP

- Locked behavior shipped:
  - skill-too-low only gets failure XP
  - weather-blocked gets none
  - generic no-result gets none
- Implementation choice:
  - used the same shared difficulty-based XP service pattern already present in fishing and other systems
  - `SkillService.award_xp(..., source={"mode": "difficulty"}, success=False, outcome="failure", event_key="forage", context_multiplier=0.25)`
- Reasoning:
  - the earlier `use_skill(... learning_multiplier=0.25)` attempt did not yield measurable XP for Jekar at rank 0 in live verification
  - switching to the shared difficulty-mode failure path produced real Outdoorsmanship pool gain without widening scope

### Phase E — Tests

- Added 3 new focused tests and strengthened 3 existing ones.
- Current suite result: `25` passing tests in `tests/test_forage.py`.
- New coverage added:
  - forage ability has no rank gate
  - rank-0 characters can attempt forage
  - skill-too-low failures report `failure_reason = skill_too_low`
  - skill-too-low failures call the XP service with `context_multiplier = 0.25`
  - weather-blocked and generic failures still award no XP

### Phase F — Live verification

#### F.1 Jekar in `#4222 Kingshade Street`

- Verified character: `Jekar`
- Verified room: `#4222 Kingshade Street, South Reach`
- Important observed fact: `terrain_primary = null`, `terrain_type = null`
- Consequence: Kingshade Street is currently a legacy-fallback room, not a terrain-driven room.
- Result: the bug is fixed there, but the post-fix behavior is fallback forage output rather than skill-too-low messaging.
- Captured attempts:
  - `You prepare to forage...` / `You expertly gather high-quality natural materials.` / `You recover high-quality stick, high-quality stick, high-quality stick.`
  - `You prepare to forage...` / `You gather some useful natural materials.` / `You recover useful stick, useful stick.`
  - `You prepare to forage...` / `You find nothing of value here.`
  - `You prepare to forage...` / `You gather some useful natural materials.` / `You recover useful berries, useful berries.`
  - `You prepare to forage...` / `You expertly gather high-quality natural materials.` / `You recover high-quality rock, high-quality rock, high-quality rock.`
- Regression addressed: Jekar no longer receives `You are not experienced enough.` in the reported room.

#### F.2 Jekar failure XP on skill-too-low

- Live terrain-set verification used a temporary steppe room because Kingshade Street has no terrain metadata and cannot exercise the skill-threshold path.
- Jekar Outdoorsmanship before 5 failed attempts in steppe room:
  - rank: `0`
  - pool: `4.0`
- Jekar Outdoorsmanship after 5 failed attempts in steppe room:
  - rank: `0`
  - pool: `13.84375`
- Captured repeated output:
  - `You prepare to forage...`
  - `You search the area but nothing within your skill catches your eye.`
  - one attempt also emitted `You feel your outdoorsmanship settling into dabbling.`
- Result: rank-0 skill-too-low failures now produce measurable Outdoorsmanship learning.

#### F.3 High-skill forage still succeeds

- Live terrain-set verification used a temporary rank-80 character in the same steppe room.
- Captured output:
  - `You prepare to forage...`
  - `You expertly gather high-quality natural materials.`
  - `You recover high-quality Yelith root, high-quality Yelith root, high-quality Yelith root, and 2 more.`
- Inventory created:
  - `high-quality Yelith root` x5

#### F.4 Existing scenarios still pass

- `ranger-forage-scaling`: PASS
  - detail: `before=0 after=4 items=['high-quality twig', 'high-quality twig', 'high-quality twig', 'high-quality twig']`
- `ranger-forage-variation`: PASS
  - detail: `resource_kinds=['berries', 'branch', 'bread_crumb', 'dirt', 'grungy_feather', 'jadice_flower', 'leaf', 'rock', 'stem', 'wood_chip']`
- `ranger-resource-visibility`: PASS
  - `exit_code: 0`, `lag_status: ok`
- `ranger-resource-sell-loop`: PASS
  - `exit_code: 0`, `lag_status: ok`

### fix1 timing note

- Measured the new failure-XP path separately on a production-shape rank-0 steppe character:
  - samples ms: `47, 47, 47, 47, 46, 47, 63, 47, 62, 47`
  - average: `50.0 ms`
  - min/max: `46.0 / 63.0 ms`
- Interpretation:
  - fix1 does not materially worsen the already-known performance concern
  - the failure-learning path sits near the previous threshold but is not dramatically worse than the pre-fix training cost profile

Followup queued:

- MT-514c-impl perf decision remains open.
- MT-515-skill-attempts remains the correct home for generalizing this pattern beyond forage.