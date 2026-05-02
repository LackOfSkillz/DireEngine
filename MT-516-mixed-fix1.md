# MT-516-mixed-fix1 — Forage stack merge, look migration, pluralization

## Background

MT-516 and MT-516-mixed shipped object presentation refactor and
mixed-target command migration. The agent reported SHIPPED for both.
Smoke test in webclient as Jekar (rank-trained Outdoorsmanship in
`#4222 Kingshade Street`) revealed three real gaps:

```
> forage
You expertly gather high-quality natural materials.
You recover high-quality twig, high-quality twig, high-quality twig.
> inv
You are carrying: ... high-quality twigs (3) ...
> l twig
More than one match for 'twig' (please narrow target):
 high-quality twig-1 (carried)
 high-quality twig-2 (carried)
 high-quality twig-3 (carried)
> l twig 1
Could not find 'twig 1'.
> l first twig
Could not find 'first twig'.
```

Three diagnoses from this output:

1. **Storage stacking did not fire for forage outputs.** Inventory
   shows `high-quality twigs (3)` as a display line — but `look`
   produces three separate matches. That means display aggregation
   is working but storage stacking is not. The three twigs are
   three separate database objects; the inventory display
   aggregated them visually, masking the underlying state.

2. **The `look` command (and aliases like `l`) was not migrated to
   the centralized resolver.** Ordinal syntaxes do not work, and
   the `target-N` disambiguation suffix is still firing — both
   violate locked decision #8 from MT-516.

3. **Pluralization rule is wrong for y-ending nouns.** Inventory
   shows `useful berrieses (2)`. Should be `useful berries (2)`.
   Y-ending nouns drop the y and add `-ies`, not `-s` or `-es`.

This dispatch fixes all three. Scope is surgical: diagnose where
the forage path bypasses the merge hook, migrate `look`, fix the
pluralization rule. No new features, no scope expansion.

## Architectural guardrails (READ FIRST)

This is a fix dispatch. Three known-broken behaviors, three targeted
fixes. The biggest risk is scope drift into "while I'm here, let me
also fix..." territory. Resist.

The second-biggest risk is premature claims of resolution. The
previous two dispatches reported SHIPPED with these behaviors broken
because the verification didn't exercise the actual forage flow
end-to-end. This dispatch's verification MUST exercise the live
forage flow with Jekar in `#4222 Kingshade Street`, the same path
that surfaced the bugs.

**Frozen scope:**

1. Phase A: Diagnose. Identify why storage stacking isn't firing
   for forage outputs. Check three things: (a) are forage catalog
   items flagged stackable, (b) is the forage creation path going
   through the merge hook, (c) is `at_object_receive` correctly
   detecting and merging stackables. Document each.
2. Phase B: Fix the forage stacking gap. Whatever Phase A reveals
   is the cause, fix it locally. Likely candidates: forage catalog
   missing stackable metadata, forage creation path bypassing
   inventory hooks, or merge hook not handling the forage item
   shape correctly.
3. Phase C: Audit `look` command resolution. Find where `look`,
   `l`, `examine` (and any other "look at named target" verbs)
   resolve their targets. Confirm whether they were missed in
   MT-516-mixed migration.
4. Phase D: Migrate `look` (and aliases) to the centralized
   resolver. Same pattern as the other migrated commands. The
   resolver should handle stack-aware lookup so `l twigs` returns
   the stack object and `l first twig` resolves via ordinal.
5. Phase E: Fix the pluralization rule. Y-ending nouns need
   `y → ies` conversion (berry → berries, not berry → berryes
   or berrys). Other irregular cases left as content overrides
   per item.
6. Phase F: Live verification with Jekar in `#4222 Kingshade Street`.
   Same character, same room as the smoke test. Forage repeatedly,
   confirm stacking, confirm `look` resolution, confirm no
   `target-N` output, confirm pluralization.
7. Phase G: Update tests to cover the three fixes:
   - Forage path produces merged stacks
   - `look` resolves stacks and ordinals
   - Pluralization handles y-ending nouns
8. Phase H: Update validation artifacts. Mark MT-516 and
   MT-516-mixed sections with the surfaced gap and the fix.

**Frozen what-not-to-do list:**

- DO NOT migrate any commands beyond `look`, `l`, `examine` and
  their direct aliases. The MT-516-mixed roster covered the rest.
