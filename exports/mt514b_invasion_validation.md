# MT-514b-invasion Validation

## Phase A vocabulary discovery

Searches across `world/`, `commands/`, tests, and zone-adjacent content found no preexisting global invasion runtime module and no locked invasion type vocabulary beyond generic prompt-side `invasion` state references.

Chosen starter vocabulary:

- `none`
- `goblin_raid`
- `bandit_incursion`
- `monster_horde`
- `siege`
- `infestation`

This vocabulary is intentionally small and expandable. No conflicting code or zone-YAML vocabulary was found.

## Phase B-E implementation

Implemented the invasion producer as state-only runtime infrastructure.

Files added:

- `world/invasion.py`
- `commands/cmd_invasion.py`
- `tests/test_invasion.py`

Files extended:

- `commands/default_cmdsets.py`
- `server/conf/at_server_startstop.py`

Patterns mirrored from weather:

- ScriptDB fallback for singleton lookup
- script-local in-memory cache with write-through persistence
- duplicate-script cleanup retaining a single keeper
- no `start()` call on already-active invasion scripts
- persistent per-zone attribute storage with metadata

Intentional non-features preserved:

- no auto-tick
- no broadcasting
- no spawning
- no mobile threats

## Phase F tests

Focused regression suite:

```text
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_invasion
............
----------------------------------------------------------------------
Ran 12 tests in 0.007s

OK
```

Covered behaviors:

- default read path returns `none`
- set/get round-trip
- invalid type raises `ValueError`
- `is_zone_invaded()` boolean behavior
- clear-to-`none`
- cache population and survival across repeated reads
- `at_start()` cache reset behavior
- write-through persistence into script attributes
- bounded-time `get_invasion_state()` regression guard
- zone-payload cache reuse

## Phase G live verification

Server restart after wiring invasion startup:

```text
[startWeb] Existing game server detected on port 4001 (PID 63428). Performing full restart...
Server stopping ...
... Server stopped.
Stopping Portal ...
... Portal stopped.
Evennia shut down.
Portal starting ...
... Portal started.
Server starting  ...
... Server started.
Evennia running.
```

Live shell producer check:

```text
c:/Users/gary/dragonsire/.venv/Scripts/evennia.exe shell -c "from world import invasion; invasion.set_current_invasion('new_landing', 'siege'); print(invasion.get_current_invasion('new_landing')); print(invasion.is_zone_invaded('new_landing')); print(invasion.get_invasion_state()['counts'].get('siege'))"

siege
True
1
```

Persistence across restart:

```text
c:/Users/gary/dragonsire/.venv/Scripts/evennia.exe shell -c "from world import invasion; import time; invasion.get_invasion_state(); start=time.monotonic(); state=invasion.get_invasion_state(); elapsed=time.monotonic()-start; print(invasion.get_current_invasion('new_landing')); print(invasion.is_zone_invaded('new_landing')); print(f'{elapsed:.6f}')"

siege
True
0.000000
```

Cleanup after verification:

```text
c:/Users/gary/dragonsire/.venv/Scripts/evennia.exe shell -c "from world import invasion; invasion.set_current_invasion('new_landing', 'none'); print(invasion.get_current_invasion('new_landing')); print(invasion.is_zone_invaded('new_landing'))"

none
False
```

Admin command behavior sanity check from the live Evennia environment:

```text
Valid invasion types: none, goblin_raid, bandit_incursion, monster_horde, siege, infestation
Invasion for new_landing set to siege.
Invasion: new_landing
────────────────────────────────
Current state:   siege
Zone name:       new_landing
Is invaded:      yes
Updated by:      admin
Updated at:      2026-05-01T20:33:18+00:00
```

The temporary `siege` state was cleared immediately after verification.

## Phase H markup integration

Status: BLOCKED

Prompt/build-time evidence confirms invasion exists in the authoring vocabulary:

- `world/builder/prompting/room_description_prompt.py` includes `"invasion": ("invasion",)`
- applicable-state tests already include invasion in prompt-side room state lists

But the runtime room-display path does not show a Dragonsire parser/evaluator for literal `$state(...)` markup fragments.

Owning runtime surface inspected:

- `typeclasses/rooms_extended.py` `ExtendedDireRoom.get_display_desc()`
- `typeclasses/rooms_extended.py` `ExtendedDireRoom.get_stateful_desc()`

Observed behavior:

- room descriptions are selected from pre-split `desc_<state>` attributes plus room tags
- no local runtime `$state(...)` parser was found in the inspected room-display path
- therefore Phase H cannot honestly claim that `$state(invasion, ...)` literal markup already renders live

This is a preexisting architectural gap, not an invasion producer defect. Per dispatch instructions, the correct outcome is to stop and report rather than silently widen scope into the room rendering system.

## Closing

MT-514b-invasion shipped as a state-only producer with admin control, persistence, cache safety, and live restart verification. Mobile threats remain deferred to MT-514d. Phase H is BLOCKED on preexisting room-description runtime behavior for literal `$state(...)` markup.