# MT-514b-perf-v2 — Weather state cache + room cache + final verification

## Background

MT-514b-perf was blocked when its profiling phase falsified the
hypothesis. The dispatch predicted that `_rooms_for_zone()` and
per-room state-group filtering would be the bottleneck. Profiling
showed otherwise:

- Full `run_weather_cycle()`: **50.3s, 5,375 queries**
- Same cycle with `_rooms_for_zone()` stubbed to `[]`: **32.5s, 558 queries**
- `tick_weather()` alone: **5.7s, 441 queries**
- `get_weather_state()` alone: **5.4s, 32 queries**

Two real bottlenecks emerged:

1. **`tick_weather()` + `get_weather_state()` do too many attribute
   reads.** Each per-zone read of weather state goes through
   Evennia's persistent attribute system, which round-trips through
   the database/ORM. With ~12 zones, this compounds to 5-6 seconds
   per call before any broadcast work happens.
2. **Broadcast machinery (`_rooms_for_zone()` + per-room filtering)
   accounts for the remaining ~18 seconds.** This is the original
   Layer 1 problem from MT-514b-perf, but it's secondary — even with
   it fully fixed, the state-read cost would leave us at ~32s.

The fix is two complementary layers: an in-memory state cache for
the WeatherScript (eliminates per-zone attribute reads), plus the
room-list cache the prior dispatch designed (eliminates per-tick
DB queries for room iteration).

This dispatch implements both, validates with a bounded-time
regression test, and captures the two outstanding live verifications
(lightning broadcast, indoor gating) on the fixed system.

## Architectural guardrails (READ FIRST)

The prior dispatch's leash language applies in full. The temptation
to refactor weather internals "while I'm here" is real and must be
resisted. Optimize against measured evidence, not speculation.

**Frozen scope:**

1. Phase A: re-profile to confirm the v1 findings hold on the
   current code state. The agent reverted v1's changes, so we're
   back at the unoptimized baseline.
2. Phase B: implement an in-memory state cache for WeatherScript.
   All zone weather reads/writes go through the cache; persistence
   is write-through to the script's persistent attributes.
3. Phase C: implement the room-list cache (Layer 1 from
   MT-514b-perf), with invalidation hooks identified during
   profiling.
4. Phase D: re-profile to confirm full cycle under 2 seconds
   (target) or 500ms (stretch).
5. Phase E: regression test that asserts bounded execution time
   for `run_weather_cycle()`.
6. Phase F: live webclient verification of lightning broadcast
   and indoor gating, both deferred from MT-514b-smoke.
7. Phase G: validation artifact updated with full evidence.

**Frozen what-not-to-do list:**

- DO NOT modify the public weather API. Specifically these stay
  source-stable: `get_current_weather`, `set_current_weather`,
  `get_weather_state`, `is_weather_plausible_for_climate`,
  `resolve_climate`, `tick_weather`, `run_weather_cycle`. Internal
  helpers may change; consumer surface stays the same.
- DO NOT modify any YAML content file (transition matrices,
  climate compatibility, lightning messages, transition messages).
- DO NOT modify the calendar module, prompt module, prompt
  templates, design docs, or zone YAMLs.
- DO NOT change the broadcast message format, content, or routing
  beyond what's necessary for caching.
- DO NOT change the persistent attribute storage shape on
  WeatherScript. The cache is in-memory; persistence on the script
  uses the same attribute keys as before. This guarantees
  forward/backward compatibility across server restarts.
- DO NOT add async/threading/Twisted-deferred dispatch.
- DO NOT add a new caching library or any third-party dependency.
- DO NOT modify foraging, ranger gather, NPCs, AI pipeline,
  builder, or any consumer of weather state.
- DO NOT add new admin commands, new weather features, or new
  player-facing surfaces.
- DO NOT modify `commands/cmd_weather.py` beyond what is necessary
  for the regression-test runner during Phase A profiling. Restore
  to clean state before merge.
- DO NOT touch the in-progress feature scope of MT-514c. Foraging
  remains untouched.

**Stop-and-report conditions:**

- If profiling reveals the bottleneck is somewhere unexpected
  (not in attribute reads or room lookups), stop and report. The
  v1 dispatch had a wrong hypothesis; do not repeat that mistake
  by assuming v2's hypothesis is correct without measuring.
- If the in-memory cache layer requires changing the persistent
  attribute storage shape, stop and report. The cache is a
  read-side optimization with write-through; if that pattern
  doesn't fit, we want to discuss before committing to a
  different storage redesign.
