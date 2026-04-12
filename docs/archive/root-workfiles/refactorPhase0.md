Phase 0 — Engine contract hardening

Before scheduler work, lock the architectural contract:

engine layer vs game/content layer
command layer vs system layer
timing policy by use case
queue/quota rules
instrumentation requirements

This is the LPMud lesson adapted to Evennia: keep infrastructure separate from gameplay policy.

Phase 1 — Time model hardening

Replace “tick-first” thinking with a formal timing matrix:

delay/task for one-shots
Script-style controllers for persistent out-of-band state
shared ticker only when many objects truly need the same interval
no custom per-object free-running loops

That is the clearest match to Evennia’s intended model.

Phase 2 — Scheduler and quota hardening

Build a scheduler wrapper, but make it thin and enforce:

deduplication keys
cancellation
reschedule
max queued jobs per owner/system
queue-depth metrics
rejection/backpressure behavior

This is where LambdaMOO’s queued-task-limit idea belongs in your engine.

Phase 3 — Combat timing hardening

Combat should use:

command-triggered action resolution
scheduled roundtime expiry
event-based status expiration
no blanket combat pulse

The tbaMUD guidance strongly supports this: use events for effect durations instead of overloading a violence pulse.

Phase 4 — World-state hardening

World systems like weather, day/night, resets, and ambient simulation may still need periodic work, but they should be:

coarse-grained
queued
conditional
measurable
preferably zone/region scoped

CircleMUD’s queued zone reset model is the historical precedent here.

Phase 5 — Out-of-band state extraction

Move long-lived system state out of Character/Object sprawl and into dedicated system/state holders where appropriate. In Evennia terms, Scripts are explicitly meant for out-of-band storage and timed system state such as economy, fights, or barter.

Phase 6 — Observability and regression hardening

Every timing path needs:

duration metrics
queue size metrics
per-system counters
DireTest replay coverage for timing-sensitive flows

This is partly an inference from the sources rather than a quoted rule, but it follows directly from the historical problems those systems were trying to control. The sources consistently emphasize explicit handlers, queues, and bounded scheduled work rather than invisible ambient processing.

The lock-worthy principles

If you want the “shoulders of giants” version of your engine doctrine, I’d lock these:

Engine and game logic stay separate.
Driver/mudlib was right then, and it is right now.
No universal global tick as the default answer.
Evennia explicitly does not require one, and you should treat that as a strength.
Choose the lightest timing primitive that fits.
Delay for one-shots, Script for persistent system controllers/state, Ticker for many same-interval subscribers.
Queued work must be bounded.
Per-owner and per-system limits are not optional.
Periodic world work must be conditional and coarse-grained.
Queue it, gate it, and avoid scanning everything just because time passed.
Combat and effect durations should be event-driven where possible.
Don’t let a violence pulse become the universal hammer.
Bottom line

After the research, I would keep the hardening blueprint, but I would rename and tighten it as:

Phase 0: Engine contract hardening
Phase 1: Time model hardening
Phase 2: Scheduler and quota hardening
Phase 3: Combat timing hardening
Phase 4: World-state hardening
Phase 5: Out-of-band state extraction
Phase 6: Observability and regression hardening

That version is much more in line with what the classic engines learned the hard way.

PHASE 0 — LOCKED OBJECTIVES

At the end of Phase 0:

✔ Engine vs game boundaries are explicit
✔ Timing model is defined (no accidental ticks)
✔ Scheduler contract exists (even if minimal)
✔ Work is measurable (metrics exist)
✔ No system can secretly introduce lag patterns
✔ DireTest can observe timing + execution behavior

🧭 PHASE 0 — MICROTASKS 001–020 (STRICT)

These are atomic, ordered, no-skips tasks for Aedan.

They are designed to:

introduce structure without breaking gameplay
create guardrails before refactoring deeper systems
align with Evennia + classic MUD best practices
🧠 SECTION A — ENGINE CONTRACT (FOUNDATION)
PH0-001 — Create Engine Architecture Document

Create:

docs/architecture/engine-contract.md

Must define:

Engine Layer (scheduler, metrics, timing)
System Layer (combat, onboarding, death, etc.)
Command Layer (input only)
Content Layer (rooms, NPCs, data)

Include rules:

commands do not contain game logic
systems do not run implicit loops
engine owns time

✅ Done when document clearly defines all 4 layers and rules

PH0-002 — Add “No Implicit Tick” Rule

In same doc, explicitly state:

No system may run periodic logic unless registered through engine timing.

Include examples of forbidden patterns:

while True loops
per-object tick methods
polling state every second

✅ Done when rule is written and visible

PH0-003 — Define Timing Model Document

Create:

docs/architecture/time-model.md

Define:

delay (one-shot)
scheduled (explicit events)
shared ticker (rare, grouped)
global tick (last resort)

Include examples for:

combat RT
XP pulse
weather

✅ Done when each timing type has at least 1 concrete use case

PH0-004 — Define Scheduler Contract

Add to same doc:

Required API:

schedule(delay, callback, key=None)
cancel(key)
reschedule(key, delay)

Define:

key uniqueness
idempotency expectation
cancellation behavior

✅ Done when contract is clear and unambiguous

⚙️ SECTION B — SCHEDULER (MINIMAL IMPLEMENTATION)
PH0-005 — Create Scheduler Module

Create file:

world/systems/scheduler.py

Initial implementation:

wrapper around Evennia delay/utils
no optimization yet

Must support:

schedule
cancel
reschedule

✅ Done when basic scheduling works via wrapper

PH0-006 — Add Key-Based Scheduling

Extend scheduler:

allow optional key
prevent duplicate scheduled jobs with same key

Behavior:

scheduling same key replaces existing job

✅ Done when duplicate scheduling is prevented

PH0-007 — Add Cancellation Support

Implement:

cancel(key)

Must:

safely cancel if exists
no error if missing

✅ Done when cancellation is safe and silent

PH0-008 — Add Reschedule Support

Implement:

reschedule(key, delay)

Behavior:

cancel existing
schedule new

✅ Done when reschedule works reliably

📊 SECTION C — METRICS (VISIBILITY)
PH0-009 — Create Metrics Module

Create:

world/systems/metrics.py

Add:

record_event(name: str, duration_ms: float)
increment_counter(name: str)

Store in-memory for now

✅ Done when events can be recorded globally

PH0-010 — Add Timing Helper

Create helper:

with measure("combat.attack"):
    ...

Automatically records duration

✅ Done when timing wrapper works

PH0-011 — Instrument Command Execution

Wrap command execution:

measure total command time
record event: "command.execute"

✅ Done when every command logs execution time

PH0-012 — Instrument Scheduler Execution

Track:

number of scheduled jobs executed
execution time per job

Events:

"scheduler.execute"

✅ Done when scheduler activity is measurable

🧪 SECTION D — DIRETEST INTEGRATION
PH0-013 — Extend DireTest Metrics Capture

Update DireTest result object to include:

scenario_duration
command_count
scheduler_events
max_command_time

✅ Done when these appear in scenario output

PH0-014 — Add Timing Snapshot to Artifacts

Artifacts must include:

{
  "metrics": {
    "commands": ...,
    "scheduler": ...,
    "timings": ...
  }
}

✅ Done when artifacts persist timing data

PH0-015 — Add Performance Summary to CLI Output

Example:

PASS combat-basic (42ms)
commands: 5 | scheduler: 3 | max_cmd: 12ms

✅ Done when summary prints after each run

🚫 SECTION E — GUARDRAILS (CRITICAL)
PH0-016 — Add Tick Violation Detector (Soft)

Scan for:

functions named tick
loops calling time repeatedly

Log warning if detected

(No enforcement yet)

✅ Done when warnings appear in dev logs

PH0-017 — Add Scheduler Usage Logging

Log when systems use scheduler:

[Scheduler] combat.rt scheduled (delay=2.0)

✅ Done when scheduling is visible

PH0-018 — Add Max Queue Size Tracking

