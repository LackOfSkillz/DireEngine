# DireMUD Microtasks 401-480 Report

## Scope

Implemented the stealth, perception, and combat-awareness work from MT 401-480 in the current Evennia codebase, adapted to the repo's existing architecture.

Key repo-specific integrations:
- Movement stealth was implemented in Character move hooks instead of a separate movement command, because room traversal is exit-driven here.
- Passive perception was integrated into the existing global status tick in `server/conf/at_server_startstop.py`.
- The existing `target` command was extended to support character focus targeting while preserving body-part targeting.

## Implemented

### MT 401-420
- Added `typeclasses/abilities_stealth.py` with:
  - `HideAbility`
  - `SneakAbility`
  - `StalkAbility`
  - `AmbushAbility`
- Imported stealth abilities into `typeclasses/abilities.py` for registry loading.
- Added Character stealth helpers:
  - `get_room_observers()`
  - `get_hidden_strength()`
  - `get_stealth_total()`
  - `is_hidden()`
  - `is_sneaking()`
  - `is_stalking()`
  - `get_stalk_target_id()`
  - `is_ambushing()`
  - `get_ambush_target_id()`
  - `break_stealth()`
- Reworked `can_perceive()` / `can_detect()` to gate hidden targets through stealth vs perception.
- Added direct `stalk` and `ambush` commands and registered them in the character cmdset.
- Broke stealth on attack in `commands/cmd_attack.py`.

### MT 421-440
- Integrated sneak detection into movement via `Character.at_pre_move()`.
- Added partial and strong observer messaging during sneaking.
- Suppressed normal movement broadcast when sneaking remains intact.
- Revealed movement only to observers who got a strong detection result.
- Added sneak fatigue cost and stealth learning on successful sneaking movement.
- Added stalk persistence handling in `Character.at_post_move()`:
  - retains stalk when the target is still present after movement
  - increases hidden strength while stalking
  - drains fatigue while stalking
  - clears stalking when the target is lost
- Integrated ambush bonuses into attack resolution:
  - accuracy bonus
  - damage bonus
  - ambush messaging

### MT 441-460
- Added awareness helpers on Character:
  - `get_awareness()`
  - `set_awareness()`
- Awareness now modifies `get_perception_total()`.
- Default awareness now initializes to `normal`.
- Added `typeclasses/abilities_perception.py` with:
  - `SearchAbility`
  - `ObserveAbility`
- Imported perception abilities into `typeclasses/abilities.py`.
- `search` now actively reveals hidden targets on successful contests.
- `observe` now sets `alert` awareness and a temporary `observing` state, then resets via Evennia delay.
- Added passive perception processing in `server/conf/at_server_startstop.py`.
- Integrated passive perception and awareness decay into the global status tick.

### MT 461-480
- Added surprise helpers on Character:
  - `is_surprised()`
  - `apply_surprise()`
  - `clear_surprise()`
  - `has_reaction_delay()`
- Ambush now applies surprise against unaware/normal targets.
- Combat resolution now applies:
  - surprise defense penalties
  - strong ambush defense bypass for unaware targets
  - awareness-based defense modifiers
  - awareness-based attack modifiers
- Successful hits now:
  - clear surprise
  - set the defender to `alert`
  - emit recovery/alert messaging
- Added `Character.get_target()` helper.
- Extended `commands/cmd_target.py`:
  - `target head/chest/arm/leg` still does body-part aiming
  - `target <person>` now focuses a combat target
- Existing `attack`, `retreat`, and `disengage` target flows already satisfied the auto-target and target-loss parts of the spec, so those behaviors were preserved rather than duplicated.

## Validation

Validated in Evennia shell with isolated disposable rooms/characters while the server was stopped to avoid SQLite locks.

Validated outcomes:
- visible abilities included `hide`, `sneak`, `stalk`, `ambush`, `search`, `observe`
- successful hide set hidden state
- failed hide left the user visible
- sneak required and preserved hidden state
- stalk persisted across movement when the target was present after the move
- stalking increased hidden strength and applied fatigue cost during movement
- low-perception observers could not perceive hidden targets
- `search` revealed hidden targets
- `observe` set `alert` awareness and `observing`
- passive perception revealed hidden targets under elevated awareness
- ambush state cleared after attack
- attacking while hidden broke stealth
- ambush attack landed with the target ending in `alert`
- surprise cleared after the first successful hit
- `target head` still set body-part aiming
- `target <person>` now set combat focus target
- cmdset registration included both `stalk` and `ambush`

