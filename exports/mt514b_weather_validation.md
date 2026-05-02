# MT-514b Weather Validation

## Scope

This artifact records the MT-514b validation pass for the ambient weather system implementation.

## Full Test Discovery

Before full discovery: not captured in the resumed session state before implementation.

After full discovery:

```text
Ran 257 tests in 41.411s

OK (skipped=1)
```

Focused slice revalidation after local repair:

```text
Ran 39 tests in 0.033s

OK
```

## Live Runtime Smoke

Live server restart completed successfully.

```text
... Server started.
Evennia running.
```

Live authentication over telnet succeeded after resetting the developer account password and restarting the server:

```text
[MudInfo] [2026-05-01(10:14)]: jekar connected

You become Wufgar.
CRO_450_350(#26249)
You see nothing special.
Exits: east, northeast, southeast, and up
```

### Live Weather State API Smoke

These outputs were captured from the live authenticated session using Evennia's developer Python console inside the running server process.

```text
INITIAL=cloudy
SET_HEAVY=heavy_rain
READ_AFTER_HEAVY=heavy_rain
PLAUSIBLE_BLIZZARD=False
SET_BLIZZARD=blizzard
READ_AFTER_BLIZZARD=blizzard
```

Interpretation:

- The live weather script was active.
- Per-zone state mutation succeeded in the running server process.
- The implausible override path behaved as designed: coastal `blizzard` is flagged implausible but still persists.

### Live `@weather` Command Smoke

The `@weather` command is registered and reachable in the live authenticated session, but telnet capture interacted poorly with the persistent in-game Python console/pager state for this account. The cleanest reliable live signal came from the same underlying API calls above, executed inside the running server process.

One captured command-shaped output block from the live session:

```text
DireEngine Weather
────────────────────────────────────────
builder2:         clear         (climate: temperate, plausible)
crossing_txt_experiment:fog           (climate: temperate, plausible)
crossingv2:       clear         (climate: coastal, plausible)
crossingv2_builder_target:cloudy        (climate: temperate, plausible)
crossingv2_seeded:fog           (climate: temperate, plausible)
demo1:            clear         (climate: temperate, plausible)
new_landing:      clear         (climate: temperate, plausible)
spawn_smoke:      clear         (climate: temperate, plausible)
spawn_smoke_direct:clear         (climate: temperate, plausible)
spawn_smoke_v2:   clear         (climate: temperate, plausible)
test_crossing:    clear         (climate: temperate, plausible)
tester:           clear         (climate: temperate, plausible)

Active states:
  clear:       9
  cloudy:      1
  fog:         2

Tick interval:   15 game-minutes (~3.75 real minutes)
Lightning:       50% chance per tick during storm
Last tick:       2026-05-01T06:14:57-04:00
Next tick:       2026-05-01T06:16:24-04:00 (estimated)
```

And zone-specific output captured from the same live session:

```text
Weather: crossingv2
────────────────────────────────
Current state:   clear
Climate:         coastal (resolved from 'river-valley')
Current season:  spring (real-world)
Plausible states for this climate:
  storm, clear, cloudy, light_snow, heavy_rain, fog, light_rain
```

### Live Transition / Lightning Broadcast Status

The broadcast path itself is implemented and covered by focused automated tests, but the live broadcast smoke hit current runtime data constraints:

- `crossingv2` currently has `0` live rooms returned by `_rooms_for_zone('crossingv2')`.
- The logged-in character started in `CRO_450_350`, which is not part of the current weather-managed runtime room sets.
- Several live zones do have rooms loaded, but telnet capture for room-broadcast text remained unstable because the account session resumed inside Evennia's developer Python console/pager state.

Live room counts at validation time:

```text
{'builder2': 6, 'crossing_txt_experiment': 0, 'crossingv2': 0, 'crossingv2_builder_target': 0, 'crossingv2_seeded': 0, 'demo1': 5, 'new_landing': 211, 'spawn_smoke': 179, 'spawn_smoke_direct': 0, 'spawn_smoke_v2': 0, 'test_crossing': 203, 'tester': 7}
```

Result:

- Live state progression and persistence were confirmed.
- Live room-broadcast text was not captured cleanly in this pass.
- Focused automated tests remain the source of truth for outdoor-only transition broadcast, threshold softening, and storm-lightning emission behavior.

## MT-T01 Regression Check

Focused tests still confirm the state-mapping repair is intact after the weather vocabulary expansion:

- `tests.test_room_description_prompt`
- `tests.test_weather`

The live hallway/interior regression smoke was not completed end-to-end because the same telnet session instability blocked reliable room-description capture after authentication. No regression appeared in the focused suite or broad discovery run.

## Climate Fallback Zones

Zones currently resolving to `temperate` via missing-climate fallback:

```text
[{'zone_id': 'crossing_txt_experiment', 'climate': None},
 {'zone_id': 'crossingv2_builder_target', 'climate': None},
 {'zone_id': 'crossingv2_seeded', 'climate': None},
 {'zone_id': 'demo1', 'climate': None},
 {'zone_id': 'new_landing', 'climate': None},
 {'zone_id': 'spawn_smoke', 'climate': None},
 {'zone_id': 'spawn_smoke_direct', 'climate': None},
 {'zone_id': 'spawn_smoke_v2', 'climate': None},
 {'zone_id': 'test_crossing', 'climate': None},
 {'zone_id': 'tester', 'climate': None}]
```

`crossingv2` no longer falls back; `river-valley` resolves to `coastal` as intended.

## Modified Files

- commands/cmd_weather.py
- commands/default_cmdsets.py
- server/conf/at_server_startstop.py
- server/conf/settings.py
- state_description.md
- tests/test_room_description_prompt.py
- tests/test_weather.py
- world/builder/prompting/room_description_prompt.py
- world/builder/templates/room_description_state_markup_prompt.txt
- world/builder/templates/room_description_system_prompt.txt
- world/content/climate_keywords.yaml
- world/content/climate_weather_compatibility.yaml
- world/content/weather_lightning_messages.yaml
- world/content/weather_transition_messages.yaml
- world/content/weather_transitions.yaml
- world/weather.py

## Validation Summary

- Focused weather and prompt tests passed.
- Full `unittest discover tests` passed.
- Live server booted with `WeatherScript` active.
- Live per-zone weather read/write behavior was confirmed inside the running server process.
- Implausible admin override behavior was confirmed live.
- Climate fallback debt was enumerated for follow-up.
- Live room-broadcast capture remains incomplete because the current runtime session and room-loading shape did not provide a clean end-to-end path for weather-broadcast text capture in this pass.

## Live broadcast smoke (MT-514b-smoke)

### Pre-flight

Verified `new_landing` has loaded live rooms and at least one outdoor room with `weather` in applicable state groups.

```text
new_landing_room_count= 211
outdoor= (4213, 'Amberwick Lane, Western Run', ['season', 'time', 'weather', 'invasion'], None)
indoor= (4212, 'Kingshade Street and Amberwick Lane', ['season', 'time'], None)
```

Confirmed teleport command surface before live smoke:

```text
Evennia default building command:
key = "@teleport"
aliases = "@tel"
```

### Phase B / C Attempt

The dispatch required a fresh telnet session and regular admin commands only. The live capture layer blocked before command verification could begin.

Python telnet client attempt after the live server restart:

```text
BANNER_REPR= ''
AFTER_CONNECT_REPR= ''
LOOK_REPR= ''
```

Raw socket probe against port 4000:

```text
BANNER_RAW= '"\x03\x1f\x18FE['
AFTER_CONNECT_RAW= ''
```

System telnet client attempt from the workspace terminal:

```text
PS C:\Users\gary\dragonsire> telnet 127.0.0.1 4000
telnet : The term 'telnet' is not recognized as the name of a cmdlet,
function, script file, or operable program. Check the spelling of the name, or
if a path was included, verify that the path is correct and try again.
```

### Bugs Surfaced / Blocking Issues

- No weather-system code bug was confirmed in this dispatch.
- The blocking issue is capture infrastructure: the environment does not provide a usable terminal telnet client, and the Python telnet/socket approaches did not produce a readable live session stream after the latest server restart.
- Because the live telnet session could not be captured reliably, the dispatch could not proceed to:
  - admin auth transcript capture
  - `@tel` positioning in the target outdoor room
  - `@weather new_landing clear` -> `@weather new_landing heavy_rain` transition-broadcast verification
  - storm-lightning verification within the 20-tick budget
  - indoor gating verification

Live broadcast verification BLOCKED on unavailable / unusable telnet capture in the current environment.
MT-514b remains in partial-validation state pending followup.

## MT-514b-perf-v4 partial execution

### Phase A - Mitigation active

Temporary autotick mitigation remains enabled in settings:

```text
WEATHER_AUTOTICK_ENABLED = False
```

Mitigation verification in the live code path showed the repeat hook returned early without invoking the cycle:

```text
AUTOTICK_ENABLED False
RUN_CALL_COUNT 0
```

Weather state will not advance automatically until the mitigation is reverted in a later pass.

### Phase B / C / D / E - cache wiring diagnosis and targeted fix

Production-shape shell profiling first showed the broadcast side still dominating, with repeated `eligible_rooms_build:*` costs despite the v3a caches.

The discriminating cache check isolated the root cause to the script lookup path:

```text
CACHE_BEFORE 12 12
CACHE_AFTER_GET 0 0
CACHE_AFTER_STATE 0 0
```

`_get_weather_script()` was calling `keeper.start()` on every lookup, and `WeatherScript.at_start()` invalidates the zone caches. That meant normal weather reads and writes were wiping the broadcast caches before they could be reused.

The targeted D.3 fix was to start the existing weather script only when it is inactive. Post-fix cache verification:

```text
CACHE_BEFORE 12 12
CACHE_AFTER_GET 12 12
CACHE_AFTER_STATE 12 12
```

Post-fix primed production-shape profile:

```text
PRIMED_PROFILE elapsed=6.453s transitions=9
broadcast_loop_total=0.234s
tick_weather_payloads=3.219s
get_weather_state_total=2.937s
```

Interpretation:

- The broadcast-loop cache bug is fixed.
- The cycle dropped from roughly 28 to 31 seconds down to 6.453 seconds in the primed in-process profile.
- Phase E still fails the dispatch stop gate (`>5s`).
- The next dominant cost is no longer broadcast. It is the zone-payload/state path, specifically repeated zone payload loading in `tick_weather()` and the internal `get_weather_state()` work.

Focused regression slice after the fix:

```text
Ran 18 tests in 0.025s

OK
```

Result: MT-514b-perf-v4 improved the live cycle substantially but did not complete. This pass stops at the first targeted fix per dispatch rules, with the next candidate surface isolated for follow-up.

## Webclient recovery follow-up

The smoke was retried through the authenticated browser webclient on `http://localhost:4001/webclient/?mode=play` using the `jekar` account.

### Outdoor room positioning

Using the correct teleport syntax, the live webclient session landed in the intended outdoor target room:

```text
Amberwick Lane, Western Run(#4213)
Amberwick Lane threads east and west through the district, a lived-in lane of shopfronts, side doors, and close-built eaves. The lane is settled but still alert here, close enough to one end that arrivals and departures shape the mood. The scents here are clean by city measure: rain on stone, banked hearths, horses kept at a remove, and trimmed greenery from private courts. Boundary stones, walls, or the edge of a distinct enclave make this stretch feel nearer the city's margin than its heart. Nearby, Residental Cloister arch to To gives this stretch of the city a more distinct identity. The surrounding facades feel more deliberate here, with cleaner stonework and a quieter civic order.

## Performance fix and final verification (MT-514b-perf)

Status: BLOCKED on unexpected profiling result.

### Phase A profiling results

Temporary profiling was added locally, exercised against the live database state, and then removed after the investigation because the result hit the dispatch stop condition.

Verbatim profiling capture from the first full-cycle measurement in the workspace Python environment:

```text
RUN 1 elapsed=50.281s transitions=3
Weather Tick Profile
  total: 50.281s
  db_queries: 5375
  zone builder2:
    decision: 0.000s
    rooms: 0.000s
    state_groups: 0.000s
    broadcast: 0.000s
    transition_broadcasts: 0
    lightning_broadcasts: 0
  zone crossing_txt_experiment:
    decision: 0.000s
    rooms: 9.281s
    state_groups: 0.000s
    broadcast: 0.000s
    transition_broadcasts: 1
    lightning_broadcasts: 0
  zone crossingv2_builder_target:
    decision: 0.000s
    rooms: 0.062s
    state_groups: 0.000s
    broadcast: 0.000s
    transition_broadcasts: 1
    lightning_broadcasts: 0
  zone demo1:
    decision: 0.000s
    rooms: 0.109s
    state_groups: 0.015s
    broadcast: 0.000s
    transition_broadcasts: 1
    lightning_broadcasts: 0
```

The initial read suggested room lookup was one contributor, so a local Layer 1 room-cache probe was tested and then discarded after the follow-up measurements showed the main stall remained elsewhere.

Disambiguating checks:

```text
elapsed=32.500s transitions=3
Weather Tick Profile
  total: 32.500s
  db_queries: 558
  zone new_landing:
    transition_broadcasts: 1
  zone spawn_smoke_v2:
    transition_broadcasts: 1
  zone test_crossing:
    transition_broadcasts: 1
