# DireMUD Experience System (Phase 1)

## 1. Overview

### Plain-Language Explanation

The DireMUD experience system is based on a field experience model inspired by DragonRealms.

Each skill has:
- A rank for permanent progression
- A field experience pool for temporary stored learning
- A mindstate for the user-facing fullness of the pool

Phase 1 only implements the core data model, pool math, mindstate math, and debug visibility.

### Code Snippet

```python
skill = caller.exp_skills.get("evasion")

print(skill.rank)
print(skill.pool)

There is no phase-wide formula in this section. Phase 1 is a container and formula foundation for later learning behavior.

- `rank = 0` means the skill has no permanent training yet.
- `pool = 0.0` means no field experience is stored.
- `mindstate = 0` means the pool is empty.

## 2. Skill Data Model
### Plain-Language Explanation

Each skill is represented by a `SkillState` object. The `SkillHandler` lives on the Character as `self.exp_skills` and lazily creates a `SkillState` the first time a skill name is requested.

The handler is transient Python state. Phase 1 does not add persistent storage or migrate the repo's older live `self.db.skills` structure.

### Code Snippet

```python
from world.systems.skills import SkillHandler, SkillState


class SkillState:
    def __init__(self, name):


class SkillHandler:
    def __init__(self, obj):
        self.obj = obj
        self.skills = {}

    def get(self, name):
        if name not in self.skills:
            self.skills[name] = SkillState(name)
        return self.skills[name]
```

### Math

There is no standalone formula in this section. This section defines the container that later formulas operate on.

### Example Values

```python
skill = SkillState("evasion")

skill.name       # "evasion"
skill.rank       # 0
skill.skillset   # "primary"
skill.mindstate  # 0
```

## 3. Field Experience Pool

### Plain-Language Explanation


This pool is not permanent progression. It is buffered learning that will be converted later. Phase 1 only stores the pool and keeps it clamped to a maximum capacity.

The maximum capacity is stored in `skill.max_pool`.

Each skill also stores a `skillset` string. In Phase 1 that value is part of the data model and the public formula signature, but no hidden skillset-specific multiplier is applied yet.

### Code Snippet

```python
skill = caller.exp_skills.get("evasion")
skill.pool = 250.0
skill.max_pool = 1000.0
skill.skillset = "primary"
skill.update_mindstate()
```

### Math

The pool is a bounded value:

$$
0 \le \text{pool} \le \text{max\_pool}
$$

That bound is enforced whenever the pool is recalculated or serialized.

### Example Values

- `pool = 250.0`, `max_pool = 1000.0` means the skill is one quarter full.
- `pool = 1000.0`, `max_pool = 1000.0` means the skill is full.
- `pool = 1400.0`, `max_pool = 1000.0` is invalid and will be clamped back to `1000.0`.

## 4. Mindstate System

### Plain-Language Explanation

Mindstate is the UI-facing representation of how full the field experience pool is.

In Phase 1 it is a number from `0` to `34`. It is not stored as an independent truth value. It is derived from the current pool ratio.

`0` means empty. `34` means full.

### Code Snippet

```python
def calculate_mindstate(pool, max_pool):
    if max_pool <= 0:
        return 0
    ratio = pool / max_pool
    return max(0, min(34, int(ratio * 34)))


def update_mindstate(self):
    self.mindstate = calculate_mindstate(self.pool, self.max_pool)
```

### Math

The Phase 1 mindstate formula is:

$$
\text{mindstate} = \left\lfloor \frac{\text{pool}}{\text{max\_pool}} \times 34 \right\rfloor
$$

Then the result is clamped into the valid range:

$$
\text{mindstate} = \max(0, \min(34, \text{mindstate}))
$$

### Example Values

- `pool = 0`, `max_pool = 1000` gives `mindstate = 0`
- `pool = 500`, `max_pool = 1000` gives `mindstate = 17`
- `pool = 999`, `max_pool = 1000` gives `mindstate = 33`
- `pool = 1000`, `max_pool = 1000` gives `mindstate = 34`

## 5. Pool Size Formula

### Plain-Language Explanation

Phase 1 uses a single documented base pool curve. The function accepts `skillset` now so callers do not need a signature change later, but the current implementation uses the same base curve for every skill.

The curve grows quickly at low ranks, then slows down as rank increases. This prevents very small pools at low skill while also preventing unbounded growth.

### Code Snippet

```python
BASE_POOL_NUMERATOR = 15000.0
BASE_POOL_OFFSET = 900.0
BASE_POOL_FLOOR = 1000.0


