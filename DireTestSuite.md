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

Current live entrypoints:

- `diretest scenario race-balance`
- `diretest scenario movement --seed 1234`
- `diretest scenario inventory --seed 1234`
- `diretest scenario combat-basic --seed 1234`
- `diretest scenario death-loop --seed 1234`
- `diretest scenario grave-recovery --seed 1234`
- `diretest scenario economy --seed 1234`
- `diretest scenario bank --seed 1234`

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
- grave recovery loop
- economy loop
- banking loop
- race scenario
- justice or stealth cleanup scenario

#### Phase 4: Descriptive Balance Support

- lightweight metrics reports
- diffable scenario outputs
- baseline comparison support
- targeted balance scenarios for combat, economy, and progression

Only after those phases are stable should DireTest expand toward broader simulation or declarative scenario definitions.

Tasks list:

DIRETEST — PHASE 1 MICROTASKS 001–020 (STRICT)
🎯 PHASE GOAL

At the end of this set:

✔ deterministic execution via seed
✔ isolated test environment (harness)
✔ snapshot system (structured)
✔ artifact bundle generation
✔ teardown + leak detection

🧱 CORE CONTRACT DEFINITIONS (MANDATORY FIRST)
DT-001 — Define Snapshot Schema (LOCKED)

File:

tools/diretest/core/snapshot_schema.py

Define canonical schema:

SNAPSHOT_SCHEMA = {
    "character": dict,
    "room": dict,
    "inventory": list,
    "equipment": list,
    "combat": dict | None,
    "attributes": dict,
    "object_deltas": {
        "created": list,
        "deleted": list
    }
}

No deviations allowed in v1.

DT-002 — Define Artifact Bundle Structure (LOCKED)

File:

tools/diretest/core/artifacts.py

Define output structure:

artifacts/<run_id>/
  scenario.json
  seed.txt
  commands.log
  snapshots.json
  metrics.json
  traceback.txt

All files REQUIRED (even if empty).

DT-003 — Define Scenario Context API (LOCKED)

File:

tools/diretest/core/context.py

Create class with EXACT methods:

ctx.cmd(command_str)
ctx.direct(func, *args, **kwargs)
ctx.snapshot(label)
ctx.assert_invariant(name)
ctx.log(message)
ctx.get_character()
ctx.get_room()

No additional methods in v1.

DT-004 — Define Runner Interface (LOCKED)

File:

tools/diretest/core/runner.py

Define:

run_scenario(scenario_func, seed: int, mode: str)

Where:

mode ∈ ["command", "direct"]
DT-005 — Define Leak Detection Rule (LOCKED)

Leak = any object where:

obj.key.startswith("TEST_")

AND still exists after teardown.

🎲 SEED + DETERMINISM
DT-006 — Implement Seed Injection Utility

File:

tools/diretest/core/seed.py

Function:

set_seed(seed: int)

Must:

control Python random
be globally applied before scenario execution
DT-007 — Store Seed in Artifact Bundle

Write:

seed.txt

Content:

seed=<int>
DT-008 — Enforce Seed Required for Scenario Execution

If no seed provided:

generate one
print it in console
store in artifacts
🏗️ HARNESS (TEST ENVIRONMENT)
DT-009 — Create Test Harness Class

File:

tools/diretest/core/harness.py

Class:

DireTestHarness

Responsibilities:

create temp room
create test character
track created objects
DT-010 — Create Temporary Room Factory

Function:

create_test_room()

Must:

name room with prefix:
TEST_ROOM_<uuid>
DT-011 — Create Test Character Factory

Function:

create_test_character()

Must:

name character:
TEST_CHAR_<uuid>
spawn in test room
DT-012 — Track Created Objects

Harness must maintain:

self.created_objects = []

Track:

rooms
characters
spawned items
📸 SNAPSHOT SYSTEM
DT-013 — Implement Snapshot Capture Function

File:

tools/diretest/core/snapshot.py

Function:

capture_snapshot(ctx) -> dict

Must return structure matching SNAPSHOT_SCHEMA.

