# MT-514b-perf — Weather tick performance + final live verification

## Background

MT-514b shipped working weather. The forced-tick path was patched in
the prior smoke (broadcast side effects now fire from `@weather tick`
the same way they fire from the natural script tick). Live evidence
captured an outdoor transition broadcast firing correctly.

But `@weather tick` takes 30-45 seconds to complete in the live
server. The natural `WeatherScript.at_repeat()` runs the same code
path, which means the live server will hang for 30-45 seconds every
~3.75 real minutes. During that hang, every player command queues
up — combat, movement, all gameplay freezes.

This dispatch profiles the lag, fixes the highest-impact bottlenecks,
adds a regression test that prevents the lag from coming back, and
in the same pass captures the two live-verification gaps that
remained from MT-514b-smoke: lightning broadcast and indoor gating.

## Architectural guardrails (READ FIRST)

This is a performance dispatch. The temptation to refactor weather
internals "while I'm here" is real and must be resisted. Optimize
based on profiling evidence; do not speculatively over-engineer.

**Frozen scope:**

1. Add timing instrumentation to `tick_weather()` and the broadcast
   helpers, run a profiling tick against the live database state,
   and report where the seconds go BEFORE optimizing anything.
2. Implement the smallest cache-layer fix that brings the full
   `@weather tick` time below 2 seconds. Stretch target: 500ms.
3. Add a regression test in `tests/test_weather.py` that asserts a
   bounded execution time for `tick_weather()` against a
   representative zone count.
4. Capture the two outstanding live-verification items via webclient
   smoke after the perf fix:
   - Lightning broadcast in an outdoor room during storm
   - Absence of broadcasts in an indoor room
5. Update `exports/mt514b_weather_validation.md` with the perf
   results, the cache-layer changes made, and the final live
   verification evidence.

**Frozen what-not-to-do list:**

- DO NOT modify the public weather API (`get_current_weather`,
  `set_current_weather`, `get_weather_state`,
  `is_weather_plausible_for_climate`, `resolve_climate`, `tick_weather`,
  the calendar promotion). Internal helpers may change; the API
  surface that consumers (foraging, etc.) depend on stays stable.
- DO NOT modify any YAML content file (transition matrices,
  climate compatibility, lightning messages, transition messages).
  This is an implementation perf pass, not a tuning pass.
- DO NOT modify the calendar module, prompt module, prompt
  templates, design docs, or zone YAMLs.
- DO NOT change the broadcast message text, format, or routing
  logic beyond what's necessary for caching room lists.
- DO NOT modify the singleton `WeatherScript`'s persistence
  shape. Stored state stays compatible with the previously-shipped
  attribute layout.
- DO NOT add async/threading/Twisted-deferred dispatch unless
  profiling specifically points at message-dispatch as the
  bottleneck AND the simpler cache fixes don't reach the 2s target.
- DO NOT add a new caching library, scheduling library, or any
  other third-party dependency.
- DO NOT touch foraging, ranger gather, NPCs, AI pipeline,
  builder, or any consumer of weather state.
- DO NOT add new admin commands or new weather features.
- DO NOT modify `commands/cmd_weather.py` beyond what is necessary
  to surface profiling output during Phase A.

**Stop-and-report conditions:**

- If profiling reveals the bottleneck is somewhere unexpected
  (not in `_rooms_for_zone()`, not in per-room state-group
  evaluation), stop and report before implementing any fix.
- If the smallest cache fix Layer 1 (room-list caching) brings the
  tick below 2 seconds, STOP. Do not continue with Layers 2-5.
  Over-optimization is out of scope.
- If cache invalidation events are unclear in this codebase
  (i.e., when do rooms move between zones, get added, get
  deleted?), stop and report before adding cache logic. We need
  the invalidation right or stale broadcasts will silently happen.
- If the regression test reveals timing variance that makes
  bounded-time assertions flaky, stop and report. We will adjust
  the assertion strategy rather than ship a flaky test.
- If the live lightning verification still fails to capture
  lightning in 20 forced ticks during storm state on the patched
  perf code, stop and report. That's a real bug, separate from
  the perf issue.
- If the live indoor verification produces messages in indoor
  rooms (gating broken), stop and report.

## Phase A — Profile

Before writing any optimization, instrument `tick_weather()` and
its callees to measure time spent in each phase. Add temporary
profiling output that the agent can capture, then remove it after
fixing.

Required instrumentation (temporary — removed before merge):
1. Wall-clock time for the full `tick_weather()` call.
2. Per-zone time spent in the transition decision (pure logic).
3. Per-zone time spent in `_rooms_for_zone()`.
4. Per-zone time spent iterating rooms and calling
   `determine_applicable_state_groups()`.
