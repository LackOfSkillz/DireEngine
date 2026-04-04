Phase 2 — What it REALLY is

From your blueprint:


Scheduler and quota hardening

But in your current engine context, this becomes:

🎯 Phase 2 Goal (refined)

Turn the scheduler from “works” into safe, bounded, and enforceable infrastructure

Right now your scheduler:

exists
works
is integrated

But it is not yet protected

Phase 2 ensures:

no system can overload it
no runaway scheduling
no silent queue growth
no invisible lag sources
⚠️ Why Phase 2 matters now

Because after Phase 1.5:

You are actively reducing what runs

Now Phase 2 controls:

how much can run at once

Without this, you can still get:

scheduler floods
burst lag
cascading events
hard-to-debug performance spikes
🧭 Core Concept of Phase 2

This is straight from classic MUD lessons:

Queued work must be bounded

Not optional. Mandatory.

🔥 What Phase 2 introduces

Four major controls:

1. Deduplication (you partially have this)

Prevent:

duplicate jobs
accidental reschedules
2. Ownership

Every scheduled job must belong to:

a system
or an object
3. Quotas

Limit:

jobs per object
jobs per system
total queue size
4. Backpressure

When limits hit:

reject
delay
replace

But NEVER silently accept

🧠 Phase 2 Philosophy

Phase 1 = correctness
Phase 1.5 = scope
Phase 2 = safety under load

🟨 PHASE 2 — MICROTASKS (LOCKED)
STATUS UPDATE

- COMPLETE: PH2-001 require ownership on schedule
- COMPLETE: PH2-002 normalize scheduler metadata
- COMPLETE: PH2-003 enforce key uniqueness
- COMPLETE: PH2-004 define quota policy
- COMPLETE: PH2-005 implement per-owner quota
- COMPLETE: PH2-006 implement per-system quota
- COMPLETE: PH2-007 implement global queue limit
- COMPLETE: PH2-008 add quota enforcement behavior
- COMPLETE: PH2-009 add rejection logging
- COMPLETE: PH2-010 add replacement strategy
- COMPLETE: PH2-011 add optional delay queue
- COMPLETE: PH2-012 track queue depth
- COMPLETE: PH2-013 track jobs by system
- COMPLETE: PH2-014 track rejections
- COMPLETE: PH2-015 add scheduler snapshot
- COMPLETE: PH2-016 add scheduler stress scenario
- COMPLETE: PH2-017 add duplicate job scenario
- COMPLETE: PH2-018 add quota violation scenario
- COMPLETE: PH2-019 add queue stability scenario
- COMPLETE: PH2-020 compare metrics

🧠 SECTION A — SCHEDULER CONTRACT HARDENING
PH2-001 — Require Ownership on Schedule [DONE]

Update scheduler API:

schedule(delay, callback, key=None, owner=None, system=None)

Rules:

owner OR system must be present
reject if neither
PH2-002 — Normalize Scheduler Metadata [DONE]

Every job must include:

{
  "key": "...",
  "owner": "...",
  "system": "...",
  "delay": ...,
  "created_at": ...
}
PH2-003 — Enforce Key Uniqueness [DONE]

If key exists:

replace OR reject (configurable)

NO duplicate silent jobs

⚙️ SECTION B — QUOTA SYSTEM
PH2-004 — Define Quota Policy [DONE]

Create:

docs/architecture/scheduler-quotas.md

Define:

max jobs per object
max jobs per system
global max queue size
PH2-005 — Implement Per-Owner Quota [DONE]

Example:

MAX_JOBS_PER_OBJECT = 5

Reject or replace if exceeded

PH2-006 — Implement Per-System Quota [DONE]

Example:

MAX_JOBS_PER_SYSTEM = 100
PH2-007 — Implement Global Queue Limit [DONE]

Example:

MAX_TOTAL_JOBS = 1000
PH2-008 — Add Quota Enforcement Behavior [DONE]

When exceeded:

Choose behavior:

reject
replace oldest
delay scheduling

Must be explicit

🔁 SECTION C — BACKPRESSURE
PH2-009 — Add Rejection Logging [DONE]

Log:

[Scheduler] REJECTED job (system=combat, reason=quota)
PH2-010 — Add Replacement Strategy [DONE]

Allow:

replace existing job with same key
or oldest job for owner
PH2-011 — Add Optional Delay Queue [DONE]

If rejecting is too harsh:

queue for later execution

(optional, can defer)

📊 SECTION D — OBSERVABILITY
PH2-012 — Track Queue Depth [DONE]

Metrics:

current jobs
peak jobs
PH2-013 — Track Jobs by System [DONE]

Metrics:

{
  "combat": 12,
  "death": 4,
  "npc_ai": 50
}
PH2-014 — Track Rejections [DONE]

Metrics:

total rejected jobs
rejection reasons
PH2-015 — Add Scheduler Snapshot [DONE]

Expose:

{
  "total_jobs": ...,
  "by_system": ...,
  "by_owner": ...
}
🧪 SECTION E — DIRETEST HARDENING
PH2-016 — Add Scheduler Stress Scenario [DONE]

Test:

many jobs scheduled
verify no crash
verify quotas enforced
PH2-017 — Add Duplicate Job Scenario [DONE]

Test:

same key scheduled repeatedly
ensure dedup works
PH2-018 — Add Quota Violation Scenario [DONE]

Test:

exceed limits
verify rejection behavior
PH2-019 — Add Queue Stability Scenario [DONE]

Test:

long-running scheduling
ensure no growth leak
PH2-020 — Compare Metrics [DONE]

Ensure:

queue bounded
no runaway growth
⚠️ HARD GUARDRAILS
❌ DO NOT
allow unlimited scheduling
silently drop jobs
hide quota violations
mix quota logic into gameplay systems
✅ DO
enforce at scheduler level ONLY
log everything
keep behavior predictable
validate with DireTest
🎯 END STATE OF PHASE 2

After this phase:

✔ Scheduler is bounded
✔ No system can overload engine
✔ Queue size is controlled
✔ Scheduling is observable
✔ Failures are visible, not silent
✔ DireTest proves stability under load