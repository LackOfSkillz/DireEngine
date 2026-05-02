# MT-514b-perf-v3a — Ship the broadcast-loop fix with flexible verification

## Background

MT-514b-perf-v3 was blocked when the live `@py` measurement transport
became unreliable for long-running profiling commands after the
server reload. Short helper probes worked; long `run_weather_cycle()`
calls were accepted by the webclient and never returned output.

But before that blocker hit, v3 captured one trusted Phase A profile
run with the refined instrumentation in place. That run is sufficient
to classify:

- `cycle_total`: 50.281s
- `broadcast_loop_total`: 37.781s (**75% of cycle time**)
- Per-zone transition times: `builder2`=11.844s, `spawn_smoke`=7.922s
  (zones with zero or near-zero loaded rooms each consuming 7-12s)

This pattern unambiguously matches v3's Pattern B.1 (broadcast loop
dominates). The signal is too concentrated for variance noise to
change the classification — single zones with empty room lists
consuming 7-12 seconds is only explainable by per-zone setup work
that runs whether or not rooms exist to broadcast to.

The authorized fix is C.1 (room-list cache + filtered-subset cache),
already designed in v3. This dispatch implements that fix and
validates the result using whatever measurement transport is
reliable, rather than insisting on the specific `@py` profiling
surface that broke v3.

The instrumentation v3 added to `world/weather.py` is still in place.
This dispatch removes it after validation, per Phase F.

## Architectural guardrails (READ FIRST)

The arc has produced four blocked dispatches. The leash has worked
each time — but the data we now have is sufficient to ship a fix.
v3a accepts that the diagnostic phase is complete and the
implementation phase begins. The stop-and-report discipline still
applies, just to different conditions.

**Frozen scope:**

1. Phase A (DEFERRED): Phase A data from v3 is accepted as
   sufficient. No re-measurement before the fix.
2. Phase B: Implement C.1 (room-list cache + filtered-subset cache)
   per v3's design. Identify cache invalidation hooks.
3. Phase C: Validate the fix using ANY of three trustworthy
   measurement methods (see Phase C below). Confirm post-fix cycle
   completes under 2 seconds, OR confirm the fix produced
   substantial improvement even if not under target.
4. Phase D: Regression test — bounded-time assertion in
   `tests/test_weather.py`.
5. Phase E: Remove all instrumentation v3 added.
6. Phase F: Live webclient verification — lightning broadcast and
   indoor gating, deferred from MT-514b-smoke.
7. Phase G: Validation artifact updated.

**Frozen what-not-to-do list:**

- DO NOT re-run Phase A profiling. v3's data is accepted. Adding
  more measurements before the fix is procrastination disguised as
  rigor.
- DO NOT modify the public weather API. Source-stable:
  `get_current_weather`, `set_current_weather`, `get_weather_state`,
  `is_weather_plausible_for_climate`, `resolve_climate`,
  `tick_weather`, `run_weather_cycle`. Internal helpers may change.
- DO NOT modify any YAML content file (transition matrices, climate
  compatibility, lightning messages, transition messages).
- DO NOT modify the calendar module, prompt module, prompt
  templates, design docs, or zone YAMLs.
- DO NOT change broadcast message format, content, or routing
  beyond what's necessary for room-list caching.
- DO NOT change the persistent attribute storage shape on
  WeatherScript. Storage layout stays compatible across restarts.
- DO NOT add async/threading/Twisted-deferred dispatch.
- DO NOT add a new caching library or any third-party dependency.
- DO NOT modify foraging, ranger gather, NPCs, AI pipeline,
  builder, or any consumer of weather state.
- DO NOT add new admin commands, new weather features, or new
  player-facing surfaces.
- DO NOT investigate or attempt to fix the webclient `@py`
  long-command transport issue. That's a separate concern; if
  documented, document it as a followup, not a blocker.
- DO NOT modify the in-progress feature scope of MT-514c.
- DO NOT "while I'm here" refactor unrelated weather internals.
- DO NOT implement additional cache layers (state cache, message
  batching, etc.) beyond C.1. If C.1 alone is insufficient, that's
  a follow-up dispatch.

