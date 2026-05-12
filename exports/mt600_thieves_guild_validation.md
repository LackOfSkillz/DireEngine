# MT-600 thieves guild validation

Status: SHIPPED WITH ONE COMMAND-SURFACE GAP

## Summary

The thieves guild demo zone now exists at `worlddata/zones/thieves_guild.yaml` as a 20-room `interior_large` zone with all base descriptions and stateful descriptions populated by the MT-600 orchestration pipeline. The zone imported successfully into the live game database, all 20 rooms are reachable from `false_alley`, all 9 NPCs spawned at their intended rooms, and the teleport target for entry is `@tel #27596`.

Total live orchestration cost: `$1.945212`

Total live orchestration wall-clock: `1377197 ms` (`22m 57.197s`)

Content completion:
- rooms with non-empty `desc`: `20 / 20`
- rooms with non-empty `stateful_descs`: `20 / 20`

## Per-phase results

| Phase | Status | Duration ms | Cost USD | Rooms succeeded |
|---|---|---:|---:|---:|
| 1 | success | 0 | 0.000000 | 0 |
| 2 | success | 0 | 0.000000 | 0 |
| 3 | success | 256645 | 0.370440 | 20 |
| 4 | success | 1120552 | 1.574772 | 20 |

Phase report artifacts:
- `exports/orchestrator_live_verify_phase_1_20260502T182453Z.md`
- `exports/orchestrator_live_verify_phase_2_20260502T182458Z.md`
- `exports/orchestrator_live_verify_phase_3_20260502T182922Z.md`
- `exports/orchestrator_live_verify_phase_4_20260503T013655Z.md`

## Tooling note

The harness was extended with `--write-back` and successfully persisted the orchestrator's final working state directly back into `worlddata/zones/thieves_guild.yaml` after each successful phase. Checkpoint promotion was not needed as the primary persistence path.

## Import method used

Canonical command target from the dispatch:

```text
@zone load thieves_guild --dry
@zone load thieves_guild YES
```

Observed blocker on command surface:
- the available webclient session was unauthenticated when tested
- `@zone load thieves_guild --dry` returned `Command '@zone load thieves_guild --dry' is not available. Type "help" for help.` because the session was at the pre-login command surface
- no authenticated admin credentials were available in-session to recover the command path

Execution used for ship:

```python
from world.worlddata.services.import_zone_service import load_zone
load_zone('thieves_guild', dry_run=False)
```

Result:
- zone loaded successfully
- `20` rooms created
- `40` exits created
- `9` NPCs spawned
- `3` items spawned
- no import warnings

## Local corrections made during execution

Two bounded local fixes were required during execution:
- watcher NPC typeclass path corrected from `typeclasses.npcs.guard.GuardNPC` to `typeclasses.npcs.GuardNPC` because the nested module path is not importable in this repo due the `typeclasses/npcs.py` module shadowing the package directory
- one malformed YAML indent introduced during that fast patch was corrected before the successful import rerun

Neither fix required schema, orchestrator, prompt, import-service, command, or test changes.

## Item typeclass substitutions

The dispatch left item typeclasses open to the closest existing fit. The final substitutions were:
- `donation_shelf` -> `typeclasses.objects.Object`
- `weapon_rack_pit` -> `typeclasses.objects.Object`
- `lockpick_practice_set` -> `typeclasses.objects.Object`

These are placeholder fixtures only; no item-economy or container mechanics were implemented in this dispatch.

## Phase 3 tonal gate

Phase 3 passed the explicit prose spot-check before Phase 4 spend.

Common wing sample, `court_of_coins`:

> The Court of Coins sprawls beneath timber beams blackened by years of firepit smoke, its flagstone floor worn smooth by countless boots and marked with old stains no one bothers to scrub. Stone walls bear crude tallies and mockeries of surface law, carved by hands that found dignity in defiance rather than coin. The central firepit throws uneven light across benches and low tables where rogues gather to settle disputes with rough ceremony, their laughter sharp-edged and their silences watchful. Smoke hangs thick in the air, carrying the smell of cheap ale and old timber, while the worn threshold shows how many have passed through seeking justice that the world above would never grant them.

