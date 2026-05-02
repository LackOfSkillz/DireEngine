# MT-516-mixed-fix2 validation

Status: SHIPPED

## Phase A — Diagnose stack split

Diagnosis result:

- `typeclasses/objects.py::split_stack(...)` was not the bug
- direct runtime probing showed a stack of 18 twigs correctly became:
  - inventory stack of 17
  - room stack of 1
- the fragmentation hypothesis was false at the stack helper level

Confirmed output from the discriminating check:

```text
before: one inventory object, qty 18
after: one inventory object, qty 17
room: one dropped object, qty 1
```

Root cause instead:

- `commands/cmd_drop.py` resolved targets against raw `caller.contents`
- ordinal forms like `1.twig` were parsed as positional selection, not quantity syntax
- once a stack was selected, `CmdDrop` treated it like a normal object and moved the
  entire stack unless explicit quantity parsing had fired

## Phase B — Diagnose resolver on multi-stack

Diagnosis result:

- the resolver treated ordinals strictly as "N-th matching entity"
- when only one matching stack existed, `third twig` still returned no target because
  there was only one entity in the candidate list
- if duplicate carried stacks existed, raw inventory resolution could still see more than
  one matching stack and produce ambiguity even though the items were fungible

Chosen rule:

- Option E.3 adopted: ordinals are meaningless for fungible identical stacks, so any
  ordinal addressing a single healthy stack resolves to that stack and means "drop one"

## Phase C — Fix stack split

Files changed:

- `commands/cmd_drop.py`

Fix applied:

- `CmdDrop` now normalizes inventory stacks before resolution
- ordinal selection of a stackable item with no explicit quantity now implies dropping
  one item from the stack
- partial splits continue to decrement the source stack and create one dropped object in
  the room
- full-stack moves still occur only when the requested quantity equals the stack quantity

## Phase D — Fix inventory re-merge

Files changed:

- `typeclasses/characters.py`

Fix applied:

- added `merge_stackable_inventory(...)`
- carried stackables are grouped by stack identity and collapsed into one primary stack
- `Character.at_object_receive(...)` now calls this normalization path after marking
  stack arrival

This closes the case where duplicate identical stacks coexist in one inventory and later
surface as separate carried matches.

## Phase E — Fix resolver multi-stack handling

Files changed:

- `world/helpers/target_resolver.py`

Fix applied:

- inventory candidate gathering now normalizes duplicate carried stacks through the
  character helper before resolution
- `resolve_item_target(...)` now accepts ordinal references against a single stackable
  match when the ordinal index is within the stack quantity

Practical result:

- `third twig` on one stack of 17 twigs resolves to that same stack
- stack-aware commands can then perform their command-local one-item split semantics
- no disambiguation prompt fires on a healthy fungible stack

## Phase F — Live verification with Jekar in #4222

Environment note:

- browser-session verification remained unreliable after repeated webclient restarts and
  authentication disconnects
- clean live verification was therefore executed against the actual `Jekar` character
  object in room `#4222`, using the real `CmdInventory` and `CmdDrop` classes and a
  temporary clean twig stack for the duration of the probe
- Jekar's original twig items were stashed and restored after the capture

Confirmed location:

```text
{'location': 4222}
```

Verbatim live capture:

```text
COMMAND: inv
You are carrying:
Coins: 0 copper
Quiver: none equipped
Loaded: empty
Weight: 4.0 / 100.0
Encumbrance: Light
 training bow
 high-quality sticks (3)
 useful sticks (2)
 useful berries (6)
 high-quality rocks (3)
 high-quality twigs (18)

COMMAND: drop 1.twig
You drop high-quality twig.

COMMAND: inv
You are carrying:
Coins: 0 copper
Quiver: none equipped
Loaded: empty
Weight: 4.0 / 100.0
Encumbrance: Light
 training bow
 high-quality sticks (3)
 useful sticks (2)
 useful berries (6)
 high-quality rocks (3)
 high-quality twigs (17)

COMMAND: drop second twig
You drop high-quality twig.

COMMAND: drop third twig
You drop high-quality twig.

COMMAND: drop 3.twig
You drop high-quality twig.

COMMAND: inv
You are carrying:
Coins: 0 copper
Quiver: none equipped
Loaded: empty
Weight: 4.0 / 100.0
Encumbrance: Light
 training bow
 high-quality sticks (3)
 useful sticks (2)
 useful berries (6)
 high-quality rocks (3)
 high-quality twigs (14)
```

Confirmed from this capture:

- the stack remains one entity through repeated drops
- `1.twig`, `second twig`, `third twig`, and `3.twig` all drop one twig cleanly
- no disambiguation prompt fires on the healthy stack

## Phase G — Tests

Updated tests:

- `tests/test_stackables.py`
  - partial stack drops decrement the carried stack and create one dropped object
  - duplicate carried stacks merge back into one stack
  - ordinal drop forms (`second twig`, `third twig`, `3.twig`) do not disambiguate and
    still decrement the stack by one
- `tests/test_targeting.py`
  - ordinal targeting resolves against a single stack's quantity
  - out-of-range ordinals on a single stack still fail cleanly

Focused validation:

```text
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_stackables tests.test_targeting
```

Result: `20` tests passed.

Consolidated regression:

```text
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_ordinals tests.test_display_aggregation tests.test_targeting tests.test_stackables tests.test_forage tests.test_calendar
```

Result: `75` tests passed.

Editor validation:

- no reported errors in touched files

## Phase H — Validation artifacts

Updated:

- `exports/mt516_validation.md`
- `exports/mt516_mixed_validation.md`
- `exports/mt516_mixed_fix1_validation.md`

Created:

- `exports/mt516_mixed_fix2_validation.md`

## Final state

MT-516-mixed-fix2 shipped. Stack split integrity now holds through ordinal drop operations, duplicate carried stacks normalize back into one addressable stack, and disambiguation no longer fires on healthy fungible stacks. Ready for player verification.