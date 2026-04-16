# Guard Patrol Script Diagnostics 021-030

Date: 2026-04-14

Scope: Instrument the actual startup hook path and persist an execution trace so the startup lifecycle can be proven instead of inferred.

## What was added

- `server/conf/at_server_startstop.py`
  - persistent startup trace entries written to `ServerConfig` under `guard_startup_diag_trace`
  - hard markers at:
    - hook entry
    - cleanup stages
    - tick setup completion
    - bootstrap entry and fine-grained bootstrap sub-steps
    - guard sync before/after markers
    - final forced sync before/after markers
    - top-level exception capture
- `world/systems/guards.py`
  - expanded sync summary fields:
    - `started`
    - `eligible_count`
    - `ineligible_count`
    - `existing_script_count`
- `server/conf/settings.py`
  - enabled startup trace and a forced final sync probe

## Locked findings

### 1. `at_server_start()` definitely runs

This is no longer a hypothesis.

Persisted startup trace shows the hook entering and advancing through multiple stages, including:

- `entered`
- `pre_cleanup`
- `post_cleanup`
- `post_tick_setup`
- `bootstrap_entered`

So the startup hook is not missing and not misconfigured.

### 2. Guards do exist by the time sync runs in a completed startup

In the completed startup trace, the hook reached:

- `guard_bootstrap_entered`
- `bootstrap_before_sync`
- `bootstrap_after_sync`
- `final_before_sync`
- `final_after_sync`
- `finished`

The persisted sync summary for that completed startup was:

- `guard_count = 15`
- `script_attached_count = 1`
- `per_guard_owned_count = 1`
- `sync_result.started = 0`
- `sync_result.eligible_count = 1`
- `sync_result.existing_script_count = 1`

This falsifies the prediction that startup sync is missing guards because they do not exist yet.

### 3. The startup path can also stall before guard bootstrap

In the later fine-grained trace, startup advanced through:

- `bootstrap_entered`
- `bootstrap_after_character_init`
- `bootstrap_after_bleed_cleanup`
- `bootstrap_after_limbo_dummy`

and then stopped before:

- `bootstrap_after_build_landing`

That means the currently observed startup stall is inside or immediately around:

`build_the_landing(area_id=LANDING_AREA_ID)`

This is upstream of any guard-specific bootstrap or per-guard sync call.

## Exact execution truth

There are now two independently true runtime facts:

1. When startup completes and reaches the guard sync path, the hook does run sync and does see the expected guards and scripts, but the sync summary still reports `started = 0` for the existing per-guard script.
2. On later traced restarts, startup can stall before it ever reaches guard bootstrap, specifically after `bootstrap_after_limbo_dummy` and before `bootstrap_after_build_landing`.

## Current fault boundaries

Primary startup sequencing boundary:

`at_server_start() -> bootstrap -> build_the_landing(...)`

Separate per-guard lifecycle boundary on completed startups:

`startup sync reached -> existing per-guard script seen -> started count remains 0`

## Practical conclusion

The original simplified theory "startup hook never runs" is false.

The stronger supported conclusion is:

- the startup hook runs
- it can reach guard sync in at least one completed startup
- when it does, it sees the target guard and script but does not register a new start transition
- on other startup attempts, the hook stalls earlier inside `build_the_landing(...)`, preventing guard sync from running at all

That means the observed startup failure is not one single missing hook. It is a startup sequencing problem with at least one upstream bootstrap stall, plus a separate no-new-start outcome for existing per-guard scripts when sync does run.