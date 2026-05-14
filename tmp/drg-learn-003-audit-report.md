# DRG-LEARN-003-AUDIT - Pulse/Pool/Mindstate Reconciliation Pre-Audit

## Summary

LEARN-003 should ship as a split: `LEARN-003a` for data and compatibility structure, then `LEARN-003b` for formula and scheduler replacement. The top risk is not rank gain or TDP accrual itself; that seam is already isolated and preserved through `world/systems/skills.py::process_rank()` into `Character.on_skill_rank_gained(...)`. The real risk is that the active learning runtime currently mixes a non-canonical 5-offset pulse scheduler, a simplified pool formula, sparse command-facing mindstate assumptions, and a fallback registry that only partially describes pulse groups. Replacing those all at once would couple data migration, runtime cadence replacement, and player-visible display changes into one high-risk dispatch.

## Step 0 Findings - Canonical Target

### Canonical pulse cadence

- Modern DR uses a fixed 200-second pulse cycle.
- Ten skill groups pulse once each per cycle.
- Each group is offset from the previous group by 20 seconds.
- Elanthipedia documents the timing as universal and fixed for all players rather than per-character randomization.

### Canonical pool formulas

Base pool size by skillset placement where `x = ranks`:

- Primary: `y=(15000*x/(x+900))+1000`
- Secondary: `y=(12750*x/(x+900))+850`
- Tertiary: `y=(10500*x/(x+900))+700`

Intelligence bonus where `x = Intelligence`:

- `< 30`: `y=((x-10)*60)/10`
- `30-60`: `y=(((x-30)*30)+1200)/10`
- `> 60`: `y=(((x-60)*15)+2100)/10`

Discipline bonus where `x = Discipline`:

- `< 30`: `y=((x-10)*20)/10`
- `30-60`: `y=(((x-30)*10)+400)/10`
- `> 60`: `y=(((x-60)*5)+700)/10`

Total pool:

- `y=((1000+i+d)/1000)*x`

### Canonical mindstate bands

Modern DR documents all 35 bands from `0/34` through `34/34`:

| Value | Name |
| --- | --- |
| 0 | clear |
| 1 | dabbling |
| 2 | perusing |
| 3 | learning |
| 4 | thoughtful |
| 5 | thinking |
| 6 | considering |
| 7 | pondering |
| 8 | ruminating |
| 9 | concentrating |
| 10 | attentive |
| 11 | deliberative |
| 12 | interested |
| 13 | examining |
| 14 | understanding |
| 15 | absorbing |
| 16 | intrigued |
| 17 | scrutinizing |
| 18 | analyzing |
| 19 | studious |
| 20 | focused |
| 21 | very focused |
| 22 | engaged |
| 23 | very engaged |
| 24 | cogitating |
| 25 | fascinated |
| 26 | captivated |
| 27 | engrossed |
| 28 | riveted |
| 29 | very riveted |
| 30 | rapt |
| 31 | very rapt |
| 32 | enthralled |
| 33 | nearly locked |
| 34 | mind lock |

### Canonical skill groups

Modern DR documents ten pulse groups:

| Offset | Canonical group composition |
| --- | --- |
| 0s | Shield Usage, Light Armor, Chain Armor, Brigandine, Plate Armor, Defending |
| 20s | Parry Ability, Small Edged, Large Edged, Twohanded Edged |
| 40s | Small Blunt, Large Blunt, Twohanded Blunt, Slings, Bow, Crossbow |
| 60s | Staves, Polearms, Light Thrown, Heavy Thrown, Brawling, Offhand Weapon, Melee Mastery |
| 80s | Missile Mastery, Primary Magic, Attunement, Arcana, Targeted Magic, Augmentation |
| 100s | Debilitation, Utility, Warding, Sorcery, Evasion, Athletics, Perception |
| 120s | Stealth, Locksmithing, Thievery, First Aid, Outdoorsmanship |
| 140s | Skinning |
| 160s | Forging, Engineering, Outfitting, Alchemy, Enchanting, Scholarship, Mechanical Lore, Appraisal |
| 180s | Performance, Tactics, Astrology, Backstab, Bardic Lore, Conviction, Empathy, Expertise, Instinct, Summoning, Thanatology, Theurgy, Trading |

