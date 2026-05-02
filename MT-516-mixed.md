# MT-516-mixed — Extend centralized resolver to mixed character/object commands

## Background

MT-516 shipped centralized object resolution, stack semantics, display
aggregation, and ordinal targeting across object-only commands. The
agent migrated 18 commands (get, drop, wear, wield, stow, appraise,
loot, analyze, compare, inspect, open, pick, skin, burgle, harvest,
preserve, unlock, study) to the centralized `resolve_target()` mixin.

The agent intentionally stopped at object-only flows and noted:

> One boundary remains intentional: mixed character/object verbs
> still use their existing search paths where changing resolution
> would also affect NPC or combat targeting. The centralized
> resolver is applied to object-only flows in this pass.

This dispatch closes that boundary. It extends the centralized
resolver to support character and NPC targeting, then migrates the
remaining mixed-target commands so locked decision #9 ("apply
consistently across all object-targeting commands AND all object-
listing surfaces") is fully satisfied.

The locked decisions from MT-516 carry forward unchanged:

1. Three equivalent positional syntaxes (English ordinal,
   numeric-suffix ordinal, numeric positional)
2. Auto-target on most-recent for non-stackable disambig
3. `target-N` suffix eliminated from output
4. Aggregation by player-visible display string
5. Possessive ("my X") filters to owned scopes

This dispatch adds:

6. The resolver supports character/NPC scope alongside object scopes
7. Mixed commands (attack, examine, look at, give, etc.) use the
   resolver consistently
8. NPC display in room presentation aggregates per the same rules
   as objects (with one explicit caveat: see Phase A.3)

## Architectural guardrails (READ FIRST)

This is the second pass of MT-516. The biggest risk is breaking
combat or social command behavior in subtle ways. The migration
is surgical: extend the resolver's scope vocabulary, then migrate
commands one at a time with regression verification.

The second-biggest risk is touching NPC presentation in ways that
break atmospheric content. NPCs in a room are often referenced in
descriptions ("a guard stands watch here"); aggregation behavior
on NPCs needs to coexist with that.

**Frozen scope:**

1. Phase A: Audit. Identify every command that targets characters,
   NPCs, or both characters and objects. Catalog the resolution
   patterns in use. Document the migration roster.
2. Phase B: Extend the resolver. Add character/NPC scope support
   to `world/helpers/target_resolver.py`. The resolver should
   accept scope hints that include "characters" or "npcs" alongside
   "inventory" and "room".
3. Phase C: Migrate object-targeting + character-capable commands
   per the Phase A roster. Each command:
   - Read existing resolution
   - Replace with `resolve_target(...)` using appropriate scope
   - Run existing tests to verify behavior preservation
   - Update tests if behavior correctly diverges
4. Phase D: Verify display aggregation behavior for NPCs in room
   presentation. Decide based on Phase A.3 audit whether NPCs
   aggregate the same as objects, or have different rules.
5. Phase E: Eliminate any remaining `target-N` suffix that survived
   in mixed-command paths.
6. Phase F: Tests. Add coverage to `tests/test_targeting.py` for
   mixed scopes, character resolution, NPC resolution.
7. Phase G: Live verification with fixtures. Multiple NPCs in a
   room, ordinal targeting, attack/examine/give scenarios.
8. Phase H: Update documentation at
   `docs/architecture/object_presentation.md` to reflect the
   widened scope (rename if appropriate).
9. Phase I: Validation artifact at
   `exports/mt516_mixed_validation.md`.

**Frozen what-not-to-do list:**

- DO NOT modify combat damage calculations, NPC behavior trees,
  social command consequences, or any non-targeting logic in the
  migrated commands. The dispatch is about resolution; the rest
  of each command stays unchanged.
- DO NOT redesign NPC presentation prose. If NPCs already render
  as "a guard stands watch here" in descriptions, that prose stays.
  Aggregation applies to the listing layer, not the prose layer.
- DO NOT change how characters/NPCs are stored, identified, or
  related to rooms. The dispatch consumes existing character/NPC
  data; doesn't restructure it.
- DO NOT extend ordinal targeting beyond what MT-516 shipped. The
  three syntaxes already exist; they just need to apply to
  character scope.
- DO NOT add admin commands for character disambiguation tooling.
- DO NOT modify the existing object-only command migrations from
  MT-516. They're working; leave them alone.
- DO NOT modify NPC creation, spawning, or AI logic.
- DO NOT add new typeclasses for characters or NPCs.
- DO NOT add new test infrastructure beyond what existing tests
  use. Reuse the patterns from MT-516.

**Stop-and-report conditions:**

- If the audit reveals mixed commands have wildly inconsistent
  resolution patterns (some assume single character, some assume
  list, some have custom matching logic for NPC types), stop and
  report. Migration may need to be staged.