**Stop-and-report conditions:**

- If the cache invalidation hooks are ambiguous (no clear point in
  the codebase where zone room composition changes), stop and
  report. We need invalidation correct or stale broadcasts will
  silently happen.
- If the fix as designed cannot be implemented without changing
  the public weather API or the persistent storage shape, stop and
  report.
- If race conditions are visible between the WeatherScript's
  `at_repeat()` tick and any code path that would invalidate the
  cache, stop and report.
- If Phase C validation shows the fix produced no improvement (cycle
  time roughly the same as before), stop and report. The diagnosis
  was wrong.
- If Phase C validation shows the fix produced partial improvement
  but cycle time is still above 5 seconds, this is acceptable —
  ship the partial improvement and queue a follow-up dispatch.
  Document explicitly in the artifact.
- If the regression test reveals timing variance making bounded-
  time assertions flaky, stop and report.
- If live lightning verification fails to capture lightning in 20
  forced ticks during storm state, stop and report.
- If live indoor verification produces broadcasts in indoor rooms
  (gating broken), stop and report.

## Phase B — Implement C.1 (room-list cache)

The agent reads `world/weather.py` to identify the current
implementation of `_rooms_for_zone()` and the per-zone broadcast
helpers (`_broadcast_weather_transition()`,
`_broadcast_storm_lightning()`).

### B.1 Add the cache layer

Approximate shape (agent adapts to actual code):

```python
_zone_room_cache: dict[str, list[ObjectDB]] = {}
_zone_eligible_cache: dict[str, list[ObjectDB]] = {}

def _rooms_for_zone(zone_id: str) -> list[ObjectDB]:
    """Return all rooms in the given zone, with caching."""
    cached = _zone_room_cache.get(zone_id)
    if cached is not None:
        return cached
    rooms = list(_query_rooms_for_zone(zone_id))  # existing query path
    _zone_room_cache[zone_id] = rooms
    return rooms

def _eligible_rooms_for_zone(zone_id: str) -> list[ObjectDB]:
    """Return rooms eligible for weather broadcasts (outdoor +
    threshold), with caching."""
    cached = _zone_eligible_cache.get(zone_id)
    if cached is not None:
        return cached

    zone_payload = _get_zone_payload(zone_id)
    rooms = _rooms_for_zone(zone_id)
    eligible = []
    for room in rooms:
        room_payload = _room_payload_from_live_room(room)
        groups = determine_applicable_state_groups(room_payload, zone_payload)
        if groups and "weather" in groups:
            eligible.append(room)

    _zone_eligible_cache[zone_id] = eligible
    return eligible
```

The broadcast helpers then use `_eligible_rooms_for_zone()` instead
of computing the filter every time.

### B.2 Cache invalidation

The agent identifies invalidation hooks by reading existing code:

- **Zone import/reload:** Likely
  `world/worlddata/services/import_zone_service.py` or wherever
  zone YAML reloads happen. Call `invalidate_zone_caches(zone_id)`
  after import completes.
- **Server boot:** Clear all caches on startup. Cleanest in
  `WeatherScript.at_start()` since that fires after server reload.
- **Room creation/deletion in a zone:** If there's a hook for
  room creation that records the zone tag, that's an invalidation
  point. If not, document this as "rooms added to a zone after
  startup require server reload to be picked up by weather
  broadcasts" and proceed. (Zone room composition is normally
  static at runtime in DireEngine.)

```python
def invalidate_zone_caches(zone_id: str | None = None) -> None:
    if zone_id is None:
        _zone_room_cache.clear()
        _zone_eligible_cache.clear()
    else:
        _zone_room_cache.pop(zone_id, None)
        _zone_eligible_cache.pop(zone_id, None)
```

If invalidation hooks for zone import are unclear, stop and report
before guessing. We can discuss whether a TTL-based fallback is
acceptable.

### B.3 Wire the cache into the broadcast path