- If the cache cannot be safely invalidated across server
  restarts (e.g., the cache loads stale data from a previous
  process), stop and report.
- If race conditions exist between the WeatherScript's
  `at_repeat()` tick and an admin-issued `set_current_weather()`
  in the same instant, stop and report. We need to understand
  the concurrency model before shipping.
- If Phase B alone brings cycle time below 2 seconds, the agent
  may stop without implementing Phase C — but must report this
  decision explicitly so we know Layer 2 was deemed unnecessary.
- If the regression test reveals timing variance that makes
  bounded-time assertions flaky, stop and report.
- If the live lightning verification fails to capture lightning
  in 20 forced ticks during storm state, stop and report.
- If the live indoor verification produces messages in indoor
  rooms (gating broken), stop and report.

## Phase A — Re-profile

The v1 perf dispatch's profiling code was reverted. The agent
re-instruments `tick_weather()`, `get_weather_state()`,
`run_weather_cycle()`, `_rooms_for_zone()`, and the broadcast
helpers. Same instrumentation pattern as v1: temporary,
removed before merge.

Required measurements:
1. Wall-clock time for full `run_weather_cycle()` (matches v1 at ~50s)
2. Wall-clock time for `tick_weather()` alone (v1: ~5.7s)
3. Wall-clock time for `get_weather_state()` alone (v1: ~5.4s)
4. DB query count for each (v1: 5375 / 441 / 32 respectively)
5. Per-zone breakdown of attribute reads in `tick_weather()` —
   the agent identifies WHICH specific attribute reads are slow
   by counting reads per call site and timing each.

The agent runs this 3 times. If the v1 numbers replicate within
±20%, proceed. If they're significantly different, stop and
report — something changed about the codebase between dispatches.

The agent writes "Phase A — Re-profiling Results" to the
validation artifact BEFORE proceeding to Phase B. The entry
includes:
- Verbatim measurements
- Confirmation that the bottleneck is consistent with v1's data
- Identified specific attribute-read locations that drive the cost

## Phase B — In-memory state cache

The WeatherScript persists per-zone weather state via Evennia
attributes (likely `db.weather_state__<zone_id>` or similar). Each
read of these attributes round-trips through the ORM. The fix is
to read all weather state into a Python dict once at script start,
serve all reads from that dict, and write through to the persistent
attributes only when state actually changes.

### B.1 Identify the cache layer's home

The agent reads `world/weather.py` to find the WeatherScript
class. The cache is added as a Python attribute on the script
instance (NOT a persistent `db.` attribute). Likely shape:

```python
class WeatherScript(DefaultScript):
    def at_script_creation(self):
        # ... existing setup ...
        self._zone_state_cache: dict[str, str] = {}
        self._cache_loaded = False

    def _ensure_cache_loaded(self) -> None:
        if self._cache_loaded:
            return
        # Bulk-load all weather state attributes into the cache
        for zone_id, value in self._iter_persistent_weather_state():
            self._zone_state_cache[zone_id] = value
        self._cache_loaded = True

    def at_start(self):
        # Called on script start AND after server reload.
        # Reset cache so a fresh server pass loads from disk.
        self._zone_state_cache = {}
        self._cache_loaded = False
```

The exact attribute names and persistent-storage layout depend on
the existing implementation. The agent reads the current code and
adapts.

### B.2 Route reads through the cache

`get_current_weather(zone_id)` becomes:

```python
def get_current_weather(zone_id: str) -> str:
    script = _get_weather_script()
    script._ensure_cache_loaded()
    return script._zone_state_cache.get(zone_id, DEFAULT_WEATHER)
```

`get_weather_state()` similarly: build the structured snapshot
from the in-memory cache plus a single read of climate
configuration. **Zero DB queries** in the hot path beyond what's
needed for the broadcast iteration.

### B.3 Route writes through the cache

`set_current_weather(zone_id, value, *, source)` becomes:

```python
def set_current_weather(zone_id: str, value: str, *, source: str = "admin") -> None:
    # Validation logic stays the same
    _validate_weather_value(value)
    
    script = _get_weather_script()
    script._ensure_cache_loaded()
    
    # Write-through: update cache AND persist
    script._zone_state_cache[zone_id] = value
    _persist_zone_state(script, zone_id, value)
```

The persist call writes to the same `db.` attribute layout that
existed before. No storage shape change; only the read path is
optimized.