def base_pool(rank, skillset):
    normalized_rank = max(0, int(rank or 0))
    return (BASE_POOL_NUMERATOR * normalized_rank / (normalized_rank + BASE_POOL_OFFSET)) + BASE_POOL_FLOOR
```

`SkillState` applies that formula on initialization and during recalculation:

```python
self.max_pool = base_pool(self.rank, self.skillset)
```

### Math

Let $x$ be the current rank.

$$
y = \frac{15000x}{x + 900} + 1000
$$

Where:

- $15000$ controls the height of the growth curve
- $900$ controls how quickly the curve bends and slows
- $1000$ is the minimum pool floor at rank $0$

As $x$ becomes very large, the fraction approaches $15000$, so the pool approaches an upper limit near:

$$
15000 + 1000 = 16000
$$

### Example Values

- `rank = 0` gives `max_pool = 1000.0`
- `rank = 100` gives `max_pool = 2500.0`
- `rank = 500` gives `max_pool ≈ 6357.1`
- `rank = 1000` gives `max_pool ≈ 8894.7`

## 6. Rank Cost Formula

### Plain-Language Explanation

The next rank cost is linear. Each new rank costs the current rank value plus a fixed base of `200`.

This keeps the formula easy to reason about and matches the recovered DragonRealms-style progression rule for this system phase.

### Code Snippet

```python
def rank_cost(rank):
    return 200 + rank
```

### Math

Let $r$ be the current rank.

$$
\text{next\_rank\_cost} = 200 + r
$$

### Example Values

- `rank = 0` gives `cost = 200`
- `rank = 50` gives `cost = 250`
- `rank = 100` gives `cost = 300`
- `rank = 500` gives `cost = 700`

## 7. XP Gain System

### Plain-Language Explanation

Phase 2 begins with direct field experience gain. XP is awarded into the skill pool, not directly into ranks.

The gain flow is:

- stop immediately if the skill is mind locked
- compute a base XP value as `3.5%` of the current max pool
- scale that base XP by difficulty
- scale it again based on success or failure
- apply continuous rank scaling so higher ranks learn less from each event
- apply any skill-specific learning modifier
- add the result to the pool, clamped to `max_pool`
- recompute mindstate from the new pool ratio

The system is still transient. It changes the in-memory `exp_skills` state only.

## Stealth Group Margin Softening

Group stealth contests apply one final shaping step after strongest-observer aggregation, support pressure, and crowd penalty are combined. This only affects extreme failure tails.

If the final margin is below `-30`, the overflow below that threshold is shifted upward toward `-20` and then softened:

$$
	ext{softened margin} = -20 + ((\text{margin} + 30) \times 0.6)
$$

Examples:

- `-30` stays `-30`
- `-35` becomes `-23`
- `-50` becomes `-32`
- `-70` becomes `-44`
- `-80` becomes `-50`

This preserves success while pulling heavy-pressure stealth results out of the catastrophic tail.

Crowded rooms then add uncertainty through support participation, not by modifying the final margin directly. Secondary observers contribute reduced support as before, but when `observer_count >= 6` each supporter's contribution is scaled by an engagement factor:

$$
    ext{engagement} = U(0.35, 1.0)
$$

$$
    ext{support contribution} = \max(0, \text{defender roll} - 0.5 \times \text{primary pressure}) \times \text{support scale} \times \text{engagement}
$$

This keeps the strongest observer as the primary counter while allowing crowded rooms to produce natural spread and occasional near-misses because not every secondary watcher reinforces at full strength every attempt.

In addition, crowded rooms apply a small softness factor to the combined defender pressure before the final margin is computed:

$$
	ext{effective detection} = (\text{primary pressure} + \text{support pressure}) \times 0.92
$$

This applies only when `observer_count >= 6`. It slightly reduces group-pressure stiffness without changing one-on-one contests.

### Code Snippet

```python
from world.systems.skills import award_xp, calculate_xp, train


skill = caller.exp_skills.get("evasion")