The agent updates `_broadcast_weather_transition()` and
`_broadcast_storm_lightning()` to use `_eligible_rooms_for_zone()`
in place of whatever the current code does. The result should be:
first call to the helper for a zone takes the same time it does
today; subsequent calls return cached results in microseconds.

### B.4 Wire `at_start()` invalidation

In `WeatherScript.at_start()`, call `invalidate_zone_caches()` (no
args, full clear). This handles the case where the server reloads
and the previous Python process's cached objects are stale.

## Phase C — Validate

The agent uses ANY of these measurement methods to validate the
fix. The agent picks the simplest reliable surface; if one fails,
they try another. We're measuring that the fix works, not running
a controlled experiment.

### C.1 (Preferred) Run the regression test

After implementing the cache, run the bounded-time regression test
from Phase D. If it passes, the fix works. Done.

### C.2 (Fallback) `@weather tick` end-to-end timing

If the regression test setup is not feasible against current state,
the agent connects to the webclient as admin and runs:

```
@weather tick
```

The agent times this from the perspective of "user hits enter, output
appears in feed." This is end-to-end including admin command parsing
and feed rendering. Acceptable signal: was it under 2 seconds, or
clearly substantially faster than the previous 30-45 seconds you
reported?

The agent runs this 3 times. If all 3 are under 2 seconds, the fix
works. If they're clearly faster than baseline but not under 2s
(e.g., 5-10s range), that's partial improvement — document and
proceed to Phase D with the actual numbers.

### C.3 (Last resort) In-process `@py` timing

If neither C.1 nor C.2 is reliable, the agent retries the v3 in-
process `@py` profiling pattern with the cache in place. If the
webclient transport is still unreliable for long commands, the
agent does ONE timing call (not three), and that's enough.

### C.4 Document the chosen method

Whichever method the agent uses, the validation artifact records:
- Which method was used and why
- The actual measurement values
- Comparison to v3's pre-fix baseline (cycle_total=50.281s)
- Verdict: fix works (under target) / partial improvement / fix
  didn't help

## Phase D — Regression test

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

If the test environment has zero zones, the test passes trivially.
The regression catches future code that accidentally reintroduces
uncached DB access in the broadcast hot path.

If the test fails locally even with the cache in place, that's the
"fix didn't work" stop condition — investigate before merging.

## Phase E — Remove instrumentation

Remove all temporary profiling code v3 added to `world/weather.py`.
The agent verifies via grep that no `_phase_timings`,
`_record_phase`, `get_phase_timings`, `reset_phase_timings`, or
similar profiling artifacts remain.

The regression test from Phase D is the long-term performance
guard. The instrumentation served its purpose during diagnosis.

## Phase F — Live verification

Run the verifications deferred from MT-514b-smoke. Use the
webclient transport patterns that worked previously
(`Evennia.msg('text', [...], {})` direct send if the input widget
is flaky; standard input widget if reliable).

### F.1 Lightning broadcast verification

1. Connect to webclient as admin (`jekar`).
2. Teleport to outdoor weather-capable room: `@teleport #4213`.
3. Run `look` — capture room.
4. Run `@weather new_landing storm`.
5. Run `@weather tick` repeatedly. With the cache fix, ticks should
   complete quickly, so 20 ticks in under a minute is feasible.
6. At 50% lightning probability per storm tick, lightning should
   appear within 2-3 attempts on average. Allow up to 20.

If the zone transitions out of storm before lightning fires, re-set
storm before the next tick. Capture the FIRST lightning message
that appears in the room feed.

If 20 attempts produce no lightning, stop and report.

### F.2 Indoor gating verification

1. Teleport to indoor room: `@teleport #4212`.
2. Run `look` — capture indoor room.
3. Run `@weather new_landing clear` then `@weather new_landing storm`.
4. Run `@weather tick` 5 times.
5. Capture verbatim output. Required:
   - Admin command echoes for each command
   - Tick summaries showing zone transitions
   - **NO transition messages** in the indoor room's feed
   - **NO lightning messages** in the indoor room's feed

