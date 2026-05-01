Locked. Drafting MT-514b.

```markdown
# MT-514b — Weather system (Layer 1: ambient state)

## Background

DireEngine has a state-mapping system that knows certain rooms can
respond to weather (urban exterior, wilderness), and prompts already
generate `$state(rain, ...)` markup in room descriptions. But there
is no runtime concept of "what is the weather right now." When the
state-mapping logic activates the `weather` state group for a room,
nothing supplies a current value, so the markup never triggers.

This dispatch builds the foundation: a per-zone weather system with
climate-driven plausibility, season-aware transitions, and Markov-
chain auto-progression. It lays groundwork for foraging (MT-514c) and
later phenomena layers (lightning effects, tornadoes, hurricanes).

This is Layer 1 — ambient weather state only. Storm phenomena (real
lightning strikes, hail mechanics) are deferred to MT-514b-storms.
Severe weather events (tornadoes, hurricanes) are deferred to their
own dispatches. Atmospheric lightning *messaging* during storms IS
included as a small narrative win.

## Architectural guardrails (READ FIRST)

This is the largest dispatch in the MT-514 arc. The leash needs to
be tighter, not looser, because the scope spans new modules, new
content files, schema changes, vocab alignment, scheduler integration,
admin commands, and tests.

**Frozen design decisions:**

1. Weather is **per-zone**, not global. Each zone has its own
   `current_weather` state evolving on its own progression.
2. Weather state lives on a singleton **`WeatherScript`** Evennia
   global script. Per-zone weather is stored as attributes on this
   script using `weather_state__<zone_id>` keys. Survives restarts.
3. Public API in `world/weather.py`:
   - `get_current_weather(zone_id: str) -> str`
   - `set_current_weather(zone_id: str, value: str, *, source: str = "admin")`
   - `get_weather_state() -> dict`  (structured snapshot for admin command)
   - `is_weather_plausible_for_climate(weather: str, climate: str) -> bool`
   - `tick_weather()`  (called by scheduler — evaluates all zones for transition)
4. Climate vocabulary (locked):
   `temperate / coastal / tropical / arid / boreal / alpine / subarctic / continental`
5. Weather vocabulary (locked):
   `clear / cloudy / light_rain / heavy_rain / storm / fog / light_snow / heavy_snow / blizzard / sandstorm`
6. Default weather for any zone with no recorded state: `clear`.
7. Auto-progression evaluates every 15 game-minutes
   (configurable via `WEATHER_TICK_INTERVAL_GAME_SECONDS`).
8. Transition probabilities are stored as data in
   `world/content/weather_transitions.yaml` (32 matrices: 8 climates ×
   4 seasons). Loaded once at module import.
9. Climate compatibility (which weather is *plausible* per climate)
   is stored in `world/content/climate_weather_compatibility.yaml`.
10. Climate values: validated via a permissive resolver that maps
    freeform strings to vocab buckets. Unresolvable values fall back
    to `temperate` with a logged warning. No zone YAML files are
    modified by this dispatch.
11. Transition messaging broadcasts only to **outdoor** rooms
    (rooms whose applicable state groups include `"weather"`).
    Threshold rooms (rooms whose `tags.structure` is in
    `_THRESHOLD_STRUCTURES`) receive a softened message. Interior and
    underground rooms are silent.
12. Atmospheric lightning messaging fires probabilistically when
    a zone's weather is `storm`. No mechanical effect, pure narrative.
13. Admin command is `@weather` with no aliases. Permission gate
    matches `@calendar`: `cmd:perm(Admin) or perm(Developer)`.

**Frozen what-not-to-do list:**

- DO NOT modify any calendar code (`world/calendar.py`,
  `commands/cmd_calendar.py`). MT-514a is shipped.
- DO NOT modify any zone YAML file under `worlddata/zones/`.
- DO NOT modify any file under `docs/`, `exports/`, `tmp/`, or
  the `MicroTask Archive/` directory.
- DO NOT add invasion runtime state. That is its own follow-on
  dispatch and is explicitly out of scope here.
- DO NOT add foraging, ForageAbility integration, or any other
  consumer of weather state. MT-514c handles foraging consumption.
- DO NOT add real lightning *strike* events with mechanical effect
  — only atmospheric messaging. Strike mechanics are MT-514b-storms.
- DO NOT add tornadoes, hurricanes, hail mechanics, sandstorm
  hazards, or any severe-weather event system.
- DO NOT add a player-facing `weather` command. Admin-only for now.
- DO NOT add weather observation skill (`OBSERVE WEATHER`,
  perception-gated forecast). That's a future dispatch.
- DO NOT modify `_STATE_GROUP_VOCABULARY` for any group other than
  `"weather"`. Time, season, invasion vocabularies are unchanged.
- DO NOT change the state-mapping function
  `determine_applicable_state_groups()`. The weather/outdoor gating
  it does is correct as of MT-T01.
- DO NOT introduce APScheduler, Twisted timers, or any new
  scheduling library. Use the existing Evennia script-tick mechanism
  the same way other periodic systems already do.
- DO NOT introduce new third-party dependencies.

**Stop-and-report conditions:**

- If the existing scheduler infrastructure
  (`world/systems/scheduler.py` and similar) has a different idiom
  for periodic ticks than Evennia's standard `Script.at_repeat`,
  stop and report so the agent can match local convention.
- If `_STATE_GROUP_VOCABULARY["weather"]` cannot be updated without
  touching tests beyond `tests/test_room_description_prompt.py`
  (e.g., other tests assert against the old `rain/snow/fog` tuple),
  stop and report.
- If the prompt-module change to support 10-stage weather
  vocabulary surfaces a regression in the state-mapping logic
  beyond mechanical vocabulary updates, stop and report.
- If existing zone YAML files have climate values that cannot be
  resolved to a vocabulary bucket by the permissive resolver, stop
  and report with the list of unresolvable values.
- If any existing test fails after this dispatch's changes (other
  than the explicit prompt-vocab updates), stop and report.

## Phase A — Climate compatibility data

### A.1 Climate vocabulary

Climate values are now constrained to:
`temperate / coastal / tropical / arid / boreal / alpine /
subarctic / continental`.

This vocabulary is enforced at runtime via a *permissive resolver*
(see Phase E). It is not enforced at zone-YAML-load time in this
dispatch — existing zones with freeform climate text continue to
work via the resolver.

### A.2 Climate-weather compatibility

Create `world/content/climate_weather_compatibility.yaml`:

```yaml
# Maps each climate to the set of weather states that are plausible.
# Used by:
#   - Markov transition matrices (zero out implausible transitions)
#   - Admin warnings on @weather set commands
#   - is_weather_plausible_for_climate() helper

