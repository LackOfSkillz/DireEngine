# DireMUD Microtasks 3000-3159 Report

This report covers reconciliation work for microtasks 3000-3159 against the current Dragonsire codebase.

## Scope Completed

- Added a profession package under `world/professions/` for profession profiles, skill weights, and subsystem controllers.
- Routed the existing character profession API through that shared registry while preserving the current profession roster and later guild specializations.
- Added `join` and `train` commands so profession entry and trainer-led advancement do not conflict with the existing combat `advance` verb.
- Expanded `profession` and `stats` output to show profession rank, descriptions, skill weighting, and social standing.
- Added room access checks through `Room.db.allowed_professions` and a helper gate in movement.
- Added profession-aware NPC reactions and shop trade denial hooks through `NPC.react_to()` and `NPC.can_trade()`.
- Added profession presence and magic/stealth flavor messaging on room entry and ability use.
- Replaced the placeholder subsystem payload with profession subsystem controllers while keeping the existing `get_subsystem()` API intact.
- Wired subsystem ticking into the existing lightweight status ticker instead of adding a new global pulse path.

## Reconciliation Notes

- MT 3080-3099 expected a profession `advance` command. The live game already uses `advance` for combat range control, so progression was implemented through `train` instead.
- MT 3000-3019 assumed a simpler starter set including a generic `mage`. The current codebase already uses later specialized magic professions, so the registry preserves `moon_mage` and `warrior_mage` rather than collapsing backward to a generic mage.
- MT 3140-3159's hide/search/awareness model was already superseded by the existing stealth and perception ability system. That subsystem was preserved and only supplemented with profession flavor/reaction hooks.

## Validation Target

Recommended validation for MT 3000-3159:

1. `profession` and `stats` show rank, social standing, and skill weights.
2. `join <profession>` only works inside a matching guild-tagged room.
3. `train` advances profession rank only with a matching trainer present.
4. Rooms with `allowed_professions` deny entry correctly.
5. Shopkeepers react to suspicious thieves and can deny trade under alert/crime conditions.
6. Profession subsystem payloads update without regressing browser client state.