- If extending the resolver to character scope conflicts with
  existing character-handling code (e.g., the resolver's noun-
  matching logic doesn't handle character names cleanly), stop
  and report.
- If NPCs in a room have aggregation-relevant differences from
  objects (e.g., they're listed in description prose rather than
  a contents list), stop and report. Aggregation may not apply
  cleanly.
- If migrating a command breaks an existing combat or social test
  in ways that aren't attributable to correct behavioral change,
  stop and report.
- If `look at second goblin` produces unexpected combat-side
  effects (e.g., targeting an NPC for examination accidentally
  marks them as hostile), stop and report. This is the kind of
  subtle interaction the boundary was protecting against.
- If the bounded-time test reveals the extended resolver is slow
  with many characters in scope, stop and report.

## Phase A — Audit

The agent identifies every command that targets characters or NPCs
(or both characters and objects) and that wasn't migrated in MT-516.

### A.1 Likely roster

Suspected targets (the agent verifies against actual code):
- `attack`, `kill`, combat verbs
- `examine`, `look at` (when targeting NPCs)
- `give` (gives item to character)
- `follow`, `unfollow`
- `whisper`, `say to`, social verbs that name a target
- `bow`, `wave`, `nod` and similar emote-with-target
- `point at`, `gesture at`
- `push`, `shove` (if combat-adjacent)
- Healing/empath commands targeting other characters
- Trade/barter commands

### A.2 For each command

Document:
- Current resolution method (Evennia default `caller.search`,
  custom matcher, helper function, etc.)
- Whether it targets only characters, only objects, or both
- Any character-specific filtering (alive/dead, faction, friend/foe)
- Any object-specific filtering (visible, accessible, type)

### A.3 NPC presentation in rooms

Audit how NPCs currently appear in room descriptions:
- Are they in the "you also see" list (objects)?
- Are they in a separate "you see here" list (characters)?
- Are they referenced in the description prose?
- Is there separate `get_display_characters()` logic?

If NPCs have separate listing logic, decide whether aggregation
applies there (probably yes — "3 goblins" is just as natural as
"3 daggers") or whether character listing has different rules
worth preserving.

The Phase D decision depends on this audit.

### A.4 Migration roster

Output: a markdown table in the validation artifact showing each
command, its current resolution method, scope (chars/objects/both),
and whether it migrates in this dispatch.

Some commands may stay unmigrated for good reason (e.g., a command
that uses location-based matching where ordinal targeting doesn't
apply). Document those explicitly.

## Phase B — Extend the resolver

`world/helpers/target_resolver.py` already supports object scopes
(inventory, room, etc.). Extend to support character scope.

### B.1 Add character scope

The resolver's scope vocabulary gains:
- `characters` — characters/NPCs in the caller's location, excluding
  the caller themselves

Possibly:
- `inventory_characters` — characters being carried (rare but valid
  for things like familiars or carried-along NPCs)

### B.2 Filtering

Character scope respects standard visibility:
- Caller can see them (not hidden, not in another room)
- Not the caller themselves (a character can't target themselves
  via the standard resolver — self-targeting is usually a separate
  command form)

### B.3 Combined scopes

Some commands target both characters and objects (`look at`).
The resolver should support scope lists that mix both:

```python
self.resolve_target(phrase, scopes=("characters", "room", "inventory"))
```

The resolver returns whichever match wins by tier-and-scope priority,
regardless of whether it's a character or object. The caller doesn't
need to know in advance which.

### B.4 Tests

Add to `tests/test_targeting.py`:
- `test_resolve_character_in_room` — single character
- `test_resolve_multiple_characters_with_ordinals` — three goblins,
  ordinal targets
- `test_mixed_scope_returns_either` — `look at goblin` and `look at
  dagger` both resolve via the same call
- `test_caller_excluded_from_character_scope` — Jekar typing
  `look at jekar` doesn't self-target via this scope
- `test_character_scope_respects_visibility` — hidden characters
  not resolved

## Phase C — Migrate commands

For each command in the Phase A.4 roster:

### C.1 Pattern

```python
# Before:
target = caller.search(self.args)

# After:
target, _, _, _ = self.resolve_target(
    self.args, scopes=("characters",)  # or ("characters", "room"), etc.
)
```

Adjust scopes per the command's actual targeting needs.

### C.2 Behavior preservation

For each migrated command:
- Run existing tests
- If tests pass, behavior is preserved
- If tests fail, determine if behavior correctly diverges (update
  test) or incorrectly diverges (fix bug)

### C.3 Edge cases

Some commands have custom matching beyond noun matching:
- Faction filtering ("attack first hostile goblin")
- State filtering ("loot first dead corpse")
- Distance filtering ("examine nearest guard")

For v1, the resolver doesn't add new filter dimensions. If a command
needs filtering beyond what the resolver provides, it does the
filtering before or after calling resolve_target. Document any such
cases in the validation artifact.

## Phase D — NPC display aggregation (decision point)

Based on Phase A.3, decide:

**Option D.1: NPCs aggregate same as objects.** "3 goblins stand
watch here." Same display rules; same code path.

**Option D.2: NPCs have separate listing rules.** Maybe they list
individually because each one might have distinguishing features
(name, faction, action). Aggregation applies only when they're
genuinely identical.

**Option D.3: Defer NPC aggregation.** Migrate the targeting (so
ordinals work) but leave display alone for now. This is the most
conservative choice.

The agent picks based on what the audit reveals about how NPCs
currently render. If they're already aggregated implicitly (by
some other code), match that. If they're listed individually,
deciding to aggregate is a content/design choice that should
probably be deferred.

