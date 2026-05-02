# MT-514b-invasion — Per-zone invasion runtime state (state-only, mobile threats deferred)

## Background

The MT-514b weather arc shipped runtime state that AI-generated content
consumes (calendar, weather, ambient atmospheric tier). MT-514c
(foraging refactor) is the next major dispatch and needs a third
runtime state input alongside terrain, weather, and calendar:
**invasion state** — is a zone currently under invasion, and if so,
what kind?

This dispatch ships invasion as readable runtime state ONLY. No mobile
threats. No NPCs spawned. No combat. No invasion-driven broadcasting.
Just per-zone state that admins can set, descriptions can read via
state-markup, and foraging will eventually consume.

The reason for the narrow scope: actual mobile invasion threats
(swarm-style "horde" mobs wandering the streets) require solving the
NPC movement perf problem first. That problem caused enough lag in
earlier guard-patrol experiments that mobile NPCs were tabled
project-wide. It needs its own focused arc (MT-514d) before invasion
can have actual orcs in the rooms.

This dispatch unblocks MT-514c without depending on MT-514d. Mobile
threats are the followup.

The architectural patterns from the weather arc are now well-established:

1. ScriptDB fallback for singleton script access (cross-process safe)
2. Script-local in-memory state cache with write-through persistence
3. Avoid calling `start()` on already-running scripts (lifecycle bug
   from MT-514b-perf-v4)
4. Bounded-time regression test plus production-shape verification

Invasion is structurally simpler than weather — no auto-progression,
no Markov chains, no broadcasting, no climate plausibility. It's
admin-set persistent state with cached reads. If those patterns
transfer cleanly, invasion ships in one dispatch.

## Architectural guardrails (READ FIRST)

The patterns are proven through the weather arc. The biggest risk in
this dispatch is NOT implementation — it's pattern drift, where the
agent invents new patterns instead of mirroring weather's. When in
doubt, look at what `world/weather.py` does and do the analogous thing
in `world/invasion.py`.

The second-biggest risk is scope creep into mobile-threat territory.
This dispatch ships state-only. Spawning, combat, NPC movement, and
invasion-driven broadcasts are explicitly out of scope.

**Frozen scope:**

1. Phase A: Read existing zone YAMLs and codebase for any existing
   invasion vocabulary or stub references. Lock vocabulary based on
   what's there.
2. Phase B: Create `world/invasion.py` mirroring `world/weather.py`'s
   structure — module-level public API, singleton script class with
   cached state, ScriptDB fallback in `_get_invasion_script()`.
3. Phase C: Create `commands/cmd_invasion.py` with `@invasion`
   admin command for inspection and admin overrides.
4. Phase D: Register `CmdInvasion` in `commands/default_cmdsets.py`.
5. Phase E: Wire invasion script startup in
   `server/conf/at_server_startstop.py` (parallel to weather
   startup).
6. Phase F: Add `tests/test_invasion.py` with bounded-time regression
   test AND cache-survival test from day one.
7. Phase G: Live verification — `@invasion` admin command works,
   state persists across server restart.