- DO NOT add new resolver features. The resolver already supports
  what's needed; the issue is `look` not using it.
- DO NOT modify the forage catalog content (item identities,
  thresholds, terrain tags). If catalog metadata is missing
  stackable flags, add them — but don't restructure existing
  data.
- DO NOT migrate existing items (the leaves Jekar has from
  before). Pre-MT-516 items remain as separate objects; only
  newly-foraged items get the stack treatment. Migration of
  existing items is a separate concern not in this scope.
- DO NOT modify the foraging gameplay logic (skill checks,
  yields, weather modifiers). Only the item-creation handoff
  to inventory.
- DO NOT redesign the pluralization system. Add the y-ending
  rule; defer irregular plurals (mouse → mice, foot → feet,
  goose → geese) as a future content task.
- DO NOT modify display aggregation logic. It's working
  correctly; the issue is storage stacking not firing.
- DO NOT touch state-aware description rendering, weather,
  invasion, calendar, terrain, or any other system.
- DO NOT chain "while I'm here" fixes for unrelated issues
  surfaced during diagnosis.
- DO NOT report SHIPPED until live verification with Jekar
  confirms all three behaviors fixed.

**Stop-and-report conditions:**

- If Phase A diagnosis reveals the forage path has multiple
  item-creation entry points and the merge hook needs to be
  added to several places, stop and report. We may need a
  larger refactor to consolidate item creation.
- If the catalog metadata for stackable flags is malformed in
  ways that suggest a content audit beyond this dispatch's
  scope, stop and report.
- If the `look` command turns out to use a different resolution
  pattern than the migrated commands (e.g., evennia's default
  appearance system handles `look at` separately from `look`),
  stop and report. The migration may need a different approach.
- If pluralization rule changes break existing displays for
  other items in unexpected ways, stop and report.
- If live verification reveals additional broken behaviors
  beyond the three documented, list them but do NOT fix them
  in this dispatch. Surface for a separate dispatch.
- If the forage stacking fix requires changes to how items are
  spawned outside the foraging system (loot, NPC drops,
  crafting), stop and report. Each item-creation surface is its
  own concern.

## Phase A — Diagnose forage stacking gap

The agent reads:

1. The forage flow in `typeclasses/abilities_survival.py` —
   specifically the item-creation path. Where do foraged items
   come from?
2. The catalog at `world/builder/content/forage_catalog.yaml` —
   do items have a stackable flag?
3. The receive hook in `typeclasses/characters.py` —
   `at_object_receive` (or wherever the merge logic lives).
   What conditions does it check before merging?
4. The merge logic itself in `world/helpers/display_aggregation.py`
   or `typeclasses/objects.py` — how does it determine if two
   objects should merge?

Each of these has a possible failure mode:

- **Catalog gap:** items don't have stackable flags. Merge hook
  fires but rejects them as non-stackable.
- **Creation path gap:** items aren't entering inventory through
  the path that triggers `at_object_receive`. Maybe they're
  being placed via `move_to(...)` with an arg that bypasses
  hooks, or being created with `location=character` directly.
- **Hook condition gap:** the hook fires and items are flagged
  stackable, but the merge rejects them due to identity mismatch
  (different db keys, missing comparison fields, etc.).
- **Identity comparison gap:** the merge logic compares fields
  that don't exist on forage outputs, or compares them in ways
  that always return False.

The agent runs a live diagnostic to identify which:

```python
# Pseudocode
char = Jekar  # or a fresh test character
catalog_entry = lookup_a_known_stackable_forage_item()
print(catalog_entry.get('stackable'))  # is the flag present?

# Force a forage attempt and inspect
result = forage_attempt(char, terrain_set_room)
new_items = list(char.contents)[-result['yield']:]
for item in new_items:
    print(item.key, item.db.stackable, item.db.catalog_category)
    print(item.location)  # confirm entered inventory
    print(item.tags.all())
```

Document the findings. The fix in Phase B is informed by which
hypothesis was confirmed.

## Phase B — Fix forage stacking

Based on Phase A, apply the targeted fix.

If catalog metadata gap: add stackable flags to the relevant
categories. The agent identifies which categories should be
stackable based on MT-516's earlier roster (filler, healing_herb,
edible, etc.) and adds the metadata.

If creation path gap: route forage item creation through a path
that triggers `at_object_receive`. This may mean using `move_to`
with `quiet=False` or explicitly invoking the receive hook after
creation.