gained = award_xp(skill, 100.0)
xp_from_training = calculate_xp(skill, difficulty=60, success=True)
trained = train(skill, difficulty=60, success=True)
```

### Math

The base XP for one training event is:

$$
	ext{base} = \text{max\_pool} \times 0.035
$$

Difficulty scaling uses the gap between challenge difficulty and current rank:

$$
	ext{gap} = \text{difficulty} - \text{rank}
$$

Then:

- if $\text{gap} < -20$, factor $= 0.2$
- if $-20 \le \text{gap} < 0$, factor $= 0.6$
- if $0 \le \text{gap} < 20$, factor $= 1.0$
- if $20 \le \text{gap} < 50$, factor $= 0.7$
- if $\text{gap} \ge 50$, factor $= 0.3$

Success scaling is:

$$
	ext{success\_modifier} =
\begin{cases}
1.0 & \text{if success} \\
0.7 & \text{if partial success} \\
0.35\text{ to }0.5 & \text{if failure, depending on skill}
\end{cases}
$$

Rank scaling is:

$$
	ext{rank\_scaling} = \frac{1}{1 + (\text{rank} / 50)}
$$

Skill-specific tuning is then applied last. Current notable modifiers are:

- `perception = 0.40`
- `stealth = 0.18`

Event weight is applied after the base skill tuning so rare actions can pay more than high-frequency ones without hardcoding direct mindstate jumps. Current notable event weights are:

- `stealth = 1.0`
- `perception = 1.0`
- `brawling = 0.7`
- `light_edge = 0.6`
- `evasion = 0.5`
- `locksmithing = 2.5`
- `trap_disarm = 3.5`

Rare-event training also gets an opportunity-sensitive difficulty multiplier:

$$
	ext{difficulty\_multiplier} = 0.5 + \frac{\text{difficulty}}{\text{difficulty} + \text{rank}}
$$

In the live XP flow this sits on top of the existing difficulty curve, so easy events stay weak, on-rank events are strongest, and very hard events are still reduced enough to avoid cheese farming.

## Outcome-Based Learning

Training events can now express more than a plain hit-or-miss result. The EXP core accepts success, failure, partial, and strong outcomes and applies skill-specific outcome weights before XP is added to the pool.

This keeps failure meaningful without making it equal to success:

- failures still teach, but slowly
- partial outcomes sit between failure and full success
- full successes remain the fastest learning path

For stealth, the live outcome weights are:

- `success = 1.0`
- `strong = 1.0`
- `partial = 0.7`
- `failure = 0.35`

These outcome weights still exist in the core EXP math, but live stealth actions now pass through an additional state-machine gate before any XP is awarded.

## Rare Event Weighting

The EXP core now accepts an optional event key in addition to the skill name. This lets a single skill use different XP opportunity weights depending on what just happened.

For example:

- routine lockpicking uses the `locksmithing` event weight
- trap disarm, trap harvest, and trap rework use the `trap_disarm` event weight

That architecture preserves the same transient pool and drain system while allowing rare actions to move several mindstate steps from one meaningful success.

Full XP calculation is:

$$
    ext{xp} = (\text{max\_pool} \times 0.035) \times \text{difficulty\_factor} \times \text{difficulty\_multiplier} \times \text{success\_modifier} \times \text{rank\_scaling} \times \text{skill\_gain\_modifier} \times \text{event\_weight} \times \text{context\_multiplier}
$$

Awarding stops completely at mind lock:

$$
    ext{if mindstate} \ge 34, \; \text{gained} = 0
$$

## Stealth Contest Gate

Stealth is no longer treated as a simple immediate-award skill hook. Hide, stalk, ambush, and sneaking movement now route through a small state machine:

1. resolve a stealth-versus-perception contest, if one exists
2. store the contest context on the character
3. wait until the action roundtime expires
4. validate whether concealment requirements were preserved
5. apply the final XP award through the normal transient EXP core

That means stealth learning is now gated by interaction state, not just by calling `award_exp_skill(...)` inline.

The live stealth context multiplier currently combines four gates:

- no contest: `x0.1`
- contest margin quality on non-fail outcomes: `clamp(margin / 100, 0.5, 1.5)`
- failure quality buckets: `margin < -50 -> x0.1`, `-50 to -10 -> x0.25`, `-10 to 0 -> x0.5`
- repeated attempts against the same target context: `1 / (1 + (attempts - 1) * 0.4)`
- position pressure: `advantaged = x1.2`, `exposed = x0.8`, melee pressure `x0.7`

For persistent concealment actions such as `hide`, `stalk`, and `sneak`, breaking concealment before the delayed finalize step cancels the award.

The no-observer path is still delayed and still routed through the same store/finalize pipeline, but it records `contest_occurred = false` and stays on the negligible-learning branch.

Developer characters now also emit a temporary server-side debug line at finalize time showing `outcome`, `margin`, the stealth-specific XP modifier, the final context multiplier, and the awarded gain.

This is the enforced system rule now:

- no meaningful contest means negligible stealth XP
- no maintained concealment means no delayed payout for concealment-preserving actions
- repeated spam against the same observer or room context diminishes quickly

### Example Values

- injecting `100` XP into an empty rank `0` evasion pool raises `pool` by `100.0`
- training at matching difficulty gives the highest XP for that rank band
- failing still grants reduced, non-zero XP
- once `mindstate = 34`, additional award attempts return `0.0`

## 8. Pulse System

### Plain-Language Explanation

Once a skill has field experience in its pool, later pulses drain a percentage of that pool into rank progress.

The pulse model implemented here is:

- a global interval constant of `200` seconds
- a pulse offset constant of `20` seconds for later group scheduling work
- skill grouping metadata for a small starter set of skills
- skillset-based drain rates
- wisdom scaling on each pulse
- drained pool converted into `rank_progress`
- `rank_progress` converted into permanent ranks using `rank_cost(rank)`

The implemented loop is:

$$
[\text{pool}] \rightarrow [\text{pulse drain}] \rightarrow [\text{rank progress}] \rightarrow [\text{rank increase}]
$$

### Code Snippet

```python
from world.systems.skills import pulse


