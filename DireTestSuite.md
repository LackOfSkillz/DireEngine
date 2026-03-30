🧪 DireTest Suite — Design Intent & Collaboration Brief
🎯 What We Are Building

We are creating DireTest, a unified testing and simulation framework for DireEngine.

DireTest is not just a test runner. It is intended to be:

The authoritative system for validating correctness, detecting bugs, measuring performance, and enforcing long-term game balance.

It will serve three core purposes:

1. ✅ Regression & System Integrity

Ensure the game works correctly and consistently across all systems:

movement
combat
inventory & containers
survival (injuries, bleeding, fatigue)
economy (loot, vendors, banking, weight)
locksmithing & traps
skinning & harvesting
death, graves, favors, resurrection
justice system
client payload integrity

This is equivalent to a traditional test suite—but game-aware.

2. 🎮 Scenario-Based Gameplay Validation

Simulate real player behavior through structured scenarios:

Example:

hunt creature → kill → search → loot → skin → open box → sell → bank → repeat
stealth approach → ambush → disengage → evade justice
die → corpse → depart → grave recovery → resurrection

These scenarios will:

validate system interactions
detect state inconsistencies
surface edge-case bugs
ensure loops feel correct and stable
3. ⚖️ Balance & System Health Simulation

This is the most important long-term goal.

DireTest will simulate:

profession vs profession matchups
PvE hunting efficiency
loot value and economic flow
skill and spell effectiveness
system dominance (meta detection)

We are not just asking:

“Does it work?”

We are also asking:

“Is it fair, diverse, and healthy?”

This includes:

win rate tracking
time-to-kill (TTK)
profit/hour
XP gain rates
usage rates (skills, spells, gear)
dominance detection (mandatory choices)
frustration indicators (lack of counterplay, lock states)
🧠 Core Design Philosophy

DireTest will follow principles used in AAA balancing pipelines:

Role-based design (not flat parity)
Segmented analysis (low/mid/high skill, PvE vs PvP)
Target bands (not exact equality)
Diversity enforcement (no mandatory builds)
Frustration tracking separate from power
Continuous simulation, not one-time tuning
🧱 Planned Structure

We are planning a CLI-driven tool:

diretest smoke
diretest combat
diretest economy
diretest death
diretest all
diretest scenario <name>
diretest balance

Current implemented entrypoint:

diretest scenario race-balance

Future expansion:

diretest balance-combat
diretest balance-economy
diretest balance-spells
diretest balance-diversity
diretest balance-frustration
🧩 Internal Architecture (High-Level)

DireTest will include:

1. Test Harness
factories for characters, NPCs, items, rooms
command execution driver (simulate real player input)
2. Scenario Engine
YAML or structured definitions of gameplay flows
deterministic execution via seeds
3. Metrics Engine
calculates performance, economy, combat stats, etc.
4. Invariant System
rules that must never break (state validation)
5. Diagnostics & Artifacts

On failure, output:

command logs
state snapshots
traceback
reproduction scenario
metrics
6. Balance Spec System

Defines:

intended roles
acceptable metric ranges
diversity thresholds
frustration thresholds
🤖 Your Role (Aedan)

You will be:

implementing the DireTest framework
running tests and simulations
analyzing outputs
debugging failures
integrating fixes
iterating on test coverage
helping refine balance simulations

Because you have direct access to the codebase, your input is critical to ensure:

feasibility
maintainability
performance
correct integration with Evennia systems
❓ Questions for You (Aedan)

We want your input before locking the architecture.

🧱 Architecture & Integration
Evennia Integration
What is the cleanest way to:
spin up test characters/NPCs?
execute commands reliably (execute_cmd, or lower-level)?
isolate test environments without polluting persistent world state?
State Reset
What’s the best strategy for:
resetting world state between tests?
avoiding DB contamination?
handling scripts/tickers during tests?
Factories
Do we need custom factory layers for:
characters
NPCs
items
rooms
Or can we safely reuse existing creation paths?
⚙️ Command Execution
What is the most reliable way to simulate player commands?
execute_cmd()?
direct command invocation?
something lower-level?
How do we:
capture output cleanly?
capture side effects (state changes, scripts, etc.)?
📊 Metrics & Logging
What’s the best way to capture:
combat results
XP changes
coin/item deltas
state transitions
Where should logs live?
file system?
DB?
hybrid?
🔁 Simulation
Can we safely run:
thousands of iterations
without memory leaks or performance degradation?
Do we need:
a “headless mode” for simulation?
stripped-down environment (no client payload overhead)?
🧠 Balance Engine
What parts of the current system are hardest to simulate?
combat loops?
spell effects?
AI/NPC behavior?
timers/roundtime?
Do we need deterministic hooks for:
RNG control (seed injection)?
combat rolls?
loot generation?
🧪 Test Coverage
What systems do you think are most likely to break and should be prioritized?
Are there systems currently too complex or fragile to test reliably?
⚠️ Risk & Constraints
What are the biggest risks in building this?
performance?
DB locking?
Evennia lifecycle issues?
script/ticker interference?
What should we NOT attempt in v1?
🚀 What We Want From You