### B.4 `tick_weather()` operates on the cache

Currently `tick_weather()` reads each zone's state, computes
transitions, writes back. With the cache:

```python
def tick_weather() -> dict[str, tuple[str, str]]:
    script = _get_weather_script()
    script._ensure_cache_loaded()
    
    transitions: dict[str, tuple[str, str]] = {}
    
    # Iterate all known zones (same logic as before)
    for zone_id in _known_zone_ids():
        current = script._zone_state_cache.get(zone_id, DEFAULT_WEATHER)
        # ... existing transition decision logic ...
        next_state = _pick_next_state(current, climate, season)
        if next_state != current:
            script._zone_state_cache[zone_id] = next_state
            _persist_zone_state(script, zone_id, next_state)
            transitions[zone_id] = (current, next_state)
    
    return transitions
```

Now `tick_weather()` does N writes for N changed zones — typically
0-3 — instead of 12 reads + 12 writes. DB query count drops from
~441 to under 10 for typical ticks.

### B.5 Re-profile after Phase B

Run the same Phase A measurements. Document in artifact.

If `run_weather_cycle()` is now under 2 seconds, **stop**. Proceed
directly to Phase D (regression test). Skip Phase C.

If it's still over 2 seconds, the remaining cost is in
`_rooms_for_zone()` and broadcast iteration. Proceed to Phase C.

## Phase C — Room-list cache

Only execute if Phase B alone is insufficient.

This is the original Layer 1 from MT-514b-perf. Same design:

```python
_zone_room_cache: dict[str, list[ObjectDB]] = {}

def _rooms_for_zone(zone_id: str) -> list[ObjectDB]:
    cached = _zone_room_cache.get(zone_id)
    if cached is not None:
        return cached
    rooms = list(_query_rooms_for_zone(zone_id))
    _zone_room_cache[zone_id] = rooms
    return rooms

def invalidate_zone_room_cache(zone_id: str | None = None) -> None:
    if zone_id is None:
        _zone_room_cache.clear()
    else:
        _zone_room_cache.pop(zone_id, None)
```

### C.1 Cache invalidation hooks

The agent identifies the right hooks by reading existing code:

- Zone import: `world/worlddata/services/import_zone_service.py`
  or wherever zones get loaded into the live database. Call
  `invalidate_zone_room_cache(zone_id)` after import completes.
- Room movement between zones: agent identifies the hook in
  room-creation/zone-tag-change code.
- Server boot: clear the cache on startup. Most cleanly done by
  calling `invalidate_zone_room_cache()` (no args) when
  `WeatherScript.at_start()` fires.

If the invalidation hooks are ambiguous, stop and report. We can
discuss whether a TTL-based cache (refresh every N minutes) is
acceptable as a simpler alternative.

### C.2 Re-profile after Phase C

Run the same measurements. Confirm `run_weather_cycle()` under
2 seconds.

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
    self.assertLess(elapsed, 2.0,
        f"run_weather_cycle() took {elapsed:.3f}s, expected < 2.0s")
```

The test runs against whatever zone state the test fixture
provides. The "warm" measurement is what matters — cold-start
cache build is allowed to be slower because it happens once per
process.

If the test environment has zero zones, the test passes
trivially. The regression catches future code that accidentally
reintroduces uncached DB access in the hot path.

## Phase E — Remove instrumentation

Remove all temporary profiling/timing code added in Phase A. The
instrumentation served its purpose. The regression test from Phase
D is the long-term performance guard.

The agent verifies via grep that no `time.monotonic()`,
`reset_queries()`, `connection.queries`, or similar profiling
artifacts remain in `world/weather.py` or `commands/cmd_weather.py`.

## Phase F — Live verification

Now that the system is fast, run the verifications deferred from
MT-514b-smoke. Use the same webclient transport that worked
previously: connect, teleport, issue commands via input widget or
`Evennia.msg('text', [...], {})` if needed.

### F.1 Lightning broadcast verification

1. Connect to webclient as admin (`jekar`).
2. Teleport to outdoor weather-capable room: `@teleport #4213`
   (verified weather-capable in MT-514b-smoke pre-flight).
3. Run `look` — capture room.
4. Run `@weather new_landing storm`.
5. Run `@weather tick` repeatedly. With the perf fix, ticks
   complete in under a second, so this is a fast loop.
6. At 50% lightning probability per storm tick, lightning should
   appear within 2-3 attempts on average. Allow up to 20.

