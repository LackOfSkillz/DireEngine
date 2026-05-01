# MT-514a Calendar Validation

## Status

Completed.

## Focused validation

- New calendar test module passed:
  - Command: `$env:DJANGO_SETTINGS_MODULE='server.conf.settings'; c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_calendar`
  - Result: `Ran 19 tests in 0.010s` / `OK`
- Static error check on all touched MT-514a files reported no errors.

## Broader regression check

- Command: `$env:DJANGO_SETTINGS_MODULE='server.conf.settings'; c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest discover tests`
- Result: failed outside MT-514a scope.
- Representative failing modules:
  - `tests.test_room_description_prompt`
- Representative failures:
  - prompt text assertions around `Description:` appearing in generated prompt guidance
  - state-mapping expectations for weather/invasion groups
- These failures are in pre-existing prompt-generation surfaces, not in any file modified for MT-514a.

## Live smoke test

- Dev server restarted successfully with `startWeb.bat`.
- Smoke executed against the live running server using the real `CmdCalendar` command class with a live developer account from the game database (`jekar`) as the caller permission source.
- `@calendar` output:

```text
DireEngine Calendar
────────────────────────────────────────
Real-world time:    2026-04-30T20:36:27-04:00 (America/New_York)
Real-world season:  spring

Game time elapsed:  82296d 2h 25m
Game time-of-day:   evening

Time factor:        4.0× real time
Ignore downtimes:   False
Epoch:              server first start
```

- `gametime` output:

```text
DireEngine Calendar
────────────────────────────────────────
Real-world time:    2026-04-30T20:36:27-04:00 (America/New_York)
Real-world season:  spring

Game time elapsed:  82296d 2h 25m
Game time-of-day:   evening

Time factor:        4.0× real time
Ignore downtimes:   False
Epoch:              server first start
```

- Alias parity confirmed: `@calendar` and `gametime` produced identical output.
- Optional permission check confirmed for a non-admin account: `You do not have permission to use this command.`

## Real-world season expectation

- Expected current real-world season for `America/New_York` on 2026-04-30: `spring`
- Actual engine-reported season: `spring`
- Actual engine-reported game time-of-day: `evening`

## Legacy room behavior check

- Verified via focused unit coverage in `tests/test_calendar.py`:
  - `ExtendedDireRoom.get_season()` delegates through `world.calendar`
  - `ExtendedDireRoom.get_time_of_day()` delegates through `world.calendar`
  - `get_stateful_desc()` still returns the seasonal description when the current season resolves to `winter`

## Files touched for MT-514a

- `world/calendar.py`
- `typeclasses/rooms_extended.py`
- `server/conf/settings.py`
- `commands/cmd_calendar.py`
- `commands/default_cmdsets.py`
- `tests/test_calendar.py`
- `exports/mt514a_calendar_validation.md`

## Scope confirmation

- No consumer system was modified.
- No changes were made to foraging, builder logic, ZoneScore, AI pipelines, weather, NPC systems, or festivals.
- No third-party dependencies were added.