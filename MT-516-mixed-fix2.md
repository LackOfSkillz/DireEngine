# MT-516-mixed-fix2 — Stack split integrity and disambiguation suppression

## Background

MT-516-mixed-fix1 shipped forage stack merging, look migration, and
pluralization fixes. Smoke test as Jekar in `#4222 Kingshade Street`
revealed two related bugs:

```
> inv
... high-quality twigs (18) ...

> drop 1.twig
You drop high-quality twig.

> drop third twig
More than one match for 'twig'. Try 'first twig', 'second twig',
or '2.twig':
 1. high-quality twig
 2. high-quality twig

> drop 3.twig
More than one match for 'twig'. Try 'first twig', 'second twig',
or '2.twig':
 1. high-quality twig
 2. high-quality twig

> drop second twig
You drop high-quality twig.
```

Two diagnoses:

1. **Stack splitting fragments instead of decrementing.** A stack
   of 18 twigs, after `drop 1.twig`, no longer behaves as one
   stack. Subsequent operations see 2 entities, not 16-quantity
   stack + 1 dropped. The drop operation is splitting the stack
   into multiple smaller entities rather than preserving a single
   stack with decremented quantity.

2. **Disambiguation is firing on what should be one stack.** Even
   if 2 entities legitimately exist, the resolver should treat
   them as a single addressable target (or aggregate them at the
   resolver layer). The current behavior shows the disambiguation
   prompt for an operation that has an unambiguous semantic answer:
   "drop one of the twigs."

The disambiguation message itself is good — clear, helpful, suggests
ordinal alternatives. But it shouldn't be triggered for stack-aware
operations on a single fungible resource.

This dispatch fixes stack split semantics and ensures disambiguation
doesn't fire on stack operations. Scope is surgical.

## Architectural guardrails (READ FIRST)

This is the second fix dispatch in this MT-516 sequence. The pattern
is now familiar: smoke test surfaces a bug verification missed; we
diagnose and fix locally; we re-verify with the same scenario.

Biggest risk: chasing the wrong abstraction. The bug could be in:
- The stack split logic (drop creates new entity instead of
  decrementing)
- The merge-on-receive logic (split stack should re-merge if
  identical stacks coexist)
- The resolver (treats stack siblings as separate targets)
- All three

Phase A diagnosis must identify which. Don't fix before knowing.

**Frozen scope:**

1. Phase A: Diagnose stack split behavior. Inspect what happens
   to a stack when `drop 1.twig` is executed. Where does the
   dropped item come from — a new entity or a decrement of the
   existing stack? What's the post-drop state of the stack?
2. Phase B: Diagnose resolver behavior on multi-stack scenarios.
   When 2 stacks of identical items exist, why does ordinal
   targeting return ambiguity? Should they be treated as one
   target?
3. Phase C: Fix stack split to decrement, not fragment. When
   dropping N from a stack of M:
   - If N < M: decrement stack to M-N, create new dropped entity
     of quantity N
   - If N == M: move whole stack to ground
   - If N > M: error (existing behavior)
4. Phase D: Fix merge-on-receive to also handle inventory-side
   re-merging. If two stacks of identical items exist in the
   same inventory (from any cause — older items, split residue,
   etc.), they should merge into one stack at the inventory
   boundary.
5. Phase E: Fix resolver to treat identical stacks as one
   addressable target. When a player types `drop twig`, the
   resolver returns one stack (the largest, the newest, or
   merges them — agent picks). Disambiguation should not fire
   for fungible identical stacks.
6. Phase F: Live verification with Jekar in `#4222`. Same
   scenario as the smoke test. Forage to a stack, drop with
   each ordinal syntax, confirm:
   - Stack maintains as one entity through drops
   - All ordinal syntaxes work consistently
   - No disambiguation prompt fires on stack operations
7. Phase G: Update tests for stack split integrity, inventory
   re-merge, and resolver behavior on multi-stacks.
8. Phase H: Update validation artifacts.

**Frozen what-not-to-do list:**

- DO NOT modify the foraging logic itself. The bug is in
  inventory operations, not item creation.
- DO NOT change which items are stackable. The forage_catalog
  flagging is correct; the issue is operations on stacks.
- DO NOT redesign the resolver's scope vocabulary or priority.
  The fix is in how stacks are addressed, not in scope rules.