### Wisdom and pulse size

- Elanthipedia is explicit that Wisdom increases pulse size.
- Elanthipedia gives magnitude reference points, not the exact pulse formula: compared to value 10, Intelligence/Wisdom produce about `112%` at 30, `121%` at 60, `125%` at 90, and `130%` at 120.
- Discipline is documented as also affecting pulse size, but at about 10% efficacy relative to Intelligence/Wisdom.
- Elanthipedia does not provide the exact modern pulse-size equation in the article text, only the directional effect and empirical magnitudes. If LEARN-003 needs an explicit equation, the code spec will need to cite a fallback authority such as the relevant GSL or forum-post-derived approximation, with that deviation called out.

### Edge cases explicitly documented

- Bits-per-rank remains `200 + current_rank`.
- At `1750` ranks, a skill no longer gains new pool XP and draining has no effect.
- Mind lock is full pool and prevents further gain into the pool.
- Pulses still drain experience out of a filled pool; the article does not describe a modern separate overflow pool beyond the distinct rested/buffer systems.
- Secondary skills under 50 ranks drain like primary skills.
- Tertiary skills under 25 ranks drain like secondary skills.

### EXPERIENCE command surface

- `EXPERIENCE` with no argument shows only skills with field experience.
- `EXPERIENCE CIRCLE` shows next-circle requirements.
- `EXPERIENCE SKILL <abbr>` or abbreviated skill names show individual skill detail.
- Skill abbreviations are documented at up to three characters when unique, but the command page also preserves specific canonical short forms such as `LE`, `TM`, `PA`, `SU`, `OUT`, and others.

## Step 1 Findings - Existing Implementation Map

### 1a. Pulse scheduler and tick handler

Primary files:

- `world/systems/exp_pulse.py`
- `engine/services/pulse_service.py`
- `server/conf/at_server_startstop.py`

Current behavior:

- The active EXP pulse runs on `PULSE_TICK = 20` with `FULL_CYCLE = 200` in `world/systems/exp_pulse.py`.
- The ticker is started from `at_server_start()` via `start_exp_ticker()` in `server/conf/at_server_startstop.py`.
- The active scheduler is not Evennia's raw shared ticker callback directly; `start_exp_ticker()` schedules `skills:process_pulse` through the repo scheduler abstraction.
- `exp_pulse_tick()` increments `GLOBAL_TICK` by 20 and hands control to `PulseService.process_skill_pulse(...)` for each active character.
- `PulseService` iterates the transient `character.exp_skills.skills` dict, filters by `is_active(skill)`, matches the current tick against the supplied group offsets, and calls `pulse(skill)`.
- Rank advancement is still local to `world/systems/skills.py::process_rank()`, which increments `skill.rank` and then fires `owner.on_skill_rank_gained(...)`.

Drift from canon:

- The scheduler already has the correct 20-second cadence and 200-second cycle.
- The configured offsets are only five buckets: `{100: 0, 120: 20, 140: 40, 160: 60, 180: 80}`.
- That means the runtime currently pulses only five offset groups, not the canonical ten.
- There is also a separate legacy `process_learning_tick()` still registered at 10 seconds in `at_server_start()`, but `Character.process_learning_pulse()` is a no-op. Today that legacy ticker only matters for teaching pulses and compatibility instrumentation, not for actual field-to-rank draining.

### 1b. Pool size calculation

Primary file:

- `world/systems/skills.py`

Current behavior:

- `base_pool(rank, skillset)` ignores the `skillset` parameter and always uses one shared formula: `(15000 * rank / (rank + 900)) + 1000`.
- `pool_stat_modifier(owner)` reads raw `intelligence` and `discipline` from `db.stats` and applies one shared linear modifier: `1.0 + (((intelligence - 10) + (discipline - 10)) * 0.005)`, clamped to `0.75..1.5`.
- `SkillState.recalc_pool()` computes `max_pool = base_pool(rank, skillset) * pool_stat_modifier(owner)`.

Drift from canon:

- Primary/secondary/tertiary have no distinct base formulas.
- Intelligence and Discipline use one linear blended modifier instead of separate breakpoint curves at 30 and 60.
- Pool size is computed dynamically, not stored as a separate persisted value.

### 1c. Mindstate naming

Primary files:

- `world/systems/skills.py`
- `typeclasses/characters.py`
- `commands/cmd_experience.py`
- `commands/cmd_skilldebug.py`

Current behavior:

- Runtime `SkillState` mindstate names come from `world/systems/skills.py::MINDSTATE_NAMES` via threshold lookup.
- That runtime map is sparse: it only defines names at `0,1,2,3,4,5,6,7,8,9,10,15,20,25,30,34`.
- Legacy `Character.get_mindstate_label()` still uses the much older coarse `MINDSTATE_LEVELS` list in `typeclasses/characters.py`, but `get_skill_detail_entry()` and `get_skill_entries()` now use the transient `exp_skill.mindstate_name()` surface instead.
- `commands/cmd_experience.py` displays whatever `get_skill_detail_entry()` returns for per-skill detail and `skill.mindstate_name()` for list rows.
- `commands/cmd_skilldebug.py` also displays the transient runtime mindstate name.

Drift from canon:

- The system is no longer on the older 8-band map at the main player-facing path, but it still does not have the canonical 35-band ordered map.
- Several current names are wrong for their numeric positions. For example, the runtime map currently returns `engaged` at 15 and `absorbed` at 20, while canon is `absorbing` at 15 and `focused` at 20.

### 1d. Pulse-to-rank conversion math

Primary file:

- `world/systems/skills.py`

Current behavior:

- `drain_skill(skill, wisdom=30)` calculates drain as `skill.max_pool * rate * mod`.
- `rate` is chosen from fixed rates: `primary=0.067`, `secondary=0.050`, `tertiary=0.035`.
- `mod` comes from `wisdom_modifier(wis) = 1 + (wis - 30) * 0.003`.
- The drained amount is subtracted from `skill.pool` and added directly to `skill.rank_progress`.
- `process_rank(skill)` converts `rank_progress` into actual ranks using `rank_cost(rank) = 200 + rank`.

Drift from canon:

- Wisdom is a simple linear modifier, not the documented diminishing-return magnitude model.
- Discipline does not affect pulse size here at all.
- The modern DR low-rank exceptions for secondaries under 50 and tertiaries under 25 do not exist.
- Drain is purely per-skill and does not consult profession, skill group semantics, or any group-level state beyond offset matching.

### 1e. Skill group composition

Primary files:

- `world/systems/skills.py`
- `engine/bundles/builtin_skills.py`
- `engine/services/pulse_service.py`

Current behavior:

- The code has a pulse-group concept via `get_skill_pulse_group(name)`.
- Pulse-group values come from the skill registry if present, otherwise from `LEGACY_SKILL_PULSE_GROUPS` in `engine/bundles/builtin_skills.py`.
- The fallback and legacy maps only cover a small subset of skills and only the five buckets `100, 120, 140, 160, 180`.
- Registry `group` is a coarse content category such as `survival`, `magic`, `weapons`, `lore`, not the canonical ten pulse groups.

Drift from canon:

- The repo has no ten-group canonical composition table.
- Group membership is partly inferred from incomplete registry metadata and partly hardcoded fallback mappings.
- The fallback skill registry itself only contains a 12-skill subset, so absent canon rows would not carry canonical pulse-group structure.

### 1f. Skillset placement (primary/secondary/tertiary)

Primary files:

- `typeclasses/characters.py`
- `world/professions/professions.py`
- `world/professions/skillsets.py`

Current behavior:

- `Character.get_exp_skillset_tier(skill_name)` first consults `EXP_SKILLSET_TIER_OVERRIDES` and otherwise falls through to `get_skill_metadata(skill_name).category` only if that category string is already one of `primary/secondary/tertiary`.
- The current override map only contains `empathy -> primary`, `first_aid -> secondary`, and `scholarship -> secondary`.
- If no override or direct `primary/secondary/tertiary` metadata exists, everything defaults to `primary`.
- Profession data in `world/professions/professions.py` only stores category priorities such as `primary = survival`, `secondary = lore`, `tertiary = weapons`; it does not store canonical per-skill placement lists.
- `world/professions/skillsets.py` stores cross-category weight multipliers by profession, not canonical per-skill placement.

