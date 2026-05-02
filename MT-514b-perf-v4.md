# MT-514b-perf-v4 — Mitigate, re-profile, fix, verify in production

## Background

MT-514b-perf-v3a shipped a broadcast-loop cache fix that passed the
regression test in the test fixture but did NOT resolve the
production-path performance problem. Live evidence:

- `@weather` (zone summary, no third arg): ~5 seconds (acceptable)
- `@weather tick` (forces `run_weather_cycle()`): 60+ seconds
  (unacceptable)

In `world/weather.py`, `WeatherScript.at_repeat()` calls
`run_weather_cycle()` directly, and the forced-tick admin path was
unified onto the same shared cycle function during MT-514b-smoke
specifically to fix parity. So the natural background tick fires
the same cycle code as `@weather tick`. If admin force-tick is 60s,
the natural tick is also 60s. That tick fires every ~3.75 real
minutes by default in `WeatherScript`'s configured interval.

A 60-second synchronous cycle running inside the live Evennia
server process every 3.75 minutes will stall responsiveness for
all connected players during each cycle. This is unshippable as-is.

The previous closeout treated "regression test passes" as
equivalent to "production-verified." It isn't. The test fixture
has different zone count, different room loading, and different
runtime state than your live database. v4 corrects that mistake.

This dispatch:
1. Lands a temporary mitigation FIRST, before any profiling, to
   stop the server from freezing every 3.75 minutes.
2. Re-profiles `run_weather_cycle()` in production with the cache
   already in place, to find what's still consuming time.
3. Applies a targeted fix matching the diagnosis from one of three
   pre-specified patterns.
4. Verifies post-fix cycle time in the live production database,
   not in the test fixture.
5. Reverts the mitigation as the final phase.

## Architectural guardrails (READ FIRST)

This is the second perf dispatch in v3-pattern (diagnose, classify,
fix, verify). The leash discipline applies in full. The
pre-specified diagnostic branches in Phase C constrain the fix
space — if the diagnosis doesn't match a branch, the dispatch
stops and reports.

**Frozen scope:**

1. Phase A: Land mitigation. Disable automatic `at_repeat()` ticks
   via a settings-level feature flag. Verify mitigation works.
2. Phase B: Re-add v3's profiling instrumentation. Re-profile in
   production via in-process `@py`. Capture per-phase breakdown.
3. Phase C: Classify the diagnosis against three pre-specified
   patterns (C.1, C.2, C.3). If no match, stop and report.
4. Phase D: Apply the targeted fix matching the diagnosis.
5. Phase E: Re-profile after fix. Confirm production cycle under
   2 seconds.
6. Phase F: Remove all instrumentation.
7. Phase G: Update or replace the regression test so it actually
   reflects production-shape data, not just test-fixture defaults.
8. Phase H: Revert the mitigation. Re-enable automatic ticks.
9. Phase I: Live observation that natural ticks no longer freeze
   the server.
10. Phase J: Validation artifact updated.

**Frozen what-not-to-do list:**

- DO NOT begin any profiling, code investigation, or fix attempts
  before Phase A mitigation lands. The server freezing every 3.75
  minutes during debug work creates compounding stall cycles.
- DO NOT use the external Pylance interpreter for any production
  timing measurement. v2a established that path is structurally
  broken for weather profiling. Use in-process `@py` against the
  live server, OR use the `evennia shell -c` invocation pattern
  that worked at the end of v3a (base64-encoded payload to bypass
  shell quoting).
- DO NOT modify the public weather API. Source-stable:
  `get_current_weather`, `set_current_weather`, `get_weather_state`,
  `is_weather_plausible_for_climate`, `resolve_climate`,
  `tick_weather`, `run_weather_cycle`. Internal helpers may change.
- DO NOT remove or weaken the broadcast cache that v3a added. That
  fix is real and addresses a real bottleneck; it just isn't
  sufficient on its own. The new fix in this dispatch ADDS to the
  v3a fix, not replaces it.
- DO NOT modify any YAML content file, calendar module, prompt
  module, prompt templates, design docs, or zone YAMLs.
