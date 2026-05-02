# MT-514b-perf-v2a — In-process state cache + ScriptDB fallback + final verification

## Background

MT-514b-perf-v2 was blocked when its Phase A baseline didn't replicate
v1's measurements. MT-514b-perf-diag (read-only diagnostic) revealed
why: both v1 and v2 were measuring `run_weather_cycle()` from an
external Pylance Python interpreter, which is a separate Django
process from the live Evennia server.

In that external-interpreter context:
- `evennia.search_script` resolves to `None`
- `world.weather.search_script` similarly resolves to `None`
- `run_weather_cycle()` therefore can't find the existing
  `global_weather` script
- It falls through to `create_script(...)`, which contends with the
  live server's SQLite write lock and produces IntegrityError /
  database-locking failures

So both v1 (50.3s/5375 queries) and v2 (8.1-8.8s tick / various
cycle behavior) were measuring an unintended fallback path, not the
actual production tick path.

The diagnostic also confirmed:
- WeatherScript persistent state is clean: 12 zones tracked, 12
  matching meta entries, zero stale references, zero anomalies. The
  "accumulated cruft" hypothesis was wrong.
- No code drift after commit 5b9077b. The drift between v1 and v2
  was runtime/environmental.
- The ScriptDB fallback pattern that makes script access safe from
  external processes already exists in
  `server/conf/at_server_startstop.py` but is NOT used in
  `world/weather.py`.

This dispatch corrects the measurement surface, adds the missing
ScriptDB fallback (a small structural fix that prevents this entire
class of failure from recurring), and proceeds with the in-memory
state cache hypothesis the v2 dispatch designed — but validates it
against the actual production tick path.

## Architectural guardrails (READ FIRST)

Three blocked dispatches in this arc have established a pattern:
when measurements don't match the hypothesis, the agent stops and
reports rather than implementing a speculative fix. That pattern
continues here.

The temptation to refactor weather internals "while I'm here" is
real and must be resisted. Optimize against in-process measured
evidence, not external-process noise.

**Frozen scope:**

1. Phase A: Add a `ScriptDB` fallback in `world/weather.py` so the
   weather script can be found reliably from any context. Mirror
   the pattern already used in `server/conf/at_server_startstop.py`.
2. Phase B: Re-profile baseline using IN-PROCESS measurement (via
   `@py` from a live admin session, NOT via external Pylance
   interpreter). Establish the actual production tick path's cost.
3. Phase C: Implement an in-memory state cache for WeatherScript.
   All zone weather reads/writes go through the cache; persistence
   is write-through to the script's persistent attributes.
4. Phase D: Re-profile after the cache lands. Confirm full cycle
   under 2 seconds (target) or 500ms (stretch).