If transition or lightning messages appear in the indoor room, the
gating is broken. Stop and report.

## Phase G — Validation artifact

APPEND a new section to `exports/mt514b_weather_validation.md`
titled `## MT-514b-perf-v3a — Broadcast cache fix and final verification`.

Section contents:

1. **Phase A acceptance.** One-line note that v3's captured Phase A
   data was accepted as sufficient classification. Diagnosis:
   Pattern B.1 (broadcast loop dominates).
2. **Phase B implementation.** What was added (room-list cache,
   eligible-rooms cache, invalidation hooks), where invalidation
   fires, what was deliberately NOT changed.
3. **Phase C validation.** Which measurement method was used, the
   actual numbers, comparison to v3's 50.281s baseline. Verdict.
4. **Phase D regression test.** Test name and threshold.
5. **Phase E confirmation.** Grep results showing no profiling code
   left in tree.
6. **Phase F.1 lightning evidence.** Verbatim webclient output.
7. **Phase F.2 indoor gating evidence.** Verbatim webclient output.
8. **Final state.** One sentence: "MT-514b is now fully closed."

If any phase blocked, the section ends with the BLOCKED status and
the specific reason.

## Verification checklist

1. Cache layer added to `world/weather.py` per B.1-B.4.
2. Invalidation hooks identified and wired (zone import, server
   boot at minimum).
3. Phase C validation completed via at least one of C.1, C.2, or
   C.3, with measurement values documented.
4. Phase D regression test added and passes.
5. All previously-passing tests still pass (focused suite + broader
   discovery run).
6. Phase E confirms no profiling code left in tree.
7. Phase F.1 lightning message captured live.
8. Phase F.2 indoor room receives no broadcasts.
9. Validation artifact appended with full evidence.
10. No code outside the in-scope list modified.

## Stop conditions

- Edit only `world/weather.py`, `tests/test_weather.py`, the
  validation artifact, and (only if cache invalidation requires it)
  `world/worlddata/services/import_zone_service.py` or similar
  zone-import points. No other files.
- Stop and report on cache invalidation ambiguity.
- Stop and report if the fix produces no improvement (diagnosis was
  wrong).
- Stop and report if partial improvement is achieved but cycle
  time still exceeds 5 seconds (acceptable to ship; document for
  follow-up).
- Stop and report on lightning failure or indoor gating failure.
- Do not "while I'm here" refactor unrelated weather internals.
- Do not investigate the webclient `@py` long-command transport
  issue.

## Required artifacts

1. Updated `world/weather.py` (room-list cache + eligible-rooms
   cache, invalidation hooks, instrumentation removed)
2. Updated `tests/test_weather.py` (regression test added)
3. Possibly updated `world/worlddata/services/import_zone_service.py`
   (one-line cache invalidation call) — only if needed
4. Updated `exports/mt514b_weather_validation.md` (new section
   appended)

## Followup queue

- MT-514b-invasion: Add `current_invasion` runtime state with
  `@invasion` admin command. Same persistence pattern as weather.
  Apply BOTH the ScriptDB fallback (from v2a) AND the per-zone
  caching pattern (from v3a) from day one. Invasion does not need
  to repeat the perf-debugging arc.
- MT-514c: Foraging refactor consuming terrain + skill rank +
  calendar + weather + invasion. Now safe to build on a perf-tuned
  weather foundation.
- Webclient long-command transport: The MT-514b-perf-v3 dispatch
  hit a real but uncharacterized issue where long-running `@py`
  commands stop returning output through the webclient. This is
  not blocking weather work but should be investigated separately
  if it recurs in future profiling or testing dispatches. Likely
  not a code defect — possibly a webclient buffer or session-state
  issue specific to long synchronous server-side commands.
- Future architectural note: any system using Evennia persistent
  attributes for frequently-read state should follow the patterns
  established here (ScriptDB fallback + in-memory cache where
  appropriate). Consider documenting in
  `docs/architecture/runtime_state_patterns.md` after the arc
  completes.