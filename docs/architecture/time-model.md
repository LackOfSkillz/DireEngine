# Time Model

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