- DO NOT touch state-aware descriptions, weather, calendar,
  invasion, terrain, or any runtime state module.
- DO NOT migrate additional commands. The scope is fixing the
  stack-aware behavior in the already-migrated commands.
- DO NOT add new ordinal syntaxes or change pluralization.
- DO NOT report SHIPPED until live verification with Jekar
  confirms all three behaviors fixed: stack maintains as one
  entity through drops; all ordinal syntaxes work; no
  disambiguation prompt fires on healthy stack operations.

**Stop-and-report conditions:**

- If Phase A reveals stack split is correctly decrementing and
  the bug is elsewhere (e.g., the resolver caching stale
  entity counts), stop and report. The fix needs different
  scope.
- If multi-stack inventory state is intentional somewhere in
  the codebase (e.g., quality-preserving stacks that the agent
  doesn't yet understand), stop and report.
- If fixing resolver disambiguation breaks legitimate
  disambiguation cases (two genuinely distinct items with same
  display name), stop and report.
- If live verification reveals additional broken behaviors
  beyond stack integrity and disambiguation, list them but do
  NOT fix them in this dispatch.
- If the inventory re-merge logic creates ordering or stability
  problems (stacks merging in unexpected ways during normal
  play), stop and report.

## Phase A — Diagnose stack split

Read the current stack drop logic in `commands/cmd_drop.py` and
`typeclasses/objects.py`. Identify:

1. When `drop 1.twig` resolves to a stack of quantity 18, what
   happens?
   - Does the stack quantity decrement to 17?
   - Or is a new entity created with quantity 1, and the original
     stack remains at 18, and one entity is "removed" but in fact
     the stack count stays the same and a separate twig entity is
     dropped?
2. After the drop, what's the inventory state?
   - One stack of 17?
   - One stack of 18 + one entity of 1? (The "fragmentation" hypothesis)
   - Two stacks?

Run a live diagnostic:

```python
# Pseudocode
char = test_character_with_stack_of_18_twigs()
print(f"Before: {len(char.contents)} items")
for item in char.contents:
    print(f"  {item.key}: stack_qty={item.db.stack_quantity}")

drop_one_twig(char)

print(f"After: {len(char.contents)} items")
for item in char.contents:
    print(f"  {item.key}: stack_qty={item.db.stack_quantity}")
```

The output tells us exactly where the fragmentation is happening.

## Phase B — Diagnose resolver on multi-stack

In the smoke test scenario, after `drop 1.twig` the inventory
fragmented somehow (showed 2 entities instead of one stack).
When `drop third twig` was attempted, the resolver returned
ambiguity.

Check:

1. Does the resolver iterate stacks and treat each one as a
   separate match for the ordinal? It probably should NOT — for
   identical stacks, ordinal addressing is unclear ("the third
   stack of twigs?").
2. Should the resolver auto-merge identical stacks before
   resolving? Or treat them as one addressable target by
   summing quantity?

Document the current behavior, then design the fix.

## Phase C — Fix stack split

Based on Phase A, fix the drop logic to decrement, not fragment.

Likely the fix is in the drop command's stack handling:

```python
# Pseudocode for correct behavior
if drop_quantity < stack.db.stack_quantity:
    # Decrement source stack
    stack.set_stack_quantity(stack.db.stack_quantity - drop_quantity)
    # Create new dropped entity with the dropped quantity
    new_entity = create_object_clone(stack)
    new_entity.set_stack_quantity(drop_quantity)
    new_entity.move_to(room)
elif drop_quantity == stack.db.stack_quantity:
    # Move whole stack to ground
    stack.move_to(room)
else:
    # Error: drop_quantity > stack_quantity
    raise InsufficientQuantityError
```

The agent finds the actual code, identifies the gap, and
implements the fix.

## Phase D — Fix inventory re-merge

If somehow two stacks of identical items end up in the same
inventory, they should merge into one stack.

This handles:
- Pre-MT-516 items that someone has consolidated to be
  stackable
- Edge cases where stack split logic accidentally created
  multiple stacks
- Future cases where items are added to inventory by paths
  that bypass the standard hooks

The merge happens at the inventory boundary (`at_object_receive`
already handles single-item-to-stack merging; this extends to
stack-to-stack).

## Phase E — Fix resolver multi-stack handling

Before resolution, the resolver should:

1. Group inventory contents by identity (the same key used for
   merge eligibility)
2. For each group with >1 entity, return them as a single
   addressable target (probably the largest stack, or auto-merge
   them as part of resolution)

This means when `drop twig` is called and 2 stacks of twigs
exist, the resolver returns one of them (consistent rule, e.g.,
the newest by creation time) and treats them as one target.

For ordinal targeting (`drop second twig`), the meaning becomes
ambiguous if multiple stacks exist. The agent picks a rule and
documents:

- Option E.1: Ordinals address individual entities within a
  stack ("the second twig in the stack")
- Option E.2: Ordinals address among stacks ("the second stack")
- Option E.3: Ordinals are meaningless for identical stacks;
  fall through to addressing the single combined target

I lean Option E.3 — for fungible identical stacks, ordinals don't
make sense because the items are interchangeable. The player saying
"drop second twig" should just drop one twig, period.

The agent decides and documents.

## Phase F — Live verification with Jekar

Same scenario, expanded:

```
[Jekar in #4222 Kingshade Street]
[Inventory should have a stack of foraged twigs from prior smoke test]

> inv
[verify: high-quality twigs (N) as one stack]

> drop 1.twig
[verify: dropped successfully, message clear]

> inv
[verify: stack count decremented by 1, still ONE stack]

> drop second twig
[verify: works without disambiguation]

> drop third twig
[verify: works without disambiguation]
[expected: drops one twig, stack decrements again]

> drop 3.twig
[verify: works equivalently to ordinal forms]

> inv
[verify: stack count decremented appropriately, still ONE stack]
```

Capture verbatim outputs.

## Phase G — Tests

Update or add:

- `tests/test_stackables.py`: add tests for split decrement
  behavior (drop 1 from 18 leaves 17 in one stack, not 18+1)
- `tests/test_targeting.py`: add tests for resolver auto-merging
  identical stacks
- Tests verifying no disambiguation fires for fungible stacks

## Phase H — Validation artifacts

Update existing artifacts noting the surfaced gap, and create
new `exports/mt516_mixed_fix2_validation.md` for this dispatch.

## Verification checklist

1. Phase A diagnosis identifies the fragmentation cause.
2. Phase B diagnosis identifies the disambiguation cause.
3. Phase C fixes stack split semantics.
4. Phase D fixes inventory re-merge.
5. Phase E fixes resolver multi-stack handling.
6. Phase F live verification with Jekar in #4222 captures
   verbatim output proving fixes landed.
7. All tests pass.
8. Artifacts updated.
9. No code outside in-scope list modified.

## Stop conditions

- Edit only:
  - `commands/cmd_drop.py` (stack split logic)
  - `typeclasses/objects.py` (stack split helpers)
  - `typeclasses/characters.py` (re-merge in receive hook)
  - `world/helpers/target_resolver.py` (multi-stack handling)
  - Tests for the three fixes
  - Three validation artifacts
- Stop on diagnostic surprises.
- Stop on legitimate disambiguation regression.
- Stop on multi-stack ordering surprises.
- Do not chain fixes for unrelated issues.
- Do not declare SHIPPED until live verification confirms.

## Required artifacts

1. Updated stack split logic
2. Updated re-merge logic
3. Updated resolver multi-stack handling
4. Updated tests
5. Updated `exports/mt516_validation.md`
6. Updated `exports/mt516_mixed_validation.md`
7. Updated `exports/mt516_mixed_fix1_validation.md`
8. New `exports/mt516_mixed_fix2_validation.md`

## Followup queue

- **Plural quantity-drop targeting:** `drop 2 twigs` doesn't
  match because the resolver expects singular nouns. Surfaced in
  fix1, deferred again. Small fix when the agent has bandwidth.

- **Plural item descriptions:** "A useful berries..." reads as
  ungrammatical for a stack. Description rendering for stacks
  needs to handle "These are useful berries..." or similar.
  Content/code task.

- **Pre-existing item migration (still deferred):** Old
  pre-MT-516 items that haven't been merged into stacks. Low
  priority cleanup.

- **MT-515 — Project-wide skill-attempts framework:** Drafts
  next, after fix2 verifies clean.

- **Manual trial zone build:** Becomes feasible after MT-515.