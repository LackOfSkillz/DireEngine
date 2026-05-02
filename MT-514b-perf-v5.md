# MT-514b-perf-v5 — Zone payload + state caches, ship the perf arc closure

## Background

MT-514b-perf-v4 fixed a real script-lifecycle bug that was silently
wiping the v3a broadcast cache on every weather operation. After
that fix, the warm-cache production cycle dropped from 28-31s
broadcast loop down to 0.234s broadcast. Total cycle time went from
60+s observed in production to 6.453s primed.

Better. Not yet good enough — the v4 acceptance gate was 2 seconds
and 6.5s is still going to be felt by players as a brief freeze
every ~3.75 real minutes in steady state.

The v4 profiling identified the remaining cost cleanly:

- `tick_weather_payloads`: 3.219s (zone payload loading per cycle)
- `get_weather_state_total`: 2.937s (internal `get_weather_state()`
  call iterating all zones reading state/climate/meta via Evennia
  attributes)
- broadcast: 0.234s (already fast)
- everything else: ~0.06s

The two dominant phases together account for 95% of remaining
cycle time. Both involve per-zone repeated work that can be cached
in memory with write-through persistence — the same pattern v3a
established for room lists, just applied to a different layer.

This dispatch:
1. Adds in-memory caches for zone payloads and zone weather state,
   matching v3a's architectural pattern.
2. Verifies post-fix cycle time in production (the live game's
   actual database state, not a test fixture).
3. Updates the regression test to reflect production-shape data
   per v4 Phase G (deferred from v4).
4. Reverts the autotick mitigation that v4 left in place.
5. Confirms via live observation that natural ticks no longer
   stall the server.
6. Closes the perf arc.

If v5 verifies cleanly in production, the perf arc that started
with MT-514b-perf v1 finally closes. Six dispatches: four blocked
or partial, two shipped (v3a fixed broadcast cost, v4 fixed
cache-lifecycle bug, v5 fixes the remaining zone payload + state
cost). The system is then ready for MT-514b-invasion and MT-514c.

## Architectural guardrails (READ FIRST)

The leash discipline that's served us through six dispatches
applies in full. v5 has a clearer diagnosis than any prior
dispatch — v4's profile data identified two specific dominant
phases — so the implementation is well-targeted. But the
production verification gate is still the closing condition.

**Frozen scope:**

1. Phase A: Implement in-memory zone payload cache. Write-through
   invalidation when zone payload changes (zone import, etc.).
2. Phase B: Implement in-memory zone state cache covering whatever
   `get_weather_state()` reads per-zone (current state, climate,
   metadata). Write-through on `set_current_weather()` and any
   other mutation path.
3. Phase C: Re-profile in production with all three cache layers
   (rooms from v3a, payloads from A, state from B) active.
4. Phase D: Acceptance gate — cycle under 2 seconds in production.
   If it isn't, stop and report.
5. Phase E: Remove all instrumentation v4 added.
6. Phase F: Update or replace the regression test per v4 Phase G
   options.
7. Phase G: Revert the autotick mitigation (`WEATHER_AUTOTICK_ENABLED`
   set to True or removed from `server/conf/settings.py`).
8. Phase H: Live observation that natural ticks don't stall the
   server.
9. Phase I: Validation artifact updated. Perf arc closed.

**Frozen what-not-to-do list:**

- DO NOT remove or weaken any existing cache layer. v3a's room
  cache and v4's lifecycle fix are real and needed; v5 ADDS new
  cache layers, doesn't replace existing ones.
- DO NOT modify the public weather API. Source-stable:
  `get_current_weather`, `set_current_weather`, `get_weather_state`,
  `is_weather_plausible_for_climate`, `resolve_climate`,
  `tick_weather`, `run_weather_cycle`. Internal helpers may change.
- DO NOT change the persistent attribute storage shape on
  WeatherScript. Cache is in-memory only.
- DO NOT modify any YAML content file, calendar module, prompt
  module, prompt templates, design docs, or zone YAMLs.
- DO NOT change broadcast message format, content, or routing.
- DO NOT add async/threading/Twisted-deferred dispatch.
- DO NOT add a new caching library or any third-party dependency.
- DO NOT modify foraging, ranger gather, NPCs, AI pipeline,
  builder, or any consumer of weather state.
- DO NOT add new admin commands, new weather features, or new
  player-facing surfaces.
- DO NOT modify the in-progress feature scope of MT-514c.
- DO NOT investigate the webclient `@py` long-command transport
  issue; use `evennia shell -c` with base64-encoded payloads as
  the standing pattern that works.
- DO NOT skip Phase G (mitigation revert) under any circumstances.
  Leaving autotick disabled in production silently breaks weather
  progression for players.
