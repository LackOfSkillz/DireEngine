# Slippy EXP Spec vs DireEngine Implementation

## Scope

This compares Slippy's posted EXP system specification against the EXP system that is actually live in this repo today, using the current implementation surfaces in:

- `world/systems/skills.py`
- `engine/services/skill_service.py`
- `world/systems/exp_pulse.py`
- `engine/services/pulse_service.py`
- `typeclasses/characters.py`
- `commands/cmd_experience.py`

It does not compare against an aspirational design. It compares against the code that currently owns learning, field XP, pulse draining, persistence, and player-facing output.

## Executive summary

The two systems are philosophically related but mechanically different.

They align on the high-level idea that learning is two-stage:

- actions award temporary field experience into a per-skill pool
- a later pulse drains that pool into permanent rank progress
- a player-facing mindstate exists as a readable expression of learning fullness

That is the strongest overlap.

From there, Slippy's design is much more faithful to a classic DragonRealms-style progression model, while DireEngine currently runs a deliberately simplified, operationally safer version of the same family of ideas.

Slippy's design is deeper, more simulation-heavy, and more tightly interconnected. DireEngine's implementation is flatter, easier to reason about, easier to tune in isolation, and clearly built to survive a live migration from older legacy skill state.

## Where the systems match

### 1. Two-stage learning model

This is the biggest common point.

Slippy's spec separates:

- field experience storage
- periodic conversion into rank progress

DireEngine does the same:

- XP enters `skill.pool`
- pulses drain `skill.pool` into `skill.rank_progress`
- `process_rank()` converts that progress into permanent rank gains

So at the architectural level, both systems reject direct "gain rank immediately on action" progression.

### 2. Per-skill pools and per-skill mindstates

Both systems treat learning as skill-local.

In DireEngine, each `SkillState` has:

- `rank`
- `rank_progress`
- `pool`
- `max_pool`
- `mindstate`

That maps cleanly to Slippy's notion of per-skill field exp plus a displayed learning state derived from pool fullness.

### 3. Batched pulse processing

Slippy's design uses a recurring timer that processes skill batches instead of all skills all at once.

DireEngine also does this in production form:

- `world/systems/exp_pulse.py` drives a global ticker
- `MAX_SKILLS_PER_TICK = 10`
- `PulseService.process_skill_pulse()` only processes active skills and gates them by group offset

That means the runtime shape is very similar even though the internal math is not.

### 4. Stats affect learning

Both systems let stats shape the experience model.

Slippy's spec uses stats heavily:

- Wisdom for conversion speed
- Intelligence and Discipline for cap sizing

DireEngine also uses those stats, but far more lightly:

- Intelligence and Discipline modify pool size through `pool_stat_modifier()`
- Wisdom modifies drain rate through `wisdom_modifier()`

So the repo is already pointed in the same direction, just with much gentler formulas.

### 5. Mind lock as a real stop condition

Both systems recognize a full learning state.

In DireEngine, `award_xp()` exits immediately when `skill.mindstate >= MIND_LOCK`.

That is directly analogous to Slippy's "mind lock" behavior where new field exp stops once the skill pool is full.

## Where DireEngine is materially different

### 1. DireEngine has no global mind model

This is the single largest design difference.

Slippy's system has two layers:

- a per-skill pool state
- a separate player-wide `mind` value from `0` to `1200` that slows conversion across all skills

DireEngine does not implement that global mind mechanic at all.

Its current mindstate is entirely per-skill and derived from `pool / max_pool`. There is no cross-skill mental saturation model, no shared "clear/fluid/murky/frozen" controller, and no global cognitive pressure that slows every skill at once.

Practical consequence:

- Slippy's design creates strong interaction between all trained skills
- DireEngine's design keeps each skill mostly isolated except for pulse scheduling and stat effects

This makes DireEngine easier to predict and tune, but it is less systemic and less strategically rich.

### 2. DireEngine uses a much simpler pool curve

Slippy's pool cap model is tiered by rank brackets and class affinity, then modified by a compound stat formula:

- piecewise rank scaling
- category-based multipliers
- `INT² + INT × DISC`
- explicit class affinity bands

DireEngine's pool model is much simpler:

- one saturating curve in `base_pool()`
- one bounded stat modifier in `pool_stat_modifier()`
- no class affinity term in the cap formula itself

This is a major simplification.

Practical consequence:

- Slippy's system makes pool capacity a major part of class identity
- DireEngine currently makes pool capacity mostly a rank-and-stats property with light skillset tier flavoring elsewhere

### 3. DireEngine's rank economics are dramatically flatter

Slippy's spec uses:

- a complex transfer formula
- a separate exp-required-per-rank formula
- fixed-point rank math with 1,000,000 internal units
- goal distance affecting conversion speed

DireEngine does not do any of that.

It uses:

- flat drain into `rank_progress`
- `rank_cost(rank) = 200 + rank`
- a straightforward while-loop that promotes rank when progress exceeds cost

This makes DireEngine much easier to debug and far easier to reason about numerically, but it is not remotely the same progression curve.

Practical consequence:

- Slippy's system is designed to create a long-tail progression economy
- DireEngine's current rank gain model is intentionally plain and serviceable

### 4. DireEngine has no goal system

Slippy's conversion depends heavily on `goal - current + 1`, with different offsets by affinity tier. That means conversion accelerates when the skill is far from goal and slows as it approaches.

DireEngine has no `goal` field and no equivalent mechanic.

Its conversion speed is driven by:

- `max_pool`
- skillset drain rate
- wisdom modifier

That means DireEngine currently lacks one of the most distinctive pacing features in Slippy's design.

### 5. Outcome and event weighting are stronger in DireEngine's award path

This is one place where DireEngine is arguably more application-focused.

Slippy's spec is very strong on macro progression rules, but the per-action award layer in the pasted spec is mostly described as representative examples and clamps.

DireEngine's live award path is tightly integrated with actual gameplay resolution:

- difficulty bands
- success/failure modifiers
- skill-specific gain modifiers
- event weights
- context multipliers

In other words, DireEngine's action-to-pool pipeline is more explicitly shaped for moment-to-moment command outcomes, while Slippy's spec is more detailed on the pool-to-rank conversion economy.

### 6. DireEngine's mindstate labeling is simpler and more game-facing

Slippy's posted system has a large named vocabulary split across:

- overall mind state labels
- per-skill pool labels

DireEngine uses a compact 0-34 model with named breakpoints such as:

- `clear`
- `learning`
- `engaged`
- `focused`
- `riveted`
- `mind lock`

This is cleaner and cheaper to display, but far less expressive than the full DR-style ladder.

### 7. DireEngine is built around migration safety

This is an important repo-specific difference.

Slippy's document reads like a clean system spec for a coherent progression model.

DireEngine is clearly carrying live migration concerns:

- `db.exp_skill_state` is the authoritative persisted store
- `_sync_exp_skill_state()` can seed from legacy `db.skills`
- `_persist_exp_skill_state()` selectively mirrors data back to legacy storage
- template-integrated skills are treated differently from legacy-only skill entries

That is not just an implementation detail. It changes the shape of the whole system.

DireEngine is not merely building an EXP model. It is also managing coexistence between old and new representations.

### 8. DireEngine currently omits many of Slippy's secondary systems

The posted Slippy design includes a wide set of related mechanics that do not appear in the current DireEngine implementation:

- newbie transfer boosts
- roleplay/event conversion multipliers with expiry counters
- study/textbook bonuses
- TDP awards
- death wiping all field exp
- blocked-zone suppression rules as a first-class EXP rule
- sleep-specific learning disruption
- overflow-guard ladders for fixed-point math
- teacher/scholarship coupling at the formula level

Some adjacent ideas exist in DireEngine under other names or other systems, but they are not implemented in the same unified EXP model presented in the Slippy spec.

## Where DireEngine is stronger than the posted spec

This is not one-way. There are places where the repo's current implementation is more operationally mature.

### 1. Service boundaries are cleaner

The repo has a fairly clean split between:

- core math/state in `world/systems/skills.py`
- orchestration in `engine/services/skill_service.py`
- ticking in `world/systems/exp_pulse.py`
- player-facing exposure in `commands/cmd_experience.py`

That is a good production shape.

Slippy's spec is mechanically rich, but as posted it is still a design document. DireEngine already has explicit service boundaries suitable for a live Evennia runtime.

### 2. Runtime cost is easier to predict

Slippy's formulas are denser and more stateful. They would be heavier to tune, test, and troubleshoot under load.

DireEngine's current formulas are much cheaper:

- no logarithmic rank-cost branches
- no global-mind transfer penalty ladder
- no goal-distance dependency
- no per-tick random jitter
- no fixed-point overflow concerns

That simplicity is not just mathematical. It reduces operational risk.

### 3. The active-skill pulse model is leaner

Slippy's design assumes broad slot processing across a large skill table.

DireEngine only pulses active learned skills, and it already gates processing by active window and group offsets. That is a pragmatic optimization for a live multiplayer environment.

### 4. Player feedback is already wired into live UX

DireEngine has transition-based messaging around mindstate changes and an `experience` command that focuses on active skills by default.

That makes the current implementation feel more integrated into live gameplay, even if the underlying economy is simpler.

## Where Slippy's design is stronger than DireEngine's current implementation

### 1. Slippy's progression model has more identity

Slippy's spec ties together:

- class affinity
- stats
- pool cap
- conversion speed
- mind pressure
- goal pacing

That creates a more coherent progression identity. DireEngine currently has pieces of that idea, but not the same tight internal logic.

### 2. Slippy's system creates more strategic tradeoffs

Because global mind affects all conversion and each skill can separately mind lock, players have to think about where, when, and how broadly they train.

DireEngine is more straightforward. That is good for clarity, but it offers fewer interesting tension points.

### 3. Slippy's formulas support long-term balance work

The posted model is much more parameterized. There are many knobs:

- pool growth bands
- affinity bands
- transfer scaling
- goal offsets
- decay rate
- low-level boosts
- RP multipliers

DireEngine is easier to operate now, but Slippy's design gives more levers for long-horizon economy tuning.

## Comparison of engineering style

The chat context around the spec is actually consistent with what this repo is already doing.

### Small refactors

Slippy says he refactors small and lets larger refactors become easier over time.

That matches the repo's current EXP path surprisingly well. The live implementation is not a single rewrite. It is a layered bridge:

- old `db.skills`
- new `db.exp_skill_state`
- transient `SkillHandler`
- selective template integration

That is exactly the kind of incremental refactor posture he described.

### Markdown-heavy development

The chat note about using markdown files as memory aids also matches this repo strongly.

DireEngine already leans heavily on markdown for:

- design notes
- as-builts
- microtask tracking
- architecture references
- system docs

So on process, the two approaches are aligned even where the mechanics differ.

### Central helper/service direction

The frozen-scope note about ordinals and target resolution also matches a recognizable repo pattern: put normalization and dispatch logic into shared helpers/services instead of scattering it through commands.

That is very similar in spirit to how DireEngine already centralizes EXP awarding in `SkillService` instead of leaving progression logic embedded in every caller.

## Bottom line

If the question is "is Slippy's system basically the same as ours?", the answer is no.

If the question is "is it from the same design family?", the answer is yes.

Slippy's posted EXP model is a more complete, more interdependent, more simulation-heavy DragonRealms-style learning economy.

DireEngine's current implementation is a simplified live adaptation with these defining traits:

- per-skill field XP pools
- per-skill mindstates
- scheduled batched draining into rank progress
- lightweight stat influence
- linear rank cost
- explicit service boundaries
- migration-safe persistence and legacy compatibility

That means DireEngine is currently closer to "a stable production skeleton with some DR-style semantics" than to "a faithful reproduction of the full system Slippy documented."

In short:

- Slippy's spec is richer and more systemic
- DireEngine's implementation is simpler and more operationally conservative
- the overlap is real, but the math and pacing model are not the same