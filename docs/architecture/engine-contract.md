# Engine Contract

## Layers

### Engine Layer

The Engine Layer owns time, scheduling, metrics, timing instrumentation, and execution guardrails.

Examples:

- scheduler wrappers
- timing helpers
- metrics collection
- timing audits

The Engine Layer may coordinate systems, but it does not contain gameplay policy.

### System Layer

The System Layer contains reusable gameplay logic.

Examples:

- combat state transitions
- onboarding orchestration
- death and grave flows
- justice and theft handling
- profession subsystem logic

Systems may request time from the engine, but they do not own clocks.

### Command Layer

The Command Layer is input translation only.

Commands should:

- validate user intent
- resolve targets
- call systems or character helpers
- emit user-facing messages

Commands must not become the long-term home for core gameplay rules.

### Content Layer

The Content Layer contains rooms, NPCs, items, authored data, static definitions, and area content.

Examples:

- room and NPC setup
- item definitions
- map and AreaForge content
- race and profession data tables

Content can configure behavior, but should not implement infrastructure.

## Rules

- Commands do not contain game logic.
- Systems do not run implicit loops.
- Engine owns time.
- Content does not define infrastructure policy.
- Timing and execution visibility are engine responsibilities.

## No Implicit Tick Rule

No system may run periodic logic unless it is registered through engine timing.

Forbidden patterns:

- `while True` loops for gameplay processing
- ad hoc per-object tick methods that are not explicitly registered through engine timing
- polling state every second when a keyed expiry or one-shot event would work
- silently adding new global/shared ticker work without an engine-facing registration point

Allowed patterns:

- keyed scheduled expirations
- one-shot delay-based callbacks
- controller Scripts for persistent out-of-band state
- shared ticker work only when many objects truly need the same interval and the cost is measurable

## Ownership Summary

- Engine decides how time and execution are scheduled.
- Systems decide gameplay rules and transitions.
- Commands translate player input into system calls.
- Content supplies the world and data the systems act on.
