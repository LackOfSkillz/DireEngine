# Guard Patrol Script Diagnostics 011-020

Date: 2026-04-14

Scope: Probe the execution lifecycle boundary after the locked 001-010 finding that the per-guard script row exists but never fires.

## What was tested

1. Read Evennia's script lifecycle implementation from the installed runtime.
2. Added `at_start()` evidence to `GuardBehaviorScript`.
3. Added an explicit `script.start()` ensure step when an existing per-guard script row is reused.
4. Restarted the server and inspected persisted start/repeat counters.
5. Invoked `sync_all_guard_behavior_scripts()` manually to test whether the patched ensure path can actually transition the script into the started state.

## Locked findings

### 1. Fresh-script creation already autostarts in Evennia

The hypothesis "new script rows are created but never started because `create_script(...)` does not autostart" is falsified.

Evidence from Evennia runtime source:

- `evennia.utils.create.create_script(...)` documents `autostart=True` by default.
- `ScriptHandler.add(...)` explicitly creates scripts with `autostart=False` and then calls `script.start()` itself.
- `DefaultScript.start()` runs `_start_task(...)`, which starts the repeat task and then calls `at_start(...)`.

This means the missing step is not the original creation path for a brand-new script.

### 2. Automatic live server start still did not start the target per-guard script

After a clean server start, the observed target script still showed:

- `start_count = 0`
- `last_started_at = 0.0`
- `repeat_fire_count = 0`
- `last_repeat_at = 0.0`

That means the live server process did not call `GuardBehaviorScript.at_start()` for the target script during the observed start path.

### 3. Manual sync can start the script row

Calling `sync_all_guard_behavior_scripts()` directly caused the same target script to show:

- `start_count = 1`
- `last_started_message = "GuardBehaviorScript STARTED for guard 24568"`

This proves the patched ensure path can transition the existing persistent script row into the started state.

### 4. The exact missing lifecycle step is narrower now

Current lifecycle state for the target per-guard script:

- created: yes
- attached: yes
- singular: yes
- started automatically during observed live server startup: no evidence
- manually startable through explicit sync: yes
- repeating in the observed live server process: still not proven

## Interpretation

The failure boundary is now:

`live server startup/restart path -> explicit start/re-registration of existing per-guard script rows`

This is narrower than the earlier broad guess of "script start is missing everywhere".

## Important caveat

Calling `script.start()` from a standalone diagnostic Python process is not equivalent to observing the server reactor-driven repeat loop. It can prove that `at_start()` runs and that the start transition happens, but it does not by itself prove that the server's live repeat cycle is running.

## Practical conclusion

The strongest supported statement after 011-020 is:

The per-guard script row is valid and startable, but the observed live server startup path did not transition it into the started state. The remaining runtime fault is in the automatic server-process lifecycle path that should re-start or re-register existing per-guard scripts.