DT-014 — Capture Object Deltas

Between snapshots track:

newly created objects
deleted objects

Store in:

object_deltas
DT-015 — Store Snapshots in Memory During Run

Structure:

ctx.snapshots = [
    {"label": str, "data": snapshot_dict}
]
DT-016 — Write Snapshots to Artifact File

Output:

snapshots.json

Full list of snapshots.

📦 ARTIFACT SYSTEM
DT-017 — Implement Artifact Writer

File:

tools/diretest/core/artifacts.py

Function:

write_artifacts(run_id, data)

Must create full directory + all required files.

DT-018 — Capture Command Log

During execution:

ctx.command_log.append(command_str)

Write to:

commands.log
DT-019 — Capture Traceback on Failure

On exception:

capture full traceback
write to:
traceback.txt
DT-020 — Write Scenario Metadata

File:

scenario.json

Contents:

{
  "name": "<scenario_name>",
  "mode": "command|direct",
  "seed": <int>
}
✅ END STATE AFTER DT-020

You now have:

✔ deterministic execution via seed
✔ isolated test harness
✔ snapshot capture system
✔ artifact bundle generation
✔ command logging
✔ failure trace capture
✔ leak definition (ready for next phase)

🧠 WHAT THIS ENABLES

You can now:

diretest scenario basic_test --seed 1042

And get:

reproducible run
snapshots
logs
artifacts

DIRETEST — MICROTASKS 021–040 (STRICT)
🎯 PHASE GOAL

At the end of this set:

✔ environment fully cleaned after every run
✔ leaks detected and reported
✔ invariants executable and reusable
✔ command-path execution working
✔ direct-path execution working

🧹 TEARDOWN SYSTEM
DT-021 — Implement Harness Teardown Method

File:

tools/diretest/core/harness.py

Add:

def teardown(self):

Must:

delete all tracked objects
clear references
run leak check after deletion
DT-022 — Delete Objects in Reverse Creation Order

Teardown must:

iterate reversed(self.created_objects)

This prevents dependency errors (items inside containers, etc.)

DT-023 — Add Safe Delete Wrapper

Create:

def safe_delete(obj):

Must:

check object exists
catch deletion errors
log failures without stopping teardown
DT-024 — Clear Object References After Teardown

After deletion:

self.created_objects = []

No stale references allowed.

DT-025 — Ensure Teardown Always Executes

Wrap scenario execution in:

try:
    run_scenario()
finally:
    harness.teardown()

Teardown must run even on failure.

🚨 LEAK DETECTION SYSTEM
DT-026 — Implement Leak Scanner

File:

tools/diretest/core/leaks.py

Function:

detect_leaks() -> list

Returns objects where:

obj.key.startswith("TEST_")
DT-027 — Run Leak Detection After Teardown

After teardown completes:

call detect_leaks()
DT-028 — Fail Test on Leak Detection

If leaks found:

mark scenario as FAILED
include leak data in artifacts
DT-029 — Log Leak Details in Artifacts

Write to:

metrics.json

Structure:

{
  "leaks": [
    {"key": "TEST_OBJ_x", "type": "..."}
  ]
}
DT-030 — Print Leak Summary to Console

Example:

Leak detected: 2 test objects were not cleaned up.

Keep concise.

🧠 INVARIANT SYSTEM
DT-031 — Create Invariant Registry

File:

tools/diretest/core/invariants.py

Structure:

INVARIANTS = {}
DT-032 — Register Invariants via Decorator

Create:

def invariant(name):

Usage:

@invariant("no_negative_currency")
def check_currency(ctx):
    ...
DT-033 — Implement Invariant Runner

Function:

run_invariant(name, ctx)

Must:

call registered function
return pass/fail + message
DT-034 — Integrate ctx.assert_invariant()

In context:

def assert_invariant(self, name):

Must:

run invariant
record result
raise error on failure
DT-035 — Add Basic Invariants (INITIAL SET)

Implement:

no_negative_currency
valid_room_state
character_exists
no_duplicate_objects

