# diremud microtasks 361-400 report

## scope

Completed the MT 361-400 batch from `MT 361 - 400.md`.

This batch added three foundational systems:

- an ability registry and ability command surface
- reusable contest utilities with difficulty tagging and learning hooks
- a generalized persistent state container on characters

## implemented

### ability framework

- Added [typeclasses/abilities.py](typeclasses/abilities.py) with:
  - `Ability`
  - `ABILITY_REGISTRY`
  - `register_ability()`
  - `get_ability()`
- Added a registered `TestAbility` keyed as `test`.

### character ability integration

- Imported `get_ability` into [typeclasses/characters.py](typeclasses/characters.py).
- Added ability methods on `Character`:
  - `use_ability()`
  - `meets_ability_requirements()`
  - `passes_guild_check()`
  - `can_see_ability()`
  - `get_visible_abilities()`
- Added `guild` and `states` persistence defaults through the existing character-default migration path.

### ability commands

- Added [commands/cmd_ability.py](commands/cmd_ability.py) for invoking a named ability.
- Added [commands/cmd_abilities.py](commands/cmd_abilities.py) for listing visible abilities grouped by category.
- Registered both commands in [commands/default_cmdsets.py](commands/default_cmdsets.py).

### contest utilities

- Added [utils/contests.py](utils/contests.py) with:
  - `contest()`
  - `resolve_outcome()`
  - `run_contest()`
  - `get_skill_total()`
  - `get_difficulty_band()`
  - `apply_learning()`
  - `skill_vs_skill()`
  - `DEBUG_CONTESTS`
- Added [utils/__init__.py](utils/__init__.py) so the new utility package imports cleanly.

### character state system

- Added persistent character state helpers in [typeclasses/characters.py](typeclasses/characters.py):
  - `set_state()`
  - `get_state()`
  - `has_state()`
  - `clear_state()`
  - `clear_all_states()`
- Ensured `db.states` is always present through the core default path.
- Cleared `aiming` state from `clear_aim()` so the older combat-specific flag and the new generalized state system stay aligned.
- Updated [commands/cmd_aim.py](commands/cmd_aim.py) to store aiming in both the existing combat field and the new state container.

### state debug command

- Added [commands/cmd_states.py](commands/cmd_states.py).
- Registered it in [commands/default_cmdsets.py](commands/default_cmdsets.py).

## validation

### import and registry validation

Confirmed:

- `commands.default_cmdsets` imports cleanly with the new commands.
- `ABILITY_REGISTRY` contains `test`.
- `get_ability("missing")` returns `None` safely.
- `run_contest()` returns the expected key set:
  - `attacker_roll`
  - `defender_roll`
  - `diff`
  - `difficulty`
  - `outcome`

### ability behavior validation

Validated with temporary characters:

- `use_ability("fake")` reports: `You don't know how to do that.`
- guild-gated ability use fails with: `You cannot use that ability.`
- skill-gated ability use fails with: `You are not skilled enough in stealth.`
- visibility gating hides a guild ability until both guild and minimum visibility rank requirements are met
- successful execution of a gated test ability produces: `Locked ability executed.`

### state system validation

Validated state storage and cleanup:

- hidden state persisted as:
  - `{'strength': 25, 'source': 'hide'}`
- aiming and stalking state values stored correctly
- `has_state("hidden")` returned `True`
- clearing one state removed only that key
- `clear_all_states()` reset the container to `{}`

### contest validation

Validated:

- `resolve_outcome(-1) -> fail`
- `resolve_outcome(5) -> partial`
- `resolve_outcome(25) -> success`
- `resolve_outcome(60) -> strong`
- `get_skill_total()` returns an integer
- `skill_vs_skill()` returns a result including a difficulty band
- `apply_learning()` increased test skill mindstate from `0` to `3` on an `ideal` difficulty input

### command-surface validation

Validated direct command outputs:

- `abilities` produced:
  - `GENERAL:`
  - `  - test`
- `ability test` produced:
  - `You perform a test ability.`
- `states` produced:
  - `hidden: {'strength': 25, 'source': 'hide'}`

## result

MT 361-400 is complete in the current workspace.

The project now has a reusable ability registry, visibility/use gating, contest resolution helpers, and a generic persistent state container that later stealth, ambush, spell, and status systems can build on without inventing new one-off patterns each time.