- DO NOT change broadcast message format, content, or routing.
- DO NOT change the persistent attribute storage shape.
- DO NOT add async/threading/Twisted-deferred dispatch.
- DO NOT add a new caching library or any third-party dependency.
- DO NOT modify foraging, ranger gather, NPCs, AI pipeline,
  builder, or any consumer of weather state.
- DO NOT add new admin commands, new weather features, or new
  player-facing surfaces.
- DO NOT modify the in-progress feature scope of MT-514c.
- DO NOT investigate or attempt to fix the webclient `@py`
  long-command transport issue from v3.
- DO NOT "while I'm here" refactor unrelated weather internals.
- DO NOT skip Phase H (mitigation revert) even if exhausted.
  Leaving the mitigation in place silently breaks weather progression
  in production.

**Stop-and-report conditions:**

- If the mitigation cannot be implemented without modifying the
  weather module's core architecture, stop and report. The
  mitigation should be a small, isolated, reversible change.
- If Phase B re-profiling shows the cycle is now actually fast
  (under 2 seconds) in production — meaning the v3a fix worked
  and the 60-second symptom was something else entirely — stop
  and report. We've misdiagnosed and need to understand the real
  cause before doing more work.
- If Phase B's diagnosis doesn't match any of C.1, C.2, or C.3,
  stop and report. Do not invent a fix for an unanticipated
  pattern.
- If the targeted fix in Phase D requires changing the public
  weather API or persistent storage shape, stop and report.
- If race conditions are visible between `at_repeat()` and admin
  commands, stop and report.
- If Phase E shows the fix didn't work (cycle still over 5
  seconds in production), stop and report. Do not attempt a
  second targeted fix in this dispatch.
- If the regression test in Phase G can't be made representative
  of production-shape data without unreasonable test infrastructure
  changes, stop and report. We'll discuss whether a less rigorous
  test plus periodic manual verification is acceptable.
- If Phase I observation shows natural ticks STILL freeze the
  server even after the fix verifies under 2s in profiling, stop
  and report. Something is different between the profiled path
  and the natural-tick path.

## Phase A — Mitigation: disable automatic ticks

Before any profiling, land a mitigation that stops the server from
freezing every 3.75 minutes during the rest of this dispatch's
work.

### A.1 Add the feature flag

In `server/conf/settings.py`, add:

```python
# MT-514b-perf-v4 mitigation: temporarily disable automatic weather
# ticks while production cycle time exceeds acceptable bounds.
# This flag is read by WeatherScript.at_repeat(). When False, the
# script's repeat callback returns early without running the cycle.
# Set to True (or remove the setting) only after live cycle time
# is verified under 2 seconds in production.
WEATHER_AUTOTICK_ENABLED = False
```

### A.2 Read the flag in WeatherScript

In `world/weather.py`, modify `WeatherScript.at_repeat()` to read
the flag and return early if disabled:

```python
def at_repeat(self):
    from django.conf import settings as django_settings
    if not getattr(django_settings, "WEATHER_AUTOTICK_ENABLED", True):
        return
    run_weather_cycle()
```

The default-True in `getattr()` means if someone removes the
setting entirely, autoticks resume. The mitigation requires
explicit `False` to engage. This is the safer default.

### A.3 Verify the mitigation works

After implementing A.1 and A.2:

1. Restart the live server.
2. Wait at least one full natural-tick interval (~3.75 minutes).
3. Confirm via in-process `@py` that `run_weather_cycle()` was NOT
   called during that interval — easiest check: add a temporary
   counter to `at_repeat()` that increments before the early return,
   verify the counter is 0 after waiting for the interval.
4. Remove the temporary counter; confirm the early-return is the
   only behavior.

### A.4 Document the mitigation

In the validation artifact, write a "Phase A — Mitigation Active"
note recording:
- The flag was added with default disabled
- The natural tick is confirmed not running
- Weather state will not progress automatically until Phase H
  reverts this

## Phase B — Re-profile in production

With the mitigation in place, the agent can profile without the
server freezing during their work.

### B.1 Re-add v3's instrumentation

