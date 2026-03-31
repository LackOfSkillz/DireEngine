# DireMUD Microtasks 3300-3319 Report

## Scope

Shoplifting was added as a high-risk branch of the existing theft system. The implementation reuses current stealth, awareness, NPC combat targeting, and room alert state rather than introducing a separate crime framework.

## 3300-3305 Shop and Shopkeeper Identity

- Added room defaults in [typeclasses/rooms.py](typeclasses/rooms.py):
  - `db.is_shop = False`
  - `db.alert_level = 0`
- Added room helpers:
  - `Room.is_shop()`
  - `Room.get_shopkeeper()`
- Added NPC defaults in [typeclasses/npcs.py](typeclasses/npcs.py):
  - `db.is_shopkeeper = False`
  - `db.witnessed_crime = False`
- Added `NPC.is_shopkeeper()`.
- Updated the Brookhollow builder in [world/brookhollow_v3_patched.py](world/brookhollow_v3_patched.py) so shop rooms are flagged from their existing `shop` room tag and NPCs created in shop rooms are marked as shopkeepers.

## 3306-3307 Shop Inventory Source

- Shoplifting now reads stock from `shopkeeper.contents`, not room contents.
- Added default item support in [typeclasses/objects.py](typeclasses/objects.py):
  - `db.stealable = True`
- Builder-created fixture items are explicitly marked non-stealable.
- Added `stock_shopkeepers()` in [world/brookhollow_v3_patched.py](world/brookhollow_v3_patched.py) to migrate `shop_stock` items from shop rooms into the corresponding shopkeeper inventory during world build.

## 3308-3312 Shoplift Command Path

- Extended [commands/cmd_steal.py](commands/cmd_steal.py).
- If `caller.location.is_shop()` is true, the command now routes to `handle_shoplifting(...)`.
- Shoplifting target selection resolves against `shopkeeper.contents`.
- Detection is harder than street theft:
  - base awareness comes from the existing state model
  - `+30` shop penalty always applies
  - `+20` extra applies for flagged shopkeepers
- On success:
  - item moves to caller
  - caller sees `You discreetly pocket <item>.`
  - caller is revealed
  - shopkeeper gains a small persistent suspicion bump via `awareness_bonus += 5`

## 3313-3318 Failure Escalation

- Shoplifting has no soft-fail branch.
- On failure:
  - caller sees `You are caught trying to steal!`
  - room gets `"<caller> is trying to steal!"`
  - caller gets `crime_flag = True`
  - caller `crime_severity += 2`
  - shopkeeper `witnessed_crime = True`
  - room `alert_level += 2`
  - caller is always revealed
- Added reusable guard-response helper in [utils/crime.py](utils/crime.py):
  - `call_guards(room, culprit)`
- Current guard hook behavior:
  - scans the room and adjacent rooms for existing guard-role NPCs
  - moves adjacent guards into the crime room when possible
  - sets them alert
  - points them at the culprit through the current target/combat API
  - stores `pending_guard_target` on the room if no responder exists yet

## 3319 Safety

- Shoplifting reuses the existing theft cooldown path through `cooldowns["steal"]`.
- The same rapid-repeat throttle now covers both street theft and shop theft.
- No room inventory scraping is used for shops.
- No silent infinite shop theft loop remains once stock is assigned to shopkeepers and cooldowns are active.

## Repo-Native Adaptations

- The requested numeric awareness changes were adapted onto the existing awareness-state system by adding a lightweight `awareness_bonus` modifier on characters.
- The requested `call_guards(...)` hook did not already exist, so a minimal reusable version was added that uses current room exits and NPC targeting instead of adding a separate pursuit subsystem.

## Result

- Streets and shops now diverge cleanly:
  - street theft allows soft failure and quieter outcomes
  - shop theft is harder, louder, and escalates immediately
- Commerce spaces now operate as high-risk crime zones with stronger witness and response behavior.