We are not asking you to just implement this.

We want your feedback on:

architecture feasibility
risks we may not see
simplifications we should make
missing pieces in the plan
better approaches based on Evennia internals
🧠 Final Intent

DireTest is meant to become:

The central nervous system of DireEngine development

If something changes in the game:

DireTest should catch regressions
DireTest should highlight balance drift
DireTest should guide iteration

If this is done correctly, we get:

faster development
safer changes
measurable balance
AI-assisted debugging
long-term system stability. the goal is to develop a comprehensive suite of testing tools and simulations, and we would like your imput on how to make it as robust and usefule to you as we can. Your imput is appreciated.

---

## DireTest V1 Refactor

### Primary Purpose

DireTest v1 is a deterministic reproduction, debugging, and validation tool.

It is not yet:

- a full balance engine
- a large-scale PvP simulator
- a YAML-driven scenario platform
- a historical analytics warehouse

The first version succeeds if it can reliably reproduce bugs, capture enough evidence to explain them, and validate high-risk gameplay loops end to end.

### Core Principle Shift

The v1 design is optimized for signal, not breadth.

The main failure mode to avoid is not insufficient simulation coverage. The main failure mode is producing large volumes of low-value output that do not help isolate bugs, explain regressions, or guide fixes.

DireTest v1 therefore prioritizes:

1. deterministic execution
2. reusable invariants
3. failure artifact bundles
4. dual execution paths
5. strict cleanup and leak detection

### Explicit V1 Scope Cuts

The following are deferred until after v1:

- YAML scenario definitions
- thousands of long-running balance simulations
- deep AI-vs-AI meta analysis
- advanced frustration scoring models
- broad persistent metrics storage in the database
- one monolithic runner that attempts to solve every test category at once

### Locked V1 Architecture

#### 1. Harness

The harness is the most important module.

Responsibilities:

- create temporary rooms, characters, NPCs, items, corpses, vendors, and other test fixtures
- apply deterministic seed control
- isolate each scenario in a temporary namespace
- guarantee teardown on pass or fail
- perform leak detection after each run

#### 2. Runner

DireTest must support two execution paths.

Command-path:

- executes through the real gameplay command layer
- catches parser, locks, cmdsets, messaging, and interaction bugs
- used for realistic end-to-end validation

Direct-path:

- invokes command classes or gameplay systems directly
- reduces noise during logic debugging
- used for fast isolation and deterministic reproduction

Both paths are required. One does not replace the other.

#### 3. Snapshot System

Every scenario step should support structured before/after snapshots.

At minimum snapshots should capture:

- character state
- room state
- inventory and equipment state
- combat state
- key persistent attributes
- object creation and deletion deltas

Snapshots should be JSON-serializable and should avoid assuming plain Python dict/list behavior where Evennia saver wrappers may be present.

Snapshot shape must be consistent across scenarios.

Minimum snapshot schema:

```json
{
	"label": "before_attack",
	"timestamp": 0.0,
	"character": {},
	"room": {},
	"inventory": [],
	"equipment": [],
	"combat": {},
	"attributes": {},
	"object_deltas": {
		"created": [],
		"deleted": []
	}
}
```

The exact field contents may expand, but the top-level shape should remain stable so diffing and artifact inspection stay reliable.

#### 4. Artifact System

This is the centerpiece of v1.

On failure, DireTest should write a reproducible artifact bundle such as:

```text
artifacts/<run_id>/
	scenario.json
	seed.txt
	commands.log
	snapshots.json
	metrics.json
	traceback.txt
```

The artifact bundle must be more valuable than the console output. Console output should stay compact. Failure details belong in the artifact bundle.

#### 5. Invariant Library

Reusable invariant checks should be callable from any scenario.

Initial invariant examples:

- no duplicate corpse or grave objects for the same owner
- no invalid combat state after move, disengage, retreat, or cleanup
- no negative currency values
- no impossible weight or encumbrance states
- race data matches canonical race definition
- death state and recovery state remain coherent
- client payload generation does not fail

#### 6. Scenario System

Scenarios in v1 are Python-defined only.

Example pattern:

```python
def scenario_basic_combat(ctx):
		ctx.cmd("wield sword")
		ctx.cmd("attack goblin")
		ctx.assert_invariant("valid_combat_state")
```

No YAML scenario DSL should be introduced until the action vocabulary and artifact format are stable.

Scenario Context must have a stable API in v1.

Minimum required context methods:

- `ctx.cmd(command_str)`
- `ctx.direct(func, *args, **kwargs)`
- `ctx.snapshot(label)`
- `ctx.assert_invariant(name)`
- `ctx.get_character(name=None)`
- `ctx.get_room(name=None)`
- `ctx.log(message)`