The v3 instrumentation pattern worked. Re-add to `world/weather.py`:

```python
import time

_phase_timings: dict[str, list[float]] = {}

def _record_phase(name: str, elapsed: float) -> None:
    _phase_timings.setdefault(name, []).append(elapsed)

def get_phase_timings() -> dict[str, list[float]]:
    return dict(_phase_timings)

def reset_phase_timings() -> None:
    _phase_timings.clear()
```

Wrap each major phase of `run_weather_cycle()` with timing:
- `tick_weather` itself
- Any internal calls to `get_weather_state()`
- The broadcast loop (total)
- Within the broadcast loop, per-zone: `_rooms_for_zone` (NOW
  CACHED), `_eligible_rooms_for_zone` (NOW CACHED), filtering work
  remaining, message dispatch
- Lightning broadcast loop
- Cycle total

The agent adapts the exact instrumentation points to match the
current code structure (post-v3a, with the cache layers already in
place). The constraint: every phase from cycle start to cycle end
is accounted for, and no phase represents more than ~10% of cycle
time without being broken into sub-phases.

### B.2 Run the profile in production

Method: in-process `@py` from the live server, OR `evennia shell -c`
with base64-encoded payload (the pattern that worked at end of v3a).

Run `run_weather_cycle()` once. Capture `get_phase_timings()`.
Reset, run again. Capture again. Reset, run a third time. Capture.

The dispatch authorizes single-run sufficiency if 3-run capture is
blocked by transport issues again — same trade-off we made in v3a,
documented and accepted. ONE trusted production run with the
cache active is enough to classify if the signal is strong.

### B.3 Phase B report

The agent writes "Phase B — Post-Cache Production Profile" to the
validation artifact BEFORE proceeding to Phase C. Required:
- Per-phase wall-clock times
- Identification of the dominant phase
- One sentence: "Dominant cost is X, accounting for Y% of cycle
  time. This matches pattern C.N below."

If the dominant phase doesn't match C.1-C.3, the agent writes:
"Dominant cost is X, which does not match any pre-specified
pattern. Stopping per dispatch instructions."

If the cycle is now under 2 seconds total, the agent writes:
"Production cycle is now under target. The 60-second symptom
observed via `@weather tick` was not from `run_weather_cycle()`
itself. Stopping per dispatch instructions."

## Phase C — Diagnosis classification

The agent classifies Phase B results against these patterns. Only
one can match.

### C.1 — `tick_weather()` itself dominates

**Trigger:** The `tick_weather` phase accounts for >40% of cycle
time (time spent in transition decision logic and per-zone state
writes).

**Diagnosis:** With the broadcast loop now cached, `tick_weather()`
itself becomes the dominant cost. v2a measured this at ~7s
standalone. With 12 zones, this is per-zone state read + write +
transition decision compounding into seconds of work.

**Authorized fix:** Phase D.1 (in-memory state cache with
write-through persistence). This is the v2a hypothesis we
deferred when the broadcast loop was the bigger problem.

### C.2 — `get_weather_state()` called internally

**Trigger:** Any internal `get_weather_state()` call within the
cycle accounts for >30% of cycle time.

**Diagnosis:** The cycle is calling `get_weather_state()` for
inspection or logging purposes, and that call hits the slow
attribute-read path that v2a measured at ~7s standalone.

**Authorized fix:** Phase D.2 (eliminate the internal call OR add
the in-memory state cache from D.1, which makes
`get_weather_state()` fast as a side effect).

### C.3 — Cache miss / cache not firing

**Trigger:** Phases that v3a should have made fast (room iteration,
eligible-rooms filtering) are still slow per-zone, indicating the
cache isn't actually being used.

**Diagnosis:** The v3a cache was implemented but not wired
correctly. Either the cache helpers exist but the broadcast helpers
still call the uncached path, or the invalidation hooks are firing
unexpectedly and constantly clearing the cache.

**Authorized fix:** Phase D.3 (fix the cache wiring or
invalidation, do NOT add new caching layers).

### C.4 — Anything else

