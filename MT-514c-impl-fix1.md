# MT-514c-impl-fix1 — Forage ability gate fix and failure-attempt XP

## Background

MT-514c-impl shipped the catalog-driven foraging refactor with all
locked decisions encoded and live verification of Phase H.1-H.5.
But Phase H.6 (bounded-time) failed at 115ms warm, and after
shipping, a more important functional bug surfaced in production:

```
> forage
You are not experienced enough.
```

Jekar (admin character with Outdoorsmanship rank 0) cannot attempt
foraging at all in `#4222 Kingshade Street`. The "You are not
experienced enough" message appears to come from the existing
ability-system `can_use` gate, which fires before the catalog
flow runs. The character is being refused at the door.

This blocks foraging entirely for any character with insufficient
skill — including all new characters, who arrive with rank 0 in
most skills.

The user's design intent is broader than this fix:

> Any character should be able to attempt a skill they could
> theoretically learn. Failed attempts at very low levels should
> award a small XP gain to enable natural skill progression.
> Characters who can't learn the skill at all (e.g., wrong-guild
> for guild-gated abilities) should hard-fail with no XP.
>
> Forage is a general (non-guild-gated) skill. Every character
> should be able to attempt it.

The full project-wide principle is queued as MT-515-skill-attempts
(separate arc). This dispatch fixes only foraging — narrow scope,
fast turnaround, validate the pattern in one ability before
generalizing.

User decisions locked for this dispatch:

1. **Failure XP amount:** 25% of successful-attempt XP.
2. **Failure XP applies only to skill-too-low failures.** Weather-
   blocked and generic-no-result failures award no XP.
3. **No guild gate for foraging.** Forage is universal. Every
   character can attempt it.

## Architectural guardrails (READ FIRST)

This is a narrow fix dispatch, not a refactor. The biggest risk
is scope drift into MT-515 territory. Resist that.

The second-biggest risk is touching the broader can_use / ability-
system framework while fixing forage's specific case. The fix
should be local to the forage ability where possible.

**Frozen scope:**

1. Phase A: Diagnose. Read `ForageAbility.can_use()` (or
   equivalent), confirm the cause of "You are not experienced
   enough" for rank-0 Outdoorsmanship characters. Document.
2. Phase B: Remove or relax the forage ability gate so any
   character can attempt forage regardless of Outdoorsmanship rank.
