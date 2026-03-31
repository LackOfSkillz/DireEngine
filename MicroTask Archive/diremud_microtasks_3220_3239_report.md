# DireMUD Microtasks 3220-3239 Report

## Scope

Control and UX refinement only. No new mechanics or backend systems were introduced beyond lightweight runtime guards inside the existing ability flow.

## 3220-3222 Ability Input Improvement

- Added shorthand ability input support through a no-match command in `commands/cmd_ability_nomatch.py`.
- The no-match command uses `CMD_NOMATCH`, so explicit commands still win automatically when a verb exists in both places.
- Unknown input now falls through to the existing ability map only if an ability with that key exists.
- Explicit `ability ...` and the existing ability wrapper commands were updated to route through the same shared execution entry point on `Character`:
  - `execute_ability_input(...)`

## 3223-3228 Ability Queue Control and Interruptibility

- Added runtime busy handling on `Character.ndb.is_busy`.
- `use_ability()` now denies execution if the character is still marked busy.
- The explicit ability entry point clears stale busy state before executing the next requested ability:
  - this satisfies the requested interrupt-on-new-ability behavior without creating a queue system.
- Movement now clears busy state and walking state in `Character.at_after_move()`.
- Ability use also clears `ndb.is_walking` before execution.

## 3229-3230 Resource Feedback

- Added pre-execution subsystem snapshot feedback in `Character.use_ability()`.
- Added post-execution subsystem delta feedback in `Character.format_subsystem_feedback(...)`.
- When live subsystem resources exist, the command stream can now show:
  - `[Inner Fire: 40]`
  - `[Inner Fire: 40 -> 20]`
- Current limitation:
  - no live subsystem-spending abilities exist yet, so these messages are wired but not meaningfully exercised for profession resources in current gameplay.

## 3231-3232 Failure Clarity

- Wrong-path failures now return:
  - `That is not your path.`
- Rank gating now returns:
  - `You are not experienced enough.`
- Resource-style failures now normalize through `normalize_ability_failure_message(...)`.
- Existing ability-specific failure messages are still used when they do not match one of the normalized clarity cases.

## 3233-3235 Ability Cooldown

- Added lightweight runtime cooldown support with `Character.ndb.cooldowns`.
- `Ability` now exposes an optional `cooldown` attribute.
- `use_ability()` checks runtime cooldown before execution.
- After execution, cooldown is set using:
  - explicit `ability.cooldown` if present
  - otherwise ability `roundtime` as the lightweight fallback
- Runtime cooldowns are now merged into the existing character payload cooldown map in `world/area_forge/character_api.py`, so the browser can reflect them through the already-existing cooldown UI path.

## 3236-3237 Auto-Walk + Ability Interaction

- Ability execution now clears `ndb.is_walking` before executing.
- Movement also clears runtime busy state to avoid sticky control states.
- This keeps movement and ability usage interruptible without building a separate action queue.

## 3238 Visual Targeting Feedback

- Added pre-execution preparation feedback in `Character.use_ability()`:
  - `You prepare to <ability>...`
- Existing abilities that already emit richer preparation text still keep their own messages.

## 3239 Debug / Control

- Added `character.db.debug_mode = True` by default.
- Added `Character.debug_log(...)`.
- Ability triggers and subsystem delta messages now print to server output when debug mode is enabled.

## Result

- Players can now trigger profession abilities directly by verb when no explicit command already owns the input.
- Ability input is interruptible and less likely to get stuck in a busy state.
- Failures are clearer and more consistent.
- Cooldowns are lightweight but live inside the existing ability and payload path.
- The control layer now feels more responsive without adding a queue, cast timer, or new subsystem.

## Remaining Practical Limits

- No profession-resource-consuming abilities exist yet, so the resource feedback and resource-specific failure messaging are wired but only become fully visible once those abilities are implemented.
- The no-match handler now owns unknown-input fallback; if you want the exact old unknown-command wording preserved, that can be adjusted later without changing the control architecture.
