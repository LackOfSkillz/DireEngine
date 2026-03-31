PHASE 1.5 — INTEREST / ACTIVATION MODEL (LOCKED, REFINED)
🧠 PHASE CONTEXT

Phase 0–1 established:

scheduler = execution mechanism
timing model = when things run
timestamps = authoritative state
metrics + DireTest = visibility
first migration proven safe
🎯 PHASE 1.5 GOAL

Introduce an engine-owned activation layer that determines:

whether continuous behavior is allowed to run

Shift from:

everything runs all the time

to:

only objects with active interest execute behavior
⚠️ CORE ARCHITECTURE (LOCK THESE)
🔒 Activation is ENGINE-OWNED
NO per-object “active flag” logic as primary system
ONE central service answers:
is_active(obj) -> bool
🔒 Separation of Responsibilities
Activation → should this run
Scheduler → when should it run
Timestamps → what is true
On-demand → how to recover state (optional, limited)
🔒 Objects always exist
no unloading
no re-instantiation
no lifecycle hacks
🔒 Activation is INTEREST-DRIVEN

Sources include:

room (same room)
proximity (radius)
zone (region)
direct targeting (combat/spell)
scheduler / controller ownership
🔒 System must be fully toggleable
runtime ON/OFF
no restart
OFF = current behavior exactly
🔒 Observability is mandatory

You must always be able to answer:

why is this object active right now?

✅ END STATE

✔ Activation service exists and is centralized
✔ Activation scopes defined and enforced
✔ Commands no longer scan global object sets
✔ At least one system uses activation safely
✔ Scheduler integrates with activation
✔ GM can toggle system at runtime
✔ Debug tools explain activation state
✔ DireTest validates ON vs OFF

🧭 PHASE 1.5 — MICROTASKS 001–025 (STRICT)
STATUS UPDATE

- COMPLETE: PH1.5-001 through PH1.5-005
- COMPLETE: PH1.5-006 through PH1.5-010
- COMPLETE: PH1.5-011 room-based activation wiring
- COMPLETE: PH1.5-012 proximity activation
- COMPLETE: PH1.5-013 zone activation
- COMPLETE: PH1.5-014 direct target activation
- COMPLETE: PH1.5-015 scheduler-based activation
- COMPLETE: PH1.5-016 interest cleanup expansion
- COMPLETE: PH1.5-018 target scope helpers
- COMPLETE: PH1.5-019 renew-all scoping under activation
- COMPLETE: PH1.5-020 scheduler respects activation
- COMPLETE: PH1.5-022 safe skip behavior
- COMPLETE: PH1.5-023 activation metrics
- COMPLETE: PH1.5-024 @engine interest debug
- COMPLETE: PH1.5-025 DireTest dual mode ON/OFF comparison

VALIDATION SURFACE

- `interest-renew-benchmark` compares legacy global renew selection against activation-scoped renew selection and records target-count plus selection-time deltas in artifacts.
- `interest-zone-activation` validates that build-tag zone membership activates same-zone rooms without leaking into unrelated zones.
- `interest-direct-activation` validates combat-target, aim-target, and temporary spell-target direct interest lifecycles.
- `interest-activation-metrics` validates active/peak object gauges, source-type gauges, and activation transition counters.
- `interest-debug-command` validates `@engine interest debug` output, including active-object reasons and source-type summaries.
- `interest-dual-mode-compare` reports OFF versus ON correctness, timing, and performance deltas for the activation-scoped renew benchmark.
- `interest-scheduled-activation` validates that pending keyed jobs attach scheduled interest to the owning object and clean it up on completion or cancellation.
- `interest-scheduler-respects-activation` validates that inactive owners are gated before scheduler callback execution and emit skip telemetry.
- `interest-scheduler-safe-skip` validates the defer path, retaining an inactive job safely and re-executing it once the scheduler reactivates the owner.
- Runtime metrics now expose `interest.transition`, `command.renew.target_select`, and `command.renew.execute` events for net-result analysis.