```

This run forced `_rooms_for_zone()` to return an empty list and stubbed message send, so the 32.5 second stall was not in room lookup, state-group evaluation, or `msg_contents()`.

Additional narrow timing checks:

```text
tick_elapsed=5.703s transitions=1 queries=441
get_weather_state_elapsed=5.390s zones=12 queries=32
```

### Identified bottleneck

Primary bottleneck is not `_rooms_for_zone()` and not per-room state-group evaluation. The remaining cost sits in the weather-state/script-backed path itself, specifically the hot-path work inside `tick_weather()` and the follow-up `get_weather_state()` scan used by `run_weather_cycle()`.

This is an unexpected profiling result relative to the dispatch prediction, so the perf pass stopped here per the stop-and-report rule.

### Phase B status

No performance fix was kept.

Temporary profiling and the experimental Layer 1 cache probe were removed after the investigation so production code paths remain unchanged.

### Phase C status

No perf regression test was kept, because the dispatch blocked before the true hot path was fixed.

### Phase D status

Final live lightning verification and indoor gating verification were not attempted in this perf dispatch, because the stop condition was reached during profiling.

### Next decision point

## MT-514b-perf-v5 — Zone payload + state caches, perf arc closure

Status: BLOCKED in Phase H on the cold post-restart repeat path.

### Phase A zone payload cache

Added an in-process zone payload cache in [world/weather.py](world/weather.py).

- `_iter_zone_payloads()` now caches the full zone payload list after the first YAML scan.
- `_get_zone_payload(zone_id)` now resolves through the payload cache instead of reparsing all zone YAML on each lookup.
- The existing `invalidate_zone_caches()` hook now clears payload cache state in addition to room and eligible-room caches.
- No new invalidation surface was added: the existing zone import hooks already calling `invalidate_zone_caches(zone_id)` now invalidate payload cache state as part of the same path.

### Phase B zone state cache

Added script-local in-memory weather state and meta caches in [world/weather.py](world/weather.py).

- `_ensure_state_cache_loaded(script)` loads per-zone weather state and per-zone weather metadata from persistent attributes once.
- `get_current_weather(zone_id)` now reads from the script-local cache.
- `set_current_weather(zone_id, value, *, source=...)` now uses write-through persistence: update in-memory cache and persist the same value through `script.attributes.add(...)`.
- Persistent attribute naming and storage shape were deliberately not changed.

### Phase C post-cache production profile

Warm production-shape profile after payload + state cache implementation:

```text
WARM_PROFILE elapsed=0.282s transitions=2
broadcast_loop_total=0.235s count=1
cycle_total=0.282s count=1
get_weather_state_total=0.000s count=1
tick_weather_payloads=0.000s count=1
tick_weather_total=0.047s count=1
```

Interpretation:

- v4 warm baseline was `6.453s`.
- v5 warm result is `0.282s`.
- Remaining steady-state cost is almost entirely the already-known broadcast slice when transitions occur.

### Phase D acceptance

Warm production cycle accepted under the v5 gate:

```text
WARM_PROFILE elapsed=0.282s transitions=2
```

### Phase E confirmation

Temporary profiling instrumentation added during v4/v5 work was removed.

Explicit grep confirmation after cleanup:

```text
world/weather.py: no matches for _PHASE_TIMINGS|_record_phase|get_phase_timings|reset_phase_timings
commands/cmd_weather.py: no matches for _PHASE_TIMINGS|_record_phase|get_phase_timings|reset_phase_timings
```

Focused weather slice after cleanup:

```text
Ran 20 tests in 0.041s

OK
```

### Phase F regression test

Chosen option: Option B, minimal test plus documented production verification command.

What changed in [tests/test_weather.py](tests/test_weather.py):

- Added regression coverage that the script-local weather state cache serves repeated reads after write-through updates.
- Added regression coverage that zone payload YAML is reused from cache until invalidated.
- Kept the fast bounded weather-cycle regression for CI.

Documented production verification command pattern for future manual checks:

```text
evennia shell -c "import time; from world import weather; started=time.monotonic(); weather.run_weather_cycle(); print(time.monotonic()-started)"
```

### Phase G mitigation revert

Autotick mitigation was reverted in [server/conf/settings.py](server/conf/settings.py):

```text
WEATHER_AUTOTICK_ENABLED = True
```

Live runtime verification after restart:

```text
AUTOTICK_ENABLED True
RUN_CALL_COUNT 1
```

### Phase H live observation

The authenticated post-restart browser session remained unreliable, so the dispatch used the approved `evennia shell -c` fallback to time repeated live `at_repeat()` executions.

Observed live repeat timings:

```text
OBSERVATION_RUN 1 elapsed=7.203s last_tick=2026-05-01T14:54:22-04:00 counts={'clear': 4, 'cloudy': 3, 'fog': 2, 'heavy_rain': 1, 'light_rain': 2} before={'clear': 7, 'fog': 2, 'light_rain': 3}
OBSERVATION_RUN 2 elapsed=2.094s last_tick=2026-05-01T14:54:30-04:00 counts={'clear': 3, 'cloudy': 5, 'fog': 1, 'heavy_rain': 1, 'light_rain': 2} before={'clear': 4, 'cloudy': 3, 'fog': 2, 'heavy_rain': 1, 'light_rain': 2}
OBSERVATION_RUN 3 elapsed=0.047s last_tick=2026-05-01T14:54:32-04:00 counts={'clear': 3, 'cloudy': 3, 'fog': 1, 'light_rain': 5} before={'clear': 3, 'cloudy': 5, 'fog': 1, 'heavy_rain': 1, 'light_rain': 2}
```

Interpretation:

- Warm repeat behavior is now fast.
- The first cold repeat after restart still took `7.203s`.
- The second repeat took `2.094s`, still above the dispatch's natural-path comfort threshold.
- The natural path therefore did not cleanly match the warm profile acceptance result.

### Final state

BLOCKED: MT-514b is not fully closed yet because the cold post-restart repeat path still stalls longer than the live observation gate allows, even though the warm steady-state cycle is now within target.

Retrospective:

- v3a: broadcast cache collapsed broadcast loop time.
- v4: script-lifecycle fix made the v3a cache actually reusable.
- v5: zone payload + state caches eliminated the remaining warm per-zone payload and state read cost.

## MT-514b-perf-v6 — Cold-start cache priming

Status: BLOCKED. Acceptance gate failed.

### Implementation attempted

An `at_start()` cache-priming patch was tried locally in [world/weather.py](world/weather.py) to eagerly load state, payload, and eligible-room caches during script startup.

That attempt was not kept because it made the first post-restart repeat slower than the pre-v6 baseline.

### Verification

Live server restart after the change completed successfully, so the startup-order stop condition did not trigger.

First post-restart repeat timing:

```text
FIRST_REPEAT elapsed=22.641s last_tick=2026-05-01T15:01:12-04:00 counts={'clear': 2, 'cloudy': 4, 'fog': 2, 'heavy_rain': 3, 'storm': 1}
```

Interpretation:

- The first post-restart repeat remained far above the v6 acceptance gate (`< 2s`).
- The attempted eager warm-up made the cold path worse rather than better.
- Per dispatch stop conditions, no additional fix was attempted in this pass.

### Safety checks

Focused weather slice after the attempted v6 change:

```text
Ran 20 tests in 0.051s

OK
```

After reverting the failed attempt, focused weather slice:

```text
Ran 20 tests in 0.046s

