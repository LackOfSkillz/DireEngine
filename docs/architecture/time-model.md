# Time Model

Related architecture:

- see `docs/architecture/interest-model.md` for the Phase 1.5 activation layer that decides whether continuous behavior should run at all

## Timing Primitives

### Delay

Use `delay` for one-shot work that does not need key-based replacement.

Examples:

- short-lived message follow-ups
- one-time deferred cleanup

### Scheduled Event

Use explicit scheduling for keyed expirations, retries, and replaceable one-shot work.

Examples:

- combat roundtime expiry
- temporary cooldown expiry
- wound reopen expiry

Required scheduler API:

- `schedule(delay, callback, key=None)`
- `cancel(key)`
- `reschedule(key, delay)`

Contract:

- Keys are unique within the scheduler registry.
- Scheduling the same key replaces the existing job.
- `cancel(key)` is silent when the key is missing.
- `reschedule(key, delay)` cancels the existing job and reuses the stored callback contract.
- Callbacks must tolerate stale state and deleted objects.

### Shared Ticker

Use a shared ticker only when many objects truly need the same interval and the work cannot be expressed as isolated expirations.

Examples:

- coarse-grained weather or regional ambient updates
- grouped XP or learning pulses when the grouping is justified and measurable

Shared ticker is a rare tool, not the default timing answer.

### Global Tick

Global tick is last resort only.

It should be used only when no lighter timing primitive can express the behavior and when the work is explicitly measured, gated, and justified.

## Use Cases

### Combat RT

Preferred model:

- scheduled event keyed to the actor

Why:

- it is a replaceable expiry, not a periodic system

Phase 0 implementation note:

- `roundtime_end` on the character remains the live state check in Phase 0
- the scheduler currently acts as keyed expiry enforcement and DireTest-safe execution plumbing
- scheduler ownership of roundtime state is deferred to Phase 1 so Phase 0 can harden the contract without rewriting the entire time model

### XP Pulse

Preferred model:

- shared ticker only if many actors legitimately share the same cadence
- otherwise move toward scheduled or state-driven updates

### Weather

Preferred model:

- coarse shared ticker or controller Script

Why:

- weather is world-level ambient state, not a per-object loop

## Controller Script Guidance

Use a persistent Script controller when the system needs long-lived out-of-band orchestration or state.

Good fits:

- multi-step onboarding orchestration
- persistent world controllers
- long-lived ambient or scenario state

Poor fits:

- one-shot expirations
- simple keyed unlocks
- repeated polling that should be event-driven

## Script Split Rules

Script behavior should be reviewed using the PH1-017 categories:

- `controller`: keep as a Script when the repeat loop is genuinely orchestrating long-lived state, multi-step flow, or actor coordination
- `poller`: convert away from Script when the repeat loop exists mainly to notice that a timestamp elapsed or to perform stateless one-shot cleanup
- `mixed`: split the responsibilities so orchestration stays in the Script and isolated expiry boundaries move to scheduler-backed events or simpler one-shot timing

When to keep a Script whole:

- the script owns persistent scenario or world-controller state
- the timing checks are part of a stage machine rather than hidden cleanup
- multiple actors or rooms are coordinated by one long-lived controller

When to split a Script:

- the script both orchestrates state and polls one-shot deadlines
- warning, deletion, expiry, or reminder boundaries are independent from the core controller loop
- parts of the logic can be expressed as keyed scheduler events without changing authoritative ownership

When to convert a Script responsibility to scheduler-backed expiry:

- the behavior is a single boundary such as expiry, warning, unlock, fade, or retry
- the deadline is derivable from durable gameplay state
- the callback can tolerate stale state and no longer needs ambient polling

When to keep controller logic in Script after a split:

- the remaining work still coordinates multi-step flow or persistent actor state
- the script maintains durable caches or orchestration state between repeats
- removing the Script would force unrelated timing behavior back into a shared ticker or hidden polls

Phase 1 examples:

- `OnboardingInvasionScript`: keep as a controller because its interval drives a stage machine
- `CorpseDecayScript`: split one-shot discovery such as memory-loss boundaries away from the controller/reload logic
- `GraveMaintenanceScript`: keep recurring grave wear in a controller only if needed, but split warning/deletion boundaries to explicit expiry where practical
- `OnboardingRoleplayScript`: keep onboarding coordination in the controller, but isolated idle reminders and prompt deadlines are split candidates

Reference audit:

- see `docs/architecture/script-usage-audit.md` for the live controller/poller/mixed classification used by these rules

## Anti-Patterns

Do not use:

- periodic scans for one-shot expirations
- per-object timing loops when keyed scheduling fits better
- new shared ticker work without a written reason
- hidden timing behavior embedded in unrelated gameplay methods

## DireTest Notes

In DireTest mode, scheduled work should be exercised through engine-facing helpers instead of direct callback invocation.

Use:

- `world.systems.scheduler.flush_due()` to run deferred due jobs during deterministic scenario validation

This keeps timing validation inside the scheduler surface even while Phase 0 still uses wall-clock state like `roundtime_end` as the immediate gameplay check.