Keep simple, deterministic.

⚔️ COMMAND-PATH RUNNER
DT-036 — Implement ctx.cmd()

In context:

def cmd(self, command_str):

Must:

execute Evennia command system
capture output
append to command_log
DT-037 — Capture Output from Command Execution

Store:

self.output_log.append(output)

Must capture:

text output
errors
DT-038 — Add Optional Snapshot After Command

After each command:

if auto_snapshot:
    self.snapshot(command_str)

Configurable flag.

⚙️ DIRECT-PATH RUNNER
DT-039 — Implement ctx.direct()
def direct(self, func, *args, **kwargs):

Must:

call function directly
capture return value
log invocation
DT-040 — Capture Exceptions in Direct Calls

Wrap:

try:
    func(...)
except Exception:
    raise

Ensure:

traceback captured
artifacts written
✅ END STATE AFTER DT-040

You now have:

✔ full teardown lifecycle
✔ leak detection + reporting
✔ invariant system
✔ command-path execution
✔ direct-path execution
✔ structured failure handling

🧠 WHAT THIS UNLOCKS

Now you can:

reproduce bugs reliably
validate system integrity
debug with artifacts
test both real gameplay and internal logic

DIRETEST — MICROTASKS 041–060 (STRICT)
🎯 PHASE GOAL

At the end of this set:

✔ diretest scenario <name> works
✔ scenarios are discoverable and runnable
✔ artifacts can be replayed
✔ basic time control exists
✔ first real scenarios implemented

🖥️ CLI INTERFACE
DT-041 — Create CLI Entrypoint

File:

tools/diretest/cli.py

Entry function:

def main():

Must:

parse arguments
route to scenario runner
DT-042 — Define CLI Command Structure

Supported format:

diretest scenario <name> --seed <int> --mode <command|direct>

Defaults:

seed = auto-generated
mode = command
DT-043 — Parse CLI Arguments

Extract:

scenario name
seed (optional)
mode (optional)

Reject unknown flags.

DT-044 — Print Run Summary Header

Before execution:

Running scenario: <name>
Mode: <mode>
Seed: <seed>
🧩 SCENARIO REGISTRATION SYSTEM
DT-045 — Create Scenario Registry

File:

tools/diretest/scenarios/registry.py

Structure:

SCENARIOS = {}
DT-046 — Add Scenario Registration Decorator
def scenario(name):

Usage:

@scenario("death-loop")
def death_loop(ctx):
    ...
DT-047 — Implement Scenario Lookup

Function:

get_scenario(name)

Must:

return function
raise error if not found
DT-048 — Validate Scenario Exists Before Execution

If missing:

Scenario not found: <name>

Exit cleanly.

🧠 EXECUTION PIPELINE
DT-049 — Wire CLI to Runner

In CLI:

run_scenario(scenario_func, seed, mode)

Must:

pass seed
pass mode
DT-050 — Create Run ID Generator

Format:

YYYYMMDD_HHMMSS_<short_uuid>

Used for artifact directory.

DT-051 — Attach Run ID to Context
ctx.run_id

Used by artifact system.

DT-052 — Initialize Context with Harness

Context must include:

harness instance
character
room
DT-053 — Capture Initial Snapshot Automatically

Before scenario starts:

ctx.snapshot("initial")
DT-054 — Capture Final Snapshot Automatically

After scenario completes:

ctx.snapshot("final")
🔁 ARTIFACT REPLAY SYSTEM
DT-055 — Add Replay CLI Command

Command:

diretest repro <artifact_path>
DT-056 — Load Artifact Metadata

From:

scenario.json
seed.txt

Extract:

scenario name
seed
mode
DT-057 — Re-run Scenario from Artifact

Call:

run_scenario(scenario_func, seed, mode)

Must match original execution.

DT-058 — Print Replay Header
Replaying scenario: <name>
Seed: <seed>
⏱️ TIME CONTROL (BASIC HOOKS)
DT-059 — Add ctx.advance_time(seconds)

Stub implementation:

def advance_time(seconds):
    pass

Must exist—even if no-op initially.

DT-060 — Add ctx.freeze_time() / resume_time()

Functions:

ctx.freeze_time()
ctx.resume_time()

Stub allowed, but interface required.

🧪 FIRST REAL SCENARIOS

(These are part of this block—do not defer)

DT-061 — Create Movement Scenario

File:

tools/diretest/scenarios/movement.py

Scenario:

look
move direction
look again
check room change invariant
DT-062 — Create Inventory Scenario
check empty inventory
pick up item
verify item in inventory
drop item
verify removal
DT-063 — Create Basic Combat Scenario
spawn target
attack target
ensure combat starts
ensure target health decreases
DT-064 — Create Death Loop Scenario
damage character to death
verify corpse exists
trigger depart
verify new state
DT-065 — Create Economy Scenario
spawn corpse
search
loot
sell item
verify currency change
DT-066 — Register All Scenarios

Ensure each scenario is added via decorator.

DT-067 — Add Scenario Names List Command

CLI:

diretest list

Output:

Available scenarios:
- movement
- inventory
- combat-basic
- death-loop
- grave-recovery
- economy
- bank
DT-068 — Add Scenario Execution Timing

Measure:

start time
end time

Store in:

metrics.json
DT-069 — Print Success/Failure Summary

On completion:

PASS: <scenario>

or

FAIL: <scenario>
See artifacts: <path>
DT-070 — Ensure All Failures Produce Artifacts

Even:

scenario lookup failure
runtime exception
invariant failure

Artifacts must always be written.

✅ END STATE AFTER DT-070

You now have:

✔ working CLI
✔ scenario registration system
✔ execution pipeline
✔ artifact replay
✔ basic time control hooks
✔ first real scenarios
✔ success/failure reporting

🧠 WHAT THIS UNLOCKS

Now Aedan can:

diretest scenario death-loop --seed 4412

and:

reproduce bugs
inspect artifacts
replay failures
debug system behavior


DIRETEST — MICROTASKS 071–090 (STRICT)
🎯 PHASE GOAL

At the end of this set:

✔ snapshot diffs exist
✔ invariants cover more real game risks
✔ failures are classified, not just dumped
✔ metrics are more informative
✔ Evennia integration is cleaner
✔ descriptive reporting begins

🧠 INVARIANT EXPANSION
DT-071 — Add valid_combat_state Invariant

Implement invariant:

@invariant("valid_combat_state")

Checks:

if character is in combat, target exists
if target exists, target is in same room unless system explicitly allows otherwise
disengaged characters must not retain active combat links
dead characters must not remain in active combat state
DT-072 — Add valid_death_state Invariant

Implement:

@invariant("valid_death_state")

Checks:

alive characters must not have active corpse objects linked as current body
dead characters must have legal life_state
departed characters must not still be attached to unresolved corpse state
no impossible combinations of life_state and recovery flags
DT-073 — Add valid_weight_state Invariant

Implement:

@invariant("valid_weight_state")

Checks:

total_weight >= 0
max_carry_weight > 0
encumbrance_ratio matches computed value within small tolerance
no negative item weights
no container over-capacity state if your runtime forbids it
DT-074 — Add valid_race_state Invariant

Implement:

@invariant("valid_race_state")

Checks:

character race exists in canonical registry
carry modifier matches race definition
learning modifiers match race definition
stat caps match race definition
DT-075 — Add client_payload_safe Invariant

Implement:

@invariant("client_payload_safe")

Checks:

structured payload generation for current character does not raise exception
map/character payload hooks return serializable data or a valid empty structure

This is a major regression catcher for browser-client changes.

📸 SNAPSHOT DIFFING
DT-076 — Create Snapshot Diff Module

File:

tools/diretest/core/diff.py

Function:

diff_snapshots(before: dict, after: dict) -> dict

Must return structured changes only.

DT-077 — Define Diff Output Schema

Locked schema:

DIFF_SCHEMA = {
    "character_changes": dict,
    "room_changes": dict,
    "inventory_changes": {
        "added": list,
        "removed": list
    },
    "equipment_changes": {
        "added": list,
        "removed": list
    },
    "combat_changes": dict,
    "attribute_changes": dict,
    "object_delta_changes": dict
}

No freeform output.

DT-078 — Generate Step-to-Step Diffs Automatically

After every new snapshot:

if a previous snapshot exists
compute diff between previous and current snapshot
store in memory on context

Structure:

ctx.diffs = [
    {"from": "label_a", "to": "label_b", "data": diff_dict}
]
DT-079 — Write Diffs to Artifact Bundle

Add file:

diffs.json

This file is REQUIRED once diffing exists.

If no diffs exist, write an empty list.

DT-080 — Add diretest diff <before> <after> CLI Command

Command:

diretest diff <before_snapshot.json> <after_snapshot.json>

Behavior:

load both snapshots
compute diff using canonical diff function
print compact summary to console
optional full JSON output to stdout or file
📊 METRICS EXPANSION
DT-081 — Expand Metrics Schema

File:

tools/diretest/core/metrics.py

Locked metrics keys for v1:

METRICS_SCHEMA = {
    "command_count": int,
    "command_timings_ms": list,
    "item_delta_count": int,
    "coin_delta": int,
    "xp_delta": int,
    "mindstate_delta": dict,
    "state_transition_count": int,
    "scenario_duration_ms": int,
    "leaks": list
}
DT-082 — Record Command Timing Per Step

For every ctx.cmd():

measure elapsed time in milliseconds
append to:
ctx.metrics["command_timings_ms"]
DT-083 — Record Coin Delta

At scenario completion:

compare initial and final character coin values
store signed result in:
ctx.metrics["coin_delta"]
DT-084 — Record Item Delta Count

At scenario completion:

compare initial vs final inventory + equipment count
store signed or absolute delta according to locked design
choose signed delta for v1
DT-085 — Record XP and Mindstate Deltas

At scenario completion:

compare initial vs final total XP / relevant XP fields
compare initial vs final mindstate structure
write to metrics

If unavailable for current actor, record zero or empty dict, not null.

🚨 FAILURE CLASSIFICATION
DT-086 — Define Failure Types Enum

File:

tools/diretest/core/failures.py

Locked failure types:

FAILURE_TYPES = [
    "scenario_lookup_failure",
    "command_execution_failure",
    "direct_execution_failure",
    "invariant_failure",
    "teardown_failure",
    "leak_failure",
    "snapshot_failure",
    "artifact_write_failure",
    "unexpected_exception"
]
DT-087 — Classify Failures Before Writing Artifacts

Whenever a failure occurs:

assign one failure type from the locked enum
store it in context
write it into artifact metadata
DT-088 — Write Failure Summary File

Add required artifact file:

failure_summary.json

Contents:

{
  "failure_type": "...",
  "message": "...",
  "scenario": "...",
  "seed": 1234,
  "mode": "command"
}

If scenario passes, still write file with "failure_type": null.

🔌 EVENNIA INTEGRATION TIGHTENING
DT-089 — Add Test Mode Flag for DireTest Runs

During scenario execution, set a scoped runtime flag such as:

ctx.test_mode = True

And expose a global or context-aware hook so engine systems can check whether they are running under DireTest.

Do NOT change game behavior by default yet. This is a hook only.

DT-090 — Add Optional Payload Suppression Hook

Create interface:

ctx.suppress_client_payloads = False

And add integration point so future scenarios can suppress expensive client sync behavior where appropriate.

Default remains False.
No behavior change unless explicitly wired.

✅ END STATE AFTER DT-090

You now have:

✔ richer invariants
✔ structured snapshot diffs
✔ stronger metrics
✔ classified failures
✔ safer Evennia integration hooks
✔ first descriptive reporting layer

🧠 WHAT THIS ADDS

DireTest is now no longer just:

“run a scenario and dump logs”

It is now:

compare state transitions
classify what failed
measure what changed
catch deeper cross-system corruption

