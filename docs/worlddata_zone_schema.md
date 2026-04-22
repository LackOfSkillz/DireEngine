# Worlddata Zone Schema

The builder, YAML files, importer, and exporter all share the same authored room contract.

## Room Fields

Each room in `worlddata/zones/<zone_id>.yaml` may define:

```yaml
rooms:
  - id: kingshade_and_amberwick
    name: Kingshade Street and Amberwick Lane
    typeclass: typeclasses.rooms_extended.ExtendedDireRoom
    short_desc: A busy knot of paving stones.
    desc: Default room description.
    stateful_descs:
      spring: Spring description.
      summer: Summer description.
      autumn: Autumn description.
      winter: Winter description.
      burning: The room is burning.
    details:
      cobbles: The cobbles are tight-set and well cared for.
      crest: An occasional iron crest brackets the doorway.
    room_states:
      - burning
    ambient:
      rate: 120
      messages:
        - A carriage rattles over the stones.
        - A distant bell rings from deeper in the district.
    environment: city
    npcs:
      - town_guard
      - goblin_grunt
    items:
      - id: iron_sword
        count: 1
      - id: health_potion
        count: 5
    zone_id: kingshade
    map:
      x: 10
      y: 12
      layer: 0
    exits:
      east:
        target: amberwick_lane
        typeclass: typeclasses.exits.Exit
      west:
        target: ferry_hold
        typeclass: typeclasses.exits_slow.SlowDireExit
        speed: walk
        travel_time: 5
    special_exits:
      gate:
        target: guild_foyer
        typeclass: typeclasses.exits.Exit
```

## Evennia Mapping

- `desc` maps to `room.db.desc`
- `stateful_descs.<state>` maps to `room.attributes.add(f"desc_<state>", text)`
- `details` maps to `room.db.details`
- `ambient.rate` maps to `room.db.room_message_rate`
- `ambient.messages` maps to `room.db.room_messages`
- `room_states` maps to tags in category `room_state`
- `npcs` stores authored NPC definition ids assigned to the room; rooms never embed full NPC objects
- `items` stores authored item definition ids with counts assigned to the room; item entries always use `{ id, count }` and may carry nested `items` for container-ready structure
- `typeclass` controls the room typeclass created by `@zone load`
- `exits.<direction>.target` maps to the destination room id
- `exits.<direction>.typeclass` controls the exit typeclass created by `@zone load`
- `exits.<direction>.speed` maps to `exit.db.move_speed`
- `exits.<direction>.travel_time` maps to `exit.db.travel_time`
- `special_exits.<direction>.*` round-trips like `exits`, but is reserved for non-spatial connectors such as `gate`, `arch`, or `bridge`

## Import Rules

- `@zone load <zone_id>` is the only runtime sync step. The builder does not live-patch runtime rooms.
- Import clears existing authored `desc_*` attributes before writing current `stateful_descs`.
- Import clears `room_state` tags before writing current `room_states`.
- Authored rooms default to `typeclasses.rooms_extended.ExtendedDireRoom` when `typeclass` is omitted.
- Authored exits default to `typeclasses.exits.Exit` when `typeclass` is omitted.
- Only `map.x`, `map.y`, and `map.layer` determine room layout. Exits and `special_exits` do not determine geometry.
- Builder slow exits use `typeclasses.exits_slow.SlowDireExit`, a project wrapper around Evennia's slow-exit behavior.

## Export Rules

- `@zone export <zone_id>` writes `desc`, `stateful_descs`, `details`, `room_states`, `ambient`, and `typeclass` back into YAML.
- Export only writes `desc_*` attributes into `stateful_descs`.
- Export writes exit target, typeclass, speed, and travel_time back into YAML when present.
- Export writes non-spatial exit keys into `special_exits` and preserves their target, typeclass, speed, and travel_time.
- Room-level `npcs` round-trips as a list of NPC ids and remains the only authored room-to-NPC relationship field.
- Room-level `items` round-trips as a list of `{ id, count }` entries; duplicate ids are normalized into a single counted entry.

## Cmdset Decision

This pass adopts the extended-room storage model and typeclass, but does not install Evennia's `ExtendedRoomCmdSet` globally.

The project already has custom look and builder/admin command surfaces, so globally replacing `look`, `@desc`, and related commands would be higher risk than the authored-world feature itself. If detail lookups or room-state admin commands need to be exposed later, fold the specific behavior into the project's command layer instead of enabling the contrib cmdset wholesale.

## Slow Exit Notes

- Slow exits delay traversal. They do not move rooms or transports.
- The builder only authors exit traversal metadata. It does not animate exits or move map nodes.
- `setspeed` and `stop` are enabled through Evennia's slow-exit cmdset so authored slow exits can be controlled in-game.