temperate:
  - clear
  - cloudy
  - light_rain
  - heavy_rain
  - storm
  - fog
  - light_snow
  - heavy_snow

coastal:
  - clear
  - cloudy
  - light_rain
  - heavy_rain
  - storm
  - fog
  - light_snow

tropical:
  - clear
  - cloudy
  - light_rain
  - heavy_rain
  - storm
  - fog

arid:
  - clear
  - cloudy
  - sandstorm
  - fog  # cold-desert nights

boreal:
  - clear
  - cloudy
  - light_rain
  - heavy_rain
  - light_snow
  - heavy_snow
  - blizzard
  - fog

alpine:
  - clear
  - cloudy
  - light_rain
  - storm
  - light_snow
  - heavy_snow
  - blizzard
  - fog

subarctic:
  - clear
  - cloudy
  - light_snow
  - heavy_snow
  - blizzard
  - fog

continental:
  - clear
  - cloudy
  - light_rain
  - heavy_rain
  - storm
  - light_snow
  - heavy_snow
  - blizzard
  - fog
```

Note that `clear` is plausible everywhere. `cloudy` is plausible
everywhere. Sandstorm is exclusive to arid. Blizzard is restricted
to cold climates. Storms in tropical climates are ordinary
thunderstorms — hurricane-grade events are deferred.

### A.3 Climate keyword resolver

The resolver maps freeform climate text from `generation_context.climate`
to a vocabulary bucket. Add `world/content/climate_keywords.yaml`:

```yaml
# Maps substring keywords (lowercase) to vocab buckets.
# Resolution: lowercase the input, check each keyword in declaration order,
# first match wins. Falls back to "temperate" with a warning if no match.

tropical:
  - tropical
  - rainforest
  - jungle
  - equatorial

arid:
  - arid
  - desert
  - parched
  - dry

coastal:
  - coastal
  - seaside
  - maritime
  - littoral
  - oceanic

