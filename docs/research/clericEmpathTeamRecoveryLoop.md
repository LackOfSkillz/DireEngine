# Cleric / Empath Team Recovery Loop

Status: Locked handoff packet
Range: CLERIC/EMPATH 201-268
Intent: Make the death -> corpse prep -> resurrection -> post-res recovery loop match the team responsibilities already established in the system contract.

## Core Contract

Death
-> Corpse forms with real wound state
-> Corpse deteriorates spiritually over time
-> Cleric can pause or slow spiritual deterioration
-> Empath extracts physical wound burden from corpse
-> Empath may need multiple passes
-> Empath can self-heal between passes
-> Cleric may need to re-stabilize during prep
-> When corpse is physically survivable, cleric resurrects
-> Cleric role ends
-> Empath finishes post-res healing

## Non-Negotiable Rules

- Cleric controls time.
- Empath controls survivability.
- Favor > 0 allows resurrection attempt.
- Favor = 0 blocks resurrection and forces release.
- Rushing resurrection before corpse is physically survivable can cause re-death.

## Phase 1 Patch Contract (CLERIC/EMPATH 201-228)

### Phase Goal

Implement the core contract only:

- corpse holds true wounds
- empath modifies corpse
- cleric stabilizes time, not wounds
- resurrection uses corpse state
- favor gates resurrection
- outcome depends on prep quality

### Hard Rules (Enforce Before Start)

Aedan must not:

- add new mechanics
- tune numbers
- introduce randomness
- improve design

Aedan must:

- implement exactly what is specified
- stop if existing code conflicts with instructions

## Patch Group A - Corpse = Source Of Truth

### CLERIC/EMPATH-201 - Snapshot Wounds On Death

File: `typeclasses/characters.py` death handler

Add:

```python
corpse.db.wounds = deepcopy(self.db.wounds)
```

Requirements:

- must include all wound components
- vitality burden
- bleeding
- internal
- per-body-part values if present

### CLERIC/EMPATH-202 - Detach Player From Wound Authority

Modify after death:

- `self.db.wounds = None`

Or mark as inactive:

- `self.db.wounds_source = "corpse"`

Rule:

- player wounds must not drive post-res state

### CLERIC/EMPATH-203 - Add Corpse Wound Accessor

Add centralized helper:

```python
def get_corpse_wounds(corpse):
    return corpse.db.wounds
```

Usage:

- empath commands
- cleric checks
- assess logic

## Patch Group B - Split Systems (Physical vs Spiritual)

### CLERIC/EMPATH-204 - Add Spiritual State To Corpse

Add:

- `corpse.db.spiritual_decay_stage = 0`
- `corpse.db.spiritual_decay_progress = 0`
- `corpse.db.spiritual_stabilized_until = 0`

### CLERIC/EMPATH-205 - Enforce Separation Of Concerns

Audit and fix.

Ensure:

- empath code only touches `corpse.db.wounds`
- cleric code only touches spiritual fields

Remove any logic where:

- cleric heals wounds
- empath pauses decay

### CLERIC/EMPATH-206 - Add Explicit Comments

At top of corpse logic:

```python
# SYSTEM CONTRACT:
# Physical survivability (wounds) is controlled by empaths.
# Spiritual stability (decay) is controlled by clerics.
# These systems must NEVER modify each other.
```

## Patch Group C - Empath Modifies Corpse

### CLERIC/EMPATH-207 - Enable Corpse Targeting In Empath Commands

Modify in all empath abilities:

```python
if target.is_corpse:
    wounds = target.db.wounds
```

### CLERIC/EMPATH-208 - Apply Transfer To Corpse, Not Player

Replace any:

```python
target.db.wounds -= X
```

With:

```python
corpse.db.wounds[part] -= amount
empath.db.wounds[part] += amount
```

### CLERIC/EMPATH-209 - Ensure Bleed Reduction Persists

Validate:

After:

```text
> take bleeding all
```

Must result in:

- `corpse.db.wounds["bleeding"]` decreases
- not just messaging

### CLERIC/EMPATH-210 - Add Multi-Pass Capability

Ensure empath actions:

- do not lock corpse
- do not mark corpse complete
- allow repeated interaction