5. Per-zone time spent in actual `msg_contents()` broadcast.
6. Total count of database queries during a single tick (use
   Django's `connection.queries` counter or equivalent).

Run profiling:
- Restart the dev server with the instrumentation in place.
- Connect via webclient as admin.
- Run `@weather tick` once. Capture the verbatim instrumentation
  output.
- Repeat 3 times to confirm the timing is stable (not a one-time
  cold cache).

Stop and write a "Phase A — Profiling Results" entry in the
validation artifact BEFORE proceeding to Phase B. The entry
includes:
- Per-phase timing breakdown
- Total tick time
- Total DB query count
- Identified primary bottleneck

The agent then writes one sentence in the entry: "Primary bottleneck
is X; fix plan is to apply cache Layer N." THEN proceeds to Phase B.

If the profiling result doesn't match the predicted bottleneck
(`_rooms_for_zone()` and per-room state-group evaluation), stop
and surface the actual data before continuing.

## Phase B — Fix

Implement cache layers in order, lightest-touch first. Stop at
the first layer that brings tick time under 2 seconds.

### Layer 1: Cache `_rooms_for_zone()` results

Add a per-zone room-list cache in `world/weather.py`. The cache
is invalidated when:
- A zone is loaded or reloaded (signal: zone-import service or
  similar — agent identifies the right invalidation hook by
  reading existing zone-load code)
- A room's zone tag changes (signal: agent identifies hook in
  room-creation/movement code)

Cache structure:
```python
_zone_room_cache: dict[str, list[ObjectDB]] = {}

def _rooms_for_zone(zone_id: str) -> list[ObjectDB]:
    cached = _zone_room_cache.get(zone_id)
    if cached is not None:
        return cached
    rooms = list(_query_rooms_for_zone(zone_id))  # the existing path
    _zone_room_cache[zone_id] = rooms
    return rooms

def invalidate_zone_room_cache(zone_id: str | None = None) -> None:
    if zone_id is None:
        _zone_room_cache.clear()
    else:
        _zone_room_cache.pop(zone_id, None)
```

The agent identifies where to call `invalidate_zone_room_cache()`:
- When a zone is imported or reloaded (likely
  `world/worlddata/services/import_zone_service.py`)
