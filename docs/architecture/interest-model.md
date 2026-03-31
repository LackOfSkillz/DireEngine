# Interest / Activation Model

## Purpose

The activation layer decides whether continuous behavior is allowed to run.

It exists to stop treating the whole world as equally active all the time. Phase 1.5 introduces a centralized engine-owned service that answers whether an object is currently active based on live interest sources.

## Separation Of Concerns

- Activation decides if behavior should run at all.
- Scheduler decides when a keyed callback executes.
- Timestamps remain the authoritative gameplay truth.
- On-demand recovery repairs stale state after inactivity or restart when needed.

Activation does not replace persistence, object lifetime, or authoritative state.

## Activation Sources

The locked source types for Phase 1.5 are:

- `room`: a player or other live focal point is in the same room as the object
- `proximity`: the object is near an active focal point, initially within one room hop
- `zone`: a zone-level controller or region marks the object as relevant
- `direct`: the object is explicitly targeted by combat, spell, tracking, or another direct reference
- `scheduled`: the object must remain eligible for keyed scheduler work

The central service records concrete sources under one of these types. Objects become active when they have one or more interest sources.

## Inactive Expectations

When the system is enabled and an object is inactive:

- continuous polling and ticker-style work should not run for that object
- one-shot authoritative timestamps remain valid
- keyed scheduled events may reactivate the object through `scheduled` interest
- recovery logic may still recompute state on demand when the object is observed again

Inactive does not mean unloaded, deleted, or forgotten.

## Runtime Toggle Contract

- `interest_activation` OFF preserves current behavior
- `interest_activation` ON enables activation-aware decisions
- the toggle must work without restart
- debug surfaces must explain why an object is active

## Initial Service Contract

Phase 1.5 starts with a centralized service in `world/systems/interest.py`.

Core API:

- `add_interest(obj, source, interest_type)`
- `remove_interest(obj, source)`
- `is_active(obj)`
- `get_activation_sources(obj)`

Optional hooks:

- `on_activate()` when an object transitions from zero sources to at least one source
- `on_deactivate()` when the last source is removed

These hooks are optional and must remain side-effect-light. They are not a replacement for authoritative state repair.