8. Phase H: Verify state-markup machinery already supports
   `$state(invasion, ...)` references. If yes, document. If no,
   stop and report (that's a separate dispatch).
9. Phase I: Validation artifact at `exports/mt514b_invasion_validation.md`.

**Frozen what-not-to-do list:**

- DO NOT spawn NPCs, mobile threats, swarm mobs, or any objects in
  rooms in response to invasion state. Invasion is readable state
  ONLY. Mobile threats are deferred to a future arc that depends on
  MT-514d (NPC movement perf diagnostic).
- DO NOT add invasion broadcasting (transition messages, atmospheric
  flavor on invasion start/end, etc.). Invasions are not weather.
  Future dispatches may add broadcast-on-state-change; this dispatch
  does not.
- DO NOT add auto-progression. Invasions don't tick automatically.
  No `at_repeat()` work in this dispatch beyond what Evennia
  requires for a persistent script. Set `interval=0` or whatever
  Evennia requires for "no automatic repeat."
- DO NOT add invasion-affected room descriptions. The state-markup
  machinery from MT-T01 should already support
  `$state(invasion, ...)` syntax — Phase H verifies that. If
  descriptions need new authoring to consume invasion state, that's
  a content task, not this dispatch.
- DO NOT touch `world/weather.py` or any weather code. Invasion is
  a separate module.
- DO NOT modify the calendar module, prompt module, prompt
  templates, design docs, or zone YAMLs.
- DO NOT modify foraging, ranger gather, NPCs, AI pipeline,
  builder, or any consumer of weather/invasion state. MT-514c
  (foraging) is the next dispatch and will consume invasion state;
  this dispatch only ships the producer.
- DO NOT add new third-party dependencies.
- DO NOT skip the bounded-time regression test. The weather arc's
  hardest lesson was that perf regressions ship silently without a
  test guarding them.
- DO NOT skip the cache-survival test. The v4 lifecycle bug
  (calling `start()` on a running script wipes caches) must be
  guarded against from day one in any new singleton script module.
- DO NOT call `start()` on an already-running script anywhere in
  the invasion module.
- DO NOT pre-commit to specific invasion type vocabulary without
  reading whether existing zone YAMLs already mention invasion
  types. Match what's there.

**Stop-and-report conditions:**

- If existing zone YAMLs reference invasion types/states that
  conflict with proposed vocabulary, stop and report. We need
  alignment before locking vocab.
- If existing weather/zone code already has an invasion stub that
  conflicts with the new module's structure, stop and report.
  We'll discuss whether to extend the stub or replace it.
- If the ScriptDB fallback pattern doesn't translate cleanly to a
  new singleton (e.g., invasion script class causes Evennia
  startup-order issues), stop and report.
- If the bounded-time regression test reveals state read/write is
  somehow already slow on the very first implementation, stop and
  report. That would mean the weather patterns aren't transferring
  cleanly.
- If `@invasion` admin command structure can't naturally mirror
  `@weather`, stop and report. Pattern drift is a code smell.
- If state persistence doesn't survive server restart in Phase G
  verification, stop and report.
- If Phase H reveals the state-markup machinery does NOT support
  `$state(invasion, ...)` syntax (or has a stub that's broken),
  stop and report. Wiring the markup is a separate concern, not
  silent expansion of this dispatch.

## Phase A — Vocabulary discovery

Before locking invasion type vocabulary, the agent searches existing
codebase for any reference to invasion concepts:

```bash
# Zone YAML references
grep -ri "invasion" world/worlddata/zones/

# State markup references in templates and prompts
grep -ri "invasion" world/builder/templates/
grep -ri "invasion" world/builder/prompting/
grep -ri "state(invasion" world/

# Existing stubs anywhere
grep -ri "invasion" --include="*.py" .

# Settings or config references
grep -ri "INVASION" --include="*.py" server/conf/
```

The agent reads what's found and decides:

- If concrete invasion types exist (e.g., "goblin_raid", "siege",
  "monster_horde"), `_INVASION_TYPES` includes them.
- If references exist but vocabulary is generic (`$state(invasion,
  ...)` with no specific types), the agent picks a small starter
  vocabulary covering common DR-style invasion archetypes.
- If references conflict (different files use incompatible vocab),
  STOP and report.

Recommended starter vocabulary if nothing is locked yet:

```python
_INVASION_TYPES = (
    "none",           # default — no invasion active
    "goblin_raid",    # small mobile threat
    "bandit_incursion",  # criminal element infiltrating
    "monster_horde",  # large-scale invasion
    "siege",          # static threat from outside
    "infestation",    # vermin, pests, supernatural creatures
)
```

These are starter values. The agent picks something reasonable based
on findings; we can expand later via content updates without code
changes.

Document the chosen vocabulary in the validation artifact with a
note that it's expandable.

## Phase B — Create `world/invasion.py`

Mirror `world/weather.py` structure. Reference that file explicitly
while implementing.

### B.1 Module skeleton

```python
# world/invasion.py

"""Per-zone invasion runtime state.

Invasions are admin-set persistent state read by other systems
(descriptions via state-markup, foraging, eventually mobile threats).
This module ships state ONLY — no auto-progression, no broadcasting,
no NPC spawning. Mobile invasion threats depend on MT-514d (NPC
movement perf) and are a future arc.

Patterns mirror world/weather.py: ScriptDB fallback for cross-process
script access, script-local in-memory cache with write-through
persistence, careful avoidance of the v4 lifecycle bug (no start()
on running scripts).
"""

import random  # only if needed; probably not
from django.conf import settings
import evennia
from evennia.scripts.scripts import DefaultScript
from evennia.scripts.models import ScriptDB

INVASION_SCRIPT_KEY = "global_invasion"
DEFAULT_INVASION = "none"

_INVASION_TYPES = (
    # ... from Phase A discovery ...
)

_INVASION_STATE_PREFIX = "invasion_state__"
_INVASION_META_PREFIX = "invasion_meta__"
```

### B.2 The script class

```python
class InvasionScript(DefaultScript):
    """Singleton script holding per-zone invasion state.

    Mirrors WeatherScript's caching pattern. interval=0 because
    invasions don't auto-progress; admin-set or quest-set only.
    """

    def at_script_creation(self):
        self.key = INVASION_SCRIPT_KEY
        self.persistent = True
        self.interval = 0  # No auto-tick
        self.repeats = 0

        self._zone_invasion_cache: dict[str, str] = {}
        self._zone_meta_cache: dict[str, dict] = {}
        self._cache_loaded = False

    def at_start(self):
        # Reset caches on script (re)start. Lazy load on first read.
        # Same pattern as WeatherScript post-v5.
        self._zone_invasion_cache = {}
        self._zone_meta_cache = {}
        self._cache_loaded = False

    def at_repeat(self):
        # No-op; invasions don't progress automatically.
        # interval=0 should mean this isn't called, but defensive.
        return

    def _ensure_state_cache_loaded(self) -> None:
        if self._cache_loaded:
            return
        for attr in self.db_attributes.all():
            key = attr.db_key
            if key.startswith(_INVASION_STATE_PREFIX):
                zone_id = key[len(_INVASION_STATE_PREFIX):]
                self._zone_invasion_cache[zone_id] = attr.value
            elif key.startswith(_INVASION_META_PREFIX):
                zone_id = key[len(_INVASION_META_PREFIX):]
                self._zone_meta_cache[zone_id] = attr.value
        self._cache_loaded = True
```

### B.3 The script lookup helper

```python
def _get_invasion_script():
    """Return the global invasion script, working from any context.

    Mirrors world.weather._get_weather_script(). Includes ScriptDB
    fallback for external-process access. Does NOT call start() on
    an already-running script (the MT-514b-perf-v4 lifecycle bug).
    """
    search_script = getattr(evennia, "search_script", None)
    if search_script is not None:
        results = search_script(INVASION_SCRIPT_KEY)
        if results:
            return results[0]

    script = ScriptDB.objects.filter(
        db_key=INVASION_SCRIPT_KEY,
        db_typeclass_path="world.invasion.InvasionScript",
    ).order_by("id").first()
    return script
```

### B.4 Public API

```python
def get_current_invasion(zone_id: str) -> str:
    """Return the current invasion type for a zone (or 'none')."""
    script = _get_invasion_script()
    if script is None:
        return DEFAULT_INVASION
    script._ensure_state_cache_loaded()
    return script._zone_invasion_cache.get(zone_id, DEFAULT_INVASION)


def set_current_invasion(
    zone_id: str,
    value: str,
    *,
    source: str = "admin",
) -> None:
    """Set the current invasion type for a zone, with write-through.

    Raises ValueError if value is not in _INVASION_TYPES.
    """
    if value not in _INVASION_TYPES:
        raise ValueError(
            f"Unknown invasion type: {value}. "
            f"Valid types: {_INVASION_TYPES}"
        )
    script = _get_invasion_script()
    if script is None:
        return
    script._ensure_state_cache_loaded()

    # Write-through: cache + persistence in lockstep
    script._zone_invasion_cache[zone_id] = value
    script.attributes.add(f"{_INVASION_STATE_PREFIX}{zone_id}", value)

    # Optional metadata: timestamp, source. Mirror weather's pattern
    # if it tracks similar metadata.
    meta = {
        "source": source,
        # Add timestamp if weather does
    }
    script._zone_meta_cache[zone_id] = meta
    script.attributes.add(f"{_INVASION_META_PREFIX}{zone_id}", meta)


def get_invasion_state() -> dict:
    """Return structured snapshot of all zones' invasion state.

    Mirrors weather.get_weather_state() shape: zones dict, counts dict.
    """
    script = _get_invasion_script()
    if script is None:
        return {"zones": {}, "counts": {}}
    script._ensure_state_cache_loaded()

    zones = dict(script._zone_invasion_cache)
    counts: dict[str, int] = {}
    for invasion_type in zones.values():
        counts[invasion_type] = counts.get(invasion_type, 0) + 1

    return {"zones": zones, "counts": counts}


def is_zone_invaded(zone_id: str) -> bool:
    """Convenience: True if zone has any active invasion."""
    return get_current_invasion(zone_id) != DEFAULT_INVASION


def list_invasion_types() -> tuple[str, ...]:
    """Return the canonical list of valid invasion types."""
    return _INVASION_TYPES
```

## Phase C — Create `commands/cmd_invasion.py`

Mirror `commands/cmd_weather.py`. The `@invasion` admin command
should support:

- `@invasion` — list all zones and their current invasion state
- `@invasion <zone_id>` — show state for a specific zone
- `@invasion <zone_id> <type>` — set invasion type for a zone
- `@invasion <zone_id> none` — clear invasion for a zone
- `@invasion --types` or similar — list valid invasion types

Output formatting can be simpler than `@weather` since there's less
to display — no climate plausibility, no transition timing.

Use the same lock structure as `@weather` (builder/admin only).

## Phase D — Register the command

In `commands/default_cmdsets.py`, find the `CmdWeather` registration
and add an analogous `CmdInvasion` registration. Mirror exactly.

## Phase E — Wire invasion script startup

In `server/conf/at_server_startstop.py`, find where the
`WeatherScript` is created or looked up at startup. Add an
analogous invasion script startup hook.

The script should:
- Be created on first server start
- Be retrieved (NOT recreated, NOT `.start()`-called) on subsequent
  starts
- Use the same ScriptDB fallback pattern that the weather startup
  uses

## Phase F — Tests

Create `tests/test_invasion.py` with at minimum:

### F.1 Basic state read/write

```python
class InvasionStateTests(unittest.TestCase):

    def test_default_invasion_is_none(self):
        # When no invasion is set, get_current_invasion returns 'none'
        ...

    def test_set_and_get_invasion(self):
        # Round-trip a state value
        ...

    def test_invalid_invasion_type_raises(self):
        # set_current_invasion with unknown type raises ValueError
        with self.assertRaises(ValueError):
            invasion.set_current_invasion("zone_x", "not_a_real_type")

    def test_is_zone_invaded(self):
        # Returns False for default, True for any non-default
        ...

    def test_clear_invasion(self):
        # Setting to 'none' clears active state
        ...
```

### F.2 Cache survival (the v4 lesson)

```python
class InvasionCacheTests(unittest.TestCase):
    """Cache behavior must not regress (the v4 lifecycle lesson)."""

    def test_cache_populated_after_first_read(self):
        # First get_current_invasion populates the cache
        ...

    def test_cache_survives_subsequent_reads(self):
        # Repeated reads don't wipe the cache.
        # This is the explicit guard against v4's
        # 'calling start() on running script wipes caches' bug.
        invasion.set_current_invasion("zone_a", "goblin_raid")
        # Confirm cache is populated
        script = invasion._get_invasion_script()
        self.assertEqual(len(script._zone_invasion_cache), 1)
        # Multiple reads should not wipe
        for _ in range(10):
            invasion.get_current_invasion("zone_a")
        self.assertEqual(len(script._zone_invasion_cache), 1)

    def test_cache_invalidated_on_at_start(self):
        # at_start() correctly resets the cache
        ...

    def test_writes_persist_to_db_attributes(self):
        # write-through: state visible in script.db_attributes
        ...
```

### F.3 Bounded-time regression

```python
class InvasionStateBoundedTimeTests(unittest.TestCase):
    """Performance regression guard."""

    def test_get_invasion_state_under_threshold(self):
        # Mirror weather's bounded-time test pattern.
        # Invasion is simpler than weather, so bound is tighter.
        import time
        # Warm path
        invasion.get_invasion_state()
        # Measure
        start = time.monotonic()
        invasion.get_invasion_state()
        elapsed = time.monotonic() - start
        self.assertLess(
            elapsed, 1.0,
            f"get_invasion_state() took {elapsed:.3f}s, "
            f"expected < 1.0s"
        )
```

The bounded threshold is 1 second (tighter than weather's 2 seconds)
because invasion has fewer per-zone operations. If this fails on
first run, the patterns aren't transferring cleanly — STOP and
report.

## Phase G — Live verification

After implementation, restart the server. Verify in the live game:

### G.1 Admin command works

1. Connect via webclient or `evennia shell -c` (whichever is
   reliable).
2. Run `@invasion` — verify clean listing of all zones.
3. Run `@invasion new_landing goblin_raid` — verify confirmation.
4. Run `@invasion new_landing` — verify state shows `goblin_raid`.
5. Run `@invasion new_landing none` — verify clearing works.

### G.2 State persists across restart

1. Set invasion: `@invasion new_landing siege`.
2. Verify: `@invasion new_landing` returns `siege`.
3. Restart server.
4. Verify: `@invasion new_landing` still returns `siege`.

### G.3 Cycle time is fast

```python
import time
from world import invasion

# Warm
invasion.get_invasion_state()

# Measure
start = time.monotonic()
state = invasion.get_invasion_state()
elapsed = time.monotonic() - start
print(f"get_invasion_state() in production: {elapsed:.3f}s")
```

If this takes more than ~100ms in production, something is wrong.
Document the measurement.

## Phase H — State-markup integration check

The state-markup machinery from MT-T01 should already support
`$state(invasion, <invasion_type>, ...)` references. This phase
verifies that without modifying anything.

### H.1 Discovery

```bash
grep -ri "state(invasion" world/builder/
grep -ri "invasion" world/builder/prompting/room_description_prompt.py
```

### H.2 Behavior verification

Try a state-markup expression in a Python shell or test:

```python
# In whatever context state-markup is normally evaluated
markup = "$state(invasion, goblin_raid, 'goblins are raiding the streets')"
# Set the zone to goblin_raid invasion
# Render the markup
# Confirm the conditional content appears
```

If this works, document it. If it doesn't work because the markup
machinery doesn't recognize `invasion` as a state group, STOP and
report. That's a markup-system task, not part of this dispatch.

The goal of Phase H is to verify the wiring exists, NOT to add
content that uses it. Authoring invasion-aware descriptions is a
content task that lives outside this dispatch.

## Phase I — Validation artifact

Create `exports/mt514b_invasion_validation.md` with sections for
each phase, mirroring `exports/mt514b_weather_validation.md`'s
structure but much shorter. Include:

1. **Phase A vocabulary discovery.** What was found, what was
   chosen, why.
2. **Phase B-E implementation.** Files created/modified, patterns
   mirrored from weather.
3. **Phase F tests.** All passing including cache-survival and
   bounded-time.
4. **Phase G live verification.** Verbatim outputs of each
   verification step.
5. **Phase H markup integration.** What works, what doesn't,
   what's deferred.
6. **One-line closing.** "MT-514b-invasion shipped. State-only,
   mobile threats deferred to MT-514d arc. Patterns transferred
   cleanly from weather."

If anything blocked, the artifact says so and the section ends
with the BLOCKED status.

## Verification checklist

1. Phase A vocabulary discovery completed; vocab locked based on
   findings.
2. `world/invasion.py` created with all the patterns from weather
   (ScriptDB fallback, script-local cache, write-through
   persistence, lifecycle correctness, no `start()` on running
   scripts).
3. `commands/cmd_invasion.py` registered in `default_cmdsets.py`.
4. `server/conf/at_server_startstop.py` includes invasion script
   startup.
5. `tests/test_invasion.py` includes the cache-survival regression
   test (the v4 lesson) and the bounded-time test.
6. All previously-passing tests still pass.
7. `@invasion` admin command works live.
8. State persists across server restart.
9. `get_invasion_state()` completes in under 100ms in production.
10. State-markup `$state(invasion, ...)` syntax confirmed working
    OR explicitly documented as deferred follow-up.
11. Validation artifact created.
12. No code outside the in-scope list modified.

## Stop conditions

- Edit only `world/invasion.py` (new), `commands/cmd_invasion.py`
  (new), `commands/default_cmdsets.py` (extend),
  `server/conf/at_server_startstop.py` (extend),
  `server/conf/settings.py` (only if vocabulary needs settings
  entries), `tests/test_invasion.py` (new), the new validation
  artifact. No other files.
- Stop and report on vocabulary conflicts.
- Stop and report on existing stub conflicts.
- Stop and report on Evennia startup-order issues.
- Stop and report on persistence failures.
- Stop and report if patterns don't transfer cleanly (e.g.,
  bounded-time test fails on first run).
- Stop and report if state-markup machinery doesn't support
  `$state(invasion, ...)`.
- Do not refactor weather code "while I'm here."
- Do not add invasion broadcasting, auto-progression, NPC
  spawning, mobile threats, or any features beyond admin-set
  persistent state.

## Required artifacts

1. `world/invasion.py` (new)
2. `commands/cmd_invasion.py` (new)
3. Updated `commands/default_cmdsets.py`
4. Updated `server/conf/at_server_startstop.py`
5. `tests/test_invasion.py` (new)
6. Possibly updated `server/conf/settings.py`
7. `exports/mt514b_invasion_validation.md` (new)

## Followup queue

- **MT-514c (next):** Foraging refactor consuming terrain + skill
  rank + calendar season + calendar time-of-day + weather +
  invasion. Now safe to build with all four runtime state systems
  shipped.
- **MT-514d (npc-movement-perf):** Diagnostic-first dispatch for
  the NPC movement lag problem that originally tabled patrolling
  guards. Per repo audit, no preserved baseline data exists; this
  arc starts diagnostic from scratch. Pre-specified diagnostic
  branches will identify whether the bottleneck is per-tick script
  overhead, movement hooks, contents-list operations, write storm,
  or something specific to the codebase. Fix follows from
  diagnosis.
- **MT-514e (swarm-mobs or equivalent):** Implement mobile
  invasion threats — likely as the swarm-mob pattern from Evennia
  Discord (one NPC with many "presence indicators") OR as
  individual-NPC patrol depending on what MT-514d's diagnostic
  reveals. Wires into invasion state set in this dispatch.
- **Future:** Invasion description authoring. Once `$state(invasion,
  ...)` markup is verified working, content authors (human or AI)
  can write invasion-aware room descriptions. Not a code dispatch;
  a content task.
- **Document the runtime state cache pattern in
  `docs/architecture/runtime_state_patterns.md`** after invasion
  ships. The pattern has now been validated three times across the
  weather arc and once again in invasion. That cross-validation
  makes it worth formalizing as project convention before MT-514c
  builds on top of it.