If the zone transitions out of storm before lightning fires,
re-set storm before the next tick:
```
@weather new_landing storm
@weather tick (capture)
if no lightning and zone now in storm: tick again
if zone left storm: re-set storm, tick
```

Capture the FIRST lightning message that appears in the room
feed. Record the verbatim line.

If 20 attempts produce no lightning, stop and report.

### F.2 Indoor gating verification

1. Teleport to indoor room: `@teleport #4212`.
2. Run `look` — capture indoor room.
3. Run `@weather new_landing clear` then `@weather new_landing storm`.
4. Run `@weather tick` 5 times.
5. Capture verbatim output. The output should include:
   - Admin command echoes for each command
   - Tick summaries showing zone transitions
   - **NO transition messages** (no rain or storm narration)
   - **NO lightning messages**

If transition or lightning messages DO appear in the indoor
room's feed, the gating is broken. Stop and report.

The verification is positive evidence that the absence holds.
The captured output, with surrounding admin-echo context proving
that ticks did fire and zones did transition, IS the evidence.

## Phase G — Validation artifact

APPEND a new section to `exports/mt514b_weather_validation.md`
titled `## MT-514b-perf-v2 — Cache fix and final verification`.

Section contents:

1. **Phase A re-profiling.** Verbatim before-fix measurements,
   confirming v1's findings.
2. **Phase B implementation.** What was added (in-memory cache),
   how invalidation works, what was deliberately NOT changed.
3. **Phase B post-fix profiling.** Same measurements, showing
   improvement.
4. **Phase C decision.** Either "Phase B sufficient, skipped Phase
   C" with the post-Phase-B numbers, or "Phase C required" with
   the design and post-Phase-C numbers.
5. **Phase D regression test.** Test name and bounded threshold.
6. **Phase F.1 lightning evidence.** Verbatim webclient output.
7. **Phase F.2 indoor gating evidence.** Verbatim webclient output.
8. **Final state.** One sentence: "MT-514b is now fully closed."

If any phase blocked, the section ends with the BLOCKED status
and the specific reason.

## Verification checklist

1. Phase A measurements replicate v1's findings within reasonable
   variance.
2. Phase B in-memory cache implemented; reads/writes route through
   it; persistence write-through preserved.
3. Phase B post-fix profiling shows substantial improvement.
4. Phase C either skipped (with justification) or implemented with
   measured benefit.
5. Final cycle time under 2 seconds (target) or 500ms (stretch).
6. Phase D regression test added and passes.
7. All previously-passing tests still pass.
8. Phase E confirms no profiling code left in the tree.
9. Phase F.1 lightning message captured live in outdoor room.
10. Phase F.2 indoor room receives no broadcasts (verbatim
    evidence).
11. Validation artifact appended with full evidence.
12. No code outside the in-scope list modified.

## Stop conditions

- Edit only `world/weather.py`, `tests/test_weather.py`, the
  validation artifact, and (only if cache invalidation requires
  it) `world/worlddata/services/import_zone_service.py` and/or
  similar zone-import points. Any other file is out of scope.
- Stop and report on any unexpected profiling result.
- Stop and report if the in-memory cache requires storage shape
  changes.
- Stop and report on cache invalidation ambiguity.
- Stop and report if race conditions are visible between the tick
  and admin set commands.
- Stop and report if Phase B alone is sufficient (this is a
  positive outcome — but document it explicitly).
- Stop and report on lightning failure or indoor gating failure.
- Do not "while I'm here" refactor unrelated weather internals.

## Required artifacts

1. Updated `world/weather.py` (in-memory cache, possibly room
   cache, instrumentation removed)
2. Updated `tests/test_weather.py` (regression test added)
3. Possibly updated zone-import service (one-line cache
   invalidation call) — only if Phase C is executed
4. Updated `exports/mt514b_weather_validation.md` (new section
   appended)

## Followup queue

- MT-514b-invasion: Add `current_invasion` runtime state with
  `@invasion` admin command. Same persistence pattern as weather.
  Will benefit from the in-memory cache pattern established here —
  apply the same architectural approach from the start rather than
  shipping slow and fixing later.
- MT-514c: Foraging refactor consuming terrain + skill rank +
  calendar + weather + invasion. Now safe to build on a perf-tuned
  weather foundation.
- Future architectural note: any other system that uses Evennia
  persistent attributes for frequently-read state should follow
  the same in-memory-cache + write-through pattern. Consider
  documenting this as a project convention.