**Trigger:** None of C.1-C.3 match.

**Action:** STOP. Do not implement a fix. Document the
unanticipated diagnosis in the validation artifact. The next
dispatch (drafted separately) will target what was found.

## Phase D — Apply targeted fix

The agent implements ONE of D.1-D.3 based on the Phase C
classification.

### D.1 — In-memory state cache (if C.1 matched)

Add `_zone_state_cache` and `_zone_meta_cache` dicts on the
WeatherScript instance. Load from persistent attributes on
`at_start()`. All reads from cache. All writes update cache AND
persist via `script.attributes.add(...)`. Same persistent storage
shape preserved.

Key implementation points:
- The cache is a Python attribute on the script, NOT a `db.`
  attribute
- `at_start()` resets and reloads the cache (handles server reload)
- `_ensure_cache_loaded()` is idempotent and called at the top of
  every read/write API
- Writes go through cache AND persistence in lockstep

### D.2 — Eliminate internal `get_weather_state()` call (if C.2 matched)

Identify why the cycle calls `get_weather_state()` internally. If
it's for logging/inspection, replace with a lighter-weight inline
build-up. If it's for legitimate state retrieval, the D.1
in-memory cache is the fix (cached `get_weather_state()` becomes
nearly free).

### D.3 — Cache wiring fix (if C.3 matched)

Read v3a's commit. Identify why the cache helpers
(`_rooms_for_zone`, `_eligible_rooms_for_zone`) aren't actually
saving time. Likely causes:
- Broadcast helpers still call the uncached path directly
- Invalidation hooks are firing too aggressively
- Cache state is stored on the wrong object (per-call instead of
  per-server-process)

Fix the wiring. Do NOT add additional cache layers — just make the
existing ones work correctly.

## Phase E — Verify in production

Run the same in-process measurement as Phase B with the fix in
place. Document the per-phase breakdown showing the improvement.

**Acceptance gate:** `run_weather_cycle()` in production must
complete in under 2 seconds.

If it doesn't, STOP and report. Do not attempt a second targeted
fix in this dispatch.

## Phase F — Remove instrumentation

Remove all temporary profiling code added in Phase B. Verify via
grep that no `_phase_timings`, `_record_phase`, `get_phase_timings`,
`reset_phase_timings`, or similar profiling artifacts remain in
`world/weather.py` or `commands/cmd_weather.py`.

The regression test from Phase G is the long-term performance
guard.

## Phase G — Update regression test for production-shape

The existing regression test from v3a passed in a fixture that
didn't represent production. Update or replace it so that:

Option G.A: Test fixture is enhanced to load multiple zones with
representative room counts, mimicking the production database
shape.

Option G.B: Test stays minimal but is supplemented by an explicit
"production verification command" — an `@py` snippet documented in
the validation artifact that the admin runs periodically to verify
production cycle time. This is less ideal but pragmatic.

Option G.C: Both — keep a fast minimal regression test for CI,
add a separate, slower test marked with `@unittest.skip` by default
that loads production-shape data and is run on demand.

The agent picks the option that's most achievable without
unreasonable test infrastructure changes. Document the choice and
why.

## Phase H — Revert the mitigation

Now that production cycle time is verified under 2 seconds, revert
the mitigation:

1. In `server/conf/settings.py`, set `WEATHER_AUTOTICK_ENABLED = True`
   (or remove the setting entirely — the `getattr` default handles
   absence).
2. The early-return code in `at_repeat()` stays in place. It's now
   inert because the flag is True. This is intentional — keeping
   the flag mechanism in code makes future temporary mitigations
   trivial to deploy.

Restart the live server. Verify natural tick fires by checking for
weather state changes after one interval.

## Phase I — Live observation

After Phase H reverts the mitigation, observe the live server for
at least 10 minutes (covers 2-3 natural tick intervals). The agent
sits in the webclient and:

1. Sends cheap commands (`look`, `who`, `@calendar`) every 30
   seconds.
2. Checks weather state (`@weather`) after each natural tick
   interval.
3. Notes whether commands ever stall for more than 1 second during
   the observation window.