3. Phase C: Verify the three-tier failure messaging fires for
   the previously-blocked rank-0 case (skill-too-low message
   when no catalog items match the character's skill).
4. Phase D: Implement failure XP for skill-too-low failures only.
   25% of successful-attempt XP. Weather-blocked and generic-no-
   result get no XP.
5. Phase E: Update or extend `tests/test_forage.py` to cover the
   new behavior — rank-0 character can attempt, gets failure
   message, gets failure XP.
6. Phase F: Live verification with Jekar specifically (or any
   rank-0 admin character). Type `forage` in the same room
   (`#4222 Kingshade Street`), confirm the fix works.
7. Phase G: Update validation artifact at
   `exports/mt514c_impl_validation.md` to reflect the fix.

**Frozen what-not-to-do list:**

- DO NOT generalize the failure-XP pattern to other abilities.
  That's MT-515-skill-attempts. This dispatch fixes only forage.
- DO NOT modify the ability framework or shared `can_use`
  helpers. If forage's gate lives in a shared helper, the fix
  bypasses or relaxes the gate locally rather than redesigning
  the shared code.
- DO NOT modify other abilities (cast, lockpick, heal, gather
  variants, etc.). Out of scope.
- DO NOT change the catalog schema or content. The 139 items
  ship as-is.
- DO NOT modify weather, invasion, calendar, or terrain modules.
- DO NOT modify the `forage` command argument parsing in ways
  that break existing usage.
- DO NOT modify the `gather` alias. It already works per fix1.
- DO NOT modify the existing 22 unit tests in unrelated ways. Add
  new tests; modify existing tests only if their assumptions
  about can_use behavior need updating.
- DO NOT touch the perf concern (115ms warm timing). That's a
  separate decision (Option 1 vs Option 2 from prior conversation).
  This dispatch focuses on functional correctness.
- DO NOT add admin-only forage commands or testing utilities.
- DO NOT extend three-tier failure messaging into a fourth tier
  or new failure modes. The existing three are correct.

**Stop-and-report conditions:**

- If the can_use gate turns out to be in a shared ability helper
  that's used by abilities outside foraging, stop and report. We
  may need to either (a) bypass the helper specifically for forage,
  or (b) defer the fix to MT-515-skill-attempts where the
  generalization happens.
- If removing the can_use gate breaks any existing tests in ways
  that aren't attributable to correct behavioral change, stop
  and report.
- If the failure-XP path conflicts with the existing skill
  training plumbing (e.g., training only fires on success), stop
  and report. We may need a small change to the training path.
- If Jekar still can't forage after the fix, stop and report.
  Live verification is the gate.
- If the fix surfaces unrelated bugs in foraging (e.g., the
  three-tier messaging doesn't actually distinguish skill-too-low
  from generic), stop and report.

## Phase A — Diagnose

Read `typeclasses/abilities_survival.py` and identify:

1. The `ForageAbility.can_use()` method (or equivalent gate)
2. What rank threshold it currently checks (likely Outdoorsmanship
   rank >= 1 from the legacy implementation)
3. Whether it's calling a shared `can_use` helper or implementing
   the check locally
4. The exact message "You are not experienced enough" and where
   it originates

Write the findings to the validation artifact under "Phase A —
Diagnosis." This anchors the fix in observed behavior, not
assumptions.

## Phase B — Relax the gate

Modify the gate so any character can attempt foraging.

Approach (agent picks based on local code structure):

- **Option B.1:** If the gate is local to `ForageAbility`, remove
  the rank check entirely. Any character with the ability available
  can attempt.
- **Option B.2:** If the gate uses a shared helper, override
  forage's specific behavior to bypass the rank check while leaving
  other abilities' gates intact.

Document the choice and reasoning in the validation artifact.

After the gate change, the forage flow should run for any character
regardless of skill rank. The catalog filter (Phase B step 5 of
the original dispatch) will produce an empty pool if all items
exceed the character's skill, and the three-tier failure path
will fire with the skill-too-low message.

## Phase C — Verify three-tier messaging fires correctly

The skill-too-low message exists per MT-514c-impl. Verify it
actually fires for rank-0 characters in terrain-set rooms after
the gate is relaxed.

Run a local test in `pylanceRunCodeSnippet` or the harness:

```python
# Pseudocode
char = make_character(rank=0)
room = terrain_set_outdoor_room()
result = forage_attempt(char, room, create_items=False)
assert result['status'] == 'failure'
assert result['failure_reason'] == 'skill_too_low'
# Or whatever the actual structure is
```

If skill-too-low isn't firing — if the empty-pool result is being
classified as `generic_no_result` or `weather_blocked` instead —
fix the failure-classification logic.

If the existing three-tier classification is broken in ways that
aren't from this fix, stop and report. We don't widen scope into
fixing pre-existing tier-classification bugs.

## Phase D — Failure XP for skill-too-low

When the forage attempt fails because the character's skill is
too low for any catalog item, award 25% of the successful-attempt
XP to Outdoorsmanship.

### D.1 Identify the success XP value

Read the existing forage success path. Find where it awards XP
on a successful attempt. The XP amount likely scales with item
difficulty, success tier, ranger profession bonus, etc.

Pick a "baseline successful XP" for failure-XP calculation. The
agent picks the right reference point and documents:

- Option D.1.a: Use a fixed baseline (e.g., the XP awarded for
  the lowest-threshold catalog item at neutral conditions)
- Option D.1.b: Use 25% of what the character *would have* earned
  if a hypothetical item had succeeded (more complex, more
  accurate)
- Option D.1.c: Use 25% of the average successful XP for the
  character's effective skill range (compromise between simplicity
  and accuracy)

Lean toward Option D.1.a for simplicity. The number is a starting
value; it can be tuned in playtesting.

### D.2 Award XP only on skill-too-low

Wire the XP award into the failure path:

```python
# Pseudocode
if result['status'] == 'failure':
    if result['failure_reason'] == 'skill_too_low':
        award_skill_xp(char, 'outdoorsmanship', failure_xp_amount)
    # Weather-blocked and generic-no-result: no XP
```

Use the existing `award_skill_xp` (or equivalent) function. Don't
build a new training path.

### D.3 Confirm the XP path doesn't cause regressions

The forage path was already calling skill-training on success
(profiling identified it as the dominant cost in the perf concern).
Adding training on skill-too-low failures may compound that cost.

The agent measures: how does adding failure-XP affect the warm
forage_attempt time? Document. If it pushes warm timing
significantly worse, that's information for the perf decision —
but it doesn't block this dispatch.

## Phase E — Tests