If hook condition gap: fix the comparison logic.

The fix should be the smallest local change that resolves the
diagnosed issue.

## Phase C — Audit `look` resolution

The agent finds where `look at <target>` is handled in DireEngine.
Likely candidates:

- `commands/cmd_look.py` (if it exists)
- Evennia's default `CmdLook` (if no override)
- A custom override in `typeclasses/characters.py`

For whichever path handles it, identify the resolution call:
- Is it `caller.search(args)` (Evennia default — produces
  `target-N`)?
- Is it `resolve_numbered_candidate` (older DireEngine pattern)?
- Is it `resolve_target` (the centralized resolver)?

Document.

The MT-516-mixed validation artifact had a migration roster.
Check if `look` was on it. If yes, why didn't migration happen?
If no, why was it missed?

## Phase D — Migrate `look` and aliases

Apply the same pattern used for the other migrated commands:

```python
# Before:
target = caller.search(self.args)

# After:
target, _, _, _ = self.resolve_target(
    self.args,
    scopes=("inventory", "characters", "room"),
)
if not target:
    caller.msg(f"Could not find '{self.args}'.")
    return
```

Adjust scope per `look`'s natural targeting (probably
`inventory`, `characters`, `room` since players look at
anything visible).

The resolver already handles stack-aware lookup (Phase B
ensured forage items become stacks; the resolver returns
the stack object). Ordinal syntax already works in the resolver.
The migration just hooks `look` into it.

Aliases (`l`, possibly `examine`) need the same treatment if
they're separate commands.

## Phase E — Fix pluralization

The pluralization helper (likely in
`world/helpers/display_aggregation.py`) needs a y-ending rule:

```python
# Pseudocode
def pluralize(noun: str) -> str:
    if noun.endswith('y') and noun[-2] not in 'aeiou':
        return noun[:-1] + 'ies'  # berry → berries
    if noun.endswith(('s', 'x', 'z', 'ch', 'sh')):
        return noun + 'es'  # box → boxes
    return noun + 's'  # leaf → leafs (still wrong, but minor)
```

The vowel-y vs consonant-y distinction matters: "berry" (consonant
y) → "berries" but "boy" (vowel y) → "boys".

Other irregular cases (leaf → leaves, mouse → mice) are left as
per-item overrides. v1 handles regular y-ending plurals; the rest
is content authoring.

Add tests for the new rule.

## Phase F — Live verification with Jekar in #4222

Same character, same room, same scenario as the smoke test.

### F.1 Test sequence

```
> drop all twig
> drop all leaf
> drop all stick
> drop all rock
> drop all berry
[clear inventory of pre-MT-516 items]

> forage
[wait roundtime]
> forage
[wait roundtime]
> forage
[get multiple foraged outputs]

> inv
[verify items appear as stacks: "high-quality twigs (3)" etc.]

> l twig
[expect: appraise/look output for the stack, NOT disambiguation prompt]

> l first twig
[expect: same stack, ordinal resolved]

> l 1.twig
[expect: same stack, numeric positional resolved]

> l 1st twig
[expect: same stack, numeric-suffix resolved]

> l berries
[verify pluralization is correct: "berries" not "berrieses"]

> drop 2 twigs
[verify split semantics work for stacks]

> inv
[verify reduced stack count]
```

### F.2 Capture verbatim

For each command in the test sequence, capture:
- The exact command typed
- The exact output observed

This goes in the validation artifact as the live evidence of
fixes landing.

### F.3 Pre-MT-516 items

The pre-existing leaves from before MT-516 will still be
separate objects. The test sequence drops them first (`drop all
leaf`) to remove the noise. They are not migrated; that's a
separate concern.

## Phase G — Tests

Update or add tests:

- `tests/test_stackables.py`: add a test that exercises the
  forage flow specifically — create a character, forage in a
  fixture room, verify outputs are stack-merged
- `tests/test_targeting.py`: add a test that `look` (or
  whatever the command is named in tests) resolves stack-aware
  with ordinal syntax
- `tests/test_display_aggregation.py`: add tests for the
  y-ending pluralization

All existing tests must continue to pass.

## Phase H — Update validation artifacts

Two artifacts need updates:

### H.1 `exports/mt516_validation.md`

Add a section noting:
- MT-516 reported SHIPPED but smoke test surfaced forage stacking
  gap
- Root cause from Phase A diagnosis
- Fix shipped in MT-516-mixed-fix1