- When the engine boots (clear on startup so stale cache from a
  previous run doesn't leak)

If invalidation hooks are ambiguous, stop and report. We can
discuss whether a TTL-based cache (refresh every N minutes) is
acceptable as a simpler alternative.

After implementing Layer 1, re-run profiling. If tick time is
under 2 seconds, **STOP. Skip Layers 2-5.**

### Layer 2: Pre-compute "weather-eligible rooms" per zone

(Only execute if Layer 1 is insufficient.)

`determine_applicable_state_groups()` is called per room per
broadcast to filter to outdoor + threshold rooms. This is
deterministic given room tags + zone context, so cache the
filtered subset.

Add a `_weather_eligible_rooms_cache` dict keyed by zone_id, with
the cached value being the list of (room, role) tuples where role
is "outdoor" or "threshold". Compute once when first needed per
zone, invalidate on the same triggers as Layer 1.

After Layer 2, re-run profiling. Stop if under 2 seconds.

### Layer 3: Single-pass broadcast

(Only execute if Layers 1-2 are insufficient.)

If both a transition broadcast AND a lightning broadcast fire for
the same zone in the same tick, ensure they share the room list.
Currently each broadcast helper likely calls `_rooms_for_zone()`
independently. Refactor so `tick_weather()` builds the per-zone
broadcast list once and passes it to both helpers.

After Layer 3, re-run profiling.

### Layer 4: Skip empty zones

(Only execute if Layers 1-3 are insufficient.)

If a zone has zero outdoor rooms with characters present, the
broadcast does work nobody experiences. Add a quick character-
presence check; skip the broadcast iteration if no characters.

After Layer 4, re-run profiling.

### Layer 5: Async dispatch

(Only execute if Layers 1-4 are insufficient AND profiling
specifically points at message dispatch.)

Use Twisted's `reactor.callLater` or Evennia's `delay` to fire
the broadcast off the tick path. The tick decides what to send;
the dispatch happens out-of-band and doesn't block subsequent ticks.

This is a meaningful architecture change and should not be
needed. If the agent reaches Layer 5 before hitting the target,
stop and report — something else is wrong.

## Phase C — Regression test

After the perf fix lands, add a regression test in
`tests/test_weather.py`:

```python
def test_tick_weather_completes_within_bounded_time(self):
    """tick_weather must complete quickly enough for periodic use.
    
    The natural script tick fires every ~3.75 real minutes; if
    tick_weather takes longer than the bounded threshold, the
    server will hang during the tick. This test guards against
    regressions in the tick performance.
    """
    import time
    # Set up: ensure cache is populated (warm path, not cold start)
    tick_weather()
    # Measure: subsequent tick should be fast
    start = time.monotonic()
    tick_weather()
    elapsed = time.monotonic() - start
    self.assertLess(elapsed, 2.0,
        f"tick_weather() took {elapsed:.2f}s, expected < 2.0s")
```

The test runs against whatever zone state the test fixture
provides (likely empty or minimal). The "warm" measurement is
what matters — cold-start cache build can be slower without
breaking gameplay because it only happens once.

If the test environment has zero zones, the test should still
pass trivially (an empty tick is fast). The test catches
regressions where someone accidentally reintroduces uncached
DB queries in the hot path.

## Phase D — Live verification

After the perf fix lands and tests pass, the agent runs the
remaining live-verification items via webclient. Use the same
approach that worked in MT-514b-smoke: webclient session,
`Evennia.msg('text', [...], {})` if the input widget is flaky,
or the standard input widget if reliable.

### D.1 Lightning broadcast verification

1. Connect to webclient as admin.
2. Teleport to outdoor room: `@teleport #4213` (verified
   weather-capable in MT-514b-smoke pre-flight).
3. Run `look` — capture room.
4. Run `@weather new_landing storm`.
5. Run `@weather tick` repeatedly. With the perf fix, each tick
   completes quickly, so 20 ticks is feasible in under a minute.
   At 50% lightning probability per storm tick, expected number
   of ticks before lightning is ~2; 20 ticks should produce
   multiple lightning events.

Important: if a tick transitions the zone OUT of storm before
lightning fires, the agent should re-set storm before the next
tick. Capture the sequence:
```text
set storm
tick (capture output)
if no lightning AND zone still in storm: tick again
if no lightning AND zone out of storm: set storm again, tick
```

Capture the FIRST lightning message that appears in the room
feed. Record the verbatim line and which lightning category
it came from (flashes, thunderclaps, or flash_then_thunder).

If 20 attempts produce no lightning, stop and report.

### D.2 Indoor gating verification

1. Teleport to indoor room: `@teleport #4212` (verified
   weather-incompatible in MT-514b-smoke pre-flight).
2. Run `look` — capture room. Confirm character is in the
   indoor location.
3. Run `@weather new_landing clear` then `@weather new_landing storm`.
4. Run `@weather tick` 5 times.
5. Capture the verbatim output. The output should include:
   - Admin command echoes for each command issued
   - Tick summaries showing zone transitions
   - **NO transition messages** (no "the rain begins to fall"
     or fallback "the weather shifts")
   - **NO lightning messages**

If transition messages or lightning messages DO appear in the
indoor room's feed, that's a real bug — the indoor gating is
broken. Stop and report.

The verification is positive evidence that the gating works. The
absence of expected messages, captured verbatim with surrounding
admin echo context, IS the evidence.

## Phase E — Validation artifact

APPEND a new section to `exports/mt514b_weather_validation.md`
titled `## Performance fix and final verification (MT-514b-perf)`.

The section includes:

1. **Phase A profiling results.** Verbatim instrumentation output
   from the unoptimized run. Total time, per-phase breakdown,
   total DB queries.
2. **Phase B fix summary.** Which cache layer(s) were applied,
   why each was needed, what was deliberately NOT done.
3. **Post-fix profiling.** Same instrumentation re-run, showing
   the timing improvement.
4. **Phase C regression test.** Test name and bounded threshold.
5. **Phase D.1 lightning evidence.** Verbatim webclient output
   showing storm set, tick, lightning message in outdoor room.
6. **Phase D.2 indoor gating evidence.** Verbatim webclient output
   showing storm set + ticks in indoor room with no broadcasts.
7. **Final state.** One sentence: "MT-514b is now fully closed."

If any phase blocked, the section ends with the BLOCKED status
and the specific reason.

## Verification checklist

1. Profiling instrumentation captures clear bottleneck data.
2. Smallest viable cache fix applied (do not over-optimize).
3. Profiling instrumentation removed from production code paths
   (kept only in optional debug helpers if useful).
4. `tick_weather()` completes in under 2 seconds with warm cache.
5. Regression test added and passes.
6. All previously-passing tests still pass.
7. Lightning message captured live in outdoor room.
8. Indoor room receives no broadcasts (verbatim evidence).
9. Validation artifact appended with full Phase A-E evidence.
10. No code outside the in-scope list modified.

## Stop conditions

- Edit only `world/weather.py`, `commands/cmd_weather.py` (only
  if profiling instrumentation requires temporary changes there),
  `tests/test_weather.py`, and the validation artifact. No other
  files unless the cache invalidation hook requires a small change
  in `world/worlddata/services/import_zone_service.py` or similar
  — in which case the change is one function call to invalidate
  the cache, nothing else.
- Stop after Layer 1 if it hits the 2s target.
- Stop and report if Layer 5 is reached.
- Stop and report on any unexpected profiling result.
- Stop and report on lightning failure or indoor gating failure.
- Do not "while I'm here" refactor unrelated weather internals.

## Required artifacts

1. Updated `world/weather.py` (cache layer, instrumentation
   removed)
2. Updated `tests/test_weather.py` (regression test added)
3. Possibly updated `world/worlddata/services/import_zone_service.py`
   (one-line cache invalidation call) — only if needed
4. Updated `exports/mt514b_weather_validation.md` (new section
   appended)

## Followup queue

- MT-514b-invasion: Add `current_invasion` runtime state with
  `@invasion` admin command. Same persistence pattern as weather.
  Will benefit from the perf-conscious patterns established here.
- MT-514c: Foraging refactor consuming terrain + skill rank +
  calendar + weather + invasion. Now safe to build on a perf-tuned
  weather foundation.
- Future: If Layer 5 (async dispatch) ever becomes necessary,
  draft a separate dispatch for it. Don't bundle into a feature
  dispatch.