skill = caller.exp_skills.get("evasion")
drained = pulse(skill, wisdom=30)
```

### Math

Pulse timing constants are:

$$
	ext{pulse interval} = 200 \text{ seconds}
$$

$$
	ext{pulse offset} = 20 \text{ seconds}
$$

Wisdom scaling is:

$$
	ext{wisdom modifier} = 1 + (\text{wisdom} - 30) \times 0.003
$$

Drain rate depends on skillset:

- primary: `0.067`
- secondary: `0.050`
- tertiary: `0.035`

Per-pulse drain is based on the skill's current pool ceiling, not the remaining pool, so each pulse removes a stable chunk until the pool runs low.

Per-pulse drain is:

$$
	ext{drain} = \text{max\_pool} \times \text{drain rate} \times \text{wisdom modifier}
$$

The drain is capped so it never exceeds the remaining pool:

$$
	ext{drain} = \min(\text{drain}, \text{pool})
$$

After drain:

$$
	ext{pool} = \max(0, \text{pool} - \text{drain})
$$

$$
	ext{rank progress} = \max(0, \text{rank progress} + \text{drain})
$$

Rank conversion is:

$$
	ext{while rank progress} \ge (200 + \text{rank}): \text{ rank += 1}
$$

### Example Values

- `pool = 1000`, `skillset = primary`, `wisdom = 30` gives `drain ≈ 67` on the first pulse
- `pool = 1000`, `skillset = tertiary`, `wisdom = 30` gives `drain ≈ 35` on the first pulse
- higher wisdom drains faster because the modifier increases above `1.0`
- repeated pulses move the pool toward zero and move `rank_progress` upward

## 9. Global Pulse System

### Plain-Language Explanation

The pulse drain math is now driven by an Evennia ticker instead of manual debug simulation alone.

The live model is:

- one global ticker firing every `20` seconds
- one global cycle of `200` seconds
- skill groups mapped to offsets inside that `200`-second cycle
- each tick only processes the skills whose offset matches the current global tick

This keeps drain timing DR-style while avoiding a single heavy sweep where every skill on every character drains at once.

### Code Snippet

```python
from evennia import TICKER_HANDLER

from world.systems.exp_pulse import start_exp_ticker


start_exp_ticker()
```

Ticker flow:

```python
GLOBAL_TICK = (GLOBAL_TICK + 20) % 200

for char in get_active_characters():
    for skill_name, skill in char.exp_skills.skills.items():
        group = SKILL_GROUPS.get(skill_name, 100)
        offset = SKILL_GROUP_OFFSETS.get(group, 0)
        if GLOBAL_TICK == offset:
            pulse(skill)