- DO NOT skip Phase H (live observation). The arc closure depends
  on confirming the natural tick path actually behaves correctly,
  not just that the profiled cycle is fast.
- DO NOT "while I'm here" refactor unrelated weather internals.

**Stop-and-report conditions:**

- If implementing the zone payload cache requires changing how
  zones are loaded or stored elsewhere in the codebase (beyond
  the weather module), stop and report.
- If invalidation hooks for the zone payload cache are ambiguous,
  stop and report. Same standard as v3a — we need invalidation
  correct or stale state will silently happen.
- If the zone state cache has subtle race conditions with
  `set_current_weather()` calls happening during a cycle, stop
  and report. The write-through pattern works in single-threaded
  Twisted reactor contexts but I want the agent to confirm there
  isn't a path that breaks it.
- If Phase D shows the post-fix cycle is still over 2 seconds,
  stop and report. Do not chain a third targeted fix into this
  dispatch. The pattern of "single fix per dispatch" has worked
  through six dispatches — preserve it.
- If Phase F regression test infrastructure changes are
  unreasonable, the agent picks v4 Phase G's Option B (minimal
  test plus documented production verification command) and
  notes the choice.
- If Phase H observation shows the natural tick path stalls the
  server even after the profiled cycle verifies under 2s, stop
  and report. Same condition as v4 Phase I — natural tick must
  match profile measurement.
- If anything during execution suggests v3a's fix or v4's fix has
  regressed (e.g., broadcast cost is back up, cache wiping is
  back), stop and report immediately.

## Phase A — Zone payload cache

The agent reads `world/weather.py` to identify how
`tick_weather_payloads` accumulates time. Likely path: per-zone,
the cycle calls something like `_get_zone_payload(zone_id)` or
`_iter_zone_payloads()` that loads the payload from disk or
recomputes it. With 12 zones × ~270ms each, that's the 3.2s
visible in v4's profile.

### A.1 Add the cache layer

Approximate shape:

```python
_ZONE_PAYLOAD_CACHE: dict[str, dict] = {}

def _get_zone_payload(zone_id: str) -> dict | None:
    """Return the zone payload, with caching."""
    cached = _ZONE_PAYLOAD_CACHE.get(zone_id)
    if cached is not None:
        return cached
    payload = _load_zone_payload(zone_id)  # existing path, renamed
    if payload is not None:
        _ZONE_PAYLOAD_CACHE[zone_id] = payload
    return payload

def invalidate_zone_payload_cache(zone_id: str | None = None) -> None:
    if zone_id is None:
        _ZONE_PAYLOAD_CACHE.clear()
    else:
        _ZONE_PAYLOAD_CACHE.pop(zone_id, None)
```

If `_iter_zone_payloads()` exists and is the dominant path, the
cache should also serve that — possibly by caching the full list
of zone payloads, not just per-zone.

### A.2 Cache invalidation

Same hooks as v3a's room cache:
- Zone import: `world/worlddata/services/import_zone_service.py`
  or wherever zone YAML reload happens. Already invalidating
  room caches there per v3a — extend the existing invalidation
  function to also clear payload caches.
- Server boot: `WeatherScript.at_start()` already clears caches.
  Extend it to clear payload caches too.

If v3a's invalidation function is named `invalidate_zone_caches`
(or similar), the v5 implementation extends it to cover payloads
in addition to rooms. This keeps the invalidation API consolidated.

### A.3 Wire the cache into the cycle

The agent updates `tick_weather()` and any other consumer of zone
payloads to use the cached `_get_zone_payload()` / `_iter_zone_payloads()`
helpers. First call per zone takes the same time as today;
subsequent calls return cached results in microseconds.

## Phase B — Zone state cache

The agent reads `world/weather.py` to identify how
`get_weather_state_total` accumulates time. Likely path:
`get_weather_state()` iterates all zones, reading per-zone weather
state, climate, and metadata via Evennia persistent attributes.
With 12 zones × ~250ms each, that's the 2.9s visible in v4's
profile.

### B.1 Add the cache layer

Approximate shape:

```python
class WeatherScript(DefaultScript):
    def at_script_creation(self):
        # ... existing setup ...
        self._zone_state_cache: dict[str, str] = {}
        self._zone_meta_cache: dict[str, dict] = {}
        self._cache_loaded = False

    def at_start(self):
        # Reset on server boot OR script (re)start
        self._zone_state_cache = {}
        self._zone_meta_cache = {}
        self._cache_loaded = False
        # ... existing v3a/v4 cache invalidation ...

    def _ensure_state_cache_loaded(self) -> None:
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

The exact attribute prefixes (`_WEATHER_STATE_PREFIX`,
`_WEATHER_META_PREFIX`) depend on the existing implementation.
The agent reads current code and adapts.

### B.2 Route reads through the cache

`get_current_weather(zone_id)` and any internal-helper analog that
reads weather state route through the cache:

```python
def get_current_weather(zone_id: str) -> str:
    script = _get_weather_script()
    if script is None:
        return DEFAULT_WEATHER
    script._ensure_state_cache_loaded()
    return script._zone_state_cache.get(zone_id, DEFAULT_WEATHER)