That is a major jump in usefulness.

DIRETEST — MICROTASKS 071–090 (STRICT)
🎯 PHASE GOAL

At the end of this set:

✔ snapshot diffs exist
✔ invariants cover more real game risks
✔ failures are classified, not just dumped
✔ metrics are more informative
✔ Evennia integration is cleaner
✔ descriptive reporting begins

🧠 INVARIANT EXPANSION
DT-071 — Add valid_combat_state Invariant

Implement invariant:

@invariant("valid_combat_state")

Checks:

if character is in combat, target exists
if target exists, target is in same room unless system explicitly allows otherwise
disengaged characters must not retain active combat links
dead characters must not remain in active combat state
DT-072 — Add valid_death_state Invariant

Implement:

@invariant("valid_death_state")

Checks:

alive characters must not have active corpse objects linked as current body
dead characters must have legal life_state
departed characters must not still be attached to unresolved corpse state
no impossible combinations of life_state and recovery flags
DT-073 — Add valid_weight_state Invariant

Implement:

@invariant("valid_weight_state")

Checks:

total_weight >= 0
max_carry_weight > 0
encumbrance_ratio matches computed value within small tolerance
no negative item weights
no container over-capacity state if your runtime forbids it
DT-074 — Add valid_race_state Invariant

Implement:

@invariant("valid_race_state")

Checks:

character race exists in canonical registry
carry modifier matches race definition
learning modifiers match race definition
stat caps match race definition
DT-075 — Add client_payload_safe Invariant

Implement:

@invariant("client_payload_safe")

Checks:

structured payload generation for current character does not raise exception
map/character payload hooks return serializable data or a valid empty structure

This is a major regression catcher for browser-client changes.

📸 SNAPSHOT DIFFING
DT-076 — Create Snapshot Diff Module

File:

tools/diretest/core/diff.py

Function:

diff_snapshots(before: dict, after: dict) -> dict

Must return structured changes only.

DT-077 — Define Diff Output Schema

Locked schema:

DIFF_SCHEMA = {
    "character_changes": dict,
    "room_changes": dict,
    "inventory_changes": {
        "added": list,
        "removed": list
    },
    "equipment_changes": {
        "added": list,
        "removed": list
    },
    "combat_changes": dict,
    "attribute_changes": dict,
    "object_delta_changes": dict
}

No freeform output.

DT-078 — Generate Step-to-Step Diffs Automatically

After every new snapshot:

if a previous snapshot exists
compute diff between previous and current snapshot
store in memory on context

Structure:

ctx.diffs = [
    {"from": "label_a", "to": "label_b", "data": diff_dict}
]
DT-079 — Write Diffs to Artifact Bundle

Add file:

diffs.json

This file is REQUIRED once diffing exists.

If no diffs exist, write an empty list.

DT-080 — Add diretest diff <before> <after> CLI Command

Command:

diretest diff <before_snapshot.json> <after_snapshot.json>

Behavior:

load both snapshots
compute diff using canonical diff function
print compact summary to console
optional full JSON output to stdout or file
📊 METRICS EXPANSION
DT-081 — Expand Metrics Schema

File:

tools/diretest/core/metrics.py

Locked metrics keys for v1:

METRICS_SCHEMA = {
    "command_count": int,
    "command_timings_ms": list,
    "item_delta_count": int,
    "coin_delta": int,
    "xp_delta": int,
    "mindstate_delta": dict,
    "state_transition_count": int,
    "scenario_duration_ms": int,
    "leaks": list
}
DT-082 — Record Command Timing Per Step

For every ctx.cmd():

measure elapsed time in milliseconds
append to:
ctx.metrics["command_timings_ms"]
DT-083 — Record Coin Delta

At scenario completion:

compare initial and final character coin values
store signed result in:
ctx.metrics["coin_delta"]
DT-084 — Record Item Delta Count

At scenario completion:

compare initial vs final inventory + equipment count
store signed or absolute delta according to locked design
choose signed delta for v1
DT-085 — Record XP and Mindstate Deltas

