# DireTest Timing Coverage

This document satisfies PH1-020 by linking Phase 1 timing migrations and timing-hardening surfaces to concrete DireTest scenarios, or explicitly flagging where coverage is still missing.

Coverage status meanings:

- `covered`: a named DireTest scenario directly validates the timing behavior
- `partial`: DireTest exercises the area indirectly, but not with a dedicated timing assertion set
- `gap`: no current DireTest scenario directly proves the behavior

Phase 1 reminder:

- coverage here refers to execution-path validation, not authoritative ownership migration
- a scenario may validate scheduler metadata, expiry execution, artifact output, or structural timing behavior without asserting low-latency performance

## Coverage Matrix

| Phase 1 Area | Timing Surface | Status | DireTest Scenario | Notes |
| --- | --- | --- | --- | --- |
| Phase 0/1 hybrid roundtime model | keyed scheduler expiry with timestamp authority | `covered` | `rt-timing` | Validates roundtime application, scheduler registration, blocked action during RT, `flush_due()` expiry, and unblocked action after expiry. |
| Scheduler metadata normalization | scheduler `system`, `timing_mode`, stable `key` visibility | `covered` | `rt-timing`, `grave-recovery`, `trap-expiry` | All three structural scenarios assert scheduler registration and emit metrics/artifacts with system and key breakdown. |
| DireTest timing artifact enrichment | scheduler counts, job key breakdown, timing audit payload, lag-policy metadata | `covered` | `rt-timing`, `grave-recovery`, `trap-expiry` | Structural timing scenarios emit `metrics.json` and `timing_audit.json`, exercising the enriched artifact surface. |
| Corpse decay migration | corpse-to-grave transition moved from poll discovery to scheduler expiry | `covered` | `grave-recovery` | Verifies corpse creation, keyed decay registration, `flush_due()`-driven grave transition, and recovery flow after decay. |
| Trap expiry migration | trap expiration moved from status ticker sweep to scheduler expiry | `covered` | `trap-expiry` | Verifies deploy path, keyed trap expiry registration, `flush_due()`-driven deletion, and snapshot diff for trap removal. |
| Shared ticker observability | ticker registration visibility in timing audit | `covered` | `ticker-execution` | Dedicated scenario asserts ticker registration metadata and produces timing-audit output with live ticker registration and performance data. |
| Ticker performance metrics | per-ticker execution count, avg ms, max ms | `covered` | `ticker-execution` | Forces a real `process_learning_tick` execution and verifies non-empty per-ticker performance in DireTest metrics and timing-audit artifacts. |
| Shared learning ticker behavior | `process_learning_tick()` cadence and activity | `partial` | `ticker-execution` | The scenario proves learning-ticker execution and registration structurally, but it does not yet validate a full session-driven learner iteration path. |
| Status ticker responsibility audit | kept vs migrated status-tick responsibilities | `partial` | `trap-expiry` | Trap expiry extraction is covered, but justice, thief, warrior-expiry, AI polling, and magic-expiry cleanup do not yet have dedicated extraction scenarios. |
| Script classification visibility | controller/poller/mixed surfaced through timing audit | `partial` | `onboarding_full`, `onboarding_lag`, structural timing scenarios | The timing audit can now render script classifications, but there is no dedicated scenario that asserts the classification payload in artifacts. |
| Onboarding controller scripts | persistent controller behavior for onboarding roleplay/invasion | `partial` | `onboarding_full`, `onboarding_lag`, `onboarding_no_armor`, `onboarding_no_attack`, `onboarding_no_heal` | Onboarding scenarios exercise the scripts in practice, but they are not targeted timing-architecture scenarios and do not assert controller-vs-poller rules. |
| Script split-rule candidates | corpse memory fade, grave warning/deletion, onboarding reminder deadlines | `gap` | none | These are now documented split candidates, but no dedicated DireTest coverage exists because the split work has not happened yet. |
| Unclassified timing warnings | dev warnings for missing scheduler/ticker/script classification metadata | `gap` | none | The warning paths were validated by direct runtime invocation, not by a named DireTest scenario. |

## Scenario Index

### `rt-timing`

- purpose: structural validation of the hybrid roundtime model
- validates:
  - scheduler registration for roundtime expiry
  - `flush_due()` execution path
  - timestamp-authoritative gameplay blocking before expiry
  - artifact timing-model visibility

### `grave-recovery`

- purpose: structural validation of scheduler-backed corpse decay
- validates:
  - corpse decay scheduler metadata
  - grave creation through scheduler expiry
  - grave recovery follow-up behavior
  - artifact timing-model visibility

### `trap-expiry`

- purpose: structural validation of scheduler-backed trap expiry
- validates:
  - trap deployment registration under `world.trap_expiry`
  - keyed scheduler expiry behavior
  - trap deletion through `flush_due()`
  - artifact timing-model visibility

### `ticker-execution`

- purpose: structural validation of real shared-ticker execution and ticker observability output
- validates:
  - `process_learning_tick` runtime execution
  - non-empty per-ticker performance metrics in `metrics.json`
  - ticker registration visibility in `timing_audit.json`
  - learning ticker metadata under `global_learning_tick`

### Onboarding scenarios

- `onboarding_full`
- `onboarding_lag`
- `onboarding_no_armor`
- `onboarding_no_attack`
- `onboarding_no_heal`

These scenarios exercise onboarding controllers in practice, but they are currently functional/tutorial-flow coverage rather than dedicated timing-model scenarios.

## Remaining Gaps

Highest-value uncovered timing-model scenarios:

- a learning-ticker scenario that proves `process_learning_tick()` registration and pulse behavior structurally
- a timing-warning scenario that asserts dev-warning surfaces for intentionally missing metadata in a controlled way
- future extraction scenarios for justice timers, thief timed states, warrior expiry cleanup, NPC AI polling, or magic-expiry cleanup if any of those migrate in later phases

## Phase 1 Outcome

PH1-020 conclusion:

- completed timing migrations are linked to concrete structural DireTest scenarios
- timing observability surfaces are partially covered through those scenarios' artifacts
- remaining untested timing architecture concerns are now explicit and reviewable instead of implicit