```

`get_weather_state()` builds its structured snapshot from the
in-memory caches plus any necessary climate/config reads. Per-zone
attribute reads disappear from the hot path.

### B.3 Route writes through the cache

`set_current_weather(zone_id, value, *, source)` writes to both:

```python
def set_current_weather(zone_id: str, value: str, *, source: str = "admin") -> None:
    _validate_weather_value(value)
    script = _get_weather_script()
    if script is None:
        return
    script._ensure_state_cache_loaded()

    # Write-through: update cache AND persist
    script._zone_state_cache[zone_id] = value
    script.attributes.add(f"{_WEATHER_STATE_PREFIX}{zone_id}", value)

    # Existing meta updates also stay; route them through cache too
    # ...
```

Same write-through pattern for meta updates.

### B.4 `tick_weather()` operates on the cache

`tick_weather()` reads each zone's state, computes transitions,
writes back. With the cache in place, the per-zone reads become
dict lookups. Writes still persist via `script.attributes.add()`
but only for zones that actually changed state.

If 12 zones tick and 0-3 transition, that's 12 reads (now from
cache) plus 0-3 persistence writes — instead of 12 attribute
reads plus 12 attribute writes the previous code may have been
doing.

## Phase C — Re-profile in production

With the autotick mitigation still in place, the agent re-runs
the v4 profiling pattern in production:

```python
import time
from world import weather
# Prime caches once
weather.run_weather_cycle()
weather.reset_phase_timings()
# Measure warm cycle
started = time.monotonic()
transitions = weather.run_weather_cycle()
elapsed = time.monotonic() - started
timings = weather.get_phase_timings()
print('WARM_PROFILE elapsed={:.3f}s transitions={}'.format(elapsed, len(transitions)))
for name in sorted(timings):
    values = timings[name]
    print(f'{name}={sum(values):.3f}s count={len(values)}')
```

Use the `evennia shell -c` with base64-encoded payload pattern
that worked in v4. If that's still reliable, single-run trusted
data is sufficient — same trade-off accepted in v3a and v4.

The agent writes "Phase C — Post-Cache Production Profile" to the
validation artifact with verbatim per-phase breakdown showing
both the v4 baseline (6.453s warm) and the v5 result.

## Phase D — Acceptance gate

If the warm production cycle is under 2 seconds, proceed to Phase E.

If between 2 and 5 seconds, the agent stops and reports. We'll
discuss whether partial success is shippable or whether v6 is
needed. Document the result honestly — don't ship past the gate
just to close the arc.

If still over 5 seconds, the diagnosis was wrong or the cache
wiring has a subtle issue. Stop and report.

## Phase E — Remove instrumentation

Remove all temporary profiling code. Verify via grep that no
`_phase_timings`, `_record_phase`, `get_phase_timings`,
`reset_phase_timings`, or similar profiling artifacts remain in
`world/weather.py` or `commands/cmd_weather.py`.

The regression test from Phase F is the long-term performance
guard.

## Phase F — Production-shape regression test

Update or replace the regression test from v3a / v4 so it actually
reflects production-shape data. Pick the option from v4's Phase G:

**Option A: Test fixture loads multiple zones with representative
room counts.** Hardest to set up but best for catching real
regressions.

**Option B: Minimal test stays + documented production verification
command.** Pragmatic. The validation artifact records an `@py`
or `evennia shell -c` snippet the admin runs periodically to
verify production cycle time.

**Option C: Both.** Fast minimal test for CI plus a separate
opt-in production-shape test marked `@unittest.skip` by default.

The agent picks based on what's achievable without unreasonable
test infrastructure changes. Documents the choice in the
validation artifact.

## Phase G — Revert the autotick mitigation

In `server/conf/settings.py`, set `WEATHER_AUTOTICK_ENABLED = True`
(or remove the setting entirely — the `getattr` default in
`at_repeat()` handles absence).

The mitigation gate code in `at_repeat()` stays in place. It's
inert when the flag is True. Keeping the mechanism in code makes
future temporary mitigations trivial to deploy.

Restart the live server. Confirm via `@py` or `evennia shell -c`
that `WEATHER_AUTOTICK_ENABLED` resolves to True and that
`at_repeat()` is now calling `run_weather_cycle()` again (a
temporary call counter — added then removed — verifies this if
the agent wants explicit evidence).

## Phase H — Live observation

After the mitigation reverts, observe the live server for at
least 10 minutes (covers 2-3 natural tick intervals). The agent
sits in an authenticated session and:

1. Sends cheap commands every 30 seconds (`look`, `who`,
   `@calendar`).
2. Checks weather state (`@weather`) after each natural tick
   interval.
3. Notes whether commands ever stall for more than 1 second
   during the observation window.

If commands respond consistently and weather state progresses
across natural tick intervals, the perf arc is closed.

If commands stall during natural tick intervals (longer than the
profiled cycle time would suggest), STOP and report. The natural
tick path differs from the profiled path in a way we haven't
characterized — same stop condition as v4 Phase I.

If authentication is an issue (as it was in v4 — webclient
session attach was unreliable post-restart), the agent can
substitute a `evennia shell -c` based observation: time the
script's `at_repeat()` execution by triggering it manually and
measuring, repeated several times.

## Phase I — Validation artifact

APPEND a new section to `exports/mt514b_weather_validation.md`
titled `## MT-514b-perf-v5 — Zone payload + state caches, perf arc closure`.

