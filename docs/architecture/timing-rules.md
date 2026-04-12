# Timing Rules

This document is the Stage 7 scheduler normalization rule set.

## Core Rule

- timed execution must go through `world.systems.scheduler.schedule_event()` / `cancel_event()`
- raw `delay(...)` calls are not allowed outside `world/systems/scheduler.py`
- services and typeclasses may request timing, but they do not own alternate timer implementations

## Required Event Shape

Every scheduled event must include:

- `key`
- `owner`
- `callback`
- metadata with:
  - `system`
  - `type`

## Authority Rule

- scheduler owns timed execution and cancellation
- object timestamps may remain authoritative when gameplay directly reads remaining time
- callbacks must re-check current state before mutating it

## Stable Key Rule

- one logical timed event per owner should reuse one logical key
- rescheduling the same event should replace the previous schedule rather than stack duplicate jobs
- examples:
  - `roundtime_end`
  - `cleric_ritual`
  - `pending_scene`
  - `skill_pulse`

## Callback Rule

- prefer named scheduler callbacks for shared engine behaviors
- callable callbacks are acceptable for localized delayed effects when wrapped by `schedule_event()`
- callbacks must tolerate stale or deleted owners safely

## No-Ad-Hoc Timing Rule

- do not introduce new direct `delay(...)` calls outside the scheduler internals
- do not add uncancelable one-shot timers for persistent gameplay state
- do not add new shared ticker usage when the scheduler can express the same behavior safely

## Validation Rule

- timing changes must be validated with a behavior-scoped check first
- when available, use scheduler snapshot or flush-based DireTest coverage to confirm events queue, execute once, and clear cleanly