boreal:
  - boreal
  - taiga
  - cold forest

alpine:
  - alpine
  - mountain
  - highland
  - peak

subarctic:
  - subarctic
  - arctic
  - polar
  - tundra
  - frozen

continental:
  - continental
  - inland
  - prairie
  - steppe
  - plains

temperate:
  - temperate
  - mild
  - moderate
```

The resolver is implemented as a pure function in `world/weather.py`:
`resolve_climate(value: str | None) -> str` returning a vocab bucket.

## Phase B — Transition matrices

Create `world/content/weather_transitions.yaml` with 32 transition
matrices (8 climates × 4 seasons).

Schema for one matrix:

```yaml
<climate>__<season>:
  # Each row is the current state. Each column-key is a target state.
  # Values are relative weights, NOT probabilities. Weights are
  # normalized at load time. Implausible states (per
  # climate_weather_compatibility) are ignored even if listed.
  clear:
    clear: 70        # most common: stay clear
    cloudy: 25
    fog: 5
  cloudy:
    cloudy: 50
    clear: 20
    light_rain: 20
    fog: 10
  # ... etc for every state plausible in this climate
```

The agent generates the full 32-matrix file. The agent is authorized
to use the following heuristic for initial weights:

- **Inertia is high.** A state should typically transition to itself
  with weight 50-75 (i.e., 50-75% chance to remain in current state
  per tick). This makes weather change at a believable pace.
- **Adjacent intensities are common.** `light_rain` → `heavy_rain`
  and `heavy_rain` → `storm` are weight 15-25. Reverse transitions
  (slacking off) are weight 15-25. Skipping intensity (clear →
  storm in one tick) is weight 0-5.
- **Recovery to clear from extreme states is gradual.** `blizzard`
  transitions to `heavy_snow` more often than to `clear` directly.
- **Season influences pool weighting.** Summer in temperate climates
  weights `storm` higher; winter shifts toward `light_snow`/`heavy_snow`.
- **Sandstorms are rare events** — start from `cloudy`, transition
  back relatively quickly. Weight ~5-10 from cloudy → sandstorm in
  arid summer.
- **Fog is most common at night** (we cannot easily condition on
  time-of-day in MT-514b, so fog stays climate/season-driven only).

Each matrix file the agent writes must include a top-of-file
comment block documenting these heuristics so future tuners can
adjust without re-deriving the rationale.

The matrices ARE content. They will be tuned later. Reasonable
starting values are sufficient for MT-514b.

## Phase C — Weather module

Create `world/weather.py`. Required structure:

```python
"""
DireEngine weather system (Layer 1: ambient state).

Per-zone weather state with climate-driven plausibility and
season-aware Markov transitions. Reads season from world.calendar;
weather progresses on its own tick independent of the calendar.

Public API:
  get_current_weather(zone_id) -> str
  set_current_weather(zone_id, value, *, source="admin")
  get_weather_state() -> dict
  is_weather_plausible_for_climate(weather, climate) -> bool
  resolve_climate(freeform_value) -> str
  tick_weather()  # called by scheduler

Storage: WeatherScript singleton Evennia global script with
per-zone state in attributes. Survives restarts.
"""
```

Required public constants:
- `CLIMATES`: tuple of 8 vocabulary values
- `WEATHER_STATES`: tuple of 10 vocabulary values
- `DEFAULT_WEATHER`: `"clear"`

Required pure helpers (no side effects, no DB access):
- `_load_climate_compatibility() -> dict[str, frozenset[str]]`
- `_load_climate_keywords() -> list[tuple[str, str]]`  (ordered list of (keyword, bucket) pairs)
- `_load_transition_matrices() -> dict[str, dict[str, dict[str, float]]]`
- `resolve_climate(value: str | None) -> str`
- `is_weather_plausible_for_climate(weather: str, climate: str) -> bool`
- `_normalized_transition_row(matrix, current_state, climate) -> dict[str, float]`
  (filters implausible targets, normalizes remaining weights to probabilities)
- `_pick_next_state(current, climate, season, *, rng=None) -> str`
  (uses transition matrices + RNG to pick next state; rng parameter
  enables deterministic testing)

Required script-backed functions:
- `_get_weather_script() -> WeatherScript`
- `get_current_weather(zone_id: str) -> str`
- `set_current_weather(zone_id: str, value: str, *, source: str = "admin") -> None`
- `get_weather_state() -> dict`  (structured snapshot of all zones)
- `tick_weather() -> dict[str, tuple[str, str]]`  (returns map of
  zone_id → (old_state, new_state) for zones that transitioned)

The `tick_weather()` function:
1. Iterates over every zone known to the engine (read from
   `worlddata` or from zones that have recorded weather state —
   the agent picks the right convention by reading existing code)
2. For each zone, reads current weather (default `clear` if unset),
   reads zone's climate (resolved via `resolve_climate`), reads
   current season from `world.calendar.get_current_season()`
3. Picks next state via Markov transition
4. If next state differs from current, updates state and adds entry
   to the return dict for messaging dispatch
5. Returns the dict so the messaging layer can broadcast transitions

The `tick_weather()` function does NOT broadcast messages itself —
it returns transitions. Messaging dispatch is handled by the script's
`at_repeat()` method (Phase D) so the pure weather logic stays
testable without Evennia object dependencies.

## Phase D — WeatherScript

Add `WeatherScript` class in `world/weather.py` (or a sibling module
`typeclasses/weather_script.py` — agent picks based on existing
convention for global persistent scripts in this repo).

Required behavior:
- Persistent global script, starts at server boot
- `at_script_creation()`: sets `interval` to
  `WEATHER_TICK_INTERVAL_GAME_SECONDS / TIME_FACTOR` real seconds
  (so 15 game-minutes at TIME_FACTOR=4.0 = 225 real seconds)
- `at_repeat()`:
  1. Calls `tick_weather()` to get transitions
  2. For each (zone_id, old, new) transition, dispatches messaging
     via `_broadcast_weather_transition(zone_id, old, new)`
  3. Independently, for every zone currently in `storm` state,
     rolls atmospheric lightning per Phase F rules

The `_broadcast_weather_transition(zone_id, old, new)` function:
1. Looks up all rooms in the zone (via existing zone-room indexing)
2. For each room, calls `determine_applicable_state_groups()` to
   check if `"weather"` is in the room's applicable states
3. If yes and room is outdoor (not threshold), broadcasts the full
   transition message
4. If room is threshold, broadcasts the softened version
5. If `"weather"` is not in applicable states, skips the room

Transition messages live in
`world/content/weather_transition_messages.yaml`:

```yaml
# Keyed by (from_state, to_state) tuple, encoded as "from__to" string.
# Each entry has "outdoor" and "threshold" variants.
# Messages adapted from DragonRealms Elanthipedia reference vocabulary.