Drift from canon:

- Placement is not profession-driven at the skill level.
- The pulse math does act on `skill.skillset`, but the assignment of that skillset is mostly placeholder/default behavior rather than canonical profession data.

## Step 2 Findings - Preservation Contracts

### 2a. LEARN-001 TDP accrual hook

Primary files:

- `world/systems/skills.py`
- `typeclasses/characters.py`
- `tests/test_tdp_foundation.py`

Contract:

- `world/systems/skills.py::process_rank(skill)` increments `skill.rank` first.
- Immediately afterward it calls `owner.on_skill_rank_gained(skill.name, previous_rank, int(skill.rank or 0), 1)`.
- `Character.on_skill_rank_gained(...)` assumes `old_rank < new_rank`, uses the reached ranks to add hidden TDP pool progress, and grants spendable TDP on each 200 pool crossed.
- `tests/test_tdp_foundation.py` verifies this exact contract, including a direct `process_rank()` scenario.

Preservation requirement:

- LEARN-003 may move where rank advancement is triggered, but every actual rank gain must still call `Character.on_skill_rank_gained(skill_id, old_rank, new_rank, ranks_gained)` with rank increments already applied.

### 2b. LEARN-002b stat training surfaces

Primary files:

- `engine/services/stat_training_service.py`
- `tests/learning/test_stat_training_service.py`

Contract:

- Stat training consumes `db.stats`, racial TDP modifiers, and `spend_tdp()`.
- It does not read runtime skill pool internals.
- Its only relationship to learning is indirect through the available TDP total.

Preservation requirement:

- Preserve TDP accrual totals and the TDP spend API. No pulse-internal shape is required by the trainer service.

### 2c. LEARN-002b circle advancement surfaces

Primary files:

- `engine/services/circle_service.py`
- `tests/learning/test_circle_service.py`

Contract:

- Circle projection sums ranks from `db.exp_skill_state` if present, otherwise falls back to `db.skills`.
- It does not read pool size, mindstate, or ticker internals.

Preservation requirement:

- Preserve rank persistence shape and continued synchronization of per-skill rank data into `db.exp_skill_state`.

### 2d. LEARN-002b exp command surfaces

Primary file:

- `commands/cmd_experience.py`

Contract:

- List view relies on transient `exp_skills`, `skill.pool`, `skill.max_pool`, `skill.rank_progress`, and `skill.mindstate_name()`.
- Detail view relies on `get_skill_detail_entry()` plus `_sync_exp_skill_state()`.
- Displayed field labels are stable: rank, mindstate, bits/pool, group/category, circle projection.
- `exp <skill>` expects a meaningful `mindstate` label and a meaningful pool/max pool display.

Preservation requirement:

- Player-visible shape must stay intact, but LEARN-003 may replace the formulas and name map beneath it.

### 2e. Skill state persistence

Primary files:

- `typeclasses/characters.py`
- `world/systems/skills.py`

Actual current shape:

- The live persisted structure is `db.exp_skill_state`, not `db.skill_states`.
- Each stored entry currently contains:
  - `rank`
  - `rank_progress`
  - `pool`
  - `skillset`
  - `mindstate`
  - `last_trained`
- Legacy compatibility data in `db.skills` stores only `rank`, `pool`, and `mindstate`.

Migration implication:

- Any LEARN-003 state additions must target `db.exp_skill_state` and continue to keep `db.skills` compatible enough for older readers.

## Step 3 Comparison Table