Track:

current scheduled job count
peak job count

Expose via metrics

✅ Done when queue size is observable

🧱 SECTION F — FIRST SAFE INTEGRATION
PH0-019 — Move Roundtime (RT) to Scheduler

Refactor:

RT expiration uses scheduler
remove any polling/tick-based RT logic

✅ Done when RT is fully event-driven

PH0-020 — Add DireTest Scenario for RT Timing

Scenario must verify:

action triggers RT
command blocked during RT
RT expires correctly
command allowed after

✅ Done when RT behavior is reproducible and stable

✅ END STATE AFTER PH0-020

You now have:

✔ Engine contract defined
✔ Timing model defined
✔ Scheduler exists and works
✔ Metrics visible
✔ DireTest capturing performance
✔ First real system (RT) using scheduler
✔ Guardrails against future tick abuse

What kind of refactor this actually is

Phase 0 is a hardening + instrumentation pass, not a behavioral rewrite.

You are:

adding structure
adding visibility
redirecting one system (RT) to scheduler

You are not yet:

rewriting combat
splitting Character deeply
changing onboarding flow
altering core game rules

That’s why risk is relatively contained.

⚠️ Where breakage can happen
1. Roundtime (RT) migration — highest risk area

This is the only part of Phase 0 that actually changes behavior.

What could break:
RT not expiring
RT expiring too early/late
commands not unlocking properly
double RT scheduling
desync between UI and actual state
Why:

You’re moving from:

implicit / possibly mixed timing

to:

explicit scheduled events

2. Scheduler bugs — second highest risk

Early scheduler implementations often have:

orphaned jobs (never canceled)
duplicate jobs
key collisions
callbacks firing after object is gone
3. Metrics wrapping — low risk but sneaky

Instrumentation can:

accidentally swallow exceptions
alter execution timing slightly
introduce edge-case bugs if wrappers aren’t clean
4. DireTest changes — safe but noisy

You might see:

test failures due to timing differences
new metrics revealing hidden issues (this is GOOD)
🟢 What will NOT break (very likely)

These are safe in Phase 0:

combat math
damage logic
skills
inventory
onboarding progression logic
world systems
NPC behavior

Because you are not touching their logic yet.

🧪 Why your risk is LOWER than normal

Most projects doing this refactor would be in danger.

You are not, because:

1. You already have DireTest

You can:

reproduce bugs
compare before/after
inspect artifacts

That is huge.

2. You are not rewriting everything at once

You are:

adding structure
migrating one system (RT)

This is exactly the correct incremental approach.

3. You are enforcing constraints BEFORE expansion

Most projects:

build → break → panic → refactor

You are:

stabilize → then build

🚨 Realistic expectation during Phase 0

You should EXPECT:

1–3 small regressions in RT behavior
possibly one scheduler edge case
a few test failures that expose existing hidden issues

You should NOT expect:

total system failure
engine instability
major gameplay collapse
🛡️ How to reduce risk to near-zero

Do these before Aedan starts:

✅ 1. Capture baseline scenarios NOW

Run and save:

diretest baseline save pre_phase0

At minimum include:

combat-basic
onboarding flow
RT behavior (if exists)
✅ 2. Add one RT-focused scenario FIRST (before refactor)

Before touching code, ensure:

RT blocks command
RT expires correctly

This becomes your safety net.

✅ 3. Implement scheduler BEFORE using it

Do NOT mix:

building scheduler
migrating RT

Sequence must be:

scheduler exists
scheduler tested in isolation
THEN move RT
✅ 4. Add logging for scheduler early

You want to SEE:

[Scheduler] RT scheduled (2.0s)
[Scheduler] RT expired

This will save hours of debugging.

✅ 5. Do NOT refactor anything else during Phase 0

No:

combat cleanup
onboarding cleanup
character splitting

Keep blast radius small.

🎯 Final assessment

If Aedan follows the tasks strictly:

Phase 0 is safe and controlled

If Aedan starts “improving things along the way”:

Risk increases dramatically