Section contents:

1. **Phase A zone payload cache.** What was added, where
   invalidation fires.
2. **Phase B zone state cache.** What was added, the write-through
   pattern, what was deliberately NOT changed.
3. **Phase C post-cache profile.** Per-phase breakdown showing
   improvement from v4's 6.453s baseline.
4. **Phase D acceptance.** Production cycle time confirmed under
   2 seconds.
5. **Phase E confirmation.** No profiling code left in tree.
6. **Phase F regression test.** Which option chosen and why.
7. **Phase G mitigation revert.** Confirmation autotick re-enabled.
8. **Phase H live observation.** Verbatim notes on command
   responsiveness across natural tick intervals.
9. **Final state.** One sentence: "MT-514b is now fully closed.
   The perf arc is complete."

Add a brief retrospective at the end of the section listing what
each shipped fix contributed:
- v3a: broadcast cache (collapsed broadcast loop time)
- v4: script-lifecycle fix (made v3a's cache actually work)
- v5: zone payload + state caches (eliminated remaining per-zone
  reads)

If any phase blocked, the section ends with the BLOCKED status
and the specific reason.

## Verification checklist

1. Phase A zone payload cache implemented with proper invalidation.
2. Phase B zone state cache implemented with write-through
   persistence.
3. Phase C re-profiles production with all caches in place.
4. Phase D confirms production cycle under 2 seconds.
5. Phase E confirms no profiling code left in tree.
6. Phase F updates the regression test per chosen option.
7. Phase G reverts the autotick mitigation.
8. Phase H confirms natural ticks don't stall the server.
9. Validation artifact updated with full evidence.
10. No code outside the in-scope list modified.
11. All previously-passing tests still pass.

## Stop conditions

- Edit only `world/weather.py`, `tests/test_weather.py`,
  `server/conf/settings.py`, the validation artifact, and (if
  Phase A invalidation requires it) zone-import service or
  similar. No other files.
- Stop and report on cache invalidation ambiguity.
- Stop and report on race conditions.
- Stop and report if Phase D shows the fix didn't work.
- Stop and report if Phase H shows natural tick stalls despite
  profiled cycle being fast.
- Do not attempt multiple targeted fixes in the same dispatch.
- Do not skip Phase G (mitigation revert) or Phase H (live
  observation) under any circumstances.

## Required artifacts

1. Updated `world/weather.py` (zone payload cache, zone state
   cache, instrumentation removed)
2. Updated `server/conf/settings.py` (mitigation reverted)
3. Updated `tests/test_weather.py` (regression test per chosen
   option)
4. Possibly updated zone-import service if invalidation requires
5. Updated `exports/mt514b_weather_validation.md` (new section
   appended)

## Followup queue

- MT-514b-invasion: Add `current_invasion` runtime state with
  `@invasion` admin command. Apply ALL the patterns established in
  the perf arc from day one: ScriptDB fallback (v2a), script-
  lifecycle care (don't call `start()` on running scripts — v4),
  per-zone room/payload/state caches with write-through (v3a, v5),
  and bounded-time regression test with production-shape
  verification (v5). Invasion does not need to repeat any part of
  this arc.
- MT-514c: Foraging refactor consuming terrain + skill rank +
  calendar + weather + invasion. Now safe to build on a perf-tuned
  weather foundation.
- Document the runtime state cache pattern in
  `docs/architecture/runtime_state_patterns.md` after this dispatch
  closes. The pattern (ScriptDB fallback + per-zone in-memory
  caches + write-through persistence + careful script lifecycle +
  bounded-time regression test + production-shape verification) is
  the project convention for any frequently-read Evennia
  persistent state.
- Webclient long-command transport issue: still unresolved. Document
  in followups but don't investigate as part of this dispatch. The
  `evennia shell -c` base64 pattern is the standing workaround.