| Subsystem | Existing | Canonical target | Replacement strategy |
| --- | --- | --- | --- |
| Pulse cadence | M | 200s cycle, 20s offsets | Preserve the 20s/200s skeleton; replace offset table and group routing |
| Skill group composition | N | 10 canonical groups with fixed membership | Add canonical pulse-group data and stop relying on five-bucket legacy fallback |
| Pool base formula | N | Primary/secondary/tertiary distinct formulas | Replace |
| Intelligence pool bonus | N | 30/60 breakpoint curve | Replace |
| Discipline pool bonus | N | 30/60 breakpoint curve plus weaker effect | Replace |
| Wisdom pulse effect | N | Canon modern magnitude, not linear placeholder | Replace |
| Mindstate scale 0-34 | M | 0-34 | Preserve |
| Mindstate names | N | 35 canonical ordered names | Replace/add full map |
| Bits-per-rank | M | 200 + current rank | Preserve |
| Skillset placement storage | N | Profession-driven per-skill placement | Add canonical data structure |
| Skillset placement used by drain | G | Placement affects drain, but current assignment is mostly placeholder | Replace assignment logic, preserve drain hook surface |
| TDP hook at rank gain | M | Rank gain awards TDP | Preserve exactly |
| Rank persistence surface | G | Persistent rank surface needed by other systems | Preserve `db.exp_skill_state` as authority; migrate fields in place |
| EXP command detail surface | G | Stable player-visible detail output | Preserve output shape, replace backing labels and math |

Legend:

- `M`: mostly matches
- `G`: good enough seam exists but data/math is incomplete
- `N`: non-canonical
- `X`: missing

## Step 4 Risks

### Risk 1 - Test coverage gaps

Assessment:

- There is more pulse-specific coverage than the earlier learning audit implied, but it is still coverage of the current non-canonical behavior rather than the canonical target.
- Existing tests and DireTest scenarios cover:
  - pulse-group staggering
  - skillset drain ordering
  - wisdom-based drain ordering
  - mind-lock behavior
  - mindstate transitions
  - ticker registration and timing audit visibility
- Existing preservation tests cover:
  - TDP rank-gain callback behavior
  - stat training independence from pulse internals
  - circle advancement dependence on persisted rank totals
  - exp command output behavior

Implication:

- LEARN-003 does not need tests before any code can move, but it does need a two-layer update strategy:
  - preserve the contract tests that should remain true
  - replace the non-canonical pulse-behavior tests with canonical cadence/group/formula expectations

### Risk 2 - Migration surface

Assessment:

- Pool size is computed dynamically, not persisted as an authoritative field.
- That avoids a full stored-value migration for `max_pool`.
- But `db.exp_skill_state.pool`, `mindstate`, and `skillset` already exist and are computed under the old formulas and old placement defaults.

Implication:

- LEARN-003 needs a lazy migration/backfill path for `skillset` and any new pulse-group metadata, and should force `recalc_pool()` under the new formulas on first touch.
- Existing pool values may remain numerically legal but semantically wrong after formula replacement until recomputed.

### Risk 3 - Skill group introduction

Assessment:

- The code already has a `pulse_group` concept, but it is only five-bucket fallback data and incomplete registry coverage.
- Registry `group` today means broad skillset/category, not canonical pulse group.

Implication:

- LEARN-003a should add explicit canonical pulse-group data rather than overloading the current broad `group` field.
- `exp <skill>` currently shows `category`, not pulse group, so introducing canonical pulse groups does not have to change the current command surface immediately.

### Risk 4 - Skillset placement coupling

Assessment:

- The profession layer does have high-level primary/secondary/tertiary category priorities.
- It does not have per-skill placement lists.
- `get_exp_skillset_tier()` currently defaults almost everything to `primary` unless a hardcoded override exists.

Implication:

- Canon placement data is missing as a first-class structure.
- This is a structural data task, not just a formula swap.
- It should land before pulse formulas are replaced so the new formulas have real input data.

### Risk 5 - Wisdom formula uncertainty

Assessment:

- Elanthipedia gives qualitative behavior and effect magnitudes, but not a single exact modern drain equation.
- The current code uses a clearly placeholder linear formula.

Implication:

- LEARN-003 must either:
  - encode a best-fit modern approximation with explicit source notes, or
  - fall back to a GSL-derived/archaeology-derived formula where modern DR documentation is silent.
- This uncertainty is one of the main reasons not to combine data-structure work and formula replacement in a single dispatch.

