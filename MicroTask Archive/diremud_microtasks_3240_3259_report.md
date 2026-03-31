# DireMUD Microtasks 3240-3259 Report

## Scope

Pickpocket consequence loop only. No guard AI, jail, persistent punishment, currency theft, or inventory UI changes were introduced.

## 3240-3245 Pickpocket Command and Target Access

- Added `steal <target>` in `commands/cmd_steal.py`.
- The command validates:
  - caller has a room
  - target exists in the room
  - target is not the caller
  - target is not an NPC for now
  - caller is currently hidden
- The theft pool is drawn from `target.contents`.
- Added a future-protection hook by skipping items with `item.db.steal_protected`.
- Empty inventories are denied cleanly.

## 3246-3247 Success Check

- The success check uses the requested lightweight roll model:
  - base `stealth = 50`
  - thief profession gets `+20`
  - roll is `random.randint(1, 100)`
- Existing repo adaptation:
  - live awareness in this codebase is state-based (`unaware`, `normal`, `alert`, `searching`) rather than numeric
  - the command maps those awareness states to a temporary numeric threshold for the theft check instead of creating a second awareness system

## 3248-3249 Success Result

- On success:
  - a random valid item is moved to the caller
  - caller sees `You successfully steal <item>.`
  - target receives no message
- Stealth is broken on successful theft because the task explicitly required reveal on item interaction.

## 3250-3253 Failure and Partial Failure

- Hard failure:
  - caller sees `You fail to steal anything.`
  - target sees `You feel someone fumbling with your belongings!`
  - caller is revealed through the existing stealth-break path
  - room reaction is broadcast with `"<target> reacts suddenly!"`
- Soft fail:
  - when the miss is close, caller sees `You hesitate and withdraw unnoticed.`
  - no reveal occurs
- Added `Character.reveal()` as a thin alias to the existing `break_stealth()` path so the theft loop uses the current stealth system instead of a new reveal system.

## 3254-3255 Cooldown and Spam Control

- Theft now uses the existing runtime cooldown path already introduced for abilities.
- `caller.ndb.cooldowns["steal"] = now + 3` is applied after each attempt.
- Cooldown is checked before the theft attempt begins.

## 3256 Awareness Impact

- Task adaptation:
  - the task text asked for `target.db.awareness += 20`
  - the live repo does not use numeric awareness
- Implemented equivalent repo-native consequence:
  - on hard failure, target awareness is escalated through the existing awareness system with `target.set_awareness("alert")`

## 3257 Stealth Break Conditions

- Stealth now always breaks on:
  - hard failure
  - successful item theft
- Soft failure does not break stealth.

## 3258 UI / Debug Feedback

- When `debug_mode` is enabled, the caller sees:
  - `[Stealth check: success]`
  - `[Stealth check: soft-fail]`
  - `[Stealth check: failed]`
- Server debug output also logs the roll, stealth total, awareness threshold, and resulting margin.

## 3259 Safety

- Theft is currently blocked for:
  - NPCs
  - empty inventories
  - protected items via the future hook `db.steal_protected`
- Currency, equipped-protection rules, guard response, and punishment persistence were not added in this batch.

## Result

- Players can now hide, attempt theft, succeed silently, fail visibly, trigger target reactions, and push awareness into a higher-response state.
- This is the first real action-detection-consequence loop built on the current stealth architecture rather than a scripted side mechanic.
