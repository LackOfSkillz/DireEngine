# MT-514b-perf-v3 — Internal cycle profiling + conditional fixes + final verification

## Background

The MT-514b perf arc has produced three blocked dispatches. Each one
narrowed the question. v3 has the answer in reach because v2a finally
measured the production path correctly.

v2a's in-process measurements established:
- `tick_weather()` alone: 6.1-7.5s
- `get_weather_state()` alone: 6.1-7.6s
- `run_weather_cycle()` total: 40.0-66.1s

The math doesn't add up. Tick + state-read accounts for ~15s at most.
That leaves 25-50s of additional cost INSIDE `run_weather_cycle()`
that has never been profiled at the per-phase level. The fix has to
target that gap.

This dispatch profiles `run_weather_cycle()`'s internal phases in
the live server process, identifies the dominant cost, applies a
targeted fix matching the diagnosis, and validates the result. The
diagnostic and the fix are bundled — but the fix only proceeds if
the diagnosis matches one of the pre-specified patterns. If the
diagnosis reveals something unexpected, the dispatch stops and
reports.

## Architectural guardrails (READ FIRST)

Three blocked dispatches have established the pattern: when
measurements contradict the hypothesis, the agent stops and reports
rather than implementing speculative fixes. That pattern continues
here, with one refinement — the dispatch pre-specifies which
diagnoses authorize which fixes. If the diagnosis matches an
authorized pattern, the fix proceeds within the same dispatch. If
the diagnosis is something else, the dispatch stops at the diagnostic
phase and reports.

**Frozen scope:**

1. Phase A: Add internal phase timing to `run_weather_cycle()`,
   `tick_weather()`, and the broadcast helpers. Re-profile in-process.
2. Phase B: Classify the diagnosis against pre-specified patterns
   (B.1-B.4 below). The dispatch only continues if the diagnosis
   matches one of these patterns.
3. Phase C: Apply the targeted fix matching the diagnosis.
4. Phase D: Re-profile after fix. Confirm full cycle under 2 seconds
   (target) or 500ms (stretch).
5. Phase E: Regression test.
6. Phase F: Remove instrumentation.
7. Phase G: Live webclient verification — lightning broadcast and
   indoor gating, deferred from MT-514b-smoke.
8. Phase H: Validation artifact updated.

**Frozen what-not-to-do list:**

- DO NOT use the external Pylance interpreter for any timing
  measurement. v2a established that path is structurally broken for
  weather profiling. All measurements come from in-process `@py`
  against the live server.
- DO NOT modify the public weather API. Source-stable: `get_current_weather`,
  `set_current_weather`, `get_weather_state`,
  `is_weather_plausible_for_climate`, `resolve_climate`,
  `tick_weather`, `run_weather_cycle`. Internal helpers may change.
- DO NOT modify any YAML content file (transition matrices,
  climate compatibility, lightning messages, transition messages).
- DO NOT modify the calendar module, prompt module, prompt
  templates, design docs, or zone YAMLs.
- DO NOT change broadcast message format, content, or routing
  beyond what's necessary to apply the diagnosed fix.
- DO NOT change the persistent attribute storage shape on
  WeatherScript. Storage layout stays compatible across restarts.
- DO NOT add async/threading/Twisted-deferred dispatch unless the
  diagnosis specifically points at it AND it's the smallest viable
  fix. Default to synchronous patterns.
- DO NOT add a new caching library or any third-party dependency.
- DO NOT modify foraging, ranger gather, NPCs, AI pipeline,
  builder, or any consumer of weather state.
- DO NOT add new admin commands, new weather features, or new
  player-facing surfaces.
- DO NOT modify `commands/cmd_weather.py` beyond what's needed to
  surface profiling output during Phases A and D. Restore to clean
  state before final commit.
- DO NOT modify the in-progress feature scope of MT-514c.
  Foraging remains untouched.
- DO NOT "while I'm here" refactor unrelated weather internals.

**Stop-and-report conditions:**

- If Phase A profiling reveals a dominant cost that doesn't match
  any pattern in B.1-B.4, stop and report. Do not invent a fix
  for an unanticipated diagnosis.
