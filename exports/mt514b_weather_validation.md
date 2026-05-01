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

## Webclient recovery follow-up

The smoke was retried through the authenticated browser webclient on `http://localhost:4001/webclient/?mode=play` using the `jekar` account.

### Outdoor room positioning

Using the correct teleport syntax, the live webclient session landed in the intended outdoor target room:

```text
Amberwick Lane, Western Run(#4213)
Amberwick Lane threads east and west through the district, a lived-in lane of shopfronts, side doors, and close-built eaves. The lane is settled but still alert here, close enough to one end that arrivals and departures shape the mood. The scents here are clean by city measure: rain on stone, banked hearths, horses kept at a remove, and trimmed greenery from private courts. Boundary stones, walls, or the edge of a distinct enclave make this stretch feel nearer the city's margin than its heart. Nearby, Residental Cloister arch to To gives this stretch of the city a more distinct identity. The surrounding facades feel more deliberate here, with cleaner stonework and a quieter civic order.
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