🧠 SECTION A — ENGINE FLAG SYSTEM
PH1.5-001 — Create Engine Flags Module [DONE]
world/systems/engine_flags.py
ENGINE_FLAGS = {
    "interest_activation": False,
}
PH1.5-002 — Add Flag API [DONE]
is_enabled(flag: str) -> bool
set_flag(flag: str, value: bool)
PH1.5-003 — Add Logging [DONE]

Log:

[Engine] interest_activation ENABLED by <admin>
PH1.5-004 — GM Command [DONE]
@engine interest on
@engine interest off
@engine interest status
PH1.5-005 — Validate Safe Toggle [DONE]
OFF = identical behavior
ON = new system
no restart
🧱 SECTION B — ACTIVATION ENGINE
PH1.5-006 — Create Activation Model Doc [DONE]
docs/architecture/interest-model.md

Must define:

activation purpose
separation of concerns
activation sources
inactive behavior expectations
PH1.5-007 — Define Activation Scopes (LOCKED) [DONE]
ROOM
PROXIMITY (radius-based)
ZONE
DIRECT
SCHEDULED
PH1.5-008 — Create Activation Service [DONE]
world/systems/interest.py

Core API:

add_interest(obj, source, type)
remove_interest(obj, source)
is_active(obj)
get_activation_sources(obj)
PH1.5-009 — Activation Rules [DONE]

Activation is derived from:

active if interest_sources > 0

NO manual flags as primary control.

PH1.5-010 — Activation Hooks (Optional but Controlled) [DONE]
on_activate()
on_deactivate()

Used sparingly (NOT required everywhere)

🎯 SECTION C — INTEREST SOURCES
PH1.5-011 — Room-Based Activation [DONE]
player in room → activate contents
PH1.5-012 — Proximity Activation [DONE]
define radius (start simple: 1 room)
expand later
PH1.5-013 — Zone Activation [DONE]
define zone boundaries
activate zone-level systems
PH1.5-014 — Direct Target Activation [DONE]
combat targets
spell targets
explicit references
PH1.5-015 — Scheduler-Based Activation [DONE]
scheduled jobs keep object active
PH1.5-016 — Interest Cleanup [DONE]

When:

player leaves
job completes
effect ends

→ remove interest

⚙️ SECTION D — COMMAND SCOPE (FIRST REAL WIN)
PH1.5-017 — Remove Global Scans

Audit commands:

Replace:

ObjectDB.objects.all()
PH1.5-018 — Add Target Scope Helpers [DONE]
get_visible_targets(caller)
get_nearby_targets(caller)
get_active_targets()
PH1.5-019 — Fix “renew all” [DONE]

Restrict to:

room
nearby
active objects
🧪 SECTION E — SCHEDULER INTEGRATION
PH1.5-020 — Scheduler Respects Activation [DONE]

Before execution:

if not is_active(obj):
    skip or defer
PH1.5-021 — Scheduler Adds Interest

Objects with pending jobs must remain active

PH1.5-022 — Safe Skip Behavior [DONE]

Ensure:

no state corruption
safe re-execution
📊 SECTION F — OBSERVABILITY (CRITICAL)
PH1.5-023 — Activation Metrics [DONE]

Track:

active object count
activation transitions
source types

Validation:

- `interest-activation-metrics` verifies active/peak object gauges, source-type gauges, and transition counters in one structural pass.
PH1.5-024 — Debug Command
@engine interest debug

[DONE]

Shows:

active objects
interest sources
why each is active

Validation:

- `interest-debug-command` verifies the admin-facing debug output includes flag state, source summaries, and per-object activation reasons.
PH1.5-025 — DireTest Dual Mode

Run all scenarios:

activation OFF
activation ON

Compare:

correctness
timing
performance

[DONE]

Validation:

- `interest-dual-mode-compare` produces a single artifact with OFF versus ON correctness, timing, and performance deltas for the activation-scoped renew benchmark.
⚠️ HARD GUARDRAILS
❌ DO NOT
implement per-object activation logic everywhere
treat activation as persistence
use OnDemand as execution control
migrate multiple systems at once
✅ DO
centralize activation decisions
keep OFF mode identical
migrate commands first
validate every step
🎯 FINAL MODEL (WHAT YOU BUILT)

At the end:

activation decides if behavior runs
scheduler executes timing
timestamps remain truth
on-demand fills recovery gaps