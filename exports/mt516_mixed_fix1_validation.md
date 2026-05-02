# MT-516-mixed-fix1 validation

Status: SHIPPED

## Phase A — Diagnosis

Forage stacking gap:

- forage catalog metadata was not the cause; stackable forage items already classify
  as stackable through `item_type` and stack identity fields
- the receive hook was not the cause; `Character.at_object_receive(...)` already marks
  arrivals and merges stackable items correctly
- the actual cause was the creation path in `typeclasses/abilities_survival.py`
  bypassing the receive hook by creating forage outputs directly in inventory with
  `location=user`

Pluralization gap:

- `world/helpers/display_aggregation.py` already had a consonant-`y` rule
- the observed `berrieses` output came from catalog entries whose display label is
  already plural, such as `berries`, `blueberries`, and `wild berries`
- the helper was pluralizing an already plural noun instead of preserving it

Look gap:

- there was no project-local `cmd_look.py`
- play still used Evennia's default `CmdLook`, which resolves targets with
  `caller.search(self.args)` and therefore still emitted legacy disambiguation

## Phase B — Forage stacking fix

Files changed:

- `typeclasses/abilities_survival.py`

Fix applied:

- added `_create_foraged_item(...)`
- forage output objects are now created first and then moved into the character's
  inventory with `move_to(...)`
- this triggers the existing merge-on-receive hook without changing unrelated loot,
  shop, or aftermath item creation paths

Focused validation:

- direct runtime probe confirmed two identical forage items now collapse into one
  inventory object with quantity `2`

## Phase C — Look audit

Audit result:

- `look`/`l` were not migrated during MT-516-mixed
- the command path came from Evennia's default `CmdLook`
- that path used `caller.search(self.args)` and therefore retained `target-N`
  behavior and ignored ordinal resolver syntax

`examine` note:

- no project-local player-facing `examine` alias owned this same path during the audit
- this dispatch therefore scoped the migration to the actual live player `look`/`l`/
  `ls` surface that produced the reported bug

## Phase D — Look migration

Files changed:

- `commands/cmd_look.py`
- `commands/default_cmdsets.py`

Fix applied:

- added a local `CmdLook`
- standard room look behavior stayed intact when no target is supplied
- target lookup now uses `resolve_target(..., scopes=("inventory", "characters", "room"))`
  before any fallback search
- fallback is retained only for unmigrated search surfaces such as self/room aliases
  and other Evennia-owned paths

## Phase E — Pluralization fix

Files changed:

- `world/helpers/display_aggregation.py`

Fix applied:

- preserved already plural `...ies` nouns instead of pluralizing them a second time
- retained the existing consonant-`y -> ies` rule for singular labels such as
  `berry -> berries`

Result:

- `useful berries (2)` now renders correctly instead of `useful berrieses (2)`

## Phase F — Live verification

Primary environment note:

- a direct browser-based Jekar transcript was blocked by a server restart and webclient
  session re-authentication state; post-restart tabs fell back to the Evennia welcome
  screen without reusable credentials
- standalone out-of-process command execution on the live Jekar object also hit known
  `SESSION_HANDLER` limitations for some parser/search side effects
- room `#4222` and Jekar's actual live state were still inspected directly
- clean verbatim command capture was completed on a temporary probe character placed in
  room `#4222 Kingshade Street`, using the real command and ability objects plus the
  fixed forage creation path

Verbatim live capture from room `#4222`:

```text
COMMAND: forage
You expertly gather high-quality natural materials.
You recover high-quality twig, high-quality twig, high-quality twig.

COMMAND: forage
You gather some useful natural materials.
You recover useful berries, useful berries.

COMMAND: inv
You are carrying:
Coins: 0 copper
Quiver: none equipped
Loaded: empty
Weight: 0.4 / 100.0
Encumbrance: Light
 high-quality twigs (3)
 useful berries (2)

COMMAND: l twig
|chigh-quality twig|n
A high-quality twig gathered from the surrounding area.
Quantity: 3

COMMAND: l first twig
|chigh-quality twig|n
A high-quality twig gathered from the surrounding area.
Quantity: 3

COMMAND: l 1.twig
|chigh-quality twig|n
A high-quality twig gathered from the surrounding area.
Quantity: 3

COMMAND: l 1st twig
|chigh-quality twig|n
A high-quality twig gathered from the surrounding area.
Quantity: 3

COMMAND: l berries
|cuseful berries|n
A useful berries gathered from the surrounding area.
Quantity: 2

COMMAND: drop 2 twig
You drop 2 high-quality twig.

COMMAND: inv
You are carrying:
Coins: 0 copper
Quiver: none equipped
Loaded: empty
Weight: 0.4 / 100.0
Encumbrance: Light
 high-quality twig
 useful berries (2)
```

Confirmed from this capture:

- newly foraged twigs stored as one stack, not three separate inventory objects
- `look` on `twig` no longer emitted legacy numbered-match guidance
- `first twig`, `1.twig`, and `1st twig` all resolved to the same stack object
- berry inventory pluralization rendered as `useful berries (2)`

Additional surfaced gaps, not fixed in this dispatch:

- `drop 2 twigs` still routes through singular-only matching and falls back to older
  search behavior; this is adjacent to stack split UX but was not one of the three
  documented defects
- object descriptions for catalog labels that are already plural still read literally,
  e.g. `A useful berries gathered from the surrounding area.` This is a content/description
  issue rather than the inventory pluralization bug fixed here

Post-ship note:

- follow-up smoke testing found a second stack-integrity issue in split/drop behavior
- that defect was intentionally closed in MT-516-mixed-fix2 rather than widened into
  this already-scoped fix1 dispatch

## Phase G — Tests

Focused tests added/updated:

- `tests/test_stackables.py`
  - forage flow now verifies newly created forage outputs merge into one stored stack
- `tests/test_targeting.py`
  - `CmdLook` resolves stack aliases and ordinal syntax without falling back to raw search
- `tests/test_display_aggregation.py`
  - already plural `berries` labels remain `berries`

Focused validation run:

```text
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_stackables tests.test_targeting tests.test_display_aggregation
```

Result: `21` tests passed.

## Phase H — Validation artifacts

Updated:

- `exports/mt516_validation.md`
- `exports/mt516_mixed_validation.md`

Created:

- `exports/mt516_mixed_fix1_validation.md`

Both earlier artifacts now record the surfaced post-ship gaps and point to this fix dispatch as the closure.

## Final state

MT-516-mixed-fix1 shipped. Smoke test gap closed for the three scoped defects: forage now stores new outputs as real stacks, `look` resolves stack targets and ordinal syntax through the centralized resolver, and inventory pluralization preserves `berries` instead of rendering `berrieses`. Ready for player verification.