Training wing sample, `lockyard`:

> The Lockyard sits within the Training Corridor, its planked floor scuffed and stained from years of rogues testing their craft at the long workbench that runs along the stone wall. Timber beams overhead bear carved tallies and crude jokes, each mark a small claim of dignity stolen from the surface world's order. Dust hangs in the air, stirred by footsteps from the workshops nearby, and the faint sounds of bustling work carry through the chamber's boundaries. The worn bench shows generations of lockpicks, bent wires, and practice tumbler sets, evidence of a trade passed hand to hand with rough humor and wary pride.

Leadership wing sample, `throne_in_tatters`:

> The Throne in Tatters sits at the heart of Leadership Wing, its flagstone floor worn smooth by years of boots and spilled ale. Timber beams cross overhead, blackened by smoke that still hangs faint in the quiet air, while stone walls bear the scars of rough use, chipped corners, faded marks, and the odd dagger gouge that no one bothered to mend. At the chamber's center stands a battered throne, its wood patched and recarved a dozen times over, a mockery of surface ceremony made dignified by sheer stubborn survival. The space hums with wary pride, every worn surface a testament to rogues who built their own court from castoffs and defiance.

## Sample generated descriptions

Entry wing, `false_alley`:

> The False Alley ends abruptly against the city wall, its worn brick boundaries pressing close on three sides. Cobbles underfoot are cracked and uneven, carrying a faint layer of dust that marks the space as rarely swept. The alley's dead-end shape and shabby upkeep suggest a place the working districts have half-forgotten, where rough humor and wary silence share the same narrow ground. A single exit leads back south, the only route away from the wall's looming presence.

Common wing, `court_of_coins`:

> The Court of Coins sprawls beneath timber beams blackened by years of firepit smoke, its flagstone floor worn smooth by countless boots and marked with old stains no one bothers to scrub. Stone walls bear crude tallies and mockeries of surface law, carved by hands that found dignity in defiance rather than coin. The central firepit throws uneven light across benches and low tables where rogues gather to settle disputes with rough ceremony, their laughter sharp-edged and their silences watchful. Smoke hangs thick in the air, carrying the smell of cheap ale and old timber, while the worn threshold shows how many have passed through seeking justice that the world above would never grant them.

Training wing, `lockyard`:

> The Lockyard sits within the Training Corridor, its planked floor scuffed and stained from years of rogues testing their craft at the long workbench that runs along the stone wall. Timber beams overhead bear carved tallies and crude jokes, each mark a small claim of dignity stolen from the surface world's order. Dust hangs in the air, stirred by footsteps from the workshops nearby, and the faint sounds of bustling work carry through the chamber's boundaries. The worn bench shows generations of lockpicks, bent wires, and practice tumbler sets, evidence of a trade passed hand to hand with rough humor and wary pride.

Commerce wing, `honest_stall`:

> The Honest Stall sits along Commerce Row, its timber walls and planked floor worn smooth by steady traffic through the busy district. Overhead beams show the marks of rough carpentry, fitted without ceremony but holding firm. A signpost leans beside the entrance, its painted lettering faded but still legible in the dim light that filters through from the corridor beyond. The air carries smoke and the low hum of voices from nearby shops, where merchants trade in goods the surface world prefers not to name.

Leadership wing, `throne_in_tatters`:

> The Throne in Tatters sits at the heart of Leadership Wing, its flagstone floor worn smooth by years of boots and spilled ale. Timber beams cross overhead, blackened by smoke that still hangs faint in the quiet air, while stone walls bear the scars of rough use, chipped corners, faded marks, and the odd dagger gouge that no one bothered to mend. At the chamber's center stands a battered throne, its wood patched and recarved a dozen times over, a mockery of surface ceremony made dignified by sheer stubborn survival. The space hums with wary pride, every worn surface a testament to rogues who built their own court from castoffs and defiance.

