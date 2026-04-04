# Timing Selection Rules

This document defines Phase 1 timing primitive selection, anti-patterns, authoritative time rules, and stable scheduler key rules.

Phase 1 constraints:

- scheduler execution is not authoritative time ownership
- timestamp state remains authoritative where live gameplay already reads it directly
- migration in Phase 1 may change execution plumbing for low-risk one-shot expiry paths, not authoritative ownership

## Primitive Selection Order

Before adding or changing timing behavior, decide in this order:

1. Identify the authoritative state.
2. Decide whether the work is one-shot expiry, persistent orchestration, or a truly shared cadence.
3. Choose the lightest primitive that expresses that behavior.
4. Add metadata and, when using the scheduler, a stable key.
5. Ensure the callback can tolerate stale state and object deletion.

## Primitive Rules

### `ONE_SHOT` (`delay`)

Use direct delay only when all of the following are true:

- the work is a single deferred callback
- replacement/cancellation by logical identity is not needed
- persistence across reload is not required
- no timing audit beyond local behavior is needed

Good fits:

- short message follow-up
- protocol handshake timeout
- local deferred cleanup

Do not use `delay` for:

- replaceable expiry paths
- persistent world state
- any deadline that needs stable naming, replacement, or audit visibility

### `SCHEDULED_EXPIRY` (scheduler)

Use the scheduler when all of the following are true:

- the behavior is a one-shot expiry, warning, retry, or deadline
- the work needs a stable logical identity
- replacement, cancellation, or rescheduling is expected
- developer visibility or deterministic DireTest execution matters

Good fits:

- roundtime expiry enforcement
- corpse decay transition
- grave warning and grave deletion boundary
- plea deadline resolution
- wound reopen or similar one-shot recovery boundary

Required constraints:

- scheduler callback is execution plumbing, not authoritative ownership, unless a later phase explicitly changes that contract
- callbacks must re-check authoritative state before mutating anything
- every scheduled event must carry consistent metadata and a stable key

### `CONTROLLER` (Script)

Use a Script controller when the system needs at least one of the following:

- persistent orchestration across server lifetime
- multi-step scenario flow or stage progression
- long-lived controller state that is larger than one expiry callback
- a world or tutorial controller that owns coordination logic

Good fits:

- onboarding invasion stage orchestration
- onboarding roleplay controller behavior
- future world-level scenario controllers

Do not use Script for:

- simple one-shot expiry
- pure polling that exists only to discover a single elapsed timestamp
- stateless work that can be expressed as scheduler events

### `SHARED_TICKER`

Use a shared ticker only when all of the following are true:

- many actors truly share the same cadence
- the work is naturally grouped rather than many isolated deadlines
- the grouping is measurable and justified in writing
- dependency risk is understood well enough that extraction work can be planned

Good fits:

- grouped learning pulse when many actors legitimately share the cadence
- rare ambient world updates that cannot be expressed as isolated expiries

Do not use a shared ticker for:

- one-shot expirations
- hidden cleanup paths
- per-object work disguised as a global loop
- new timing behavior without a written reason and observability

## Selection Examples

### Roundtime

- authoritative state: `db.roundtime_end`
- primitive: `SCHEDULED_EXPIRY`
- Phase 1 rule: keep timestamp authority and scheduler enforcement together; do not migrate authority

### Wound Reopen

- authoritative state: wound or tend window timestamp on the character/body part
- preferred primitive: `SCHEDULED_EXPIRY`
- rule: schedule the reopen boundary if it is a one-shot event; do not leave it buried in a scan loop

### Corpse Decay

- authoritative state: `corpse.db.decay_time`
- preferred primitive: `SCHEDULED_EXPIRY`
- rule: the timestamp may remain authoritative while the decay transition moves from poller logic to explicit expiry execution

### Onboarding Prompts

- authoritative state: onboarding progression state and prompt cadence timestamps
- preferred primitive: `CONTROLLER` for scenario flow, `SCHEDULED_EXPIRY` or `ONE_SHOT` for isolated nudges when split out
- rule: keep orchestration in a controller, but do not hide one-shot reminder deadlines inside ambient polling when a separate expiry fits better

### Regen And Learning Pulses

- authoritative state: per-character resources or learning state
- preferred primitive: `SHARED_TICKER` only when the shared cadence remains justified and measured
- rule: if a regen-like behavior becomes a set of isolated deadlines, it should stop living in a ticker

## No Ambient Time Logic Rule

Do not introduce or preserve these patterns without an explicit exception:

- periodic scans for one-shot events
- per-object polling loops
- hidden time checks embedded in unrelated gameplay methods
- controller Scripts used only to notice that a single timestamp elapsed
- new shared ticker work without declared responsibility and dependency risk

If a behavior is fundamentally a single expiry boundary, it should not depend on ambient polling.

## Authoritative Time Decision Criteria

### Keep Timestamp State Authoritative When

- gameplay reads remaining time directly from object state
- multiple call sites need immediate time-left answers without waiting for a callback
- the state must survive missed callbacks or server timing drift gracefully
- the current model already works as hybrid timestamp authority plus execution callback

### Scheduler Ownership May Be Considered Later When

- there is exactly one clear logical owner of the timing state
- direct gameplay reads no longer depend on a stored timestamp
- missed callback recovery and stale-event safety are proven
- deterministic tests cover expiry, replacement, cancellation, and reload behavior

### Evidence Required Before Ownership Migration

- inventory classification exists for the path
- primitive choice is documented and justified
- stable scheduler key format is defined and implemented
- audit and metrics can show the path clearly
- DireTest or equivalent deterministic coverage exists
- rollback path is obvious and low risk

## Stable Scheduler Key Rules

Stable keys are required for scheduler-backed work that can be replaced, cancelled, audited, or reviewed.

### Canonical Format

Use colon-delimited keys in this shape:

`domain:event:subject[:qualifier]`

Rules:

- use lowercase ASCII segments
- make segments human-readable and reviewable
- use stable persisted identifiers such as db ids or durable names
- add a qualifier only when multiple concurrent jobs for the same subject are legitimate

Examples:

- `combat:roundtime:123`
- `status:wound-reopen:123:left-arm`
- `crime:plea-deadline:123`
- `world:grave-expiry:456`
- `tutorial:invasion-stage:789:intro`

### Uniqueness Expectations

- one key represents one logical event
- rescheduling the same logical event must reuse the same key
- different systems must not share keys accidentally
- keys must be derivable from the owning gameplay state, not from callback instance identity

### Collision Handling

- same logical event colliding with itself is expected replacement
- different logical events colliding is a bug and should produce a developer warning once PH1-019 is implemented
- if multiple simultaneous jobs are valid, add an explicit qualifier rather than weakening the namespace

### Disallowed Key Inputs

Do not build stable scheduler keys from:

- `id(self)` or other process-local memory identity
- object `repr()` output
- wall-clock timestamps used as uniqueness padding
- anonymous counters with no gameplay meaning

### Legacy Compatibility

Existing shipped paths may still use older key shapes during Phase 1.

Current known example:

- `character.roundtime.<id>` in `typeclasses/characters.py`

Phase 1 rule:

- do not bulk-rename existing keys during inventory and rules work
- any path touched for real scheduler standardization or migration should move to the canonical stable-key format at that time

## Review Boundary

This document defines selection and key policy only.

It does not itself migrate timing paths or change authoritative ownership.