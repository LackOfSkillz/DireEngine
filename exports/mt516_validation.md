# MT-516 Validation

## Scope Summary

Implemented:

- pure ordinal parsing in `world/helpers/ordinals.py`
- centralized item resolver in `world/helpers/target_resolver.py`
- render-time aggregation in `world/helpers/display_aggregation.py`
- stack quantity and merge-on-receive support in `typeclasses/objects.py`
- item-arrival recency stamping in room, object/container, and character receive hooks
- room object aggregation in `typeclasses/rooms.py`
- inventory aggregation in `commands/cmd_inventory.py`
- container-content aggregation in wearable containers, gem pouches, and fish strings
- partial stack drop support via `drop 5 leaves`
- object-only command migration to the centralized item resolver for:
  - `get`, `drop`, `wear`, `wield`, `stow`
  - `loot`, `appraise`, `analyze`, `compare`, `inspect`, `open`, `pick`, `skin`
  - `burgle`, `harvest`, `preserve`, `unlock`, `study`

Intentionally not widened in this pass:

- mixed character/object commands such as empath-facing or NPC-facing verbs
- NPC/character presentation
- foraging production logic itself
- MT-514d state-aware room description rendering

## Phase A Reference Notes

Reference consumed from `docs/references/slippy_target_resolver_2026-05-01.md`.

Patterns adapted:

- newest-first resolution order
- ordinal and compact positional targeting
- article/possessive normalization
- `other <name>` shorthand

Patterns not adopted directly:

- fully shared scope routing for objects, players, and room occupants
- making generic Evennia `search()` the primary migration seam

Reason: local archaeology showed existing resolution is inconsistent, and the
same repo-local numbered matcher is also used for character-targeting flows.
Using an item-only resolver avoided changing combat/NPC selection semantics.

## Tests Run

Focused MT-516 helper and integration modules:

```text
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_ordinals tests.test_display_aggregation tests.test_targeting tests.test_stackables
```

Result: `16` tests passed.

Focused helper superset during implementation:

```text
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_mt516_helpers
```

Result: `13` tests passed after fixing `other <name>` handling.

Nearby regressions:

```text
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_calendar tests.test_forage
```

Result: `44` tests passed.

Editor/static validation:

- no reported errors in touched command, helper, typeclass, or test files

## Live Runtime Verification

Workspace Python snippet with Django/Evennia bootstrap created temporary objects,
then cleaned them up.

Observed output:

```text
{'container_count': 1, 'container_quantity': 2}
You see: daggers (2)
```

Interpretation:

- two identical stackable `useful leaf` objects merged into one container entry with quantity `2`
- two separate `dagger` objects in a room aggregated at render time into `daggers (2)`

## Known Boundaries

- The centralized resolver currently covers migrated object-only commands, not every mixed semantic `caller.search(...)` path in the repo.
- Auto-target newest-first depends on the new `db.mt516_arrived_at` stamp. Older preexisting objects without that stamp fall back to creation time and object id ordering.
- Partial stack splitting is implemented for `drop <quantity> <item>` only in v1.
- Non-stackable room aggregation uses the visible label and exact counts, per the locked decision.

## Outcome

MT-516 shipped the v1 object-presentation contract without changing NPC/character presentation or reopening MT-514d rendering. The main architectural constraint discovered during implementation was command-resolution divergence; the final solution centralized item resolution while deliberately avoiding shared character-targeting paths.

## Surfaced Gap And Fix

Post-ship smoke testing exposed a real forage stacking gap that MT-516's original
verification missed.

Observed symptom:

- foraged outputs rendered as aggregated inventory lines such as `high-quality twigs (3)`
- `look twig` still found multiple underlying objects instead of one stored stack

Root cause:

- the forage path in `typeclasses/abilities_survival.py` created items with direct
  `location=user` assignment via `create_simple_item(...)`
- that bypassed `Character.at_object_receive(...)`, so the MT-516 merge-on-receive
  hook never ran for new forage outputs

Fix shipped in MT-516-mixed-fix1:

- forage item creation now routes through a local `_create_foraged_item(...)` helper
  that creates the object first and then moves it into inventory with `move_to(...)`
- this triggers the existing merge hook without widening stack behavior for unrelated
  item creation surfaces

Second surfaced gap from post-fix smoke testing:

- stack split integrity and stack-aware ordinal drops were still inconsistent after
  MT-516-mixed-fix1
- `drop 1.twig`/`drop third twig` could drive whole-stack moves or disambiguation logic
  instead of treating a fungible stack as one decrementable target

Fix shipped in MT-516-mixed-fix2:

- stack-aware drop resolution now treats ordinal addressing on a single fungible stack
  as dropping one item from that stack
- inventory duplicate stacks are normalized before carried-item resolution so identical
  stack fragments collapse back into one addressable target