## Patch Group D - Cleric Controls Time (Not Healing)

### CLERIC/EMPATH-211 - Add Stabilization Effect

File: cleric command handler

Add:

```python
corpse.db.spiritual_stabilized_until = current_time + STABILIZE_DURATION
```

### CLERIC/EMPATH-212 - Ensure Stabilization Does Not Affect Wounds

Remove any code like:

```python
corpse.db.wounds["bleeding"] -= X
```

Rule:

- cleric cannot heal physical damage

### CLERIC/EMPATH-213 - Allow Repeated Stabilization

Ensure calling stabilize again:

- extends or refreshes `stabilized_until`

Not:

- blocked
- ignored

### CLERIC/EMPATH-214 - Add Decay Pause Check

Add helper:

```python
def is_spirit_stable(corpse):
    return current_time < corpse.db.spiritual_stabilized_until
```

## Patch Group E - Resurrection Contract

### CLERIC/EMPATH-215 - Enforce Favor Gate

Modify:

```python
if player.favor <= 0:
    return FAIL
```

Else:

- allow resurrection

No randomness.

### CLERIC/EMPATH-216 - Restore Player From Corpse State

Critical replace:

```python
player.db.wounds = deepcopy(corpse.db.wounds)
```

Remove any:

- cached wounds
- pre-death wounds
- safe defaults

### CLERIC/EMPATH-217 - Remove Hidden Healing On Resurrection

Search and delete:

- bleed resets
- vitality resets
- internal resets
- revive quality healing

### CLERIC/EMPATH-218 - Add Revive Protection Tick

Add:

- `player.db.just_revived = True`
- `player.db.revive_protection_ticks = 1`

### CLERIC/EMPATH-219 - Modify Death Check

Add:

```python
if player.db.just_revived and player.db.revive_protection_ticks > 0:
    skip death check
```

Then decrement each tick.

### CLERIC/EMPATH-220 - Ensure Normal Damage Resumes

After protection:

- bleed and internal damage tick normally
- no suppression

## Patch Group F - Survival Logic

### CLERIC/EMPATH-221 - Add Physical Survivability Function

Add:

```python
def is_physically_survivable(wounds):
    return (
        wounds["bleeding"] < 15 and
        wounds["internal"] < 20 and
        wounds["vitality"] < 80
    )
```

Temporary values only.

### CLERIC/EMPATH-222 - Classify Post-Res State

After resurrection:

```python
if is_physically_survivable(wounds):
    state = "STABLE"
else:
    state = "CRITICAL"
```

### CLERIC/EMPATH-223 - Do Not Auto-Kill On Resurrection

Ensure:

- even if lethal, player survives at least the initial tick
- then dies via normal progression

### CLERIC/EMPATH-224 - Ensure Re-Death Is Natural

Validate re-death must come from:

- bleed ticks
- internal damage

Not:

- forced death event
- instant kill

## Patch Group G - Validation Tests

### CLERIC/EMPATH-225 - Bad Prep Test

Scenario:

- corpse not stabilized physically
- resurrection
- player dies within a few ticks

Expected: pass

### CLERIC/EMPATH-226 - Good Prep Test

Scenario:

- corpse below survivable threshold
- resurrection
- player survives

Expected: pass

### CLERIC/EMPATH-227 - Borderline Test

Scenario:

- corpse near threshold
- resurrection
- player unstable but not instant death

Expected:

- survives briefly
- requires intervention

### CLERIC/EMPATH-228 - No Favor Test

Scenario:

- favor = 0
- resurrection attempt
- fail
- must release

Expected: pass

### Completion Check

System is correct only if:

1. corpse holds real wounds
2. empath reduces corpse wounds
3. cleric cannot heal wounds
4. resurrection uses corpse state
5. favor gates resurrection
6. good prep equals survival
7. bad prep equals re-death
8. no favor equals fail

Do not proceed to CLERIC/EMPATH 229+ until all four validation tests pass consistently.

## Patch Group H - Post-Res Survival Loop

### CLERIC/EMPATH-229 - Make Post-Res State Land In One Of Three Bands

After resurrection, classify patient:

- Stable: survives without urgent intervention
- Critical: survives briefly but needs immediate empath care
- Lethal: likely re-dies quickly

### CLERIC/EMPATH-230 - Define Post-Res Care Window Explicitly

Implement a measurable window for critical cases.
Goal:

- enough time for coordinated empath action
- not enough time to ignore the problem

### CLERIC/EMPATH-231 - Ensure Poor Prep Can Re-Die Naturally

If corpse was resurrected too early:

- player can die again through normal wound progression

### CLERIC/EMPATH-232 - Ensure Good Prep Survives Reliably

If corpse crossed the physical stable threshold before resurrection:

- player should not re-die from the same burden immediately

### CLERIC/EMPATH-233 - Keep Empath Useful After Resurrection

Post-res empath actions should remain necessary for:

- finishing bleed reduction
- reducing remaining vitality burden
- preventing delayed collapse

### CLERIC/EMPATH-234 - Make Cleric Effectively Done After Resurrection

After successful resurrection:

- cleric's primary role ends
- empath owns recovery

Unless future design adds advanced cleric aftercare.

## Patch Group I - Thresholds And Bands

### CLERIC/EMPATH-235 - Define Physical Stable Threshold Numerically

Create initial thresholds for:

- bleeding
- internal
- vitality burden

This is the line below which re-death should not occur from the same corpse burden.

### CLERIC/EMPATH-236 - Define Critical Threshold Numerically

This is the band where:

- resurrection succeeds
- player returns unstable
- empath must act quickly

### CLERIC/EMPATH-237 - Define Lethal Threshold Numerically

This is the band where:

- resurrection succeeds if favor exists
- but player is very likely to re-die if rushed

### CLERIC/EMPATH-238 - Keep Thresholds Centralized

Do not scatter magic numbers.
Put thresholds in one config or helper module.

### CLERIC/EMPATH-239 - Add Helper Names That Reflect Actual Semantics

Because higher `vitality` is worse in this codebase, rename internally where practical or comment aggressively to avoid confusion.

## Patch Group J - Multi-Actor Coordination

### CLERIC/EMPATH-240 - Support Two-Empath Corpse Prep Properly

Multiple empaths should be able to contribute sequentially or cooperatively.

### CLERIC/EMPATH-241 - Prevent Duplicate-Transfer Corruption

Ensure two empaths do not overwrite or double-count corpse wound changes.

### CLERIC/EMPATH-242 - Add Coordination-Safe Messaging

Examples:

- "Another empath may still help."
- "This body has been pushed as far as your hands can take it."

### CLERIC/EMPATH-243 - Preserve Cleric And Empath Role Clarity In Group Messaging

Messages should make clear whether failure is due to:

- spirit instability
- physical lethality
- insufficient prep time
- empath strain

## Patch Group K - Release And Hard Death Path

### CLERIC/EMPATH-244 - Lock Release Path When Favor Is Zero

If no favor:

- resurrection fails
- player must release spirit

### CLERIC/EMPATH-245 - Implement Heavy XP Regression On Release

Attach this to release, not to successful resurrection.

### CLERIC/EMPATH-246 - Implement Coin Loss On Release

On release:

- drop or remove coins carried at death according to your design

### CLERIC/EMPATH-247 - Implement Gear Loss Rules On Release

If you want partial gear loss:

- define the exact rule now
- implement it in release path only

### CLERIC/EMPATH-248 - Keep Resurrection Path Lighter Than Release Path

Successful resurrection should still carry sting and penalties, but much less severe than forced release.

## Patch Group L - Messaging

### CLERIC/EMPATH-249 - Update Cleric Messaging To Reflect Team Loop

Examples:

- "The spirit is held, but the body is not yet ready."
- "The body's pattern is steady for now."
- "Its spiritual hold is slipping again."

### CLERIC/EMPATH-250 - Update Empath Messaging To Reflect Corpse Prep Progress

Examples:

- "This body remains too damaged to survive the return."
- "This body may survive, but only barely."
- "This body should survive the return."

### CLERIC/EMPATH-251 - Update Patient Ghost Messaging

Ghost or player should feel:

- when body is being prepared
- when spirit is stabilized
- when decay worsens
- when return is risky