clear__cloudy:
  outdoor: "A few clouds drift in, slowly graying the sky."
  threshold: "The light outside dims as clouds gather."
clear__fog:
  outdoor: "Tendrils of fog begin to creep across the ground."
  threshold: "A bank of fog rolls in from outside."
cloudy__light_rain:
  outdoor: "Light rain begins to fall from the sky."
  threshold: "You hear rain start to patter outside."
light_rain__heavy_rain:
  outdoor: "The rain begins to come down even more heavily."
  threshold: "The rain outside intensifies."
heavy_rain__storm:
  outdoor: "The steady rains turn into a driving storm."
  threshold: "A storm breaks outside."
storm__heavy_rain:
  outdoor: "The heavy rains lessen to a steady shower."
  threshold: "The storm outside slackens."
heavy_rain__light_rain:
  outdoor: "The rain slackens off to a heavy downpour."
  threshold: "The rain outside softens."
light_rain__cloudy:
  outdoor: "The rain stops, leaving only an overcast sky."
  threshold: "The rain outside stops."
cloudy__clear:
  outdoor: "Most of the clouds blow away on a cool, gentle breeze."
  threshold: "The sky outside clears."

# Snow transitions
cloudy__light_snow:
  outdoor: "Light snow begins to fall from the sky."
  threshold: "You see snow beginning to fall outside."
light_snow__heavy_snow:
  outdoor: "The snow begins to fall more heavily."
  threshold: "The snowfall outside thickens."
heavy_snow__blizzard:
  outdoor: "The snow increases in severity and is now a blizzard."
  threshold: "The snow outside has become a blizzard."
blizzard__heavy_snow:
  outdoor: "The blizzard slackens to heavy snow."
  threshold: "The blizzard outside lessens."
