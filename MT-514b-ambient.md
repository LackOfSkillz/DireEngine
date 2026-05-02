# MT-514b-ambient — Two-tier tick architecture and ambient weather messages

## Background

The MT-514b weather arc shipped a system that broadcasts only on
state transitions. Between transitions, weather is silent. Players
see "The steady rains turn into a driving storm" when state
changes, but nothing during the 15+ game-minutes that storm holds.

Comparison to a parallel implementation in another DR-style
Evennia project surfaced two related improvements:

1. **Ambient messages** between transitions. When state holds,
   broadcast atmospheric flavor ("Thunder rumbles ominously
   overhead") to outdoor rooms. Makes weather feel alive in the
   gaps.
2. **Tick interval should match weather progression timescales.**
   Currently weather state can transition every 3.75 real minutes
   (15 game-minutes), which is meteorologically frantic — storms
   form and dissipate faster than real weather should. State
   transitions should be slower, but ambient flavor should be
   faster.

The cleanest solution is a two-tier tick architecture: outer
"atmospheric tick" every few minutes broadcasts ambient messages
when state holds; inner "state tick" every N atmospheric ticks
evaluates Markov transitions. One script, one timer, two rhythms.

This dispatch implements that architecture, extends weather YAML
schema to support ambient messages, ships placeholder content, and
adds regression coverage. Player-visible content expansion is
deferred to a separate content task.

## Architectural guardrails (READ FIRST)

The weather arc is closed and stable. This dispatch deliberately
preserves that stability by ADDING capabilities rather than
modifying existing ones. If you find yourself reworking
`tick_weather()` or `run_weather_cycle()`, stop and re-read scope.

**Frozen scope:**

1. Phase A: Extend weather state YAML schema to support optional
   `ambient_messages` field per state per climate.
2. Phase B: Add two-tier tick architecture to `WeatherScript`. Track
   atmospheric-tick counter; trigger state-progression every N
   atmospheric ticks.
3. Phase C: Add ambient broadcast helper that fires on
   atmospheric ticks when state holds (i.e., not on a state-tick
   that produced a transition).
4. Phase D: Settings entries for tick rates and atmospheric/state
   ratio.
5. Phase E: Ship placeholder ambient content — 2-3 ambient messages
   per state per climate, recognizable as placeholder so the human
   knows to expand them.
6. Phase F: Tests including bounded-time regression for the new
   atmospheric-tick path.
7. Phase G: Live verification — ambient message visible during
   state-hold tick in outdoor room; nothing during state-hold tick
   in indoor room.
8. Phase H: Validation artifact entry.

**Frozen what-not-to-do list:**

- DO NOT modify the existing public weather API. Source-stable:
  `get_current_weather`, `set_current_weather`, `get_weather_state`,
  `is_weather_plausible_for_climate`, `resolve_climate`,
  `tick_weather`, `run_weather_cycle`. The new behavior is added
  via internal helpers.
- DO NOT modify the cache layers from v3a/v5. The eligible-rooms
  cache is reused for ambient broadcasts; no new cache layers.
- DO NOT modify the calendar module, prompt module, prompt
  templates, design docs, or zone YAMLs.
- DO NOT modify foraging, ranger gather, NPCs, AI pipeline,
  builder, or any consumer of weather state.
- DO NOT modify lightning broadcast logic. Lightning still fires
  on state ticks during storms, separate from ambient.
- DO NOT add a second persistent script. One WeatherScript handles
  both rhythms via internal counter.
- DO NOT increase tick frequency beyond what settings explicitly
  allow. The atmospheric tick should be configurable but defaults
  set deliberately.
- DO NOT add ambient broadcasts to `set_current_weather()` admin
  override path. Admin overrides remain instantaneous; ambient
  flow is automatic-tick-only.
- DO NOT skip the bounded-time regression test. Atmospheric ticks
  fire more frequently than state ticks; perf must stay verified.
- DO NOT call `start()` on already-running scripts (the v4
  lifecycle bug).
- DO NOT write extensive ambient message content. Ship 2-3
  placeholders per state per climate. Content expansion is a
  separate human task.

**Stop-and-report conditions:**

- If the YAML schema extension conflicts with how existing zone
  loaders parse the file, stop and report.
- If two-tier tick logic introduces race conditions between
  atmospheric and state ticks, stop and report.
- If ambient broadcast performance regresses cycle time above the
  bounded threshold (1 second for atmospheric tick, 2 seconds for
  state tick), stop and report.
- If the placeholder content set conflicts with existing content
  conventions in zone YAMLs, stop and report.
- If live verification shows ambient messages bleeding into indoor
  rooms (gating broken), stop and report.
- If the natural tick path stops working after the architecture
  change (e.g., neither atmospheric nor state ticks fire), stop
  and report.

## Phase A — YAML schema extension

Read the existing weather state YAMLs to identify their structure.
Likely path: `world/content/weather_transition_messages.yaml` and
`world/content/weather_lightning_messages.yaml`. There may be a
parallel structure for ambient messages or this may be a new file.

### A.1 Extend or add ambient messages YAML

Either add an `ambient_messages` section to existing weather
content YAML, or create a new `world/content/weather_ambient_messages.yaml`
with parallel structure. Match whichever pattern existing weather
content uses.

Approximate shape:

```yaml
# world/content/weather_ambient_messages.yaml

temperate:
  clear:
    - "[PLACEHOLDER] A gentle breeze stirs the air."
    - "[PLACEHOLDER] Sunlight filters down warmly."
    - "[PLACEHOLDER] The sky stretches clear and blue overhead."
  cloudy:
    - "[PLACEHOLDER] Grey clouds drift slowly across the sky."
    - "[PLACEHOLDER] The overcast sky feels close and heavy."
  light_rain:
    - "[PLACEHOLDER] Steady rain patters on every surface."
    - "[PLACEHOLDER] Droplets tap quietly against stone and wood."
  heavy_rain:
    - "[PLACEHOLDER] Rain hammers down in relentless sheets."
    - "[PLACEHOLDER] Water streams across every surface."
  storm:
    - "[PLACEHOLDER] Thunder rumbles ominously overhead."
    - "[PLACEHOLDER] The storm rages with driving rain."
  fog:
    - "[PLACEHOLDER] Mist swirls in lazy tendrils."
    - "[PLACEHOLDER] Visibility is poor in the heavy fog."
  # ... other states

coastal:
  # ... mirror structure
arid:
  # ... mirror structure
# ... other climates
```

Each placeholder string is prefixed with `[PLACEHOLDER]` so it's
visually obvious in-game when ambient content hasn't been expanded
yet. The agent ships a starter set covering at minimum:
- Two climates (`temperate` and one other) with full state coverage
- Other climates with at least one state covered (the most common
  state for that climate)

This gives enough content for live verification to capture real
ambient messages without becoming a content-writing task.

### A.2 Loader integration

Identify how existing weather YAML content is loaded. Likely a
`load_weather_messages()` or similar helper. Extend it to load
ambient messages with the same pattern.

Add a public helper:

```python
def get_ambient_message(climate: str, weather_state: str) -> str:
    """Return a random ambient message for climate + state, or '' if none."""
    messages = _AMBIENT_MESSAGES.get(climate, {}).get(weather_state, [])
    if not messages:
        return ""
    return random.choice(messages)
```

If no ambient messages are defined for a climate/state combination,
the helper returns empty string and ambient broadcasting silently
skips that tick. This is correct behavior — content gaps don't
break the tick.

## Phase B — Two-tier tick architecture

Modify `WeatherScript` to support atmospheric and state rhythms.

### B.1 Add atmospheric-tick counter

```python
class WeatherScript(DefaultScript):
    def at_script_creation(self):
        # ... existing setup ...
        self.interval = ATMOSPHERIC_TICK_INTERVAL_SECONDS  # see Phase D
        self.persistent = True
        # ...
        self.db.atmospheric_tick_counter = 0

    def at_repeat(self):
        from django.conf import settings
        if not getattr(settings, "WEATHER_AUTOTICK_ENABLED", True):
            return

        # Always fire atmospheric tick
        run_atmospheric_tick()

        # State tick fires every Nth atmospheric tick
        ratio = getattr(settings, "WEATHER_STATE_TICK_RATIO", 5)
        self.db.atmospheric_tick_counter += 1
        if self.db.atmospheric_tick_counter >= ratio:
            self.db.atmospheric_tick_counter = 0
            run_weather_cycle()  # existing state-progression path
```

The atmospheric tick is the new fast rhythm. The state tick fires
every N atmospheric ticks (default 5), preserving the existing
slower progression rhythm.

### B.2 The atmospheric tick path

```python
def run_atmospheric_tick() -> None:
    """Broadcast ambient messages for zones whose weather is holding.

    Does NOT advance state. Does NOT compute Markov transitions.
    Pure broadcast layer — reads current state, dispatches ambient
    messages to weather-eligible rooms.
    """
    script = _get_weather_script()
    if script is None:
        return
    script._ensure_state_cache_loaded()

    for zone_id, current_state in script._zone_invasion_cache.items():
        # NOTE: agent uses correct cache name from v5 implementation
        climate = _resolve_climate_for_zone(zone_id)
        message = get_ambient_message(climate, current_state)
        if not message:
            continue

        # Probabilistic gate to avoid noise
        ambient_probability = getattr(
            settings, "WEATHER_AMBIENT_BROADCAST_PROBABILITY", 0.4
        )
        if random.random() > ambient_probability:
            continue

        # Reuse v3a's eligible-rooms cache
        eligible_rooms = _eligible_rooms_for_zone(zone_id)
        for room in eligible_rooms:
            _broadcast_message(room, message)
```

The probabilistic gate (default 40%) prevents ambient messages
from firing on every atmospheric tick, which would feel like
spam. Configurable via settings.

### B.3 Coordination with state ticks

When a state tick fires AND produces a transition, that tick's
atmospheric work is suppressed for those zones (transition message
already covered the broadcast).

When a state tick fires AND state holds (no transition), the
atmospheric portion of that tick still fires normally. Players see
either a transition OR an ambient, not both, on a state-tick.

The agent handles this coordination by either:
- Running atmospheric tick BEFORE state tick (then state tick
  produces transitions that supersede ambient), or
- Running state tick first and tracking which zones transitioned,
  skipping those in the atmospheric pass

Whichever is cleaner in the existing code. Document the choice.

## Phase C — Ambient broadcast helper

The actual broadcast call should reuse existing infrastructure:
- `_eligible_rooms_for_zone()` from v3a (cached)
- `_broadcast_message()` or whatever the existing broadcast
  primitive is

The agent reads the existing broadcast helpers and uses them
directly. No new broadcast code; just a new caller.

## Phase D — Settings entries

In `server/conf/settings.py`, add:

```python
# MT-514b-ambient: Two-tier weather tick architecture
#
# Atmospheric tick: fast rhythm, broadcasts ambient messages.
# Default: 4 minutes (~240s). Adjust to taste.
WEATHER_ATMOSPHERIC_TICK_INTERVAL_SECONDS = 240

# State tick ratio: state progression fires every Nth atmospheric tick.
# Default: 5 (atmospheric tick every 4 minutes, state tick every 20 minutes).
# Increases yield slower weather progression more meteorologically realistic.
WEATHER_STATE_TICK_RATIO = 5

# Ambient broadcast probability: chance ambient message fires on
# any given atmospheric tick when state is holding. 0.0 = never,
# 1.0 = every tick. Default 0.4 keeps weather alive without spam.
WEATHER_AMBIENT_BROADCAST_PROBABILITY = 0.4
```

The script's `interval` property should derive from
`WEATHER_ATMOSPHERIC_TICK_INTERVAL_SECONDS` rather than hardcoding.

The existing `WEATHER_AUTOTICK_ENABLED` flag from v4 stays in
place and continues to gate the entire `at_repeat()` body.

## Phase E — Placeholder content

Ship the YAML from Phase A.1 with [PLACEHOLDER] prefixes on every
ambient message string. Coverage requirement (minimum):

- `temperate` climate: all defined weather states (clear, cloudy,
  light_rain, heavy_rain, storm, fog, light_snow, heavy_snow,
  blizzard) — 2-3 placeholders per state.
- One additional climate (agent picks based on what zones in the
  game database actually use): all states for that climate.
- Remaining climates: minimum one placeholder per "common" state
  (clear and the most likely transition target for that climate).

Total content: roughly 60-100 placeholder strings. Sufficient for
live verification to actually capture ambient messages without
becoming a content writing task.

## Phase F — Tests

Add to `tests/test_weather.py`:

### F.1 YAML loading test

```python
def test_ambient_messages_load(self):
    """Ambient messages YAML loads correctly."""
    # Use existing loader; verify get_ambient_message returns
    # something for at least one climate/state combination.
    ...

def test_ambient_message_falls_back_to_empty(self):
    """Unknown climate/state returns empty string, no exception."""
    self.assertEqual(get_ambient_message("nonexistent", "clear"), "")
    self.assertEqual(get_ambient_message("temperate", "nonexistent"), "")
```

### F.2 Two-tier tick test

```python
def test_atmospheric_tick_does_not_advance_state(self):
    """Atmospheric tick broadcasts ambient but doesn't transition state."""
    # Set known state, run atmospheric tick, verify state unchanged.
    ...

def test_state_tick_fires_every_N_atmospheric_ticks(self):
    """State progression fires on the configured ratio."""
    # Mock atmospheric ticks N times, verify state tick fires
    # exactly once at the Nth call.
    ...

def test_atmospheric_tick_respects_autotick_flag(self):
    """When WEATHER_AUTOTICK_ENABLED is False, neither tier fires."""
    ...
```

### F.3 Bounded-time regression for atmospheric tick

```python
def test_run_atmospheric_tick_completes_within_bounded_time(self):
    """Atmospheric ticks fire ~5x more frequently than state ticks.
    Performance must stay tight to avoid cumulative drag."""
    import time
    run_atmospheric_tick()  # warm
    start = time.monotonic()
    run_atmospheric_tick()
    elapsed = time.monotonic() - start
    self.assertLess(
        elapsed, 1.0,
        f"run_atmospheric_tick() took {elapsed:.3f}s, expected < 1.0s"
    )
```

The existing `test_run_weather_cycle_completes_within_bounded_time`
from v3a/v5 stays unchanged. State ticks have 2-second budget;
atmospheric ticks have 1-second budget (less work per tick).

## Phase G — Live verification

After implementation, restart the server. Verify in the live game:

### G.1 Ambient broadcast in outdoor room

1. Connect via webclient as admin (`jekar`).
2. Teleport to outdoor weather-eligible room: `@teleport #4213`.
3. Set weather to a state with placeholder ambient content:
   `@weather new_landing storm` (assuming temperate climate
   has storm placeholders).
4. Wait for atmospheric tick (4 minutes default), OR force tick
   via `@weather tick` (which now triggers state cycle, not
   atmospheric — see note below).
5. Repeat: continue waiting for atmospheric ticks until ambient
   message appears (probabilistic, may take 2-3 atmospheric ticks
   at 40% probability).
6. Capture the verbatim ambient message that appears.

Note on `@weather tick`: this command currently triggers a state
cycle. Whether it should trigger atmospheric ticks too is a UX
question; the dispatch defers it. Admin can use `@py
world.weather.run_atmospheric_tick()` to force atmospheric tick if
needed for verification.

### G.2 Indoor gating preserved

1. Teleport to indoor room: `@teleport #4212`.
2. Wait for several atmospheric ticks across a state-hold window.
3. Verify: NO ambient messages appear in the indoor room's feed.

If indoor rooms receive ambient broadcasts, the gating is broken.
Stop and report.

### G.3 State progression preserved

1. Wait for at least one full state-tick cycle (5 atmospheric ticks
   = 20 minutes default).
2. Verify weather state has progressed (or had the opportunity to)
   per Markov chain.

## Phase H — Validation artifact

APPEND a new section to `exports/mt514b_weather_validation.md`
titled `## MT-514b-ambient — Two-tier tick architecture and ambient messages`.

Section contents:

1. **Phase A YAML schema.** Where ambient content lives, structure.
2. **Phase B two-tier tick.** Counter mechanism, ratio default,
   coordination with state ticks.
3. **Phase C broadcast helper.** Reuses v3a's eligible-rooms cache.
4. **Phase D settings entries.** New flags, default values.
5. **Phase E placeholder content.** Coverage shipped, expansion
   note for human content task.
6. **Phase F test results.** All passing.
7. **Phase G live verification.** Verbatim ambient message
   captured, indoor gating preserved.
8. **Final state.** One-line: "Two-tier ticks shipped. Weather
   feels alive between transitions. Content expansion is queued as
   human task."

## Verification checklist

1. Ambient messages YAML loads cleanly.
2. Two-tier tick architecture preserves existing state progression.
3. Atmospheric ticks broadcast ambient messages probabilistically.
4. Settings entries control all three rates (atmospheric interval,
   state ratio, ambient probability).
5. Bounded-time regression test for atmospheric tick passes.
6. Existing bounded-time regression test for state tick still
   passes.
7. All previously-passing tests still pass.
8. Live ambient message captured in outdoor room.
9. Live indoor room receives no ambient broadcasts.
10. Validation artifact updated.
11. No code outside the in-scope list modified.

## Stop conditions

- Edit only `world/weather.py`, `tests/test_weather.py`,
  `server/conf/settings.py`, `world/content/weather_ambient_messages.yaml`
  (or wherever ambient content lives), the validation artifact.
  No other files.
- Stop and report on YAML schema conflicts.
- Stop and report on two-tier tick race conditions.
- Stop and report on perf regression.
- Stop and report on indoor gating breakage.
- Do not extend placeholder content beyond the minimum specified.

## Required artifacts

1. Updated `world/weather.py` (atmospheric tick logic, ambient
   broadcast helper)
2. New or updated `world/content/weather_ambient_messages.yaml`
3. Updated `server/conf/settings.py` (new settings entries)
4. Updated `tests/test_weather.py` (new test cases)
5. Updated `exports/mt514b_weather_validation.md` (new section)

## Followup queue

- Content expansion task: replace [PLACEHOLDER] ambient messages
  with proper content. Approximately 240-480 short atmospheric
  sentences across all climate/state combinations. This is human
  content work; not a dispatch.
- Future: consider whether `@weather tick` admin command should
  trigger atmospheric or state tick (or both). Current behavior:
  triggers state tick only. Defer until UX feedback.
- MT-514b-invasion: deferred from before this dispatch. Unblocked
  after this lands; same patterns apply (per-zone state, no
  broadcasting needed for invasion).
- MT-514c: Foraging refactor, unblocked after invasion ships.
```

That's the dispatch.

A few notes on what I built into it:

**The two-tier architecture is the load-bearing change.** Single `WeatherScript` handles both rhythms via an internal counter. Atmospheric tick fires every 4 real minutes (default), state tick fires every 5 atmospheric ticks (~20 real minutes default). That gives players ambient flavor on a noticeable rhythm and weather progression on a meteorologically appropriate one.

**The probabilistic gate (40% default) prevents ambient spam.** Without it, every atmospheric tick produces a broadcast and players see weather messages every 4 minutes constantly. With probabilistic gating, ambient messages feel earned — sometimes the world is quiet, sometimes it murmurs.

**All three rates are settings-driven.** You can tune atmospheric interval, state ratio, and ambient probability without code changes. If 40% feels noisy, drop it to 25%. If 4-minute intervals feel slow, drop to 3 minutes. Configurable from day one.

**Placeholder content is bounded and obvious.** The dispatch ships ~60-100 placeholder strings, all prefixed with `[PLACEHOLDER]` so they're visually obvious in-game. You'll see "[PLACEHOLDER] Thunder rumbles ominously overhead" during testing, and you'll know exactly what content you need to replace later. The agent doesn't try to write good ambient content; that's your task on your timeline.

**The state cycle is preserved unchanged.** v5's perf-tuned `run_weather_cycle()` still fires on state ticks. The atmospheric tick is a new path that runs alongside, reusing the same eligible-rooms cache from v3a. Zero changes to the perf-tuned hot path.

**Coordination between atmospheric and state ticks.** When a state tick produces a transition, that broadcast supersedes the atmospheric broadcast for affected zones. The dispatch lets the agent decide the cleanest implementation order but requires the result: players see one message per cycle per zone, not two.

**Indoor gating is preserved via the existing cache.** Ambient broadcasts use `_eligible_rooms_for_zone()` which already filters out indoor rooms. No new gating logic needed; just reuse existing.

**Bounded-time regression for atmospheric tick at 1 second.** Tighter than state tick's 2-second budget because atmospheric ticks fire 5× more frequently. Cumulative drag matters here.

**The dispatch unblocks invasion explicitly in the followup queue.** Once this ships, MT-514b-invasion is the next thing.

When the agent reports back, ideally we'll see:
- Two-tier tick architecture working
- Ambient placeholder messages firing in outdoor rooms during state-hold ticks
- Indoor rooms still silent during ambient ticks
- All tests pass including the new bounded-time guard
- State progression still works on the longer rhythm
- Validation artifact entry
- Then we send MT-514b-invasion