### Risk 6 - Pulse-during-mind-lock semantics

Assessment:

- Current code stops gain at mind lock via `award_xp()` and continues drain via `pulse()` and `drain_skill()`. That matches the broad modern expectation.
- The system does not implement any additional overflow or alternate holding area beyond current pool semantics.
- Existing DireTest scenarios already assert no further gain after mind lock.

Implication:

- This area is relatively low risk and should largely be preserved.
- The main LEARN-003 work here is making sure canonical drain cadence and formulas continue to treat a locked pool as drainable while rejecting additional gain.

## Step 5 Recommendation

### Recommended shape: split into LEARN-003a + LEARN-003b

#### LEARN-003a - Data and compatibility structure

Scope:

- Add canonical ten-group pulse metadata to the skill registry or a parallel learning registry.
- Add profession-driven per-skill placement data instead of the current three-skill override map.
- Replace the sparse runtime mindstate name map with the full 35-name canonical map.
- Add any compatibility helpers needed so commands and persistence readers can consume the richer data without changing formulas yet.
- Add or rewrite tests so canonical data expectations are pinned before formula replacement.

Why first:

- It is mostly additive and local.
- It gives LEARN-003b authoritative inputs instead of forcing formula replacement to invent missing data inline.
- It reduces the number of unknowns in the formula dispatch.

#### LEARN-003b - Formula and cadence replacement

Scope:

- Replace pool size formulas with primary/secondary/tertiary + Int/Disc breakpoint math.
- Replace current drain math with canon-shaped pulse-size behavior, including the low-rank exceptions for secondaries and tertiaries if that remains in scope.
- Expand the active scheduler from the current five-offset runtime to the full ten-group rotation.
- Preserve rank-gain callback behavior and persisted rank surfaces.
- Update pulse-focused tests from current placeholder behavior to canonical expectations.

Why second:

- Once the data structure and label work are already in place, this becomes a bounded runtime replacement instead of an architectural mixed dispatch.

### Why not a single LEARN-003 dispatch

- A single dispatch would combine four different change classes:
  - new canonical data structures
  - persistence normalization
  - player-visible label changes
  - runtime formula and scheduler replacement
- That is exactly the kind of surface mix that forced LEARN-002 to split.
- The current code already has enough independent seams that splitting reduces risk without creating artificial fragmentation.

### Why not a three-way split

- The cadence work is already half-present: the 20s shared tick and 200s cycle exist.
- The missing scheduler work is mainly expansion from five pulse offsets to ten plus new group membership data.
- That is substantial, but it does not justify a third dispatch once 003a has already laid down the canonical groups and placement data.

## Estimated Scope

### LEARN-003a

- Estimated code delta: roughly 700-1200 LOC
- Main files likely touched:
  - `engine/bundles/builtin_skills.py`
  - `world/professions/professions.py` or a new profession-placement module
  - `world/systems/skills.py`
  - `typeclasses/characters.py`
  - pulse/command tests
- Estimated implementation window: 1 focused dispatch

### LEARN-003b

- Estimated code delta: roughly 1200-1800 LOC
- Main files likely touched:
  - `world/systems/skills.py`
  - `world/systems/exp_pulse.py`
  - `engine/services/pulse_service.py`
  - preservation tests and pulse scenarios
- Estimated implementation window: 1 larger focused dispatch

Combined, this is still in the rough range of a 2000-3000 LOC body of work, but the split keeps each part testable and keeps the replacement dispatch from having to invent its own missing data model mid-stream.

## Verification Checklist

- [x] Step 0 completed: modern DR canon re-read from Elanthipedia Experience and Experience command pages
- [x] Step 1 completed: pulse scheduler, pool math, mindstate naming, drain math, group composition, and skillset placement audited
- [x] Step 2 completed: TDP hook, stat training, circle advancement, exp command, and persistence contracts documented
- [x] Step 3 completed: comparison matrix filled
- [x] Step 4 completed: six risks assessed with code references
- [x] Step 5 completed: recommendation made
- [x] Report written to `tmp/drg-learn-003-audit-report.md`
- [x] No gameplay code changed
- [x] Time-box respected within the requested audit pass