Document the choice in the validation artifact with rationale.

## Phase E — Eliminate residual `target-N` suffix

After Phase C migrations, audit for any remaining `target-N` suffix
in mixed-command output paths. Migrate or override as needed.

If any command still produces `target-N` after migration, that's a
gap. Either:
- Migrate the command to the resolver
- Override the relevant Evennia method in the command's typeclass
- Document the gap if it's not feasible to fix in this dispatch

## Phase F — Tests

Extend existing test files. New tests cover:
- Combat targeting via ordinals
- Social verb targeting via ordinals
- Mixed-scope commands (look at) work for both characters and
  objects
- NPC aggregation behavior per Phase D decision
- No `target-N` in player-facing output across migrated commands

## Phase G — Live verification

Same fixture pattern.

### G.1 Multiple NPC scenario

1. Create a fixture room
2. Spawn 3 identical goblins (or use existing goblin typeclass)
3. Move Jekar to the fixture room
4. Test commands:
   - `look at goblin` — auto-target most-recent
   - `look at first goblin` — ordinal English
   - `look at 2nd goblin` — ordinal numeric-suffix
   - `look at 3.goblin` — numeric positional
   - `attack first goblin` — combat with ordinal (verify no
     unexpected side effects)
5. Capture verbatim outputs

### G.2 Mixed-scope commands

1. In a fixture room with a goblin and a dagger
2. `look at goblin` resolves to goblin
3. `look at dagger` resolves to dagger
4. Both via the same code path

### G.3 Cleanup

Delete fixtures, restore Jekar.

## Phase H — Documentation update

`docs/architecture/object_presentation.md` becomes
`docs/architecture/object_and_character_presentation.md` (or stays
named the same if the agent prefers — agent picks).

Update sections:
- Targeting now applies to characters/NPCs as well
- Examples include character/NPC scenarios
- The Phase D decision documented (NPC aggregation rules)

## Phase I — Validation artifact

`exports/mt516_mixed_validation.md`:

```markdown
# MT-516-mixed validation

Status: SHIPPED

## Phase A — Audit
[Migration roster as a markdown table. Commands and their current
resolution methods, target scopes, migration decision.]

## Phase B — Resolver extension
[Character scope support added. Combined scope support added.
Tests passing.]

## Phase C — Command migration
[Each migrated command, its scope, its test result.]

## Phase D — NPC aggregation decision
[Which option chosen and why.]

## Phase E — target-N elimination
[Any remaining gaps documented.]

## Phase F — Tests
[Test counts, all-passing confirmation.]

## Phase G — Live verification
[Verbatim outputs of fixture scenarios.]

## Phase H — Docs
[Updated documentation location.]

## Final state
[One line summary.]
```

## Verification checklist

1. Audit complete; migration roster documented.
2. Resolver supports character scope alongside object scopes.
3. Mixed-scope (character + object) targeting works through one
   call.
4. All commands in the migration roster either migrated or
   explicitly excluded with rationale.
5. NPC aggregation decision made and documented.
6. No residual `target-N` in migrated command paths.
7. New tests pass; existing tests still pass.
8. Live verification all scenarios green.
9. Documentation updated.
10. Validation artifact complete.
11. No code outside the in-scope list modified.

## Stop conditions

- Edit only:
  - `world/helpers/target_resolver.py` (extend scopes)
  - Commands per the Phase A.4 migration roster
  - `tests/test_targeting.py` (extend tests)
  - Possibly room typeclass for NPC display (per Phase D decision)
  - `docs/architecture/object_presentation.md` (or rename)
  - `exports/mt516_mixed_validation.md` (new)
- Stop and report on inconsistent existing patterns.
- Stop and report on resolver/character-handling conflicts.
- Stop and report on NPC presentation surprises.
- Stop and report on subtle combat/social side effects from
  resolution change.
- Stop and report on bounded-time misses with many characters.
- Stop and report on live verification anomalies.
- Do not modify combat or social logic beyond resolution.
- Do not redesign NPC presentation prose.
- Do not extend ordinal/scope features beyond what's needed.
- Do not chain follow-up fixes within this dispatch.

## Required artifacts

1. Updated `world/helpers/target_resolver.py`
2. Updated commands per migration roster
3. Updated `tests/test_targeting.py`
4. Updated documentation
5. New `exports/mt516_mixed_validation.md`
6. Possibly updated room typeclass for NPC display

## Followup queue

- **MT-515 — Project-wide skill-attempts framework:** Drafts next.

- **Manual trial zone build:** Becomes feasible after MT-515 ships.

- **NPC aggregation v2 (if Phase D deferred):** Revisit NPC display
  aggregation when content shows it's needed.

- **Targeting v2 (deferred from MT-516):** Faction-aware filtering,
  state-aware filtering, distance-aware filtering. Add when
  combat/playtesting reveals the need.

- **Documentation pass:** After MT-515 + trial zone, full docs
  pass on architecture for external adopters.