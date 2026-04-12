# TRAINING GROUNDS TESTING MICROTASKS

Version: SIR-EP v3.0
Status: LOCKED
Scope: Post-implementation validation for TG-100 through TG-105.
Intent: Validate reality against player experience, not just code completion.

## Test Gate Rule

Do not write new Phase 2 feature microtasks.

Do not implement TG-106 through TG-112.

Do not casually patch text in isolation.

Phase 1 must first pass this validation gate.

If any test reveals friction, repetition, hesitation without payoff, or tone drift:

1. update the spec
2. re-implement against the spec
3. re-run the gate

## What This Gate Is Checking

This is not a simple correctness pass.

This gate checks whether the player is pulled forward without hesitation.

It validates:

- command forgiveness
- hesitation escalation
- flow continuity
- cognitive clarity
- message integrity
- edge-case stability

It does not stop at:

- `it works`
- `the state advanced`
- `the test passed`

## Pass / Fail Standard

Phase 1 passes only if:

- the player is never left unsure what to do next
- hesitation produces escalation, not repetition
- alias failures do not create friction spikes
- no dead air persists longer than the intended escalation window
- no step loses forward pull

Phase 1 fails if:

- the same instruction is effectively repeated instead of escalated
- the player is forced to guess MUD verbs without support or hinting
- optional beats become invisible
- transitions feel mechanically correct but emotionally flat

## Test Group 1 - Command Forgiveness

### T1.1 - Sword Pickup Variants

Test:

- `take sword`
- `grab sword`
- `get weapon`

Assert:

- all succeed
- no error text appears
- onboarding progression is identical to `get sword`
- pickup aliases do not produce duplicate or conflicting messaging

Validation:

- Player question: `Can I just take it the way I naturally would?`
- Expected next action: proceed immediately without parser confusion

### T1.2 - Equip Variants

Test:

- `equip sword`
- `wield sword`
- `hold sword`

Assert:

- at least one alias path beyond raw `wield sword` works cleanly
- if `hold sword` is not supported, the redirect is clear and immediate
- onboarding continues without confusion or stall

Validation:

- Player question: `Am I being blocked, or corrected?`
- Expected next action: complete the wield step without trial-and-error loops

## Test Group 2 - Hesitation Escalation

### T2.1 - Idle After Entry

Test:

- do nothing for about 6 to 8 seconds after the opening prompt

Assert:

- guide escalation fires
- the second message is sharper, not merely restated
- if a third escalation exists, it introduces pressure or consequence
- no duplicate `Start moving.` spam appears

Validation:

- Player question: `Why do I need to move now?`
- Expected next action: move east because pressure increased

### T2.2 - Idle At Sword Step

Test:

- reach the sword beat and do not pick up the weapon

Assert:

- escalation occurs
- tone shifts from instruction to pressure
- no repeated `Take one.` phrasing appears verbatim as the escalation strategy
- environmental or situational pressure increases without tone break

Validation:

- Player question: `What happens if I keep standing here?`
- Expected next action: take the sword immediately

### T2.3 - Idle At Equip Step

Test:

- hold the weapon but do not wear or wield properly

Assert:

- guide correction reacts to misuse, not to inaction alone
- escalation reflects `you're doing it wrong` rather than replaying the same instruction
- no dead air persists after the player has clearly stalled

Validation:

- Player question: `What's wrong with how I'm holding this?`
- Expected next action: wear the available gear and wield or equip the sword correctly

## Test Group 3 - Flow Continuity

### T3.1 - Full Run Without Hesitation

Run:

- move
- get
- inventory if prompted
- equip
- attack

Assert:

- no extra idle prompts fire
- no redundant messages appear
- pacing feels continuous
- each beat transitions directly into the next question

Validation:

- Player question at each phase resolves into the next one cleanly
- Expected next action: immediate progression through the full phase chain

### T3.2 - Full Run With Hesitation

Run:

- pause at each phase long enough to trigger escalation

Assert:

- escalation fills gaps without breaking tone
- no dead air longer than the configured escalation threshold persists
- instructions are not duplicated as fallback behavior
- the flow remains coherent under hesitation

Validation:

- Player question: `What happens if I freeze?`
- Expected next action: act because the world got tighter, not because the system got louder

## Test Group 4 - Cognitive Validation

This group is observational.

It exists to prevent technically correct but psychologically flat implementations.

### T4.1 - Player Question Tracking

After each phase, record what the player is most likely thinking.

Required mapping:

- Entry: `What is this place?`
- Move: `What's next?`
- Get: `What is this for?`
- Equip: `Am I using this right?`
- Combat: `Can I do this?`

Assert:

- each question naturally leads to the next action
- no phase answers too much and collapses forward pull

### T4.2 - Friction Detection

Log:

- where the player hesitates
- where the player tries the wrong command
- where the player rereads or appears to stall

Assert:

- hesitation stays under roughly 2 seconds per step in the ideal path
- no confusion loops appear
- wrong-command recovery is immediate and clear

## Test Group 5 - Message Integrity

### T5.1 - No Repetition

Search captured output for:

- identical instruction lines repeated verbatim as fallback prompting

Assert:

- none exist where escalation should have happened

### T5.2 - Escalation Pattern Integrity

Verify the actual sequence is:

- instruction
- reinforcement
- pressure

Assert:

- all three exist where hesitation is expected
- the system does not skip straight to pressure too early
- the system does not remain stuck at reinforcement forever

## Test Group 6 - Edge Cases

### T6.1 - Player Spam Commands

Test:

- spam unrelated or invalid commands during onboarding

Assert:

- guard logic holds
- responses stay consistent
- onboarding state does not break or drift
- the player is redirected, not buried in error noise

### T6.2 - Wrong-Direction Movement

Test:

- attempt to move in the wrong direction mid-step

Assert:

- the move is blocked cleanly
- the redirect is clear
- the player is not punished with state corruption or confusing extra text

## DireTest Targets For Phase 1

At minimum, add or validate these automated scenarios in `diretest.py`:

- `training-move`
- `training-get`
- `training-equip`
- `training-equip-alias`
- `training-inventory-skip-nudge`

The automated scenarios should protect:

- exact copy for required lines
- alias behavior where locked
- escalation behavior where deterministic
- correct onboarding step transitions
- absence of duplicate fallback messaging

## Manual Review Output Format

For each test group, record:

- `PASS` or `FAIL`
- where the player hesitated
- what line fired next
- whether the next action became more obvious or less obvious

If a test fails, record:

- what the player likely thought
- which line or command created the break
- whether the fix belongs in spec, code, or both

## Exit Condition

You may proceed to TG-106 through TG-112 only when:

- command forgiveness is clean
- hesitation escalation is real and non-repetitive
- Phase 1 full runs feel continuous
- cognitive validation matches the intended question chain
- message integrity confirms escalation instead of duplication

If that bar is not met, Phase 1 is not done.