heavy_snow__light_snow:
  outdoor: "The snow slackens to a moderate flurry."
  threshold: "The snow outside lightens."
light_snow__cloudy:
  outdoor: "The snow stops, leaving only an overcast sky of grey."
  threshold: "The snow outside stops."

# Fog transitions
cloudy__fog:
  outdoor: "A heavy fog settles in around you."
  threshold: "Fog rolls in from outside."
fog__cloudy:
  outdoor: "The fog slowly thins and dissipates."
  threshold: "The fog outside lifts."
fog__clear:
  outdoor: "The last wisps of fog burn away."
  threshold: "The fog outside clears entirely."

# Sandstorm transitions (arid only)
cloudy__sandstorm:
  outdoor: "A wall of swirling sand sweeps in, biting and stinging."
  threshold: "A sandstorm rises outside, the wind howling against the walls."
sandstorm__cloudy:
  outdoor: "The sandstorm subsides, leaving a hazy, gritty sky."
  threshold: "The sandstorm outside subsides."

# Direct-to-clear transitions (uncommon but possible)
fog__clear:
  outdoor: "The fog burns away, revealing clear skies."
  threshold: "The fog outside clears."
heavy_rain__cloudy:
  outdoor: "The heavy rains taper off, leaving the sky overcast."
  threshold: "The rain outside ends abruptly."
```

If the agent encounters a transition pair not in this file (because
the matrices allow it but messaging wasn't authored), the agent
generates a generic fallback message at runtime: `"The weather
shifts."` and logs a warning so we know to add the proper messaging
later.

## Phase E — Settings and prompt vocab alignment

### E.1 Settings

In `server/conf/settings.py`, add:

```python
# ---------------------------------------------------------------------------
# Weather system
# ---------------------------------------------------------------------------
# How often the weather progression evaluates each zone.
# Expressed in game-seconds. At TIME_FACTOR=4.0, 15 game-minutes
# (900 game-seconds) = 225 real seconds = 3.75 real minutes.
WEATHER_TICK_INTERVAL_GAME_SECONDS = 900

# Probability per tick that a zone in `storm` state produces a
# lightning/thunder atmospheric event. Tick is 15 game-minutes,
# so probability of ~0.5 means roughly one event per 30 game-minutes
# of storm.
WEATHER_LIGHTNING_PROBABILITY_PER_TICK = 0.5
```

### E.2 Prompt vocabulary alignment

In `world/builder/prompting/room_description_prompt.py`, locate
`_STATE_GROUP_VOCABULARY` and update the `"weather"` tuple:

```python
_STATE_GROUP_VOCABULARY = {
    "time": ("night", "morning", "afternoon", "evening"),  # unchanged
    "season": ("spring", "summer", "autumn", "winter"),  # unchanged
    "weather": (
        "clear", "cloudy", "light_rain", "heavy_rain", "storm",
        "fog", "light_snow", "heavy_snow", "blizzard", "sandstorm",
    ),
    "invasion": ("invasion",),  # unchanged
}
```

This expansion means the AI generator can produce richer
state-conditional descriptions (e.g., `$state(blizzard, ...)` is
now a known state, not a vocab violation). Existing zone YAML with
the older `$state(rain, ...)` markup remains valid — `rain` is no
longer in the vocabulary, but markup keys aren't validated against
this vocab at runtime. The vocabulary controls *generation*, not
*rendering*. (Confirm by reading the markup-render code path; if
it does validate, stop and report.)

Update the prompt template files to match (same locations as MT-T01):
- `world/builder/templates/room_description_system_prompt.txt`
- `world/builder/templates/room_description_state_markup_prompt.txt`

In each template, update the weather vocabulary list from the old
`rain, snow, fog` to the full new list. Same approach as MT-T01:
keep the format style consistent with existing template phrasing,
just expand the enumeration.

Same exhaustive verification as MT-T01:
- `state_description.md` updates to reflect new vocab
- After updates, run repo-wide search for `"rain", "snow", "fog"` as
  a literal vocab tuple — should find zero hits in production code
  outside the new full-list locations

### E.3 Test expectation updates

`tests/test_room_description_prompt.py` has assertions about the
`weather` vocabulary tuple. Update the relevant test fixtures to
expect the new 10-value tuple. Specifically:

- Line ~621: an assertion of the form
  `[..., "rain", "snow", "fog", "invasion"]` — update to include
  the full 10 weather values.