At scenario completion:

compare initial vs final total XP / relevant XP fields
compare initial vs final mindstate structure
write to metrics

If unavailable for current actor, record zero or empty dict, not null.

🚨 FAILURE CLASSIFICATION
DT-086 — Define Failure Types Enum

File:

tools/diretest/core/failures.py

Locked failure types:

FAILURE_TYPES = [
    "scenario_lookup_failure",
    "command_execution_failure",
    "direct_execution_failure",
    "invariant_failure",
    "teardown_failure",
    "leak_failure",
    "snapshot_failure",
    "artifact_write_failure",
    "unexpected_exception"
]
DT-087 — Classify Failures Before Writing Artifacts

Whenever a failure occurs:

assign one failure type from the locked enum
store it in context
write it into artifact metadata
DT-088 — Write Failure Summary File

Add required artifact file:

failure_summary.json

Contents:

{
  "failure_type": "...",
  "message": "...",
  "scenario": "...",
  "seed": 1234,
  "mode": "command"
}

If scenario passes, still write file with "failure_type": null.

🔌 EVENNIA INTEGRATION TIGHTENING
DT-089 — Add Test Mode Flag for DireTest Runs

During scenario execution, set a scoped runtime flag such as:

ctx.test_mode = True

And expose a global or context-aware hook so engine systems can check whether they are running under DireTest.

Do NOT change game behavior by default yet. This is a hook only.

DT-090 — Add Optional Payload Suppression Hook

Create interface:

ctx.suppress_client_payloads = False

And add integration point so future scenarios can suppress expensive client sync behavior where appropriate.

Default remains False.
No behavior change unless explicitly wired.

✅ END STATE AFTER DT-090

You now have:

✔ richer invariants
✔ structured snapshot diffs
✔ stronger metrics
✔ classified failures
✔ safer Evennia integration hooks
✔ first descriptive reporting layer

🧠 WHAT THIS ADDS

DireTest is now no longer just:

“run a scenario and dump logs”

It is now:

compare state transitions
classify what failed
measure what changed
catch deeper cross-system corruption

That is a major jump in usefulness.

GOAL

At the end of this set:

✔ command latency measured and classified
✔ spikes and jitter detected
✔ lag summarized in artifacts
✔ scenarios can fail on performance
✔ onboarding + combat responsiveness measurable
✔ reproducible lag diagnostics (not guesswork)

🧱 PHASE: LAG DETECTION CORE
🟩 LAG-001 — Define Lag Metrics Schema (LOCKED)

File:

tools/diretest/core/lag.py
LAG_SCHEMA = {
    "avg_ms": float,
    "max_ms": float,
    "min_ms": float,
    "p95_ms": float,
    "spike_count": int,
    "slow_count": int,
    "jitter": float,
    "status": str  # ok | warning | bad | critical
}

No deviations.

🟩 LAG-002 — Define Threshold Constants (LOCKED)
LAG_THRESHOLDS = {
    "warning_ms": 150,
    "bad_ms": 250,
    "critical_ms": 500,
    "spike_ms": 300
}
🟩 LAG-003 — Implement Lag Analyzer

Function:

def analyze_latency(command_timings_ms: list[float]) -> dict:

Must compute:

avg
min
max
p95
spike_count (timing > spike_ms)
slow_count (timing > warning_ms)
jitter (std deviation)
🟩 LAG-004 — Compute Status Level

Rules:

Condition	Status
max < 150	ok
any >150	warning
any >250	bad
any >500	critical

Return single status.

🟩 LAG-005 — Integrate into Metrics Engine

File:

tools/diretest/core/metrics.py

Add:

ctx.metrics["lag"] = analyze_latency(ctx.metrics["command_timings_ms"])
🟩 LAG-006 — Write Lag Data to metrics.json

Ensure output:

"lag": {
  "avg_ms": ...,
  "max_ms": ...,
  ...
}
🧠 PHASE: COMMAND TIMING ACCURACY
🟩 LAG-007 — Ensure Timing Starts Before Parser