### H.2 `exports/mt516_mixed_validation.md`

Add a section noting:
- MT-516-mixed reported SHIPPED but smoke test surfaced look
  migration gap
- `look` was not in the migrated roster (or was incorrectly
  classified)
- Migration completed in MT-516-mixed-fix1

### H.3 New `exports/mt516_mixed_fix1_validation.md`

Standard fix dispatch validation:

```markdown
# MT-516-mixed-fix1 validation

Status: SHIPPED

## Phase A — Diagnosis
[Root cause of forage stacking gap]

## Phase B — Forage stacking fix
[Fix applied, files changed]

## Phase C — Look audit
[Status of look in MT-516-mixed migration]

## Phase D — Look migration
[Migrated commands, scope, files changed]

## Phase E — Pluralization fix
[Y-ending rule, code change]

## Phase F — Live verification
[Verbatim output of all test commands as Jekar in #4222]

## Phase G — Tests
[Test count, all-passing confirmation]

## Phase H — Validation artifacts
[MT-516 and MT-516-mixed marked with surfaced gaps; this artifact
created]

## Final state
[One line: "MT-516-mixed-fix1 shipped. Smoke test gap closed.
Foraging produces stacks; look resolves stacks and ordinals;
pluralization handles y-ending nouns. Ready for player verification."]
```

## Verification checklist

1. Phase A diagnosis identifies the forage stacking root cause.
2. Phase B fixes it locally; foraging produces merged stacks
   for new items.
3. Phase C audits look command resolution.
4. Phase D migrates look (and aliases) to centralized resolver.
5. Phase E adds y-ending pluralization rule.
6. Phase F live verification with Jekar in #4222 captures
   verbatim output for each test command.
7. Phase G tests pass.
8. Phase H validation artifacts updated.
9. No code outside the in-scope list modified.
10. No `target-N` suffix appears in player-facing output for
    foraged items.
11. All three ordinal syntaxes work for `l <target>`.
12. Pluralization is correct for berry → berries.

## Stop conditions

- Edit only:
  - `world/helpers/display_aggregation.py` (pluralization)
  - `world/helpers/target_resolver.py` (only if Phase A diagnosis
    requires it)
  - `commands/cmd_look.py` or wherever look lives (migration)
  - `typeclasses/abilities_survival.py` or wherever forage
    creates items (only if Phase A diagnosis requires it)
  - `world/builder/content/forage_catalog.yaml` (only if Phase A
    diagnosis requires stackable flag additions)
  - `typeclasses/objects.py` or `typeclasses/characters.py`
    (only if Phase A diagnosis requires hook fixes)
  - Test files for the three fixes
  - Three validation artifacts
- Stop and report on diagnosis surprises.
- Stop and report on look using non-standard resolution.
- Stop and report on pluralization rule conflicts.
- Stop and report on live verification gaps beyond the three
  fixes.
- Do not chain follow-up fixes within this dispatch.
- Do not declare SHIPPED until live verification confirms.

## Required artifacts

1. Updated forage stacking path (file TBD by Phase A)
2. Updated `cmd_look.py` (or equivalent)
3. Updated `world/helpers/display_aggregation.py`
4. Updated test files
5. Updated `exports/mt516_validation.md`
6. Updated `exports/mt516_mixed_validation.md`
7. New `exports/mt516_mixed_fix1_validation.md`

## Followup queue

- **Pre-MT-516 item migration (optional, deferred):** Existing
  items in characters' inventories from before MT-516 are
  separate objects, not stacks. A one-shot migration could merge
  identical pre-existing items into stacks. Low priority — they're
  legacy artifacts, mostly testing residue. Address if it becomes
  a real player-facing issue.

- **Irregular plural overrides (deferred):** leaf → leaves,
  mouse → mice, foot → feet. Per-item override hook in catalog
  or item typeclass. Content task.

- **Verification methodology improvement (process):** This
  dispatch surfaces that unit tests + agent runtime probes can
  miss bugs that smoke testing catches. Future dispatches with
  user-facing UX changes should include explicit player-facing
  smoke tests in their verification phases, not just code-level
  verification. Consider this a meta-lesson for dispatch authoring
  going forward.

- **MT-515 — Project-wide skill-attempts framework:** Drafts
  next, after this fix lands and verifies clean.

- **Manual trial zone build:** Becomes feasible after MT-515.