Representative validation result:

```python
{
    'visible_abilities': ['ambush', 'hide', 'observe', 'search', 'sneak', 'stalk', 'test'],
    'hide_success': True,
    'sneak_success': True,
    'stalk_persists': True,
    'stalk_hidden_strength': 42,
    'stalk_move_fatigue': 3,
    'hide_fail_leaves_visible': True,
    'low_perception_blocked': False,
    'search_reveals_hidden': True,
    'observe_awareness': 'alert',
    'observe_state': True,
    'passive_detection_reveals': True,
    'ambush_clears_state': True,
    'attack_breaks_hidden': True,
    'ambush_damage_lands': True,
    'combat_target_alerted': 'alert',
    'surprise_cleared_after_hit': True,
    'body_part_target': 'head',
    'combat_target_focus': 'mt480_combat_target_tmp',
    'cmdset_stalk': True,
    'cmdset_ambush': True,
}
```

## Notes

- Added direct commands for `hide`, `sneak`, `search`, and `observe` so the stealth/perception loop no longer depends on the generic `ability` command for those common verbs.
- Enabled `SEARCH_AT_RESULT` in settings and implemented hidden-target filtering in `server/conf/at_search.py` by delegating to Evennia's default `at_search_result()` after removing matches the caller cannot perceive.
- The custom search filtering only applies to object-like matches with `is_hidden`; command lookup still uses Evennia's normal search-result handling path without stealth filtering side effects.

## Follow-up Extension

After the initial MT401-480 delivery, the following two integration steps were completed in the same batch:

1. Direct verb commands
- Added direct wrappers for:
  - `hide`
  - `sneak`
  - `search`
  - `observe`
- Registered them in the default character cmdset so players can use the verbs directly instead of typing `ability <name>`.

2. Global hidden-target search filtering
- Enabled the custom search result hook in settings.
- Implemented filtering in `server/conf/at_search.py` so `caller.search()` no longer returns hidden characters the caller cannot perceive.
- Preserved normal Evennia nomatch and multimatch behavior by delegating the filtered results to Evennia's built-in `at_search_result()` helper.
- Confirmed against Evennia's `DefaultObject.search()` implementation that this hook applies to normal search flows; `quiet=True` searches intentionally bypass `SEARCH_AT_RESULT` and still return raw match lists for callers that want to handle errors/results manually.

## Follow-up Validation

Additional validation performed after the follow-up extension:

- direct `hide` command set hidden state
- direct `sneak` command set sneaking state
- direct `search` command worked when the caller met perception requirements
- direct `observe` command set `alert` awareness and `observing`
- normal `caller.search("hidden target")` returned `None` when the caller could not perceive the hidden target
- normal `caller.search("hidden target")` returned the target once the caller's perception was high enough
- cmdset registration included `hide`, `sneak`, `search`, and `observe`

## Post-Implementation Login Fixes

After MT401-480 landed, follow-up debugging uncovered unrelated login and puppeting regressions that surfaced during webclient validation. These were fixed as part of stabilizing the environment after the stealth/perception work.

Implemented fixes:
- Narrowed `server/conf/at_search.py` so hidden-target filtering only applies to in-game object searches and does not interfere with account-side character selection.
- Hardened `typeclasses/accounts.py` login behavior:
  - clears stale account-to-character puppet links
  - ignores `at_post_login(session=None)` calls
  - auto-puppets webclient sessions into the browser-selected character when available
  - otherwise falls back to the account's last-used/playable character list
  - syncs the chosen character back into the browser session for consistent webclient reconnects
- Fixed an infinite recursion bug in `typeclasses/characters.py` where `ensure_core_defaults()` called `set_awareness()`, which re-entered `ensure_core_defaults()` through `set_state()` during puppeting.
- Added a custom account-level `ic` override in `commands/cmd_ic.py` so playable characters are matched before broader builder/global object searches.

Validated outcomes:
- `ic jekar` no longer collides with unrelated same-named builder-search objects
- character puppeting no longer fails with maximum-recursion-depth errors
- stale puppet/account links from failed login attempts are cleaned safely
- the account login path now attempts direct webclient auto-puppeting before falling back to OOC; server reload succeeded after this change, but browser-side login confirmation should still be verified in a live session