If commands respond consistently and weather progresses, MT-514b
is verified as production-ready.

If commands stall during natural tick intervals (longer than the
profiled cycle time would suggest), STOP and report. The natural
tick path differs from the profiled path in a way we haven't
characterized.

## Phase J — Validation artifact

APPEND a new section to `exports/mt514b_weather_validation.md`
titled `## MT-514b-perf-v4 — Mitigation, re-diagnosis, fix, production verification`.

Section contents:

1. **Phase A mitigation.** What was added, why, confirmed working.
2. **Phase B post-cache profile.** Per-phase breakdown from
   production. Dominant cost identified.
3. **Phase C classification.** Which pattern matched.
4. **Phase D fix.** What was added, why it targets the diagnosed
   pattern.
5. **Phase E post-fix profile.** Same per-phase breakdown showing
   improvement. Production cycle time confirmed under 2 seconds.
6. **Phase F confirmation.** No profiling code left in tree.
7. **Phase G regression test.** Which option chosen and why.
8. **Phase H mitigation revert.** Confirmation autotick re-enabled,
   weather progressing.
9. **Phase I live observation.** Verbatim notes on command
   responsiveness across natural tick intervals.
10. **Final state.** One sentence: "MT-514b is now production-
    verified."

If any phase blocked, the section ends with the BLOCKED status
and the specific reason.

## Verification checklist

1. Phase A mitigation lands first, before any profiling.
2. Phase B re-profiles production with cache in place.
3. Phase C classifies the diagnosis against pre-specified patterns,
   OR stops if unanticipated.
4. Phase D applies ONLY the authorized fix for the matched
   pattern.
5. Phase E confirms production cycle under 2 seconds.
6. Phase F confirms no profiling code left in tree.
7. Phase G updates the regression test toward production-shape
   verification.
8. Phase H reverts the mitigation; weather progresses again.
9. Phase I confirms natural ticks don't stall the server.
10. Validation artifact updated with full evidence.
11. No code outside the in-scope list modified.

## Stop conditions

- Edit only `world/weather.py`, `tests/test_weather.py`,
  `server/conf/settings.py`, the validation artifact, and (only if
  Phase D requires it) zone-import service or similar invalidation
  hooks. No other files.
- Stop and report on any unexpected Phase B diagnosis.
- Stop and report if Phase E shows the fix didn't work.
- Stop and report on race conditions, persistent storage shape
  changes, regression test infrastructure issues, or Phase I
  showing natural tick still stalls the server.
- Do not attempt multiple targeted fixes in the same dispatch.
- Do not skip Phase H (mitigation revert) under any circumstances.

## Required artifacts

1. Updated `world/weather.py` (mitigation flag check, targeted fix
   from Phase D, instrumentation removed)
2. Updated `server/conf/settings.py` (mitigation flag added with
   default True after Phase H revert)
3. Updated `tests/test_weather.py` (regression test updated per
   Phase G option chosen)
4. Possibly updated zone-import service if Phase D fix requires
5. Updated `exports/mt514b_weather_validation.md` (new section
   appended)

## Followup queue

- MT-514b-invasion: Add `current_invasion` runtime state with
  `@invasion` admin command. Apply BOTH the ScriptDB fallback
  (from v2a), the per-zone caching pattern (from v3a), AND
  whatever cache pattern v4 establishes. Invasion does not need to
  repeat any of the perf-debugging arc. Production-shape
  verification is required before closing.
- MT-514c: Foraging refactor. Now safe to build on a perf-tuned
  weather foundation, ASSUMING v4 verifies cleanly. If v4 reveals
  a deeper architectural issue, MT-514c is blocked until that's
  resolved.
- Document the runtime state cache pattern in
  `docs/architecture/runtime_state_patterns.md` after v4 closes.
  This pattern (ScriptDB fallback + per-zone cache + write-through
  persistence + bounded-time regression test + production
  verification) is the project convention for any frequently-read
  Evennia persistent state.
- Webclient long-command transport: Still unresolved from v3.
  Document if it recurs but do not investigate as part of this
  dispatch.