```

### Math

Ticker cadence is:

$$
	ext{pulse tick} = 20 \text{ seconds}
$$

$$
	ext{full cycle} = 200 \text{ seconds}
$$

Global tick advancement is:

$$
	ext{GLOBAL\_TICK} = (\text{GLOBAL\_TICK} + 20) \bmod 200
$$

For each skill:

$$
	ext{if GLOBAL\_TICK} = \text{offset(group)}, \text{ then pulse(skill)}
$$

Current offsets are:

- group `100` -> `0`
- group `120` -> `20`
- group `140` -> `40`
- group `160` -> `60`
- group `180` -> `80`

### Why Staggered Execution Exists

Without offsets, all skills would drain on the same tick and create bursty server work.

With offsets, work is spread across the cycle:

- lower spike risk
- more predictable timing
- easier future scaling across many characters

## 10. Skill Activity System

### Plain-Language Explanation

Each skill now records the last time it was trained. This makes activity explicit instead of inferred from pool size alone.

Training updates `last_trained` when `train()` is used. That timestamp is then used by the live pulse engine to decide whether a skill is still recent enough to keep draining.

### Code Snippet

```python
import time


class SkillState:
    def __init__(self, name, owner=None):
        self.last_trained = 0.0


def train(skill, difficulty, success=True):
    skill.last_trained = time.time()
    return award_xp(skill, calculate_xp(skill, difficulty, success=success))
```

### Example Behavior

- a newly created skill starts with `last_trained = 0.0`
- `train(evasion, 20)` updates `last_trained` to the current wall clock time
- later pulse checks use that stored timestamp instead of guessing from pool fullness

## 11. Active Skill Filtering

### Plain-Language Explanation

The EXP ticker no longer drains every known skill. It now drains only skills that were trained recently enough to still count as active.

The active window is `600` seconds, with a `30` second grace buffer. If a skill has been idle longer than that combined window, the ticker skips it completely.

### Code Snippet

```python
ACTIVE_WINDOW = 600
GRACE_WINDOW = 30


def is_active(skill):
    return (time.time() - skill.last_trained) <= (ACTIVE_WINDOW + GRACE_WINDOW)


for skill_name, skill in char.exp_skills.skills.items():
    if not is_active(skill):
        continue
    pulse(skill)
```

### Example Behavior

- train `evasion`, wait `5` minutes, and it still drains because it is inside the activity window
- train `evasion`, wait `15` minutes, and it stops draining because it is outside the activity window and grace buffer
- if two skills share the same offset group but only one was trained recently, only that one drains

## 12. Player Feedback System

### Plain-Language Explanation

Each skill now tracks the last mindstate value that was reported and the last time feedback was sent. When the mindstate changes by at least `5`, the system tries to notify the owning character.

Feedback is intentionally minimal in this phase. The message is just a small confirmation that the skill improved, with no special formatting or UI integration.

### Code Snippet

```python
FEEDBACK_THRESHOLD = 5
FEEDBACK_COOLDOWN = 10


def send_feedback(skill):
    owner = getattr(skill, "owner", None)
    if owner is None:
        return False
    owner.msg(f"Your {skill.name} improves.")
    return True
```

### Example Behavior

- if `mindstate` changes from `0` to `6`, the character can receive `Your evasion improves.`
- if the skill changes again immediately, the cooldown suppresses another message for `10` seconds
- tiny changes under the threshold do not send anything

## 13. Performance Safeguards

### Plain-Language Explanation

This phase adds two explicit safeguards to keep the live ticker cheap:

- inactive skills are skipped before offset and pulse work
- each character processes at most `10` skills in one EXP tick

That prevents one character with many remembered skills from turning the shared ticker into a bursty sweep.

### Code Snippet

```python
MAX_SKILLS_PER_TICK = 10


processed = 0
for skill_name, skill in char.exp_skills.skills.items():
    if processed >= MAX_SKILLS_PER_TICK:
        break
    if not is_active(skill):
        continue
    pulse(skill)
    processed += 1
```

### Example Behavior

- an inactive skill costs only a quick activity check and is skipped
- a character with more than `10` eligible skills only drains the first `10` seen in that tick
- the ticker stays bounded even if a character has a large transient skill map

## 14. Mindstate Naming System

### Explanation

Mindstate values now resolve to named labels instead of only numeric fractions. The resolver uses thresholds, so every current mindstate maps to the highest matching label.

### Mapping Table

| Threshold | Name |
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
| 15 | engaged |
| 20 | absorbed |
| 25 | focused |
| 30 | riveted |
| 34 | mind lock |

### Code Snippet

```python
def get_mindstate_name(value):
    current = "clear"
    for threshold in sorted(MINDSTATE_NAMES):
        if value >= threshold:
            current = MINDSTATE_NAMES[threshold]
    return current
