# Guard Patrol Script Diagnostics 001-010

Date: 2026-04-14

Scope: Diagnose one `GuardBehaviorScript` owner in hybrid mode without changing the patrol architecture.

## Instrumentation added

- `typeclasses/scripts.py`
  - `GuardBehaviorScript.at_repeat()` now records persistent DB-backed counters and last-fire metadata on the script object.
  - For the diagnostic target guard, it also writes a proof string of the form `GuardBehaviorScript fired for guard X`.
- `world/systems/guards.py`
  - Added targeted helper functions to select one diagnostic guard, persist per-guard diagnostic state, and count behavior and movement events.
  - Added a diagnostic-only force-move override path for the selected guard so decision-vs-execution can be separated if the script fires.
- `server/conf/settings.py`
  - Enabled the targeted diagnostic path.
  - Left the target guard id at `0`, which means "pick the first per-guard-owned guard".

## Target observed

- Guard id: `24568`
- Guard key: `Town Guard`
- Script id: `1632`
- Script key: `guard_behavior`

## Verified state

- Exactly one `GuardBehaviorScript` is attached to the target guard.
- The script reports `is_active = true` and `persistent = true`.
- The actual interval on the live script is `22.0s`.
- The script jitter state is:
  - base interval: `25.0s`
  - jitter: `-2.6984593701805393s`
- Diagnostic force-move was enabled for the target guard, but only as a contingent probe if `at_repeat()` fired.

## 60-second observation

Before:

- `repeat_fire_count = 0`
- `last_repeat_at = 0.0`
- `last_behavior_result = ""`
- guard diagnostic state: empty

After 60 seconds:

- `repeat_fire_count = 0`
- `last_repeat_at = 0.0`
- `last_behavior_result = ""`
- guard diagnostic state: still empty

Deltas over the full 60-second window:

- `repeat_fire_count = 0`
- `behavior_call_count = 0`
- `movement_attempt_count = 0`
- `movement_success_count = 0`
- `movement_skipped_count = 0`

## Findings

1. `GuardBehaviorScript.at_repeat()` did not execute even once during the 60-second observation window.
2. Because `at_repeat()` never ran, `process_guard_behavior_tick()` was never called.
3. Because behavior never ran, no movement attempt was made, so movement logic was not the limiting factor in this specific diagnostic slice.
4. The configured interval is not too long. A `22.0s` interval should have yielded roughly 2-3 firings over 60 seconds.
5. Duplicate-script suppression does not appear to be the issue for the observed guard. There is exactly one active script row attached.

## Current fault boundary

For this hybrid per-guard guard, the failure boundary is upstream of behavior and movement:

`scheduler / script execution -> at_repeat()`

The diagnostic force-move path was never reached, so it cannot yet be used to judge movement logic under autonomous per-guard scheduling.

## Practical conclusion

The strongest current evidence supports this statement:

`GuardBehaviorScript` ownership exists in the database, but the live repeating callback is not firing reliably in runtime.

That keeps the primary defect in the scheduler/script-execution layer, not in Builder export and not in the per-guard patrol decision code.