- If Phase A shows `run_weather_cycle()` is now under 2 seconds
  (which would contradict v2a's measurement), stop and report.
  Something has changed environmentally and we want to understand
  before optimizing.
- If the targeted fix cannot be implemented without changing the
  persistent storage shape, stop and report.
- If race conditions are visible between the WeatherScript's
  `at_repeat()` and admin-issued `set_current_weather()` calls,
  stop and report.
- If the regression test reveals timing variance making bounded-
  time assertions flaky, stop and report.
- If live lightning verification fails to capture lightning in 20
  forced ticks during storm state, stop and report.
- If live indoor verification produces broadcasts in indoor rooms
  (gating broken), stop and report.

## Phase A — Internal cycle profiling

The agent adds temporary instrumentation to `world/weather.py`. The
instrumentation captures wall-clock time spent in each internal phase
of `run_weather_cycle()`. Approximate shape:

```python
import time

_phase_timings: dict[str, list[float]] = {}

def _record_phase(name: str, elapsed: float) -> None:
    _phase_timings.setdefault(name, []).append(elapsed)

def get_phase_timings() -> dict[str, list[float]]:
    return dict(_phase_timings)

def reset_phase_timings() -> None:
    _phase_timings.clear()
```

Within `run_weather_cycle()`, wrap each major phase:

```python
def run_weather_cycle():
    cycle_start = time.monotonic()

    tick_start = time.monotonic()
    transitions = tick_weather()
    _record_phase("tick_weather", time.monotonic() - tick_start)

    # If the cycle calls get_weather_state() internally:
    state_start = time.monotonic()
    # ... existing call ...
    _record_phase("get_weather_state_call", time.monotonic() - state_start)

    # Broadcast loop:
    broadcast_loop_start = time.monotonic()
    for zone_id, (old_state, new_state) in transitions.items():
        zone_broadcast_start = time.monotonic()

        rooms_start = time.monotonic()
        rooms = _rooms_for_zone(zone_id)
        _record_phase(f"rooms_for_zone:{zone_id}", time.monotonic() - rooms_start)

        filter_start = time.monotonic()
        # ... existing filtering logic ...
        _record_phase(f"filter_rooms:{zone_id}", time.monotonic() - filter_start)

        dispatch_start = time.monotonic()
        # ... existing msg_contents() calls ...
        _record_phase(f"msg_dispatch:{zone_id}", time.monotonic() - dispatch_start)

        _record_phase(f"zone_broadcast_total:{zone_id}",
                      time.monotonic() - zone_broadcast_start)

    _record_phase("broadcast_loop_total",
                  time.monotonic() - broadcast_loop_start)

    # Lightning broadcast (similar shape):
    lightning_start = time.monotonic()
    # ... existing lightning logic ...
    _record_phase("lightning_broadcast", time.monotonic() - lightning_start)

    _record_phase("cycle_total", time.monotonic() - cycle_start)

    return transitions
```

The agent adapts the exact instrumentation points to match the
actual code structure. The constraint is: every phase from cycle
start to cycle end is accounted for, and no phase spans more than
~5% of cycle time without being broken into sub-phases.

### A.1 Run the profile

The agent connects to the live server via webclient as admin
(`jekar`). All measurements use `@py`, NOT external Pylance.

Reset timings, run `run_weather_cycle()` 3 times, dump `get_phase_timings()`
between each run. Capture all output.

Format the result as a per-phase breakdown showing min/mean/max
across the three runs.

### A.2 Phase A report

The agent writes "Phase A — Internal Cycle Profiling Results" to
the validation artifact BEFORE proceeding to Phase B. The entry
must include:
- Per-phase wall-clock times (3 runs, min/mean/max per phase)
- Identification of the dominant phase (the one accounting for the
  largest share of cycle time)
- One sentence: "Dominant cost is X, accounting for Y% of cycle
  time. This matches pattern B.N below."

If the dominant phase doesn't match B.1-B.4, the agent writes:
"Dominant cost is X, which does not match any pre-specified
pattern. Stopping per dispatch instructions."

## Phase B — Diagnosis classification

The agent classifies the Phase A result against these pre-specified
patterns. Only one pattern can be matched.

### B.1 — Broadcast loop dominates

**Trigger:** `broadcast_loop_total` accounts for >40% of cycle time,
AND within the broadcast loop, `_rooms_for_zone(...)` and/or
filtering is the dominant per-zone cost.

**Diagnosis:** Each broadcast iteration re-queries rooms from the
database and re-evaluates `determine_applicable_state_groups()`
per room. Caching room lists (and their pre-filtered weather-eligible
subset) per zone is the targeted fix.

**Authorized fix:** Phase C.1 (room-list cache + filtered-subset cache).

### B.2 — Per-zone state attribute writes dominate

**Trigger:** `tick_weather` and/or per-zone state writes account for
>40% of cycle time, AND timing varies linearly with the number of
zones that transition.

**Diagnosis:** Each transition writes to the script's persistent
attribute via Evennia's ORM, which is slow. Batching writes or
deferring persistence is the targeted fix.

**Authorized fix:** Phase C.2 (in-memory state cache with
write-through persistence; batch writes if individual write cost
is the issue).

### B.3 — `get_weather_state()` called internally

**Trigger:** `get_weather_state_call` (or equivalent) inside the
cycle accounts for >30% of cycle time.

**Diagnosis:** The cycle is calling `get_weather_state()` for
inspection or logging purposes, and that call hits the same slow
attribute-read path that v2a measured at 6-7s standalone.

**Authorized fix:** Phase C.3 (eliminate the internal call, OR
implement the in-memory cache from B.2 which makes
`get_weather_state()` fast as a side effect).

### B.4 — Message dispatch dominates

**Trigger:** `msg_dispatch:*` phases account for >40% of cycle
time, AND timing scales with the number of rooms in the broadcast
target list.

**Diagnosis:** `msg_contents()` or equivalent message-routing
machinery has per-room overhead that compounds when many rooms
receive a broadcast.

**Authorized fix:** Phase C.4 (batch message dispatch where the
Evennia API allows it; presence-check rooms before dispatching to
skip empty rooms).

### B.5 — Anything else

**Trigger:** None of B.1-B.4 match.

**Action:** STOP. Do not implement a fix. Document the unanticipated
diagnosis in the validation artifact. The next dispatch (drafted
separately) will target what was found.

## Phase C — Apply targeted fix

The agent implements ONE of C.1-C.4 based on the Phase B
classification. Implementations are sketched below; the agent
adapts to the actual code structure.

### C.1 — Room-list cache (if B.1 matched)

Add a per-zone room-list cache keyed by zone_id. Invalidate on
zone import (read `world/worlddata/services/import_zone_service.py`
and identify the existing post-import hook) and on server boot
(`WeatherScript.at_start()`).

If B.1 also implicates the per-room filtering as a hot path, also
cache the pre-filtered subset of weather-eligible rooms per zone.

### C.2 — In-memory state cache (if B.2 matched)

Add `_zone_state_cache` and `_zone_meta_cache` dicts on the
WeatherScript instance. Load from persistent attributes on
`at_start()`. All reads from cache. All writes update cache AND
persist via `script.attributes.add(...)`. Same persistent storage
shape preserved.

If write cost specifically is the issue (rather than read cost),
batch the persistence: collect dirty zones during the cycle, write
them all at the end of `tick_weather()` rather than per-zone.

### C.3 — Eliminate internal `get_weather_state()` call (if B.3 matched)

Identify why the cycle calls `get_weather_state()` internally. If
it's for logging/inspection, replace with a lighter-weight inline
build-up. If it's for legitimate state retrieval, the C.2 in-memory
cache is the fix (since cached `get_weather_state()` becomes nearly
free).

### C.4 — Batch message dispatch (if B.4 matched)

Investigate Evennia's `msg_contents()` or equivalent. If the API
allows batched dispatch (sending one message to many recipients
in one call), use it. Otherwise, add a presence check before each
per-room dispatch — if the room has zero characters, skip the
broadcast for that room entirely.

## Phase D — Re-profile after fix

Run the same 3-run in-process measurement. Document per-phase
breakdown showing the improvement.

If `run_weather_cycle()` is now under 2 seconds, proceed to Phase E.

If still over 2 seconds, the targeted fix didn't fully resolve
the issue. STOP and report. Do not attempt a second targeted fix
in this dispatch — that's a follow-up.

## Phase E — Regression test

Add to `tests/test_weather.py`:

```python
def test_run_weather_cycle_completes_within_bounded_time(self):
    """run_weather_cycle must complete quickly enough for periodic use.

    The natural script tick fires every ~3.75 real minutes; if a
    cycle takes longer than the bounded threshold, the server will
    hang during the cycle, freezing all player commands. This test
    guards against regressions in cycle performance.
    """
    import time
    # Warm path: ensure caches are populated
    run_weather_cycle()
    # Measure: subsequent cycle should be fast
    start = time.monotonic()
    run_weather_cycle()
    elapsed = time.monotonic() - start
    self.assertLess(
        elapsed, 2.0,
        f"run_weather_cycle() took {elapsed:.3f}s, expected < 2.0s"
    )
```

The test runs against whatever zone state the test fixture provides.
Cold-start cache build is allowed to be slower; the warm measurement
is what matters.

## Phase F — Remove instrumentation

Remove all temporary profiling code added in Phase A. Verify via
grep that no `_phase_timings`, `_record_phase`, `time.monotonic()`,
or similar profiling artifacts remain in `world/weather.py` or
`commands/cmd_weather.py`.

The regression test from Phase E is the long-term performance
guard.

## Phase G — Live verification

Now that the system is fast, run the verifications deferred from
MT-514b-smoke. Use the same webclient transport patterns that
worked previously.

### G.1 Lightning broadcast verification

1. Connect to webclient as admin (`jekar`).
2. Teleport to outdoor weather-capable room: `@teleport #4213`.
3. Run `look` — capture room.
4. Run `@weather new_landing storm`.
5. Run `@weather tick` repeatedly. With the perf fix, ticks
   complete quickly, so 20 ticks in under a minute is feasible.
6. At 50% lightning probability per storm tick, lightning should
   appear within 2-3 attempts on average. Allow up to 20.

If the zone transitions out of storm before lightning fires,
re-set storm before the next tick. Capture the FIRST lightning
message that appears in the room feed.

If 20 attempts produce no lightning, stop and report.

### G.2 Indoor gating verification

1. Teleport to indoor room: `@teleport #4212`.
2. Run `look` — capture indoor room.
3. Run `@weather new_landing clear` then `@weather new_landing storm`.
4. Run `@weather tick` 5 times.
5. Capture verbatim output. Required:
   - Admin command echoes for each command
   - Tick summaries showing zone transitions
   - **NO transition messages** (no rain or storm narration)
   - **NO lightning messages**

If transition or lightning messages appear in the indoor room's
feed, the gating is broken. Stop and report.

## Phase H — Validation artifact

APPEND a new section to `exports/mt514b_weather_validation.md`
titled `## MT-514b-perf-v3 — Cycle profiling, targeted fix, and final verification`.

Section contents:

1. **Phase A internal profiling.** Verbatim per-phase breakdown
   from 3 runs. Min/mean/max per phase.
2. **Phase B classification.** Which pattern matched. Why.
3. **Phase C fix.** What was added/changed, why it targets the
   diagnosed pattern.
4. **Phase D post-fix profiling.** Same per-phase breakdown,
   showing the improvement.
5. **Phase E regression test.** Test name and threshold.
6. **Phase F confirmation.** No profiling code left in tree.
7. **Phase G.1 lightning evidence.** Verbatim webclient output.
8. **Phase G.2 indoor gating evidence.** Verbatim webclient output.
9. **Final state.** One sentence: "MT-514b is now fully closed."

If any phase blocked, the section ends with the BLOCKED status
and the specific reason.

## Verification checklist

1. Phase A produces per-phase profile data.
2. Phase B classifies the diagnosis against pre-specified patterns,
   OR stops if the diagnosis is unanticipated.
3. If diagnosis matched, Phase C applies ONLY the authorized fix
   for that diagnosis. No scope expansion.
4. Phase D confirms post-fix cycle under 2 seconds.
5. Phase E regression test added and passes.
6. All previously-passing tests still pass.
7. Phase F confirms no profiling code left in the tree.
8. Phase G.1 lightning message captured live.
9. Phase G.2 indoor room receives no broadcasts.
10. Validation artifact appended with full evidence.
11. No code outside the in-scope list modified.

## Stop conditions

- Edit only `world/weather.py`, `tests/test_weather.py`, the
  validation artifact, and (only if Phase C.1 cache invalidation
  requires it) `world/worlddata/services/import_zone_service.py`
  or similar zone-import hooks. No other files.
- Stop and report on any unexpected Phase A diagnosis.
- Stop and report if Phase D shows the fix didn't work.
- Stop and report on race conditions, persistent storage shape
  changes, lightning failure, indoor gating failure.
- Do not attempt multiple targeted fixes in the same dispatch.
  One diagnosis → one fix → measure → ship or stop.

## Required artifacts

1. Updated `world/weather.py` (targeted fix, instrumentation removed)
2. Updated `tests/test_weather.py` (regression test added)
3. Possibly updated zone-import service (one-line cache invalidation
   call) — only if C.1 is the chosen fix
4. Updated `exports/mt514b_weather_validation.md` (new section
   appended)

## Followup queue

- MT-514b-invasion: Add `current_invasion` runtime state with
  `@invasion` admin command. Same persistence pattern as weather.
  Apply both the ScriptDB fallback (from v2a) and whatever caching
  pattern v3 establishes from day one. Invasion code does NOT need
  to repeat the perf-debugging arc.
- MT-514c: Foraging refactor consuming terrain + skill rank +
  calendar + weather + invasion. Now safe to build on a perf-tuned
  weather foundation.
- Future architectural note: any system using Evennia persistent
  attributes for frequently-read state should follow the patterns
  established here. Consider documenting in
  `docs/architecture/runtime_state_patterns.md` after v3 ships.