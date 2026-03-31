# DireMUD Microtasks 3200-3219 Report

## Scope

UI and player feedback layer only. No new gameplay mechanics were introduced.

## 3200-3203 Character Panel Profession Identity

- Added profession and profession-rank fields to the existing character payload in `world/area_forge/character_api.py`.
- Added minimal profession-rank support in `typeclasses/characters.py`:
  - `db.profession_rank` defaults to `1`
  - `get_profession_rank()` returns the live value
- Added browser panel fields in `web/templates/webclient/webclient.html`:
  - `#char-profession`
  - `#char-rank`
- Added `updateCharacterPanel(data)` in `web/static/webclient/js/dragonsire-browser-v2.js`.
- Character handler now updates the character panel through the existing `character` message path.
- Missing profession data now falls back to `Unknown`.

## 3204-3206 Subsystem Resource Bar

- Added `#subsystem-bar` in `web/templates/webclient/webclient.html`.
- Existing `subsystem` message path now updates the bar through `updateSubsystemUI(data)`.
- The UI supports the requested known resource shapes:
  - `fire` / `max_fire`
  - `focus` / `max_focus`
  - `transfer_pool` / `max_pool`
  - `attunement` / `max_attunement`
- Fallback display remains safe when data is missing.

## 3207-3210 Ability Visibility

- The `abilities` command in `commands/cmd_abilities.py` now lists both unlocked and locked abilities using the existing ability registry.
- Locked entries are filtered through the existing guild/profession and requirement checks.
- Locked abilities now show feedback like:
  - `ability_name (locked - requires rank X in skill)`
- The browser ability list now also supports locked entries through the existing character payload.
- Locked abilities are shown but cannot be activated from the browser list.

## 3211-3212 Command Feedback Improvement

- Added lightweight subsystem delta feedback in `Character.use_ability()` via `format_subsystem_feedback(...)`.
- When a future ability changes a tracked subsystem resource, the player will now see feedback in the existing command stream like:
  - `[Inner Fire: 40 -> 20]`
- Current limitation:
  - no live subsystem-spending abilities exist yet in the codebase, so exact insufficient-resource failure text such as `You lack sufficient Inner Fire.` cannot be observed in play until those mechanics exist.
  - the existing failure path still preserves ability-provided failure messages.

## 3213 Map + Profession Signal

- Player map node coloring in `web/static/webclient/js/dragonsire-browser-v2.js` now uses profession-aware colors for the current character.
- This is a light-touch signal only and does not alter map mechanics.

## 3214 Room Feedback

- Added room-entry feedback in `typeclasses/characters.py`.
- On entering a room with `room.db.guild_tag`, the player now receives:
  - `You feel the presence of a guild here.`

## 3215-3216 Debug Panel

- Added profession/rank summary output to the existing browser debug panel.
- Added subsystem summary output to the existing browser debug panel.
- The live `subsystem` message also appends to the existing debug log.

## 3217 State Sync Check

- Login: covered by `at_post_puppet()` calling `sync_client_state(include_map=True)`.
- Profession change: covered by `CmdProfession` calling `sync_client_state()`.
- Ability use: covered by `use_ability()` refreshing state after execution.
- Movement: covered by `at_after_move()` calling `sync_client_state(include_map=True)`.
- These were wired in code; no full manual in-game verification pass was run in this batch.

## 3218-3219 Safety

- Client update helpers now guard against missing payload data.
- Profession display falls back to `Unknown`.
- Subsystem bar also remains stable when optional fields are absent.

## Result

- Players can now see profession and rank in the character panel.
- The subsystem channel now has a visible UI target.
- Ability lists are clearer about what is available versus locked.
- Movement and guild-tag rooms now produce player-facing feedback.
- Debug surfaces now expose profession and subsystem state for validation.