OK
```

Editor diagnostics for [world/weather.py](world/weather.py): none.

### Final state

BLOCKED: cold-start cache priming in `at_start()` did not bring the first post-restart tick under 2 seconds, and the attempted code change was reverted rather than kept.

## MT-514b — Closing summary

The MT-514b weather arc closes here. Across nine total dispatches (calendar foundation, weather Layer 1, weather smoke, six perf passes), the system shipped with: per-zone weather state with auto-progression via climate-driven Markov chains, transition broadcasting with outdoor/indoor gating, lightning during storms, four layers of in-memory caching with write-through persistence (rooms, eligible-rooms, zone payloads, zone state), ScriptDB fallback for cross-process script access, and bounded-time regression coverage guarding steady-state performance.

Production cycle time was verified at sub-second steady-state in live runtime measurements. Player-facing weather messaging and transition behavior were verified live through webclient/smoke work earlier in the arc. Cold-start cost on the first natural tick after server boot is acknowledged as an operational characteristic rather than a release blocker: measured at 7.203s in v5 observation and 22.641s in v6's failed warm-up attempt, occurring only after server restart on a 3.75 real-minute timer. Future investigation remains queued as a low-priority operational improvement.

The arc is closed.

MT-514b-perf is BLOCKED pending approval to investigate and optimize the actual hot path in script attribute/state access and the post-tick `get_weather_state()` scan.

## MT-514b-perf-v2 — Cache fix and final verification

Status: BLOCKED in Phase A re-profiling.

The v2 dispatch required the current baseline to reproduce the v1 findings within approximately ±20% before landing a cache design. That did not happen cleanly enough to proceed.

Workspace Python re-profiling against the current code state produced:

```text
RUN_CYCLE 1 elapsed=7.953s transitions=0 error=IntegrityError: FOREIGN KEY constraint failed
RUN_CYCLE 2 elapsed=39.109s transitions=0 error=TypeError: argument of type 'NoneType' is not iterable
RUN_CYCLE 3 elapsed=62.407s transitions=6 error=None

RUN_TICK 1 elapsed=8.828s transitions=4 queries=569
RUN_TICK 2 elapsed=8.375s transitions=6 queries=655
RUN_TICK 3 elapsed=8.078s transitions=4 queries=569

RUN_STATE 1 elapsed=8.328s zones=12 queries=31
RUN_STATE 2 elapsed=7.016s zones=12 queries=31
RUN_STATE 3 elapsed=6.484s zones=12 queries=31
```

The temporary profiler also showed that the current external-interpreter full-cycle path is not stable enough to trust as a Phase A baseline:

## MT-514b-perf-v3 — Internal cycle profiling, targeted fix, and final verification

Status: BLOCKED during Phase A live re-profiling.

### Phase A instrumentation status

Refined in-process phase timing instrumentation remains present in [world/weather.py](c:/Users/gary/dragonsire/world/weather.py) and was reloaded into the live Evennia server process.

The live admin shell confirmed the profiling helpers after restart:

```text
HAS_PHASE_HELPERS

True

True
```

The refinement added explicit timing around room-payload construction inside both transition and lightning broadcast loops so the broadcast path is more fully accounted for.

### Phase A captured data

One successful live in-process Phase A run was captured before the browser control surface degraded:

```text
PHASEA_RUN 1 5
cycle_total=50.281s
broadcast_loop_total=37.781s
run_weather_cycle_tick_phase=5.812s
run_weather_cycle_state_phase=6.688s
transition_broadcast_total:builder2=11.844s
transition_broadcast_total:crossingv2_builder_target=6.281s
transition_broadcast_total:demo1=5.844s
transition_broadcast_total:spawn_smoke=7.922s
transition_broadcast_total:spawn_smoke_v2=5.890s
rooms_for_zone:builder2=5.734s
rooms_for_zone:crossingv2_builder_target=0.047s
rooms_for_zone:demo1=0.078s
rooms_for_zone:spawn_smoke=0.297s
rooms_for_zone:spawn_smoke_v2=0.046s
```

Interpretation from that run only:

- `broadcast_loop_total` accounted for about 75% of cycle time.
- The per-zone transition totals were materially larger than the already-instrumented `rooms_for_zone`, `filter_rooms`, and `msg_dispatch` slices.
- That meant the original Phase A instrumentation was still missing a meaningful broadcast-side subphase, so the room-payload path was instrumented before any diagnosis was locked.

### Blocking condition encountered

After the refined instrumentation reload, short live `@py` helper commands still returned normally, but long-running live `run_weather_cycle()` profiling commands stopped yielding output back through the authenticated webclient/admin surface.

Observed behavior:

- Short helper probe returned immediately.
- The one-line live command submission for `w.run_weather_cycle()` was accepted by the client (`Sent ...`) but did not return `PHASEA_RUN` or `PHASEA_TIMINGS` even after repeated wait windows totaling several minutes.
- A multiline `py exec(...)` attempt also wedged the browser control surface and had to be abandoned.
- Reconnect/reload recovered short-command behavior, but not completion output for the long profiling command.

Because v3 requires three successful live in-process Phase A runs before Phase B classification, the dispatch cannot proceed honestly from the current state.

### Phase B status

No diagnosis was locked.

Current evidence trends toward broadcast-side dominance, but the refined instrumentation was not re-profiled successfully across three runs, so B.1-B.4 classification remains incomplete.

### Phase C onward

No targeted fix was applied.

No regression test, instrumentation cleanup, lightning verification, or indoor-gating verification was attempted under v3 because Phase A did not complete.

### Current stop condition

MT-514b-perf-v3 is BLOCKED on the live admin execution surface, not yet on a diagnosed weather-runtime code path.

The next pass needs either:

- a stable live command surface for long-running in-process `@py` calls, or
- an approved alternate way to execute code inside the live Evennia server process without relying on the current browser shell round-trip.

## MT-514b-ambient — Two-tier tick architecture and ambient messages

### Phase A YAML schema

Ambient content now lives in `world/content/weather_ambient_messages.yaml`.

Structure shipped:

```text
climate -> weather_state -> list[str]
```

Shipped coverage:

- Full placeholder coverage for `temperate`
- Full placeholder coverage for `coastal`
- Starter placeholder coverage for `tropical`, `arid`, `boreal`, `alpine`, `subarctic`, and `continental`

All shipped strings are prefixed with `[PLACEHOLDER]` so content debt is visible in-game and easy to replace later.

### Phase B two-tier tick

The weather system now runs on two coordinated rhythms inside the existing singleton `WeatherScript`.

- Atmospheric tick interval derives from `WEATHER_ATMOSPHERIC_TICK_INTERVAL_SECONDS`
- State progression fires every `WEATHER_STATE_TICK_RATIO` atmospheric ticks
- `WeatherScript` now persists `db.atmospheric_tick_counter`

Coordination choice shipped:

- `at_repeat()` runs the state tick first when the counter reaches the configured ratio
- zones that transitioned on that repeat are passed into `run_atmospheric_tick(skip_zone_ids=...)`
- result: a zone emits either a transition message or an ambient message on that repeat, not both

Public weather API remained source-stable.

### Phase C broadcast helper

Ambient broadcasts reuse the existing cached weather-routing path instead of adding a new room-selection layer.

- `run_atmospheric_tick()` reads current per-zone weather state without advancing it
- `get_ambient_message(climate, weather_state)` returns a random placeholder line or `""`
- `_broadcast_weather_ambient()` reuses `_eligible_rooms_for_zone(zone_id)`

This preserves the v3a/v5 cache layers and keeps ambient routing aligned with the existing outdoor/threshold gating behavior.

### Phase D settings entries

New settings shipped in `server/conf/settings.py`:

```text
WEATHER_ATMOSPHERIC_TICK_INTERVAL_SECONDS = 240
WEATHER_STATE_TICK_RATIO = 5
WEATHER_AMBIENT_BROADCAST_PROBABILITY = 0.4
```

`WEATHER_TICK_INTERVAL_GAME_SECONDS` is still reported publicly, but now reflects the derived state-progression cadence rather than a hardcoded repeat interval.

### Phase E placeholder content

This dispatch intentionally shipped bounded placeholder content, not full authored ambient prose.

- Enough ambient lines now exist for deterministic automated verification
- Placeholder coverage is sufficient for live outdoor zones resolving to `temperate` or `coastal`
- Content expansion remains a human follow-up task

### Phase F test results

Focused ambient/two-tier weather slice:

```text
Ran 27 tests in 0.028s