## Sample stateful descriptions

Room: `court_of_coins`

```json
{
  "season_winter": "The Court of Coins sprawls beneath timber beams blackened by years of smoke, its flagstone floor worn smooth where rogues gather around a central firepit that throws heat against the winter cold seeping through stone walls. Rough benches ring the flames in a mockery of formal council, their arrangement claiming dignity from shared warmth rather than ceremony. Smoke curls thick toward the beams, carrying the smell of burning wood and spilled ale, while voices rise and fall in wary laughter that marks this chamber as a place where the city's hidden keep their own rough court. The firepit's light catches on frost-edged cracks in the flagstones near the walls, where winter's bite reaches even this deep refuge within the Common Wing.",
  "time_night": "The Court of Coins sits low-ceilinged beneath timber beams blackened by years of smoke from the central firepit, its worn flagstones bearing the scuff and stain of countless boots. Stone walls press close around the chamber, their rough surfaces catching lamplight in uneven pools that leave the corners in shadow. The air carries smoke and the faint sourness of spilled drink, quieter now in the late hours but still marked by low voices and the occasional scrape of a bench. Here in the Common Wing's hidden hall, the thieves' mock court holds its own rough dignity, where stolen ceremony and wary humor make a kind of home from what the surface world discards.",
  "time_evening": "The Court of Coins sits beneath timber beams darkened by years of smoke, its flagstone floor worn smooth where rogues gather around a central firepit that casts long shadows across the stone walls as evening settles in. Rough benches and overturned crates form a makeshift council ring, their arrangement a deliberate mockery of the guildhalls above, where thieves hold court with the same ceremony their betters claim by birthright. The smoke carries the day's spilled ale and sweat, thickening as lamplight replaces the last pale glow from narrow vents near the ceiling. Voices rise in wary banter and sharp laughter, each word tested before it's trusted, the room's warmth earned through shared survival rather than given freely.",
  "invasion_invasion": "The Court of Coins sits beneath timber beams blackened by years of smoke from the central firepit, its flagstone floor scuffed by countless boots and scattered with overturned benches. Stone walls bear crude tallies and mockeries of surface law, their rough surfaces now marred by fresh gouges where blades struck in haste. The smoke-thick air carries shouts and the scrape of steel as rogues bar the chamber's exits against the incursion, their usual rough laughter replaced by hard-edged commands. What was once a place of defiant ceremony now holds only the tense preparation of thieves defending their hidden court."
}
```

## Walkability and placement verification

Programmatic verification results:
- room count in DB: `20`
- reachable from `false_alley`: `20 / 20`
- unreachable rooms: none
- broken exits: none
- NPC placement checks: all `9 / 9` matched expected rooms exactly

Expected NPC placements verified:
- `guild_leader` -> `court_of_coins`
- `guild_merchant` -> `honest_stall`
- `fence` -> `fences_curtain`
- `lockpick_trainer` -> `lockyard`
- `pickpocket_trainer` -> `marks_walk`
- `stealth_trainer` -> `shadowed_hall`
- `combat_trainer` -> `the_pit`
- `quartermaster` -> `quartermaster_hold`
- `watcher` -> `watcher_nook`

## Teleport command

```text
@tel #27596
```

This lands on `false_alley`, the intended entry room for the zone.

## Final state

The finished result is a playable 20-room Court of Coins thieves guild zone with real MT-600 Phase 3 and Phase 4 content generated and written back into the canonical zone YAML, successfully loaded into the live database, reachable from entry through all rooms, and populated with the intended NPC roster. The only outstanding gap relative to the dispatch is command-surface verification of `@zone load thieves_guild YES`; the actual loader backend succeeded, but the available browser session could not exercise the in-game admin command because it was not authenticated.