- Any other test that asserts the weather tuple directly: update
  to match.
- B1 state-mapping tests still pass because they assert the *names*
  of state groups (`"weather"`), not the contents of the vocab.

If updating these test expectations would conflict with any other
test in the suite (e.g., a test that asserts the tuple has length 3),
stop and report.

## Phase F — Atmospheric lightning messaging

When the weather script ticks and a zone is in `storm` state, roll
the `WEATHER_LIGHTNING_PROBABILITY_PER_TICK` chance to broadcast
an atmospheric event. No mechanical effect.

Lightning messages live in
`world/content/weather_lightning_messages.yaml`:

```yaml
# Atmospheric lightning/thunder messages broadcast probabilistically
# during storm weather. Pure narrative, no mechanical effect.
# A random message is chosen per event.

flashes:
  - "A bright flash of lightning illuminates the rain."
  - "Lightning crackles across the sky to the east."
  - "A jagged streak of lightning splits the storm."
  - "The sky flashes white with distant lightning."
  - "Lightning flickers within the heavy clouds overhead."

thunderclaps:
  - "Thunder rolls across the sky."
  - "A peal of thunder echoes through the storm."
  - "Distant thunder rumbles ominously."
  - "Sudden thunder cracks overhead, sharp as breaking timber."
  - "The thunder grows louder, closer."

flash_then_thunder:
  - "Lightning flashes, followed seconds later by a roll of thunder."
  - "A bright flash splits the sky, and thunder follows close behind."
```

Implementation:
- Each event independently rolls one of three categories: `flashes`
  (40%), `thunderclaps` (40%), `flash_then_thunder` (20%).
- Within the chosen category, picks a random message uniformly.
- Broadcast to outdoor and threshold rooms in the zone (same gating
  as transition messages — threshold rooms see the message verbatim,
  no softening for lightning).
- Indoor and underground rooms silent.

## Phase G — Admin command

Create `commands/cmd_weather.py`:

```python
"""@weather admin command — inspect and set per-zone weather."""
```

Required behavior:
- `@weather` (no args): displays current weather across all known
  zones, plus aggregate stats (count by state).
- `@weather <zone_id>`: displays current weather for a specific zone,
  including the zone's resolved climate and the current season.
- `@weather <zone_id> <state>`: sets the zone's weather to the
  specified state. If the state is implausible for the zone's climate,
  shows a warning but proceeds (Option β from prior discussion).
- `@weather <zone_id> clear`: resets weather to `clear` (a valid
  set, not a special "reset" path — `clear` is just one of the
  weather states).
- `@weather tick`: forces an immediate `tick_weather()` evaluation
  (for testing/debugging without waiting 3.75 real minutes).

Permission: `cmd:perm(Admin) or perm(Developer)` (matches
`@calendar`).

Output formatting for `@weather` (no args):

```
DireEngine Weather
────────────────────────────────────────
crossingV2:        light_rain  (climate: temperate, plausible)
new_landing:       fog          (climate: coastal, plausible)
brookhollow_v3:    clear        (climate: temperate, plausible)
demo1:             snow         (climate: tropical, IMPLAUSIBLE — admin override)

Active states:
  clear:        1
  light_rain:   1
  fog:          1
  snow:         1

Tick interval:   15 game-minutes (~3.75 real minutes)
Lightning:       50% chance per tick during storm
Last tick:       2026-05-01T11:42:13-04:00
Next tick:       2026-05-01T11:45:58-04:00 (estimated)
```

Output for `@weather <zone_id>`:

```
Weather: crossingV2
────────────────────────────────────────
Current state:   light_rain
Climate:         temperate (resolved from "northern temperate")
Current season:  spring (real-world)
Plausible states for this climate:
  clear, cloudy, light_rain, heavy_rain, storm, fog,
  light_snow, heavy_snow
```

Add registration in `commands/default_cmdsets.py` near the
`CmdCalendar` registration (matching MT-514a pattern):

```python
from commands.cmd_weather import CmdWeather
# ... in at_cmdset_creation:
self.add(CmdWeather())
```

## Phase H — Tests

Add `tests/test_weather.py` with:

### Unit tests (pure logic)