### CLERIC/EMPATH-252 - Add Resurrection Outcome Messaging Bands

Examples:

- clean return
- unstable return
- perilous return

Without implying physical safety if it is not present.

## Patch Group M - DireTest Coverage

### CLERIC/EMPATH-253 - Add Iterative Prep Scenario

Test:

- corpse deteriorates
- cleric stabilizes
- empath preps
- stabilization lapses
- cleric re-stabilizes
- empath finishes
- resurrection succeeds
- patient survives

### CLERIC/EMPATH-254 - Add Rushed-Res Scenario

Test:

- favor present
- cleric resurrects too early
- patient re-dies

### CLERIC/EMPATH-255 - Add Good-Team Scenario

Test:

- repeated cleric stabilization
- multi-pass empath prep
- resurrection after stable threshold
- patient survives

### CLERIC/EMPATH-256 - Add Low-Rank Empath Scenario

Test:

- one low-rank empath hits strain cap
- cannot fully prepare alone in one pass
- must self-heal and return or needs second empath

### CLERIC/EMPATH-257 - Add Multi-Empath Assist Scenario

Test:

- one empath cannot finish
- second empath contributes
- corpse becomes survivable
- resurrection succeeds cleanly

### CLERIC/EMPATH-258 - Add Decay-Pressure Scenario

Test:

- if cleric stops stabilizing, spiritual decay worsens during empath prep

### CLERIC/EMPATH-259 - Add Zero-Favor Hard-Fail Scenario

Test:

- perfect corpse prep
- no favor
- resurrection blocked
- release required

### CLERIC/EMPATH-260 - Add Post-Res Continued-Healing Scenario

Test:

- corpse only brought to critical-not-stable
- resurrection succeeds
- empath keeps healing
- patient survives because post-res care is timely

## Patch Group N - Harness And Reporting

### CLERIC/EMPATH-261 - Update Full Death-To-Res Harness To Reflect Iterative Loop

Harness must support:

- repeated cleric stabilize actions
- repeated empath prep passes
- empath self-heal phase
- optional second empath

### CLERIC/EMPATH-262 - Log Both Decay And Physical Bands Separately

Every run should report:

- spiritual decay band
- physical survivability band

### CLERIC/EMPATH-263 - Add Why-Did-This-Fail Classifier

Classify failures as:

- no favor
- rushed resurrection
- insufficient physical prep
- spiritual lapse
- empath strain ceiling
- post-res care failure

### CLERIC/EMPATH-264 - Add Effort-Cost Metrics For Team Loop

Log:

- number of cleric stabilization cycles
- number of empath prep cycles
- number of self-heal cycles
- time to safe resurrection

### CLERIC/EMPATH-265 - Add Safe-To-Res Marker To Reports

Explicitly log the moment the corpse crosses survivable threshold.

## Patch Group O - Implementation Safety

### CLERIC/EMPATH-266 - Remove Stale Summary Language In Logs And Tests

Update any old report text that still says re-death proves the system is broken.

### CLERIC/EMPATH-267 - Audit For Hidden One-Step Assumptions

Search for logic that assumes:

- one stabilization
- one empath pass
- one clean linear sequence

Replace with iterative-safe logic.

### CLERIC/EMPATH-268 - Add Inline Comments At Contract Boundaries

In code, comment:

- what cleric owns
- what empath owns
- what favor controls
- what causes re-death

## Acceptance Criteria

Aedan is done only when these are true:

1. Corpses deteriorate spiritually over time.
2. Clerics can repeatedly pause that deterioration.
3. Empaths can repeatedly reduce physical burden across multiple passes.
4. Favor > 0 allows resurrection attempt every time.
5. Favor = 0 blocks resurrection and forces release.
6. Rushed resurrection can re-die.
7. Properly prepared resurrection survives.
8. Borderline resurrection survives only with immediate post-res empath care.
9. Logs and DireTests reflect the iterative team loop, not a one-pass loop.

## Suggested Implementation Order

Have Aedan do these in this order:

1. Patch Groups A-E
2. Then Patch Groups F-G
3. Then Patch Groups H-I
4. Then Patch Groups J-M