Time-control methods must also exist, even if some start as limited implementations:

- `ctx.advance_time(seconds)`
- `ctx.freeze_time()`
- `ctx.resume_time()`

### Determinism Requirements

Every scenario must support explicit seed injection.

Example:

```text
diretest scenario death-loop --seed 4412
```

If a failure occurs, the seed must be recorded in the artifact bundle so the exact run can be reproduced later.

### State Isolation Requirements

Each scenario should run in an isolated temporary world context.

Requirements:

- all created objects receive a deterministic test prefix and run id
- teardown executes even when exceptions occur
- a leak check runs after teardown
- leftover test objects fail the scenario

Leak detection must be explicitly defined.

In v1, a leak is any test-created object whose key begins with `TEST_` and still exists after scenario teardown.

Leak detection should:

- run after teardown completes
- search for remaining `TEST_` objects associated with the run id or scenario namespace
- fail the scenario if any are found
- record leaked objects in the artifact bundle

### Time, Tickers, and Scripts

Time-sensitive systems are a major risk area.

DireTest v1 should support at least the following modes conceptually, even if they are implemented incrementally:

- real-time mode
- stepped time mode
- suppression mode for systems where scripts or tickers would add noise

Stepped execution is more valuable for debugging than maximum realism.

The scenario context should expose time control directly so time-sensitive bugs can be reproduced without requiring real wall-clock waits.

### Initial CLI Direction

DireTest should remain a thin CLI over a shared harness.

The CLI surface should stay focused.

Examples:

- `diretest scenario <name>`
- `diretest invariant <name>`
- `diretest repro <artifact_path>`
- `diretest diff <before> <after>`

The existing first entrypoint remains:

- `diretest scenario race-balance`

Replay is a first-class contract, not an informal goal.

To support replay, every failure artifact must include at minimum:

- scenario name
- seed
- full command and direct-action sequence
- scenario options and runtime mode

`diretest repro <artifact_path>` must:

- rebuild the test environment
- rerun the same scenario with the same seed
- replay the recorded command and direct-action sequence
- compare the reproduced outcome against the saved artifact

### Required First Scenarios

These scenarios provide the highest immediate value and should be built before broader simulation work:

1. movement, look, and inventory coherence
2. combat loop: attack, retreat, disengage, cleanup
3. death loop: death, corpse, depart, grave recovery, resurrection
4. economy loop: search, loot, box, sell, bank
5. race invariant and race-balance scenario
6. justice or stealth loop with state cleanup validation

These scenarios should catch a large share of early regressions in the current codebase.

### Metrics for V1

Metrics should be useful before they are ambitious.

Initial recommended metrics:

- command timings
- coin and item deltas
- XP and mindstate deltas
- state transition counts
- projected encumbrance by race
- projected XP gain by race category
- stable combat fixture metrics such as hit chance proxy, defense proxy, and time-to-resolution bands

Balance evaluation should begin as descriptive reporting first. Hard pass/fail balance gates should only be added after enough stable baseline data exists.

### Major Risks To Design Around

The following are expected failure sources and should be treated as first-class design constraints:

- database contamination from incomplete cleanup
- script and ticker interference with deterministic runs
- saver-wrapper data not behaving like plain dict/list values
- divergence between command-path and direct-path behavior
- performance degradation from expensive normalization or full payload sync during test runs

### Development Constraint

DireTest is not a separate concern to be added after systems are built.

For DireEngine v1, gameplay systems should be designed with testability as a first-class constraint.

That means:

- deterministic hooks are preferred over hidden randomness when practical
- state transitions should be inspectable
- important side effects should be capturable in snapshots and artifacts
- systems should expose enough narrow hooks for both command-path and direct-path validation

The working philosophy is not "build systems, then test them later." The working philosophy is "build systems in a way that makes reliable testing and debugging possible from the start."

### Concrete V1 Success Condition

DireTest v1 is successful if an admin or Copilot can run:

```text
diretest scenario death-loop --seed 4412
```

and, on failure, receive a compact console summary plus a rich artifact bundle that makes the failure reproducible and explainable.

In other words, the first job of DireTest is not to be broad. The first job is to become a debugging weapon.

### Implementation Phases

#### Phase 1: Reproduction Core

- harness
- seed control
- temporary fixture creation
- teardown and leak detection
- artifact bundle writer
- basic snapshot system

#### Phase 2: Shared Validation Layer

- invariant library
- command-path runner
- direct-path runner
- compact CLI wrappers over the shared core

#### Phase 3: High-Value Scenarios

- movement/look/inventory
- combat loop
- death loop
- economy loop
- race scenario
- justice or stealth cleanup scenario

#### Phase 4: Descriptive Balance Support

- lightweight metrics reports
- diffable scenario outputs
- baseline comparison support
- targeted balance scenarios for combat, economy, and progression

Only after those phases are stable should DireTest expand toward broader simulation or declarative scenario definitions.