- `resolve_climate` returns correct buckets for each keyword
- `resolve_climate` falls back to `temperate` with warning on no match
- `is_weather_plausible_for_climate` correctly accepts/rejects pairs
- Transition matrices load without error from YAML
- `_normalized_transition_row` correctly filters implausible states
  and normalizes weights
- `_pick_next_state` is deterministic when given an RNG with fixed seed

### Integration tests (with WeatherScript)

- Default weather for a zone with no recorded state is `clear`
- `set_current_weather` persists across script reloads
- `set_current_weather` to an implausible state succeeds with a
  warning logged but no exception
- `tick_weather` evaluates all known zones
- `tick_weather` returns transitions for zones that changed
- Two ticks produce statistically reasonable transition rates
  (e.g., over 100 ticks of clear-temperate-spring, transitions to
  cloudy occur within expected probability bounds)

### Messaging tests (mocked broadcast)

- Transition broadcast goes to outdoor rooms but not interior rooms
- Threshold rooms get softened messages
- Lightning messages fire at expected probability during storm
- No lightning during non-storm states

### Vocabulary alignment tests

- `_STATE_GROUP_VOCABULARY["weather"]` contains all 10 new states
- Test fixtures that assert weather vocabulary match the new tuple

Tests use the same Django + Evennia harness as `tests/test_calendar.py`.

## Phase I — Live smoke test

After all unit tests pass:

1. Restart the dev server (`./startWeb.bat` or equivalent).
2. As admin, run `@weather`. Verify output shape matches the spec.
3. Run `@weather <some-zone>`. Verify zone-specific output.
4. Run `@weather <some-zone> heavy_rain`. Verify the set succeeds
   and the zone's state changes.
5. Run `@weather <some-zone> blizzard` on a tropical-climate zone.
   Verify the implausibility warning appears AND the set still
   proceeds.
6. Run `@weather tick`. Verify a forced tick fires and transitions
   may occur.
7. Stand a test character in an outdoor room of an active-weather
   zone. Run `@weather <that-zone> storm` — set storm. Then run
   `@weather tick` repeatedly until you observe a lightning message.
   Verify only outdoor rooms receive it.
8. **Regression check from MT-T01:** Stand a test character in a
   `hallway` interior room of any zone. Confirm the room descrption
   does NOT show a `$state(invasion, ...)` block when no invasion
   is set, but DOES include `$state(season, ...)` and
   `$state(time, ...)` per the existing markup. (This confirms the
   MT-T01 state-mapping repair is still active.)

## Verification checklist

1. `world/weather.py` exists with the locked public API.
2. `world/content/climate_weather_compatibility.yaml` exists with
   all 8 climates.
3. `world/content/climate_keywords.yaml` exists.
4. `world/content/weather_transitions.yaml` exists with all 32
   matrices.
5. `world/content/weather_transition_messages.yaml` exists with
   reasonable coverage.
6. `world/content/weather_lightning_messages.yaml` exists.
7. `commands/cmd_weather.py` exists; `default_cmdsets.py` registers it.
8. `WeatherScript` is implemented and starts at server boot.
9. `_STATE_GROUP_VOCABULARY["weather"]` is the locked 10-value tuple.
10. Prompt template files updated with new vocabulary.
11. `state_description.md` updated.
12. All previously-passing tests still pass.
13. New `tests/test_weather.py` tests pass.
14. Live `@weather` command produces expected output.
15. Live transition messaging fires correctly to outdoor rooms only.
16. Live lightning messaging fires during storm state.
17. Climate resolver handles all real-world zones in `worlddata/zones/`
    without falling back to `temperate` for any of them.
    (Stop-and-report if any zone resolves to `temperate` because
    its climate text was unresolvable — surface for review.)

## Stop conditions

- Edit only files in the in-scope list.
- Do not modify zone YAML, calendar code, or any historical
  artifact directory.
- Stop and report on any test that fails outside the explicit
  vocab updates.
- Stop and report if any zone's climate text resolves to
  `temperate` via fallback (we want to know which zones need
  climate cleanup).
- Stop and report if the markup-render code path validates state
  keys against the vocabulary (which would mean changing vocab
  breaks existing zones).
- Stop and report if the existing scheduler convention differs
  from Evennia's `Script.at_repeat`.
- Do not "while I'm here" refactor any other system.
- Do not add invasion, foraging, severe weather, observation
  skill, or player-facing weather command.

## Required artifacts