5. Phase E: Optional room-list cache (the original Layer 1 from
   v1's blocked dispatch), only if Phase C alone insufficient.
6. Phase F: Regression test asserting bounded execution time for
   `run_weather_cycle()` against a representative zone count.
7. Phase G: Remove temporary instrumentation.
8. Phase H: Live webclient verification of lightning broadcast and
   indoor gating, both deferred from MT-514b-smoke.
9. Phase I: Validation artifact updated with full evidence.

**Frozen what-not-to-do list:**

- DO NOT use the external Pylance interpreter for any timing
  measurement of `run_weather_cycle()`, `tick_weather()`, or
  `get_weather_state()`. The diagnostic established that path is
  structurally broken. All timing measurements must come from
  in-process `@py` against the live server, OR from a properly
  isolated test environment.
- DO NOT modify the public weather API. Specifically these stay
  source-stable: `get_current_weather`, `set_current_weather`,
  `get_weather_state`, `is_weather_plausible_for_climate`,
  `resolve_climate`, `tick_weather`, `run_weather_cycle`. Internal
  helpers may change; consumer surface stays stable.
- DO NOT modify any YAML content file (transition matrices,
  climate compatibility, lightning messages, transition messages).
- DO NOT modify the calendar module, prompt module, prompt
  templates, design docs, or zone YAMLs.
- DO NOT change the broadcast message format, content, or routing
  logic beyond what's necessary for cache integration.
- DO NOT change the persistent attribute storage shape on
  WeatherScript. The cache is in-memory; persistence on the script
  uses the same `weather_state__<zone>` and `weather_meta__<zone>`
  attribute keys as before. This guarantees forward/backward
  compatibility across server restarts.
- DO NOT add async/threading/Twisted-deferred dispatch.
- DO NOT add a new caching library or any third-party dependency.
- DO NOT modify foraging, ranger gather, NPCs, AI pipeline,
  builder, or any consumer of weather state.
- DO NOT add new admin commands, new weather features, or new
  player-facing surfaces.
- DO NOT modify `commands/cmd_weather.py` beyond what's needed to
  surface profiling output during Phases B and D. Restore to
  clean state before final commit.
- DO NOT modify the in-progress feature scope of MT-514c.
  Foraging remains untouched.
- DO NOT expand the ScriptDB fallback into a broader script-access
  refactor. Mirror the existing pattern; do not improve it.

**Stop-and-report conditions:**

- If profiling reveals the bottleneck is somewhere unexpected
  (not in attribute reads or expected hot paths), stop and report
  before implementing the cache. The previous two dispatches
  taught us that hypotheses about where time goes can be wrong;
  do not repeat that mistake by assuming v2a's hypothesis is
  correct without confirmation.
- If the in-process baseline measurement (Phase B) shows
  `run_weather_cycle()` already completes in under 2 seconds, the
  perf problem doesn't exist in the production path and STOP.
  Skip Phases C-G, proceed to Phase H (live verification only).
  Document the surprise in the validation artifact.
- If the in-memory cache requires changing the persistent
  attribute storage shape, stop and report.
- If the cache cannot be safely invalidated across server
  restarts (e.g., the cache loads stale data from a previous
  process), stop and report.
- If race conditions are visible between the WeatherScript's
  `at_repeat()` tick and an admin-issued `set_current_weather()`
  in the same instant, stop and report. We need to understand
  the concurrency model before shipping.
- If Phase C alone brings cycle time below 2 seconds, the agent
  may stop without implementing Phase E (room cache) — but must
  report this decision explicitly so we know Phase E was deemed
  unnecessary.
- If the regression test reveals timing variance that makes
  bounded-time assertions flaky, stop and report.
- If the live lightning verification fails to capture lightning
  in 20 forced ticks during storm state, stop and report.
- If the live indoor verification produces messages in indoor
  rooms (gating broken), stop and report.

## Phase A — ScriptDB fallback in `world/weather.py`

Read `server/conf/at_server_startstop.py` lines 100-140 to see the
existing pattern for safely accessing the `global_weather` script
from any context. The pattern uses `ScriptDB.objects.filter(...)`
as a fallback when `evennia.search_script` is not yet bound.

Replicate that pattern in `world/weather.py`'s `_get_weather_script()`
helper. Approximate shape:

```python
def _get_weather_script():
    """Return the global weather script, working from any context."""
    # Preferred path: evennia.search_script (works in live server)
    search_script = getattr(evennia, "search_script", None)
    if search_script is not None:
        results = search_script("global_weather")
        if results:
            return results[0]

    # Fallback: ScriptDB direct query (works in external interpreters)
    from evennia.scripts.models import ScriptDB
    script = ScriptDB.objects.filter(
        db_key="global_weather",
        db_typeclass_path="world.weather.WeatherScript",
    ).order_by("id").first()
    if script:
        return script

    # No script found via either path
    return None
```

The exact existing helper name and shape may differ; the agent
adapts to match the current code. The constraint is:
- Existing callers must continue to work unchanged
- The fallback must NOT call `create_script()`. If both paths fail,
  return None and let the caller handle absence.

After Phase A, the agent verifies via in-process `@py`:
- `_get_weather_script()` returns the live script
- `_get_weather_script().db_attributes.count()` returns the
  expected number of attributes (around 24 — 12 state + 12 meta)

If the verification fails, stop and report.

## Phase B — In-process re-profile

The agent connects to the live server via webclient as admin
(`jekar`). All measurements use `@py`, NOT external Pylance.

The agent runs each measurement 3 times and reports all 3 values:

1. Wall-clock time for full `run_weather_cycle()`
2. Wall-clock time for `tick_weather()` alone
3. Wall-clock time for `get_weather_state()` alone

For DB query counting via `@py`, use Django's
`connection.queries_log` or wrap calls in
`django.test.utils.CaptureQueriesContext`. The agent is responsible
for finding the right pattern; query counting is informative but
not strictly required if it complicates the in-process measurement.

The agent writes "Phase B — In-Process Baseline Measurements" to
the validation artifact BEFORE proceeding. The entry must include:
- Three runs each of cycle/tick/state with wall-clock times
- Comparison to the (now-known-broken) v1/v2 external measurements
- Identification of the actual primary bottleneck based on the
  in-process numbers
- One sentence: "Primary bottleneck appears to be X; cache plan in
  Phase C is targeting Y."

If `run_weather_cycle()` in-process is under 2 seconds, the perf
problem doesn't exist in the production path. Stop and report.

If it's over 2 seconds, proceed to Phase C.

## Phase C — In-memory state cache

If and only if Phase B confirms the perf problem exists in the
production path, implement the in-memory cache.

### C.1 Cache layer location

The cache is a Python attribute on the WeatherScript instance
(NOT a persistent `db.` attribute). Approximate shape:

```python
class WeatherScript(DefaultScript):
    def at_script_creation(self):
        # ... existing setup ...
        self._zone_state_cache: dict[str, str] = {}
        self._zone_meta_cache: dict[str, dict] = {}
        self._cache_loaded = False

    def at_start(self):
        # Called on script start AND after server reload.
        # Reset cache so a fresh server pass loads from disk.
        self._zone_state_cache = {}
        self._zone_meta_cache = {}
        self._cache_loaded = False

    def _ensure_cache_loaded(self) -> None:
        if self._cache_loaded:
            return
        for attr in self.db_attributes.all():
            key = attr.db_key
            if key.startswith(_WEATHER_STATE_PREFIX):
                zone_id = key[len(_WEATHER_STATE_PREFIX):]
                self._zone_state_cache[zone_id] = attr.value
            elif key.startswith(_WEATHER_META_PREFIX):
                zone_id = key[len(_WEATHER_META_PREFIX):]
                self._zone_meta_cache[zone_id] = attr.value
        self._cache_loaded = True
```

The exact attribute names and persistent-storage layout depend on
the existing implementation. The agent reads the current code and
adapts.

### C.2 Route reads through the cache

`get_current_weather(zone_id)` becomes (approximate):

```python
def get_current_weather(zone_id: str) -> str:
    script = _get_weather_script()
    if script is None:
        return DEFAULT_WEATHER
    script._ensure_cache_loaded()
    return script._zone_state_cache.get(zone_id, DEFAULT_WEATHER)
```

`get_weather_state()` similarly: build the structured snapshot
from the in-memory cache plus any necessary climate config reads.
Zero DB queries in the hot path.

### C.3 Route writes through the cache

`set_current_weather(zone_id, value, *, source)` becomes
(approximate):

```python
def set_current_weather(zone_id: str, value: str, *, source: str = "admin") -> None:
    _validate_weather_value(value)
    script = _get_weather_script()
    if script is None:
        # Existing error path (unchanged)
        return
    script._ensure_cache_loaded()

    # Write-through: update cache AND persist
    script._zone_state_cache[zone_id] = value
    script.attributes.add(f"{_WEATHER_STATE_PREFIX}{zone_id}", value)

    # Existing meta updates also stay; route them through cache too
    # ...
```

The persist call writes to the same `db.` attribute layout that
existed before. No storage shape change; only the read path is
optimized.

### C.4 `tick_weather()` operates on the cache

`tick_weather()` reads each zone's state, computes transitions,
writes back. With the cache:

```python
def tick_weather() -> dict[str, tuple[str, str]]:
    script = _get_weather_script()
    if script is None:
        return {}
    script._ensure_cache_loaded()

    transitions: dict[str, tuple[str, str]] = {}

    for zone_id in _known_zone_ids():
        current = script._zone_state_cache.get(zone_id, DEFAULT_WEATHER)
        # ... existing transition decision logic ...
        next_state = _pick_next_state(current, climate, season)
        if next_state != current:
            script._zone_state_cache[zone_id] = next_state
            script.attributes.add(
                f"{_WEATHER_STATE_PREFIX}{zone_id}",
                next_state,
            )
            transitions[zone_id] = (current, next_state)

    return transitions
```

Now `tick_weather()` does N writes for N changed zones — typically
0-3 — instead of 12 reads + 12 writes per cycle.

## Phase D — Re-profile after Phase C

Run the same in-process measurements as Phase B. Document in
artifact.

If `run_weather_cycle()` is now under 2 seconds, **stop**. Proceed
directly to Phase F (regression test). Skip Phase E.

If still over 2 seconds, the remaining cost is likely in
`_rooms_for_zone()` and broadcast iteration. Proceed to Phase E.

## Phase E — Room-list cache

Only execute if Phase D shows Phase C alone is insufficient.

This is the original Layer 1 from MT-514b-perf v1. Same design:

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

### E.1 Cache invalidation hooks

The agent identifies the right hooks by reading existing code:
- Zone import: `world/worlddata/services/import_zone_service.py`
  or wherever zones get loaded into the live database. Call
  `invalidate_zone_room_cache(zone_id)` after import completes.
- Server boot: clear the cache on startup. Most cleanly done by
  calling `invalidate_zone_room_cache()` (no args) when
  `WeatherScript.at_start()` fires.

If the invalidation hooks are ambiguous, stop and report.

### E.2 Re-profile after Phase E

Run the same in-process measurements. Confirm
`run_weather_cycle()` under 2 seconds.

## Phase F — Regression test

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

Run the test in a properly isolated test environment (not against
the live server). The "warm" measurement is what matters —
cold-start cache build can be slower because it happens once per
process.

If the test environment has zero zones, the test passes trivially.
The regression catches future code that accidentally reintroduces
uncached DB access in the hot path.

## Phase G — Remove instrumentation

Remove all temporary profiling/timing code added in Phases B and D.
The instrumentation served its purpose. The regression test from
Phase F is the long-term performance guard.

The agent verifies via grep that no `time.monotonic()`,
`reset_queries()`, `connection.queries_log`,
`CaptureQueriesContext`, or similar profiling artifacts remain in
`world/weather.py` or `commands/cmd_weather.py`.

## Phase H — Live verification

Now that the system is fast (or confirmed already fast in Phase B),
run the verifications deferred from MT-514b-smoke. Use the same
webclient transport patterns that worked previously.

### H.1 Lightning broadcast verification

1. Connect to webclient as admin (`jekar`).
2. Teleport to outdoor weather-capable room: `@teleport #4213`
   (verified in MT-514b-smoke pre-flight).
3. Run `look` — capture room.
4. Run `@weather new_landing storm`.
5. Run `@weather tick` repeatedly. With the perf fix (or
   confirmation that no fix was needed), ticks complete in under
   a second, so 20 ticks is feasible in under a minute.
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

### H.2 Indoor gating verification

1. Teleport to indoor room: `@teleport #4212`.
2. Run `look` — capture indoor room.
3. Run `@weather new_landing clear` then `@weather new_landing storm`.
4. Run `@weather tick` 5 times.
5. Capture verbatim output. The output must include:
   - Admin command echoes for each command
   - Tick summaries showing zone transitions
   - **NO transition messages** (no rain or storm narration)
   - **NO lightning messages**

If transition or lightning messages DO appear in the indoor
room's feed, the gating is broken. Stop and report.

The verification is positive evidence that the absence holds.
The captured output, with surrounding admin-echo context proving
that ticks did fire and zones did transition, IS the evidence.

## Phase I — Validation artifact

APPEND a new section to `exports/mt514b_weather_validation.md`
titled `## MT-514b-perf-v2a — Cache fix and final verification`.

Section contents:

1. **Phase A summary.** Confirmation that `_get_weather_script()`
   now works in any context. Note the small structural fix that
   future external profiling/test scripts will benefit from.
2. **Phase B in-process baseline.** Verbatim three-run measurements
   for cycle/tick/state. Comparison to (broken) v1/v2 external
   measurements. Identification of actual bottleneck.
3. **Phase C implementation.** What was added (in-memory cache),
   how invalidation works, what was deliberately NOT changed.
   Skipped if Phase B showed perf problem doesn't exist.
4. **Phase D post-fix profiling.** Same in-process measurements,
   showing improvement. Skipped if Phase C was skipped.
5. **Phase E decision.** Either "Phase C sufficient, skipped Phase
   E" with the post-Phase-D numbers, or "Phase E required" with
   the design and post-Phase-E numbers. Skipped if Phase B showed
   no perf problem.
6. **Phase F regression test.** Test name and bounded threshold.
7. **Phase G confirmation.** No profiling code left in tree.
8. **Phase H.1 lightning evidence.** Verbatim webclient output.
9. **Phase H.2 indoor gating evidence.** Verbatim webclient output.
10. **Final state.** One sentence: "MT-514b is now fully closed."

If any phase blocked, the section ends with the BLOCKED status
and the specific reason.

## Verification checklist

1. ScriptDB fallback added to `world/weather.py`,
   `_get_weather_script()` works in any context.
2. Phase B in-process measurements taken (NOT external Pylance).
3. Either: Phase B shows production path is already fast (<2s) OR
   Phase C cache implemented and Phase D confirms substantial
   improvement.
4. Phase E either skipped (with justification) or implemented with
   measured benefit.
5. Final cycle time under 2 seconds (target) or 500ms (stretch).
6. Phase F regression test added and passes.
7. All previously-passing tests still pass.
8. Phase G confirms no profiling code left in the tree.
9. Phase H.1 lightning message captured live in outdoor room.
10. Phase H.2 indoor room receives no broadcasts (verbatim
    evidence).
11. Validation artifact appended with full evidence.
12. No code outside the in-scope list modified.

## Stop conditions

- Edit only `world/weather.py`, `tests/test_weather.py`, the
  validation artifact, and (only if cache invalidation requires
  it in Phase E) `world/worlddata/services/import_zone_service.py`
  or similar zone-import points.
- Stop and report on any unexpected profiling result.
- Stop and report if the in-memory cache requires storage shape
  changes.
- Stop and report on cache invalidation ambiguity.
- Stop and report if race conditions are visible between the tick
  and admin set commands.
- Stop and report if Phase B shows the perf problem doesn't exist
  in production path (positive outcome, but document explicitly).
- Stop and report if Phase C alone is sufficient (skip Phase E
  with explicit justification).
- Stop and report on lightning failure or indoor gating failure.
- Do not "while I'm here" refactor unrelated weather internals.
- Do not use external Pylance interpreter for any timing
  measurements.

## Required artifacts

1. Updated `world/weather.py` (ScriptDB fallback, in-memory cache
   if needed, possibly room cache, instrumentation removed)
2. Updated `tests/test_weather.py` (regression test added)
3. Possibly updated zone-import service (one-line cache
   invalidation call) — only if Phase E is executed
4. Updated `exports/mt514b_weather_validation.md` (new section
   appended)

## Followup queue

- MT-514b-invasion: Add `current_invasion` runtime state with
  `@invasion` admin command. Same persistence pattern as weather.
  Will benefit from the in-memory cache pattern established here —
  apply the same architectural approach (cache + write-through)
  from the start rather than shipping slow and fixing later. Apply
  the ScriptDB fallback pattern in the invasion module from day
  one.
- MT-514c: Foraging refactor consuming terrain + skill rank +
  calendar + weather + invasion. Now safe to build on a perf-tuned
  weather foundation.
- Future architectural note: any other system that uses Evennia
  persistent attributes for frequently-read state should follow
  the same in-memory-cache + write-through pattern. Any new
  singleton script should include the ScriptDB fallback in its
  access helper. Worth documenting as a project convention in
  `docs/architecture/`.