Add to `tests/test_forage.py`:

```python
def test_rank_zero_character_can_attempt_forage(self):
    """Any character can attempt forage regardless of skill rank.

    This is the regression test for the can_use gate bug —
    rank-0 characters were being blocked at the door.
    """
    char = make_character(outdoorsmanship_rank=0)
    room = terrain_set_outdoor_room('forest')
    # Should not raise; should return a result dict
    result = forage_attempt(char, room, create_items=False)
    self.assertIsNotNone(result)

def test_rank_zero_skill_too_low_failure_message(self):
    """Empty pool from skill threshold produces skill-too-low message.

    Three-tier failure messaging should classify this correctly,
    not as generic-no-result.
    """
    char = make_character(outdoorsmanship_rank=0)
    room = terrain_set_outdoor_room('forest')
    result = forage_attempt(char, room, create_items=False)
    self.assertEqual(result['status'], 'failure')
    self.assertEqual(result['failure_reason'], 'skill_too_low')
    # Or whatever the actual key is

def test_failure_xp_awarded_on_skill_too_low(self):
    """Skill-too-low failures award 25% of successful XP.

    Validates the natural-progression path: low-skill characters
    can train Outdoorsmanship by foraging despite zero successes.
    """
    char = make_character(outdoorsmanship_rank=0)
    room = terrain_set_outdoor_room('forest')
    initial_xp = char.get_skill_xp('outdoorsmanship')
    result = forage_attempt(char, room, create_items=False)
    final_xp = char.get_skill_xp('outdoorsmanship')
    self.assertGreater(final_xp, initial_xp)
    # Specific value depends on D.1 choice; assert in a tunable way

def test_weather_blocked_failure_no_xp(self):
    """Weather-blocked failures award NO XP (locked decision)."""
    char = make_character(outdoorsmanship_rank=80)
    room = terrain_set_outdoor_room('forest')
    initial_xp = char.get_skill_xp('outdoorsmanship')
    result = forage_attempt_with_weather(char, room, weather='storm')
    if result['status'] == 'failure' and result['failure_reason'] == 'weather_blocked':
        final_xp = char.get_skill_xp('outdoorsmanship')
        self.assertEqual(final_xp, initial_xp)

def test_generic_failure_no_xp(self):
    """Generic-no-result failures award NO XP (locked decision)."""
    # Setup: character with sufficient skill but bad-luck failure
    # This may require multiple attempts to trigger; iterate or
    # mock the random roll
    char = make_character(outdoorsmanship_rank=80)
    room = terrain_set_outdoor_room('forest')
    initial_xp = char.get_skill_xp('outdoorsmanship')
    # Force generic failure via mocked random or repeated attempts
    result = force_generic_failure_forage(char, room)
    if result['status'] == 'failure' and result['failure_reason'] == 'generic':
        final_xp = char.get_skill_xp('outdoorsmanship')
        self.assertEqual(final_xp, initial_xp)
```

Adapt the test names and assertions to match the actual code
structure. The intent is what matters: rank-0 characters can
attempt, get correct failure message, get failure XP for
skill-too-low only.

## Phase F — Live verification

After implementation, restart the server. The agent connects via
webclient or `evennia shell -c` and verifies:

### F.1 Jekar can attempt forage

1. Connect as Jekar (admin character) in `#4222 Kingshade Street`.
2. Run `forage`.
3. Capture the output. Expected: skill-too-low failure message.
   NOT "You are not experienced enough."
4. Run `forage` 3-5 more times. Confirm consistent behavior.

### F.2 Jekar gains Outdoorsmanship XP

1. Before foraging, capture Jekar's Outdoorsmanship XP.
2. Run `forage` 5 times.
3. Capture XP after.
4. Expected: small but measurable XP gain.

### F.3 Forage still works for skilled characters

1. Use a test character with rank 80 Outdoorsmanship (or set Jekar
   to rank 80 temporarily).
2. Run `forage` in the same room.
3. Expected: successful forage with item returned.
4. Confirm the existing behavior hasn't regressed.

### F.4 No regression in existing scenarios

Re-run the four DireTest scenarios:
- `ranger-forage-scaling`
- `ranger-forage-variation`
- `ranger-resource-visibility`
- `ranger-resource-sell-loop`

All should still pass.

## Phase G — Validation artifact

Update `exports/mt514c_impl_validation.md` with a new section:

```markdown
## fix1 — Forage ability gate relaxed and failure XP added

Status: SHIPPED

Problem identified: Rank-0 characters were blocked from foraging
by the legacy `can_use` gate, producing "You are not experienced
enough" before the catalog flow could run. Jekar in `#4222
Kingshade Street` could not attempt forage at all.

Phase A — Diagnosis: [Where the gate was, what it checked, why
it fired for rank-0 characters.]

Phase B — Gate relaxed: [Approach taken, code changed.]

Phase C — Three-tier messaging: [Verified skill-too-low fires
correctly for rank-0 characters in terrain-set rooms.]

Phase D — Failure XP: [25% of successful-attempt XP awarded for
skill-too-low only. Weather-blocked and generic-no-result award
nothing per locked decision. Implementation choice for "successful
attempt baseline" documented here.]

Phase E — Tests: [Number of new tests added to test_forage.py.]

Phase F — Live verification:
- F.1: Jekar in #4222 can attempt forage — captured: [verbatim]
- F.2: Jekar Outdoorsmanship XP before/after 5 attempts — captured
- F.3: High-skill character still succeeds — captured
- F.4: Existing scenarios still pass

Status: fix1 SHIPPED. Forage is now usable by characters at any
skill level. Skill-too-low failures award XP enabling natural
progression.

Followup queued:
- MT-515-skill-attempts: Generalize the "any character can attempt
  any skill they could theoretically learn" pattern across other
  general-skill abilities (first aid, perception, athletics, etc.).
  Establish guild-gated abilities (cast, lockpick, etc.) as
  hard-fail with no XP. Probably 2-3 dispatches.
```

## Verification checklist

1. Phase A diagnosis documented (where the gate was, what it
   checked).
2. Phase B gate relaxed locally; any character can attempt forage.
3. Phase C three-tier failure messaging fires correctly for rank-0
   characters in terrain-set rooms.
4. Phase D failure XP awarded for skill-too-low only; not for
   weather-blocked or generic-no-result.
5. Phase E new tests added covering all the above.
6. Phase F.1 Jekar can attempt forage live.
7. Phase F.2 Jekar gains XP from failed attempts.
8. Phase F.3 high-skill character still succeeds.
9. Phase F.4 existing scenarios still pass.
10. Validation artifact updated.
11. No code outside the in-scope list modified.

## Stop conditions

- Edit only:
  - `typeclasses/abilities_survival.py` (relax gate, add failure XP)
  - `tests/test_forage.py` (new tests)
  - `exports/mt514c_impl_validation.md` (new section)
  - Possibly `commands/cmd_forage.py` if the gate is reached
    via the command rather than the ability — only if necessary
- Stop and report on shared can_use helper conflicts.
- Stop and report on training-path conflicts.
- Stop and report if Jekar still can't forage after the fix.
- Stop and report on three-tier messaging classification bugs.
- Do not generalize the pattern beyond foraging.
- Do not chase the perf concern in this dispatch.

## Required artifacts

1. Updated `typeclasses/abilities_survival.py`
2. Updated `tests/test_forage.py`
3. Updated `exports/mt514c_impl_validation.md`

## Followup queue

- **MT-514c-impl perf decision:** After fix1 ships, revisit the
  115ms warm timing question. Either accept (Option 1 — gate was
  too tight, real user-facing latency is imperceptible) or queue
  perf follow-up (Option 2 — diagnose skill-award persistence,
  optimize). Decision deferred until fix1 reveals whether failure-
  XP path makes timing worse.

- **MT-515-skill-attempts:** Generalize the design principle
  across the ability system. The pattern locked in this dispatch:
  - General skills: any character can attempt; failed attempts
    at low skill award 25% of successful XP for skill-too-low
    failures only; weather/environment failures and generic-no-
    result failures award no XP.
  - Guild-gated skills: characters of the wrong guild hard-fail
    with a "you can't even begin to attempt this" message and no
    XP.
  - Apply to: first aid, perception, athletics, climbing,
    swimming, and other general skills currently in the codebase.
  - Hard-fail apply to: empath healing (non-empaths), spell
    casting (wrong-guild attempts), lockpicking (non-thief if
    gated), specific guild-locked abilities.
  - Audit existing abilities and document which category each
    falls into.
  - Build a shared "attempt-with-failure-learning" helper for
    consistent implementation.
  - Test coverage for the framework.
  - Likely 2-3 dispatches.

- **Documentation:** After MT-515 ships, document the project-wide
  skill-attempt pattern in `docs/architecture/skill_attempts.md`.
  This becomes a project convention referenced by all future
  ability work.