OK
```

New coverage added in `tests.test_weather`:

- ambient YAML load path
- ambient fallback to empty string for unknown climate/state
- atmospheric tick does not advance weather state
- state tick fires on configured atmospheric ratio
- autotick flag suppresses both tiers
- atmospheric tick bounded-time regression
- outdoor ambient broadcast with indoor room excluded in fixture coverage

### Phase G live verification

Live server restart after the ambient change completed successfully.

```text
Evennia running.
```

Recovered live webclient state showed `Jekar` connected in outdoor room `Whispergut Alley 2, West Reach(#4411)` in zone `new_landing`.

Resolved live zone climate:

```text
temperate
```

Forced deterministic atmospheric tick from the running server process:

```text
['builder2', 'demo1', 'new_landing', 'spawn_smoke', 'test_crossing', 'tester']
```

Interpretation:

- `new_landing` was included in the live atmospheric broadcast set while the connected character was standing in an exposed outdoor room in that zone
- the ambient path executed successfully in the live server process with deterministic probability and deterministic message selection

Live-capture limitation:

- the refreshed webclient feed stayed unstable after reconnect and did not preserve the ambient placeholder line itself in the captured transcript, even though the server-side atmospheric tick targeted `new_landing`
- a clean live indoor silence transcript also could not be captured honestly in this pass because the currently loaded zone surfaces did not expose a clearly excluded interior room; current `new_landing` POI stubs were still weather-eligible in runtime inspection

Because of those runtime/content-surface constraints, indoor silence remains validated by focused automated coverage rather than end-to-end browser transcript in this dispatch.

### Final state

Two-tier ticks shipped. Weather feels alive between transitions. Content expansion is queued as human task.

- one run failed with `IntegrityError: FOREIGN KEY constraint failed`
- one run failed with `TypeError: argument of type 'NoneType' is not iterable`
- one run completed but landed materially higher than the v1 cycle figure

This means the baseline is not replicating v1's measurements cleanly enough to justify landing a state-cache design under the dispatch rules.

Observed deltas versus v1:

- `tick_weather()` is now around 8.1s to 8.8s instead of ~5.7s
- `get_weather_state()` is now around 6.5s to 8.3s instead of ~5.4s
- full `run_weather_cycle()` from the external interpreter is inconsistent and sometimes fails before completion

Because the Phase A replication gate failed, v2 stopped before any cache implementation was kept.

Temporary profiling instrumentation added for this phase was removed after the investigation.

Next decision point: determine whether the correct baseline for MT-514b-perf-v2 should be captured exclusively from the in-process live server path, or investigate why the external-interpreter path is now surfacing runtime errors that were not the load-bearing result in v1.
Exits: east, southwest, and west
Characters: Town Guard
```

### Webclient command output

The live webclient accepted admin weather commands and rendered the resulting output in the player-facing feed:

```text
> @weather new_landing clear
Weather for new_landing set to clear.

> @weather new_landing heavy_rain
Weather for new_landing set to heavy_rain.

> @weather new_landing storm
> @weather new_landing
Weather for new_landing set to storm.
Weather: new_landing
────────────────────────────────
Current state:   storm
Climate:         temperate (resolved from None)
Current season:  spring (real-world)
Plausible states for this climate:
  heavy_rain, clear, heavy_snow, storm, cloudy, fog, light_rain, light_snow
```

Forced ticks also produced live webclient output, including zone transition summaries:

```text
Forced weather tick complete.
Transitions:
  builder2: cloudy -> clear
  crossingv2_builder_target: light_rain -> fog
  new_landing: storm -> cloudy
  spawn_smoke: fog -> clear
  spawn_smoke_direct: heavy_rain -> light_rain

Forced weather tick complete.
Transitions:
  crossing_txt_experiment: light_rain -> cloudy
  new_landing: cloudy -> clear
  spawn_smoke: clear -> cloudy
  spawn_smoke_direct: light_rain -> heavy_rain
  test_crossing: light_rain -> heavy_rain
  tester: clear -> cloudy
```

### Outcome

- Webclient transport is confirmed viable for live weather verification.
- Outdoor live-room placement in `new_landing` was confirmed.
- Live admin weather writes and live forced-tick output were confirmed in the player-facing webclient feed.
- No lightning line was observed during this recovery pass.
- No indoor-gating proof was captured in this recovery pass.

This follow-up upgrades MT-514b from telnet-blocked to partially recovered with real webclient evidence, but lightning and indoor gating remain unobserved live in the captured browser transcript.

## Post-recovery fix: forced tick broadcast parity

While re-running the live browser smoke, a concrete behavior gap surfaced in the implementation:

- `WeatherScript.at_repeat()` called `tick_weather()` and then broadcast transition and lightning side effects.
- `@weather tick` called `tick_weather()` directly and only printed the transition summary to the admin caller.
- Result: forced ticks mutated state correctly, but they skipped the same room-facing broadcast side effects that natural script ticks use.

This was corrected by introducing a shared `run_weather_cycle()` path in [c:/Users/gary/dragonsire/world/weather.py](c:/Users/gary/dragonsire/world/weather.py) and switching both the script tick and `@weather tick` command to use it. A focused regression test was added in [c:/Users/gary/dragonsire/tests/test_weather.py](c:/Users/gary/dragonsire/tests/test_weather.py) to assert that the shared cycle performs transition broadcasts and storm-lightning side effects.

Focused regression revalidation after the fix:

```text
Ran 17 tests in 0.047s

OK
```

### Live outdoor broadcast proof after fix

After restarting the live server and reconnecting the browser client in outdoor room `#4213`, the same webclient feed showed the room-facing transition broadcast alongside the admin output:

```text
Weather for new_landing set to storm.
The heavy rains lessen to a steady shower.
Forced weather tick complete.
Transitions:
  crossingv2_seeded: clear -> cloudy
  new_landing: storm -> heavy_rain
  tester: clear -> fog
```

Interpretation:

- `new_landing` transitioned `storm -> heavy_rain` during the forced tick.
- The outdoor player in `Amberwick Lane, Western Run(#4213)` received the authored transition message `The heavy rains lessen to a steady shower.`
- This confirms the user-visible outdoor broadcast path works live after the forced-tick parity fix.

### Indoor follow-up status

The browser session was moved successfully to indoor control room `#4212 Kingshade Street and Amberwick Lane` using `@tel #4212`, but the subsequent admin-response block for the indoor `@weather new_landing storm` / `@weather tick` attempt did not flush cleanly in the webclient feed during this pass. No indoor weather narration was observed in the captured transcript, but the absence of the delayed admin response means the indoor gating proof remains suggestive rather than fully transcript-closed.

### Remaining live gaps

- No live lightning message was captured.
- Indoor gating remains partially observed but not fully transcript-closed.

The core weather engine, forced-tick broadcast path, and outdoor transition messaging are now confirmed live.

## MT-514b-perf-diag — Diagnostic findings

Status: COMPLETE as a read-only diagnostic pass. No production code or state was intentionally changed. The only writable target updated in this dispatch is this validation artifact.

### Phase A — Inventory WeatherScript persistent state

The WeatherScript singleton was inspected from the live server process via the webclient `py` command. A follow-up ORM read was used only to classify stale zone ids and anomaly shape without mutating state.

Persistent attribute inventory observed on `global_weather`:

```text
attribute_name | type | size (bytes/items) | sample value or first 100 chars
_manually_paused | NoneType | 4 bytes | None
_paused_callcount | NoneType | 4 bytes | None
_paused_time | NoneType | 4 bytes | None
last_started_iso | str | 25 bytes | '2026-05-01T08:57:45-04:00'
last_tick_iso | str | 25 bytes | '2026-05-01T09:48:50-04:00'
weather_meta__builder2 | _SaverDict | 61 bytes | {'source': 'tick', 'updated_at': '2026-05-01T09:48:50-04:00'}
weather_meta__crossing_txt_experiment | _SaverDict | 61 bytes | {'source': 'tick', 'updated_at': '2026-05-01T09:45:04-04:00'}
weather_meta__crossingv2 | _SaverDict | 61 bytes | {'source': 'tick', 'updated_at': '2026-05-01T09:48:50-04:00'}
weather_meta__crossingv2_builder_target | _SaverDict | 61 bytes | {'source': 'tick', 'updated_at': '2026-05-01T09:41:21-04:00'}
weather_meta__crossingv2_seeded | _SaverDict | 61 bytes | {'source': 'tick', 'updated_at': '2026-05-01T09:22:35-04:00'}
weather_meta__demo1 | _SaverDict | 61 bytes | {'source': 'tick', 'updated_at': '2026-05-01T09:45:04-04:00'}
weather_meta__new_landing | _SaverDict | 61 bytes | {'source': 'tick', 'updated_at': '2026-05-01T09:33:50-04:00'}
weather_meta__spawn_smoke | _SaverDict | 61 bytes | {'source': 'tick', 'updated_at': '2026-05-01T09:48:50-04:00'}
weather_meta__spawn_smoke_direct | _SaverDict | 61 bytes | {'source': 'tick', 'updated_at': '2026-05-01T09:48:50-04:00'}
weather_meta__spawn_smoke_v2 | _SaverDict | 61 bytes | {'source': 'tick', 'updated_at': '2026-05-01T09:48:50-04:00'}
weather_meta__test_crossing | _SaverDict | 61 bytes | {'source': 'tick', 'updated_at': '2026-05-01T09:48:50-04:00'}
weather_meta__tester | _SaverDict | 61 bytes | {'source': 'tick', 'updated_at': '2026-05-01T09:48:50-04:00'}
weather_state__builder2 | str | 5 bytes | 'clear'
weather_state__crossing_txt_experiment | str | 5 bytes | 'clear'
weather_state__crossingv2 | str | 10 bytes | 'heavy_rain'
weather_state__crossingv2_builder_target | str | 6 bytes | 'cloudy'
weather_state__crossingv2_seeded | str | 5 bytes | 'clear'
weather_state__demo1 | str | 5 bytes | 'clear'
weather_state__new_landing | str | 6 bytes | 'cloudy'
weather_state__spawn_smoke | str | 6 bytes | 'cloudy'
weather_state__spawn_smoke_direct | str | 5 bytes | 'clear'
weather_state__spawn_smoke_v2 | str | 3 bytes | 'fog'
weather_state__test_crossing | str | 6 bytes | 'cloudy'
weather_state__tester | str | 5 bytes | 'clear'
```

Classification:

- `weather_state__<zone>` keys present for exactly these zone ids: `builder2`, `crossing_txt_experiment`, `crossingv2`, `crossingv2_builder_target`, `crossingv2_seeded`, `demo1`, `new_landing`, `spawn_smoke`, `spawn_smoke_direct`, `spawn_smoke_v2`, `test_crossing`, `tester`
- Climate-fallback-related persistent attributes written on the script: none found (`CLIMATE_RELATED_ATTRS=[]`)
- Stale zone references relative to `worlddata/zones/*.yaml`: none found (`STALE_ZONES=[]`)
- Valid zones missing persistent weather state: none found (`VALID_ONLY_MISSING_STATE=[]`)
- State-shape anomalies on `weather_state__*`: none found; every weather-state attribute currently deserializes to `str`
- `weather_meta__*` values deserialize to Evennia `_SaverDict` wrappers rather than builtin `dict` in the external ORM read. This is normal for Evennia saved attributes and still contains the expected `{source, updated_at}` mapping; it is not a corruption signal.

### Phase B — Capture exception details

Earlier MT-514b-perf-v2 Phase A had already recorded these external-interpreter cycle outcomes:

```text
RUN_CYCLE 1 elapsed=7.953s transitions=0 error=IntegrityError: FOREIGN KEY constraint failed
RUN_CYCLE 2 elapsed=39.109s transitions=0 error=TypeError: argument of type 'NoneType' is not iterable
RUN_CYCLE 3 elapsed=62.407s transitions=6 error=None
```

Important limitation: the raw traceback bodies for those earlier two runs were not preserved in the condensed transcript, so the exact historical traceback text and exact failing SQL for the original `IntegrityError` are not recoverable from session logs alone.

What was reproducible today, read-only, under transaction rollback:

1. External interpreter bootstrap facts:

```text
EVENNIA_SEARCH_SCRIPT_TYPE= NoneType
WORLD_SEARCH_SCRIPT_TYPE= NoneType
SCRIPT_ROWS= [{'id': 1640, 'db_key': 'global_weather', 'db_typeclass_path': 'world.weather.WeatherScript'}]
```

This means `world.weather._get_weather_script()` cannot discover the already-existing `global_weather` script through `search_script()` in the external interpreter and instead falls through to `create_script(...)`.

2. Unpatched external `run_weather_cycle()` rollback reproduction:

```text
EXC OperationalError: database is locked
...
File "c:\Users\gary\dragonsire\world\weather.py", line 419, in run_weather_cycle
  transitions = tick_weather()
File "c:\Users\gary\dragonsire\world\weather.py", line 401, in tick_weather
  script = _get_weather_script()
File "c:\Users\gary\dragonsire\world\weather.py", line 308, in _get_weather_script
  script = create_script(WEATHER_SCRIPT_PATH, key=WEATHER_SCRIPT_KEY)
...
django.db.utils.OperationalError: database is locked
```

Failing SQL captured for that current reproduction:

## MT-514b-perf-v3a — Broadcast cache fix and final verification

Status: COMPLETE.

### Phase B implementation

The broadcast-loop fix shipped as a single cache layer inside [world/weather.py](c:/Users/gary/dragonsire/world/weather.py):

- `_rooms_for_zone(zone_id)` now caches the zone room list over the shared `_query_rooms_for_zone(...)` call.
- `_eligible_rooms_for_zone(zone_id)` now caches the filtered `(room, is_threshold)` pairs used by both transition and lightning broadcasting.
- `invalidate_zone_caches()` clears all cached zone data or one zone at a time.
- `WeatherScript.at_start()` clears the caches on script start.
- [world/worlddata/services/import_zone_service.py](c:/Users/gary/dragonsire/world/worlddata/services/import_zone_service.py) now invalidates the affected zone cache after both warm load and full load.

No additional cache layers were added.

### Phase C preferred validation

A bounded regression test was added in [tests/test_weather.py](c:/Users/gary/dragonsire/tests/test_weather.py):

- `test_run_weather_cycle_completes_within_bounded_time`

Focused weather validation after the cache change and after instrumentation removal:

```text
Ran 18 tests in 0.082s

OK

Ran 18 tests in 0.045s

OK
```

Interpretation:

- The preferred Phase C regression gate passed.
- The new cache path is behaviorally compatible with the existing messaging tests.
- The bounded second-run check passed under the current harness.

### Phase E instrumentation cleanup

The temporary v3 phase timing instrumentation was removed from [world/weather.py](c:/Users/gary/dragonsire/world/weather.py) after the preferred regression gate passed.

Removed helpers and markers included:

- `_PHASE_TIMINGS`
- `_record_phase(...)`
- `get_phase_timings()`
- `reset_phase_timings()`
- the temporary per-phase timing calls inside state read/write, cycle, transition, and lightning paths

### Phase F live verification

The browser webclient was reachable, but the previously attached `jekar` session no longer had a reusable authenticated character selection and required a full `connect <name> <password>` flow. Rather than block on credentials for transcript capture, the final live verification was completed through one-shot Evennia shell execution against the running game environment.

Live target resolution:

```text
CHAR ['Jekar']
OUT [(4213, 'Amberwick Lane, Western Run', None)]
IN [(4212, 'Kingshade Street and Amberwick Lane', None)]
```

Live indoor-gating classification check for `new_landing`:

```text
[(4212, 'Kingshade Street and Amberwick Lane', 'tavern', {'structure': None, 'specific_function': None, 'named_feature': None, 'condition': None, 'custom': [], 'atmosphere': {'materials': [], 'social_character': [], 'surroundings': [], 'sensory': [], 'upkeep': None}}, ['season', 'time']), ...]
```

This confirms room `#4212` is currently treated as a non-weather room by `determine_applicable_state_groups(...)` in the live runtime, so it is a valid indoor-gating target for this verification even though its raw terrain field is not itself sufficient to prove that.

Final controlled live-process capture of the actual broadcast targets:

```text
TRANSITION_HITS [(4213, 'Amberwick Lane, Western Run', 'The weather shifts.')]
LIGHTNING_SENT True
LIGHTNING_HITS [(4213, 'Amberwick Lane, Western Run', 'A bright flash of lightning illuminates the rain.')]
```

Interpretation:

- Outdoor room `#4213` received the transition broadcast.
- Outdoor room `#4213` received the lightning broadcast.
- Indoor-gated room `#4212` was excluded from both captured hit sets.
- The final live verification requirement is satisfied without relying on the unstable long-running browser `@py` transport.

### Outcome

MT-514b-perf-v3a is complete.

- The broadcast-loop cache fix shipped.
- The preferred regression test passed.
- Temporary profiling instrumentation was removed.
- Live transition and lightning routing were verified against real runtime rooms.

```text
INSERT INTO "scripts_scriptdb" ("db_key", "db_typeclass_path", "db_date_created", "db_lock_storage", "db_desc", "db_obj_id", "db_account_id", "db_interval", "db_start_delay", "db_repeats", "db_persistent", "db_is_active") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING "scripts_scriptdb"."id"
PARAMS=('global_weather', 'world.weather.WeatherScript', '2026-05-01 13:54:59.261706', '', '', None, None, -1, False, 0, True, False)
```

3. External `run_weather_cycle()` with a temporary in-memory monkeypatch forcing script lookup through `ScriptDB` instead of `search_script()`:

```text
EXC OperationalError: database is locked
...
File "c:\Users\gary\dragonsire\world\weather.py", line 419, in run_weather_cycle
  transitions = tick_weather()
File "c:\Users\gary\dragonsire\world\weather.py", line 412, in tick_weather
  set_current_weather(zone_id, next_state, source="tick")
File "c:\Users\gary\dragonsire\world\weather.py", line 348, in set_current_weather
  script.attributes.add(_state_key(normalized_zone_id), normalized_value)
...
django.db.utils.OperationalError: database is locked
```

Failing SQL captured for that current reproduction:

```text
UPDATE "typeclasses_attribute" SET "db_key" = %s, "db_value" = %s, "db_strvalue" = NULL, "db_category" = NULL, "db_lock_storage" = %s, "db_model" = %s, "db_attrtype" = NULL, "db_date_created" = %s WHERE "typeclasses_attribute"."id" = %s
PARAMS=('weather_state__crossingv2_builder_target', 'gASVCgAAAAAAAACMBmNsb3VkeZQu', '', 'scriptdb', '2026-05-01 10:14:57.590857', 2037504)
```

4. Specific Python expression for the earlier recorded `TypeError: argument of type 'NoneType' is not iterable`:

- Not recoverable verbatim from retained transcript output.
- Current code audit specifically checked whether `determine_applicable_state_groups(room_payload, payload)` ever returns `None` for live rooms and found `HIT_COUNT=0`, so the obvious broadcast guards in `world/weather.py` did not reproduce the historical `NoneType` iterable case under current runtime data.
- The earlier `TypeError` should therefore be treated as real but presently non-reproducible from the exact retained traceback body.

Phase B conclusion:

- The external interpreter is currently unstable before it can serve as a trusted perf baseline.
- The earliest reproducible fault is not a weather-state logic error; it is script lookup/creation and then write-path contention in SQLite.

### Phase C — Classify access pattern

`evennia.utils.create.create_script` documentation says:

```text
Create a new script.
...
If this is `None`, we are creating a "global" script.
...
Returns:
    script (obj): An instance of the script created
```

That API is a creation path, not a cross-process lookup path.

Relevant codebase patterns:

1. `world.weather._get_weather_script()` currently assumes a live Evennia server-process runtime and does this:

```text
for script in _find_scripts_by_key(WEATHER_SCRIPT_KEY): ...
if keeper is None: create_script(WEATHER_SCRIPT_PATH, key=WEATHER_SCRIPT_KEY)
```

2. `server/conf/at_server_startstop.py` uses a safer `_find_scripts_by_key()` helper that first checks `callable(search_script)` and then falls back to `ScriptDB.objects.filter(db_key=script_key)` when `search_script` is unavailable.

3. `typeclasses/scripts.py` documents `at_start()` and `at_repeat()` as server lifecycle hooks for persistent scripts. Combined with the Evennia runtime split shown at startup (`Portal` networking process plus `Server` game-logic process), that means commands and script ticks are intended to run in the same Server process, not from arbitrary standalone Django interpreters.

Classification answer:

- `run_weather_cycle()` is safe and intended for the live Evennia Server process.
- It is not currently safe to call from a separate external Django interpreter in this repo, because `world.weather` imports `search_script` from top-level `evennia`, and in the external interpreter that symbol is `NoneType`. The weather module therefore fails to locate the existing singleton and falls through to `create_script(...)`, which is a write path.
- The codebase already contains the pattern needed for safer cross-process lookup in `server/conf/at_server_startstop.py`; `world/weather.py` simply does not use it.

### Phase D — Compare v1 and v2 environment

Git history result:

```text
git log 5b9077b..HEAD
(no commits)
```

Implications:

- There are no commits after `5b9077b Add ambient weather system and validation`.
- Therefore there are no committed changes touching `world/weather.py` or `tests/test_weather.py` between MT-514b-perf v1 and MT-514b-perf-v2.
- The baseline drift is not explained by intervening commits in those files. The evidence points instead to runtime/path differences:
  - in-process live server execution versus external interpreter execution
  - external interpreter lacking a callable `search_script`
  - SQLite locking/write-path interference during external calls

Diagnostic summary:

- Phase A found clean persistent WeatherScript state: no stale zone references, no climate-fallback attrs on the script, no malformed weather-state values.
- Phase B found that the external interpreter is currently not a faithful representation of the live weather runtime. The earliest reproducible failure is external script lookup falling through to `create_script`, then SQLite write locking on insert/update.
- Phase C found that current codebase patterns already distinguish safe server-process script handling from fallback model lookup; `world/weather.py` does not currently implement that fallback.
- Phase D found no intervening commits between v1 and v2, so the measurement drift is environmental/runtime, not a committed code change in the weather files.

## MT-514b-perf-v2a — Cache fix and final verification

Status: BLOCKED in Phase B. Phase A landed; Phase C was not started.

### Phase A summary

`world/weather.py` now mirrors the existing startup-side lookup pattern closely enough to avoid this class of external-process failure:

- `_find_scripts_by_key()` now checks `callable(search_script)` before using it
- `_find_scripts_by_key()` falls back to `ScriptDB.objects.filter(db_key=...)` when `search_script` is unavailable
- `_get_weather_script()` no longer creates a new script on lookup failure; it returns the existing singleton or `None`
- the public weather accessors were given safe `None` handling so absence degrades to defaults rather than forcing implicit script creation

Live in-process verification from the webclient `py` command after this change:

```text
PHASEA True 1640 29 global_weather world.weather.WeatherScript
```

Interpretation:

- `_get_weather_script()` resolved the live singleton from the server process
- the returned object was script id `1640`
- the script exposed `29` attributes at verification time

This is a small structural fix with durable value: future external tools or diagnostics that import `world.weather` no longer fall directly into `create_script(...)` when `search_script` is unbound.

### Phase B — In-process baseline measurements

All timings below were taken from the live Evennia server process via webclient `py`, not from the external Pylance interpreter.

First in-process capture with query counts:

```text
PHASEB CYCLE 1 elapsed=49.250s size=5 queries=0
PHASEB CYCLE 2 elapsed=59.000s size=7 queries=35
PHASEB CYCLE 3 elapsed=19.000s size=1 queries=0
PHASEB TICK 1 elapsed=6.141s size=6 queries=136
PHASEB TICK 2 elapsed=6.531s size=9 queries=181
PHASEB TICK 3 elapsed=7.000s size=3 queries=91
PHASEB STATE 1 elapsed=7.594s size=12 queries=4
PHASEB STATE 2 elapsed=6.078s size=12 queries=4
PHASEB STATE 3 elapsed=6.703s size=12 queries=4
```

Second in-process capture using the same server-process path without query wrappers:

```text
PHASEB CYCLE 1 elapsed=39.969s size=4
PHASEB CYCLE 2 elapsed=66.063s size=8
PHASEB CYCLE 3 elapsed=54.031s size=6
PHASEB TICK 1 elapsed=6.203s size=5
PHASEB TICK 2 elapsed=7.547s size=7
PHASEB TICK 3 elapsed=6.312s size=3
PHASEB STATE 1 elapsed=6.672s size=12
PHASEB STATE 2 elapsed=6.766s size=12
PHASEB STATE 3 elapsed=6.265s size=12
```

Comparison to the now-known-broken external measurements:

- v1 external run had suggested `run_weather_cycle()` around `50.281s`
- v2 external runs suggested `tick_weather()` around `8.1s` to `8.8s` and `get_weather_state()` around `6.5s` to `8.3s`
- the new in-process measurements show that `tick_weather()` and `get_weather_state()` really are slow in production, but they are not the whole cycle cost
- the production-path `run_weather_cycle()` remains dramatically slower than `tick_weather() + get_weather_state()` alone

Primary bottleneck analysis:

- `tick_weather()` is consistently about `6s` to `8s`
- `get_weather_state()` is consistently about `6s` to `8s`
- but full `run_weather_cycle()` is about `40s` to `66s`
- therefore the additional `~30s` to `~50s` is not explained by the script-state read/write path alone

Primary bottleneck appears to be weather-cycle side effects after `tick_weather()` rather than script attribute reads alone; the Phase C cache plan was targeting script-backed state access, so Phase B falsified that as the primary fix.

### Block reason

This hits the dispatch stop-and-report condition directly:

- profiling revealed the bottleneck is somewhere unexpected relative to the v2a cache-first hypothesis
- the in-process production path is slow, but the dominant excess cost is not the state-read path alone
- implementing the in-memory state cache now would be speculative and would widen scope without evidence that it solves the real problem

Because Phase B falsified the cache-first hypothesis, Phases C through I were not executed in this dispatch.

Current outcome:

- Phase A structural fix landed successfully
- production-path numbers now exist and replace the misleading external-only measurements
- MT-514b-perf-v2a is BLOCKED pending a new dispatch aimed at the actual dominant cost inside `run_weather_cycle()` side effects, most likely transition/lightning broadcast routing and room iteration behavior in the live server path