```

### Example Output

- `0/34 (clear)`
- `5/34 (thinking)`
- `17/34 (engaged)`
- `34/34 (mind lock)`

## 15. Player Feedback Messaging

### Explanation

The skill system now sends messages when a skill enters a new named mindstate. Messages only fire on transitions, respect the character feedback toggle, and obey the feedback cooldown.

### Mapping Table

| Transition | Message |
| --- | --- |
| normal named change | `You feel your <skill> settling into <name>.` |
| `mind lock` | `Your <skill> is fully absorbed. You can learn no more.` |
| `clear` | `Your <skill> clears from your mind.` |

### Code Snippet

```python
def handle_mindstate_change(skill, new_name, now=None):
    if new_name == skill.last_mindstate_name:
        return False
    if not skill.owner.db.exp_feedback:
        return False
    if time.time() - skill.last_feedback_time < FEEDBACK_COOLDOWN:
        return False
```

### Example Output

- `You feel your evasion settling into thinking.`
- `You feel your evasion settling into absorbed.`
- `Your evasion is fully absorbed. You can learn no more.`
- `Your evasion clears from your mind.`

## 16. Experience Commands

### Usage

Players can view skill learning with:

- `experience`
- `exp`
- `experience all`
- `exp all`

### Examples

- `exp` shows only skills with `mindstate > 0`
- `exp` prints `No actively training skills to display. Use exp all to see everything.` when nothing is above clear and active
- `exp all` shows all currently tracked skills, rank percent, and visible field experience bits

### Output Format

```text
                     Skill        Rank/% -> Mindstate      Bits (pool / max)
                         Evasion:   25 08% attentive   (12/34)         (352/1294)
                         Stealth:   18 03% ruminating  (8/34)          (276/1346)

