# Client State Sync

## Authoritative Path

Live browser state updates already flow through the Character sync surface.

- `CombatService.attack()` delegates damage, fatigue, and roundtime mutation into `StateService`.
- `StateService` applies those mutations through Character setters such as `set_hp()`, `set_roundtime()`, and `set_fatigue()`.
- Those setters call `Character.sync_client_state()`.
- `Character.sync_client_state()` fans out structured `character` and `subsystem` payloads through `world.area_forge.character_api` and `world.area_forge.utils.messages.send_structured()`.
- `web/static/webclient/js/dragonsire-browser-v2.js` listens for those payloads and rerenders the character panel and related browser state.

## Explicit Reset Hook

`Character.sync_state_to_client(session=None)` is the explicit full-sync wrapper for call sites that need to push a complete browser refresh without depending on a specific setter side effect.

- `combatreset` still uses `Character.combat_reset_state()` as its mutation entrypoint.
- `Character.combat_reset_state()` now ends by calling `sync_state_to_client()` so dead-state cleanup pushes the same structured payload path that live combat uses.

## Dead-State Command Gate

Browser dead-state command access is enforced in `typeclasses/characters.py`, not only in the shared command base.

- `Character.execute_cmd()` routes raw browser input through `Character.can_execute_while_dead()`.
- `combatreset` and `cmbreset` must be allowlisted in the Character-level dead-state command set or the browser session will refuse them before command execution.
- Any admin or infra command intended to function during impaired character states such as death, stun, or other incapacity must be allowlisted in both the shared command base and the Character-level execution gate.

## Verified Behavior

DRG-INFRA-001 live validation confirmed this sequence works without logging out:

1. a browser session remains attached to a dead character
2. an admin issues `combatreset <character>`
3. the same browser session returns to alive `character` and `subsystem` presentation
4. the browser can immediately execute follow-up commands such as `look`