In ctx.cmd():

Measure:

start = time.perf_counter()
execute_cmd()
end = time.perf_counter()

Must include:

parsing
execution
output generation
🟩 LAG-008 — Capture Timing Even on Failure

If command errors:

still record timing
🟩 LAG-009 — Tag Each Timing Entry

Store:

{
  "command": "attack goblin",
  "ms": 82.3
}

Replace raw list with structured entries.

🟩 LAG-010 — Preserve Backward Compatibility

Also maintain:

command_timings_ms = [entry["ms"]]
🧪 PHASE: SPIKE & JITTER DETECTION
🟩 LAG-011 — Add Spike Detector

Function:

def detect_spikes(timings):

Criteria:

ms > spike_ms
🟩 LAG-012 — Add Jitter Calculation

Use:

statistics.stdev()

If <2 samples → jitter = 0

🟩 LAG-013 — Flag High Jitter

If:

jitter > 75ms

Add warning flag.

🧠 PHASE: CLI & OUTPUT
🟩 LAG-014 — Print Lag Summary to Console

After scenario:

Lag Summary:
  avg: 82ms
  max: 312ms
  spikes: 2
  status: WARNING
🟩 LAG-015 — Print Warning Only If Needed

Only print if:

status != ok
🟩 LAG-016 — Add --check-lag CLI Flag

CLI:

diretest scenario onboarding_full --check-lag

If enabled:

treat “bad” or “critical” as failure
🟩 LAG-017 — Add Lag Failure Type

Update:

FAILURE_TYPES

Add:

"lag_failure"
🟩 LAG-018 — Fail Scenario on Critical Lag

If:

status == "critical"

→ fail scenario

🧠 PHASE: SCENARIO INTEGRATION
🟩 LAG-019 — Add Lag Snapshot Markers

After key steps:

ctx.snapshot("post_attack")
ctx.snapshot("post_move")

Used to correlate spikes.

🟩 LAG-020 — Correlate Lag with Commands

Add mapping:

ctx.lag_events = [
    {"command": ..., "ms": ..., "snapshot": ...}
]
🟩 LAG-021 — Highlight Slow Commands in Artifacts

In metrics.json:

"slow_commands": [
  {"cmd": "attack goblin", "ms": 312}
]
🧠 PHASE: ONBOARDING-SPECIFIC DIAGNOSTICS
🟩 LAG-022 — Add Onboarding Lag Scenario

Scenario:

onboarding_lag

Steps:

gender
race
mirror
combat
vendor

Measure:

latency per step
🟩 LAG-023 — Add “First Response Time” Metric

Measure:

time from command → first output line

Important for perceived lag.

🟩 LAG-024 — Add NPC Response Delay Metric

Measure:

time between player action and mentor/gremlin response
🟩 LAG-025 — Add Combat Responsiveness Metric

Measure:

time from attack → damage applied
🧠 PHASE: ARTIFACT ENHANCEMENT
🟩 LAG-026 — Write lag.json Artifact

New file:

artifacts/<run_id>/lag.json

Include:

full timing entries
spike events
jitter
slow commands
🟩 LAG-027 — Include Lag in failure_summary.json
"lag_status": "warning"
🟩 LAG-028 — Add Replay Support

When running:

diretest repro <artifact>

Ensure:

lag metrics recomputed
compared with original
🧠 PHASE: ADVANCED (OPTIONAL BUT HIGH VALUE)
🟩 LAG-029 — Add Payload Timing Hook

If possible:

Measure:

time spent generating client payload
🟩 LAG-030 — Add Script/Ticker Delay Detection

Track:

delayed script execution
queued events
🎯 FINAL STATE

After LAG-001 → LAG-030:

DireTest becomes:

Capability	Status
Detect slow commands	✅
Detect spikes	✅
Detect jitter	✅
Diagnose cause (command-level)	✅
Fail on lag	✅
Reproduce lag	✅
🧠 KEY INSIGHT

You are NOT building:

a performance profiler

You ARE building:

a playability detector
