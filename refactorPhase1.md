PHASE 1 — TIME MODEL HARDENING (LOCKED)
🧠 PHASE CONTEXT (UPDATED — MUST READ)

Phase 0 established:

engine contract
scheduler (execution layer)
metrics + observability
DireTest deterministic timing (flush_due)
first scheduler-backed integration (RT)
⚠️ CRITICAL PHASE 1 CONSTRAINT

The engine is currently in a HYBRID TIME MODEL

authoritative state → timestamps (roundtime_end, etc.)
scheduler → executes expiry / callbacks
🔒 Rules:
scheduler is NOT the source of truth
timestamps remain authoritative in Phase 1
do NOT migrate authoritative timing state yet
do NOT attempt full scheduler ownership yet

Phase 1 must still produce an explicit source-of-truth decision for later phases:

- which systems should remain timestamp-authoritative
- which systems are candidates for scheduler-owned state later
- what migration criteria must be met before authoritative ownership moves
🎯 PHASE 1 GOAL

Turn timing from:

implicit, scattered, habit-based

into:

explicit, classified, observable, and controlled

✅ END STATE

At the end of Phase 1:

✔ All timing paths are inventoried
✔ Every timing path has a classification
✔ Primitive selection is documented and enforced
✔ Shared ticker usage is audited and justified
✔ One-shot expirations are no longer periodic hacks
✔ Script usage is intentional (controller vs poller)
✔ Scheduler usage is tagged and observable
✔ DireTest reports timing model behavior
✔ At least one additional timing path is safely migrated

🧭 PHASE 1 — MICROTASKS 001–020 (STRICT)
🧠 SECTION A — TIME MODEL INVENTORY
PH1-001 — Create Timing Inventory Document

Create:

docs/architecture/timing-inventory.md

List ALL timing paths:

delay usage
scheduler usage
Scripts (at_repeat)
shared ticker callbacks
manual time.time() checks
roundtime logic
regeneration
onboarding timers

Include file + function references.

✅ Done when inventory maps real code paths

PH1-002 — Classify Each Timing Path

Add column:

ONE_SHOT (delay)
SCHEDULED_EXPIRY (scheduler)
CONTROLLER (Script)
SHARED_TICKER
INVALID

✅ Done when ALL paths classified

PH1-003 — Create Timing Selection Rules

Create:

docs/architecture/timing-selection-rules.md

Define when to use:

delay
scheduler
Script
ticker

Include examples:

roundtime
wound reopen
corpse decay
onboarding prompts
regen
🔒 MUST INCLUDE:

Scheduler is NOT authoritative time source.

PH1-003A — Record Authoritative Time Decision Criteria (NEW)

In the same doc, add a short decision section defining:

- when timestamp state remains authoritative
- when scheduler ownership may be considered later
- what evidence is required before any ownership migration

✅ Done when later phases can evaluate time ownership deliberately instead of by habit

PH1-004 — Add “No Ambient Time Logic” Rule

Explicitly forbid:

polling loops
periodic scans for one-shot events
per-object ticking
hidden time checks

✅ Done when anti-patterns documented

⚙️ SECTION B — ENGINE TIMING SURFACE
PH1-005 — Create Time Model Module

Create:

world/systems/time_model.py

Add constants:

ONE_SHOT
SCHEDULED_EXPIRY
CONTROLLER
SHARED_TICKER

No logic yet.

PH1-006 — Standardize Scheduler Metadata

Phase 0 already records scheduler metadata.

Phase 1 must normalize and enforce it across all scheduler usage.

Required fields:

system name
timing mode
key
delay

✅ Done when scheduler registrations consistently carry the same metadata contract
PH1-006A — Enforce Stable Scheduler Keys (NEW — CRITICAL)

Define:

key format rules
uniqueness expectations
collision handling

Example:

combat:rt:<char_id>
status:bleed:<char_id>

✅ Done when all scheduler usage follows stable, reviewable keys

PH1-007 — Add Shared Ticker Wrapper

Wrap ticker registration:

Require:

system name
interval
reason

Disallow ad hoc registration

PH1-008 — Document Script Controller Rules

Update:

docs/architecture/time-model.md

Define when Script is valid:

persistent system state
orchestration
multi-step flows
🔒 RULE:

Do NOT use Script for simple expiry or stateless work

📊 SECTION C — AUDIT & OBSERVABILITY
PH1-009 — Unify Timing Audit Output

Phase 0 already exposes pieces of timing visibility (`get_scheduler_snapshot`, tick audit warnings).

Phase 1 must unify them into one developer-facing audit view.

Expose:

scheduled jobs
ticker registrations
Script controllers

Also include:

- scheduler source/timing_mode breakdown
- suspicious tick audit findings
- unclassified timing registrations

CLI/dev output is fine.

PH1-010 — Extend Timing Mode Metrics

Phase 0 already captures scheduler execution and command timing.

Phase 1 must add category-level timing metrics.

Track:

scheduled_event_count
ticker_count
controller_count
delay_count

✅ Done when timing usage is visible by category, not only by raw scheduler totals
PH1-011 — Add Ticker Performance Metrics

Track per ticker:

execution count
avg time
max time
PH1-012 — Extend DireTest Timing Visibility

Phase 0 already captures scheduler counts, flush usage, and lag override metadata.

Artifacts must additionally include:

timing modes exercised
scheduler job counts
ticker usage
Script activity
🔧 INCLUDE:
scheduler.flush usage
lag override metadata
job key breakdown

✅ Done when DireTest can explain timing-model behavior, not only scheduler presence
🧪 SECTION D — LOW-RISK MIGRATIONS
PH1-013 — Identify One-Shot Expiry Candidates

Find candidates:

cooldowns
temporary flags
reopen windows
simple expirations

List at least 3.

PH1-014 — Migrate ONE Safe Expiry Path

Convert:

periodic check → scheduler event
🔒 RULE:

Do NOT migrate timestamp-authoritative systems (like RT)

Do NOT move authoritative ownership; only migrate the execution path for a clearly scoped non-RT expiry.

PH1-015 — Audit Shared Ticker Responsibilities

List all ticker responsibilities.

For each:

keep
migrate
remove
🔧 ADD:
dependency on execution order
shared state reliance
PH1-016 — Extract ONE Ticker Responsibility

Move one responsibility to:

scheduler OR
delay OR
Script
🧱 SECTION E — SCRIPT HARDENING
PH1-017 — Classify Script Usage

Label each Script:

controller
poller
mixed

Examples:

bleed
corpse decay
onboarding
PH1-018 — Define Script Split Rules

Document:

when to split
when to convert to scheduler
when to keep controller
🚫 SECTION F — GUARDRAILS
PH1-019 — Add Warning for Unclassified Timing

If timing usage lacks metadata:

→ emit dev warning

This applies to:

- scheduler registrations
- shared ticker registrations
- controller/timed Script registrations where classification is expected

PH1-020 — Link Timing to DireTest Coverage

For each migration:

list scenario OR
flag missing test
⚠️ PHASE 1 SAFETY RULES
DO NOT:
convert all timing systems at once
remove timestamps
centralize everything into scheduler
rewrite combat timing
introduce quotas/backpressure
DO:
classify first
migrate ONE system at a time
verify with DireTest
keep changes reversible
🎯 FINAL ASSESSMENT

If Aedan follows this strictly:

Phase 1 will convert your engine from “timing habits” → real timing architecture

If Aedan drifts:

Phase 1 turns into unstable partial rewrites