Total Ranks Displayed: 43
```

`exp all` now starts with `Showing all skills with field experience.` and uses a display-name layer so internal keys like `light_edge`, `targeted_magic`, and `locksmithing` render as player-facing labels such as `Light-Edged`, `Targeted Magic`, and `Lockpicking`.

## 17. Template Skill Integration

### Purpose

This batch wires six high-value template skills into the transient EXP system. These are template integrations, not the final full rollout for every skill and spell in the repo.

The first six templates are:

- `evasion` -> passive defense in melee and targeted-magic defense
- `stealth` -> `hide`, `sneak`, `stalk`, hidden movement, and resolved ambush contests
- `perception` -> `search`, `observe`, and anti-stealth checks
- `brawling` -> successful unarmed attack loop
- `targeted_magic` -> offensive spell cast resolution
- `appraisal` -> lore and inspection branches in `appraise`

### Action Mapping Table

| Skill | Command / System Driver | Legacy-Only Before | Bridge Result | DireTest Proof |
| --- | --- | --- | --- | --- |
| Evasion | physical attack defense, targeted-magic defense | yes, no real EXP hook | conservative passive EXP hook added | `exp-evasion-passive`, `exp-command-visibility` |
| Stealth | `hide`, `sneak`, `stalk`, hidden movement, resolved ambush contests | yes | contest context is stored, payout is delayed until validation, failed hide attempts now pay through the real command path without requiring concealment, solo practice hides train only below a capped early-rank threshold, strongest-observer-first aggregation now drives room detection pressure, failure quality scales by miss margin, and learning now routes into `exp_skills` | `exp-stealth-bridge`, `exp-stealth-no-observer`, `exp-stealth-practice-cap`, `exp-stealth-empty-room-loop`, `exp-stealth-failure-margins`, `exp-stealth-observer-aggregation`, `exp-stealth-perception-dual`, `exp-stealth-state-machine`, `exp-command-visibility` |
| Perception | `search`, `observe` | yes | learning now routes into `exp_skills` | `exp-stealth-perception-dual` |
| Brawling | unarmed `attack` success path | yes | successful-hit learning now routes into `exp_skills` | `exp-brawling-bridge` |
| Targeted Magic | `prepare` + `cast` offensive spell resolution | yes | hits and misses both route into `exp_skills` | `exp-targeted-magic-bridge`, `exp-command-visibility` |
| Appraisal | `appraise` weapon, armor, gem, and creature branches | yes | appraisal branches now route into `exp_skills` | `exp-appraisal-loop`, `exp-command-visibility` |

### Easier Bridges vs New Hooks

The easiest bridges were `stealth`, `perception`, `appraisal`, and `targeted_magic` because they already had clean command or resolution points that previously called `use_skill(...)`.

`brawling` was simpler than `evasion`, but only because current repo behavior already limited brawling learning to successful attacks. That behavior was preserved for this batch.

`evasion` was the only template that required new hook creation because it was deeply involved in defense math but did not have a real learning bridge before this batch.

### Command Behavior

`exp` now shows only skills that are both:

- above clear mindstate
- still inside the active learning window

`exp all` shows all tracked skills, including the six seeded template skills for deterministic visibility.

## 18. Practice Learning Phase

### Explanation

Stealth now has an explicit solo-practice phase for early ranks.

- if a hide resolves with no observers, the action enters practice mode instead of the contested-learning branch
- solo practice trains only while `stealth` is below rank `15`
- practice XP is reduced below contested XP and decays as the skill approaches the cap
- once `stealth` reaches rank `15`, empty-room practice hard-stops and further growth requires real opposition
- repeated solo practice still goes through the same diminishing-returns bucket logic, so empty-room looping remains a weak, fading path rather than an optimal one

### Practice Curve

Solo-practice context uses:

```python
practice_progress = stealth_rank / 15
practice_scale = max(0.1, 1.0 - practice_progress)
context_multiplier = 0.4 * practice_scale
```

This gives new characters meaningful early repetitions while forcing the learning path outward as the basic motion becomes familiar.

### Expected Behavior

| Stealth Rank | Empty-Room Practice |
| --- | --- |
| 1-5 | clearly positive, still reduced vs contested hides |
| 10-14 | positive but fading quickly |
| 15+ | zero |

### Debug Output

Developer stealth probes now include a `practice_mode=` flag so empty-room traces can be separated from contested hides at a glance.

## 19. Observer Aggregation

### Explanation

Stealth detection no longer collapses a room by treating every observer as a full-strength equal counter.

- the strongest observer is the primary detector
- the next few observers add reduced support instead of full stacked perception
- the rest of the room contributes only a capped crowd penalty
- this keeps one excellent watcher dangerous while preventing large groups of weak watchers from becoming a mathematically absurd wall

### Aggregation Shape

```python
primary_pressure = best_observer_roll
support_pressure = sum(max(0.0, roll - best_observer_roll * 0.5) for roll in next_three_rolls) * 0.15
crowd_penalty = min(15.0, (observer_count - 1) * 1.5)

final_margin = stealth_roll - (primary_pressure + support_pressure) - crowd_penalty
```

### Intended Behavior

| Room Situation | Expected Result |
| --- | --- |
| one very strong observer vs weak stealth | mostly severe failures |
| many weak observers vs elite stealth | harder than solo, but still beatable |
| one strong observer plus several medium observers | hard, mixed, and materially riskier than many weak extras |

Developer stealth output now includes `observer_pressure=`, `support_pressure=`, and `crowd_penalty=` so live-room probes can show whether the strongest watcher or the crowd term is responsible for the final margin.

### Example Gameplay Output

```text
> exp
              Skill        Rank/% -> Mindstate      Bits (pool / max)
                 Stealth:    0 00% considering  (6/34)          (176/1000)
             Appraisal:    1 00% thoughtful    (4/34)          (124/1017)
        Targeted Magic:    0 00% learning      (3/34)          (88/1000)
                 Evasion:    1 00% perusing      (2/34)          (62/1017)

Total Ranks Displayed: 2
```

```text
> exp all
Showing all skills with field experience.

              Skill        Rank/% -> Mindstate      Bits (pool / max)
             Appraisal:    1 00% thoughtful    (4/34)          (124/1017)
                 Evasion:    1 00% perusing      (2/34)          (62/1017)
          Hand-To-Hand:    0 00% clear         (0/34)          (0/1000)
            Perception:    1 00% clear         (0/34)          (0/1017)
                Stealth:    0 00% considering  (6/34)          (176/1000)
        Targeted Magic:    0 00% learning      (3/34)          (88/1000)