1. `world/weather.py` (new, ~400 lines)
2. `world/content/climate_weather_compatibility.yaml` (new)
3. `world/content/climate_keywords.yaml` (new)
4. `world/content/weather_transitions.yaml` (new, 32 matrices)
5. `world/content/weather_transition_messages.yaml` (new)
6. `world/content/weather_lightning_messages.yaml` (new)
7. `commands/cmd_weather.py` (new)
8. Updated `commands/default_cmdsets.py`
9. Updated `server/conf/settings.py`
10. Updated `world/builder/prompting/room_description_prompt.py`
11. Updated `world/builder/templates/room_description_system_prompt.txt`
12. Updated `world/builder/templates/room_description_state_markup_prompt.txt`
13. Updated `state_description.md`
14. Updated `tests/test_room_description_prompt.py`
15. New `tests/test_weather.py`
16. `exports/mt514b_weather_validation.md` — validation report
    covering:
    - Verbatim "before"/"after" full test discovery summary lines
    - Verbatim output of live `@weather`, `@weather <zone>`,
      `@weather <zone> <state>`, `@weather <zone> blizzard` (tropical
      implausibility test), `@weather tick`
    - At least one captured transition message (admin sets weather,
      tick produces transition, message broadcast captured)
    - At least one captured lightning message during storm state
    - Confirmation that the MT-T01 regression repair is still active
      (interior + invasion mapping check)
    - List of files modified, matching the in-scope list
    - List of zones whose climate resolved to `temperate` via fallback
      (for review — these need climate cleanup in a future pass)

## Followup queue

- MT-514b-invasion (next): Add `current_invasion` runtime state
  with `@invasion` admin command. Small dispatch. Same persistence
  pattern as weather.
- MT-514c: Foraging refactor — consumes terrain + skill rank +
  calendar season + calendar time-of-day + weather state +
  invasion state.
- MT-514b-storms: Real lightning *strike* events (mechanical
  effect, target rooms, possible character damage in fully exposed
  positions). Consumer of the storm state.
- MT-514d-tornadoes: Tornado event system, only spawnable in
  temperate/continental climates during storm + spring/summer.
- MT-514e-hurricanes: Hurricane regime system, only spawnable
  in coastal/tropical climates.
- Future: `OBSERVE WEATHER` skill-gated player command with
  forecast.
- Future: Climate vocabulary enforcement at zone-YAML-load time.
- Future: Auto-generated transition messages for missing pairs
  (use AI to fill gaps in `weather_transition_messages.yaml`).
```

That's the dispatch.

A few things to watch for when the agent reports back:

**The 32 transition matrices.** This is the largest piece of content the agent has to write in any dispatch in this arc. The starter values should *feel* right but they're tuning targets, not gospel. When the agent's smoke test shows the system in motion, you'll likely see at least one transition that surprises you ("storm in spring boreal? really?"). That's normal — the matrices live in YAML for exactly this reason. Tune them in subsequent passes.

**The climate resolver fallback list.** Item 17 in the verification checklist is the load-bearing one for content health. Every zone whose climate text falls back to `temperate` is a zone where the system silently chose a default rather than matching what the builder intended. The agent's report should list these explicitly so you know which zones need climate cleanup.

**The schedule mechanism.** I told the agent to stop-and-report if your existing scheduler infrastructure uses a non-standard idiom. There's a `world/systems/scheduler.py` module that already does periodic work. If it has its own pattern (queues, decorators, registry), the agent should use that. If it's a thin wrapper around Evennia's `Script.at_repeat`, the agent uses Evennia's standard. Watch the report for which path they took and whether it makes sense.

**The vocab validation question.** I told the agent to stop-and-report if the markup-render path validates state keys against the vocab. If it does, expanding from 3 to 10 values is fine, but any zone that has `$state(rain, ...)` in its YAML will silently fail to render because `rain` is no longer in the vocab. We'd need a migration. The likelihood is low (markup rendering usually doesn't validate against vocab — it just substitutes when state matches), but the agent should check.

**The MT-T01 regression check in the live smoke test.** I added this to step 8 of Phase I. It's a free verification — while the agent is testing weather messaging in outdoor rooms, they can also confirm that interior rooms still have invasion in their state mapping. This catches any regression we accidentally introduced by touching the prompt vocab. Worth confirming explicitly.

Send the dispatch.