Total Ranks Displayed: 3
```

### Migration Control Note

For the exact bridge audit, including where legacy `use_skill(...)` previously lived and whether parallel legacy learning still remains for each template skill, see `docs/skill_template_bridge.md`.

## 18. Second-Wave Skill Bridges

### Purpose

This batch extends the transient EXP bridge beyond the original six template skills and wires four live gameplay skills into the same `award_exp_skill(...)` path:

- `athletics` -> `attempt_climb()` and `attempt_swim()` terrain actions
- `locksmithing` -> `inspect_box()`, `disarm_box()`, `pick_box()`, `analyze_trap()`, `harvest_trap()`, and `rework_trap()`
- `debilitation` -> `resolve_debilitation_spell()` hit and resist outcomes
- `light_edge` -> successful armed melee attacks when the resolved weapon skill is `light_edge`

### Seed And Visibility Rules

These four skills are now part of `TEMPLATE_EXP_SKILLS`, so `ensure_core_defaults()` seeds transient EXP state for them after starter-skill defaults and persisted `db.skills` ranks are in place.

That order matters because `exp all` should show the persisted baseline rank for these seeded second-wave skills immediately, instead of creating zero-rank transient placeholders before the legacy data is normalized.

### Action Mapping Table

| Skill | Command / System Driver | Bridge Result | DireTest Proof |
| --- | --- | --- | --- |
| Athletics | `climb`, `swim`, terrain traversal attempts | success and failure both route through EXP with outcome-sensitive gain | `exp-athletics-bridge` |
| Locksmithing | box and trap workflow | inspection and box/trap actions now route through EXP instead of legacy `use_skill(...)` | `exp-locksmithing-bridge`, `exp-second-wave-command-visibility` |
| Debilitation | offensive debuff spell resolution | successful casts and resisted casts both route through EXP | `exp-debilitation-bridge`, `exp-second-wave-command-visibility` |
| Light Edge | armed melee `attack` success path | successful weapon hits now train `light_edge` instead of falling back to brawling or legacy learning | `exp-light-edge-bridge`, `exp-second-wave-command-visibility` |

### Naming Note

The live repo skill key for planned Small Edged gameplay is `light_edge`.

This bridge deliberately does not introduce a duplicate `small_edged` skill name into the live EXP system, commands, or seeded skill list.

### Deferred Combat Work

`parry_ability` and `shield_usage` are still deferred. They need dedicated combat-system hook design rather than this bridge-only EXP pass.

## 19. Worked Examples

### Plain-Language Explanation

These worked examples use the exact formulas implemented in code.

### Code Snippet

```python
skill.rank = 50
skill.recalc_pool()
xp = calculate_xp(skill, difficulty=60, success=True)
```

### Math

Example 1: rank `50`, difficulty `60`, success `True`

- gap $= 60 - 50 = 10$
- difficulty factor $= 1.0$
- success modifier $= 1.0$
- rank scaling $= \frac{1}{1 + (50 / 50)} = 0.5$

At rank `50`, the pool formula gives:

$$
	ext{max\_pool} = \frac{15000 \times 50}{50 + 900} + 1000 \approx 1789.5
$$

Base XP is:

$$
	ext{base} = 1789.5 \times 0.035 \approx 62.6
$$

Final XP is:

$$
62.6 \times 1.0 \times 1.0 \times 0.5 \approx 31.3
$$

Example 2: same rank and difficulty, but failure

$$
62.6 \times 1.0 \times 0.4 \times 0.5 \approx 12.5
$$

Example 3: rank `100`, difficulty `60`, success `True`

- gap $= 60 - 100 = -40$
- difficulty factor $= 0.2$
- success modifier $= 1.0$
- rank scaling $= \frac{1}{1 + (100 / 50)} \approx 0.33$

That produces much lower XP than the optimal-rank case.

### Example Values

- `rank = 50`, `difficulty = 60`, success gives about `31.3` XP
- `rank = 50`, `difficulty = 60`, failure gives about `12.5` XP
- `rank = 100`, `difficulty = 60`, success is heavily reduced because the challenge is too easy

Example 4: pulse drain from a full pool

- pool $= 1000$
- skillset $= \text{primary}$
- wisdom $= 30$
- drain rate $= 0.067$
- wisdom modifier $= 1.0$

First pulse drain is:

$$
1000 \times 0.067 \times 1.0 = 67
$$

So after the first pulse:

- pool becomes about `933`
- rank progress increases by about `67`

Over about `15` pulses, a `1000`-point pool drains down close to zero under the current percentage-drain model.
