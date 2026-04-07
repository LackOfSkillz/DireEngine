# TRAINING GROUNDS MICROTASKS

Version: SIR-EP v3.0
Status: LOCKED
Intent: Replace "tutorial checklist" thinking with a controlled player-lifecycle simulation that teaches systems through lived moments.

## Core Frame

The onboarding flow is not a sequence of lessons.

It is a controlled simulation of the first player arc:

1. arrival
2. preparation
3. first action
4. first success
5. first growth
6. first failure
7. recovery
8. safety net
9. release

If a beat explains itself like a tutorial, it is wrong.

If a beat creates forward pull and teaches a system as a side effect, it is correct.

## Global Execution Rule

This is not a feature implementation document.

This is a controlled experience pipeline.

Every task must preserve:

1. Forward momentum: each step must create the next question.
2. Single-focus interaction: one concept per step.
3. Emotional continuity: no abrupt tone or pacing breaks.
4. Zero ambiguity in player action.

If any task introduces:

- confusion
- delay without purpose
- redundant messaging
- system explanation without context

it must be rejected or revised.

## Hard Rules

- No branching in the required critical path.
- No randomness in onboarding-critical outcomes.
- No extra dialogue beyond the locked lines for each beat.
- No system-dump explanations.
- No repeated lessons.
- Every beat must leave a question unanswered just long enough to pull the player forward.
- Returning players must be able to bypass the entire sequence without friction.

## Current Code Alignment

The current repo already provides part of this flow:

- account-level chargen finalization in `systems/chargen/` and `systems/character/creation.py`
- room-based onboarding state in `systems/onboarding.py`
- onboarding guide delivery in `typeclasses/onboarding_guide.py`
- onboarding room bootstrap in `server/conf/at_server_startstop.py`
- first-area threshold handoff in `systems/first_area.py`
- exact-text DireTest coverage for the current narrow onboarding slice in `diretest.py`

This phase expands the current onboarding from:

- move
- get sword
- attack dummy

into the full training-grounds arc:

- move
- take gear
- inspect inventory
- wear / wield
- controlled combat
- experience awareness
- scripted lethal escalation
- recovery / healing
- depart safety net
- release

## Phase Map

### Phase 0 - Entry Hook

Player question:

`Where am I?`

Teaches:

- controlled arrival
- immediate forward motion

Forward pull:

`What happens if I move?`

### Phase 1 - Movement

Player question:

`Why do I need to move?`

Teaches:

- navigation
- exit use

Forward pull:

`What am I supposed to take?`

### Phase 2 - Possession

Player question:

`What is this for?`

Teaches:

- item pickup
- inventory awareness

Forward pull:

`Am I using it correctly?`

### Phase 3 - Preparation

Player question:

`Is holding it enough?`

Teaches:

- wearing gear
- wielding gear
- inventory confirmation

Forward pull:

`Now what do I do with it?`

### Phase 4 - Controlled Combat

Player question:

`Can I actually use this?`

Teaches:

- attack
- first successful impact

Forward pull:

`Did that matter?`

### Phase 5 - Learning

Player question:

`Am I getting better?`

Teaches:

- experience visibility
- progression awareness

Forward pull:

`What happens when the danger is real?`

### Phase 6 - Escalation

Player question:

`What happens when it fights back?`

Teaches:

- real combat pressure
- loss expectation

Forward pull:

`What happens if I lose?`

### Phase 7 - Failure

Player question:

`Did I just die?`

Teaches:

- the world can beat you
- failure is part of the loop

Forward pull:

`Am I still in this?`

### Phase 8 - Recovery

Player question:

`What happens after death?`

Teaches:

- resurrection or recovery flow
- healing
- condition awareness

Forward pull:

`How do I save myself next time?`

### Phase 9 - Safety Net

Player question:

`What if nobody is here to help me?`

Teaches:

- depart
- favor / return awareness

Forward pull:

`If I can survive failure, where do I go now?`

### Phase 10 - Release

Player question:

`What now?`

Teaches:

- world release
- agency after compression

Forward pull:

`What happens in the world outside?`

## Locked Experience Copy

### TG-000 - Intake Rewrite

Replace the Intake Chamber description with:

Lantern light settles across slate floors scored with old lines, as if many have stood here before you and been measured the same way.

The air smells faintly of oil and leather.

A lone figure waits, watching.

The only open path leads east.

### TG-001 - Guide First Line

Locked guide output:

"You're awake. Good."

Pause.

"Start moving."

`(Type east or click the exit.)`

Rule:

- No explanation.
- Only forward motion.

## Implementation Microtasks

### TG-100 - Reframe Onboarding State Machine

Update the onboarding step model in `systems/onboarding.py` to represent the full training arc.

Required locked steps:

- `start`
- `movement`
- `possession`
- `preparation`
- `combat`
- `learning`
- `failure`
- `recovery`
- `depart`
- `complete`

Done when:

- onboarding state can express every required beat without overloading one step with multiple meanings
- current helper functions and blocked-command logic still operate on the expanded model

Validation:

- Player question: `What am I supposed to do first?`
- Expected next action: move east with no hesitation about the critical path

### TG-101 - Rewrite Intake Chamber Hook

File targets:

- `server/conf/at_server_startstop.py`
- `systems/onboarding.py`

Changes:

- replace the existing Intake Chamber description with the locked rewrite
- ensure first guide dialogue uses the locked opening lines
- keep only one obvious path forward
- if the player issues an invalid early command during the first beat, the redirect must be specific: `Not yet. Start by moving east.`
- after the opening movement beat, generic redirect language may resume

Done when:

- room text and first guide delivery match the locked copy exactly

Validation:

- Player question: `What happens if I go?`
- Expected next action: type `east` or click the only obvious exit

### TG-102 - Training Hall Escalation

File targets:

- `server/conf/at_server_startstop.py`
- `systems/onboarding.py`

On entering Training Hall:

- set `onboarding_step = "movement"`

Replace or confirm room description as:

The space opens slightly--less confined, but no less controlled.

Racks line the wall. Nothing decorative. Nothing wasted.

Guide prompt:

"You'll need something in your hands."

A small nod toward the rack.

"Take one."

`(Type get sword)`

Pickup target rules:

- the sword must support aliases that include `sword`, `weapon`, and `training sword`
- parser normalization must preserve `take` -> `get`
- parser normalization must preserve `grab` -> `get`

Done when:

- room entry advances state cleanly
- exact prompt text is emitted once

Validation:

- Player question: `Why do I need this?`
- Expected next action: attempt `get sword`, `take sword`, `grab sword`, or click the visible item

### TG-103 - Possession Beat

File targets:

- `systems/onboarding.py`
- `commands/cmd_get.py`

Locked pickup response:

The weight settles into your grip--unfamiliar, but not entirely foreign.

Inventory hint immediately after:

You adjust your hold, testing the balance.

`(Type inventory to see what you're carrying.)`

Advance state to:

- `preparation`

Done when:

- generic pickup spam is suppressed for the onboarding weapon
- the new inventory hint is delivered as part of the curated beat

Validation:

- Player question: `What do I do with this?`
- Expected next action: inspect inventory or attempt to use the item correctly

### TG-104 - Inventory Beat

File targets:

- `systems/onboarding.py`
- `commands/cmd_inventory.py`

Requirements:

- allow `inventory`, `inv`, and `i` inside onboarding
- if player uses inventory during the preparation beat, treat it as acknowledged but do not block progress if they proceed without it
- onboarding should track whether the player has seen inventory once
- if the player does not type inventory within about 6 seconds of the possession beat, emit this reinforcement nudge:

The guide glances at what you're holding.

"Know what you carry."

Rule:

- this is a hint, not a hard gate

Done when:

- onboarding can detect the first inventory check and use it for narrative reinforcement or test coverage

Validation:

- Player question: `What am I actually carrying right now?`
- Expected next action: type `inventory`, `inv`, or `i`

### TG-105 - Preparation / Equip Beat

File targets:

- `systems/onboarding.py`
- `server/conf/at_server_startstop.py`
- equipment command surfaces that handle `wear` and `wield`

Guide lines:

The guide watches your grip for a moment.

"That'll slow you down."

A slight shake of the head.

"Wear what you can. Carry it properly."

Enable during onboarding:

- `wear`
- `wield`
- `equip` if it can be cleanly normalized

Command clarity rule:

- preferred behavior: map `equip sword` to the same result as `wield sword`
- if full alias support is not cleanly possible, the onboarding prompt for this beat must include a direct wield hint instead of assuming MUD verb knowledge

Required onboarding starter gear:

- a wearable armor piece or equivalent training gear must exist in the controlled room
- the training sword must be wieldable

Transition tension line before combat:

The space ahead is marked more heavily--strikes, impact, repetition.

Locked equip response:

The fit is rough, but it settles into place.

Done when:

- player can complete one wear and one wield action in onboarding
- generic equipment output is either acceptable or suppressed in favor of the locked response
- state advances to `combat`

Validation:

- Player question: `Am I using this right?`
- Expected next action: wear the available gear and wield or equip the training sword

### TG-106 - Controlled Combat Beat

File targets:

- `systems/onboarding.py`
- `commands/cmd_attack.py`
- `server/conf/at_server_startstop.py`

Training dummy intro text:

A training dummy stands ahead, scarred from repeated impact.

Guide lines:

"It won't fight back."

A pause.

"That's not the point."

`(Type attack dummy)`

Locked first-hit feedback:

You strike the dummy.

The impact travels back through your arms--rough, imperfect, real.

The structure shudders but holds.

Something clicks. Not mastery. Not even skill.

Just the beginning of it.

Done when:

- onboarding dummy combat still bypasses noisy generic combat output
- successful hit advances state to `learning`

### TG-107 - Learning Beat

File targets:

- `systems/onboarding.py`
- `commands/cmd_experience.py`

Locked output after first dummy success:

That moment lingers.

Not skill. Not yet.

But something closer to it.

`(Type exp to review your experience.)`

Requirements:

- allow `exp` and `experience` during onboarding
- onboarding should record whether the player checked experience at least once
- this is a prompted beat, but it should not become a long report explanation

Done when:

- the player can see progression feedback before the lethal escalation begins

### TG-108 - Real Escalation Trigger

File targets:

- `systems/onboarding.py`
- `server/conf/at_server_startstop.py`
- any supporting script or NPC typeclass needed for a deterministic breach event

Trigger:

- on entering the yard after the learning beat, or after a short deterministic delay

Locked scene intro:

The noise reaches you first.

Shouting. Metal. Something breaking.

By the time you see it, it's already too close.

Rules:

- the enemy must be real
- the encounter must be unwinnable
- the loss must resolve quickly
- the player must feel outmatched, not punished for using the wrong command

Done when:

- escalation always occurs the same way
- failure is deterministic

### TG-109 - Failure Beat

File targets:

- `systems/onboarding.py`
- combat or death hooks that currently emit defeat text

Locked collapse output:

The world tilts.

Sound pulls away first.

Then everything else follows.

Rule:

- do not emit a blunt `you are dead` onboarding message in this scene

Done when:

- onboarding failure uses the locked collapse copy instead of generic death messaging

### TG-110 - Recovery Beat

File targets:

- `systems/onboarding.py`
- healing / recovery hooks
- `server/conf/at_server_startstop.py`

Required NPC recovery lines:

Empath:

"Easy. Don't fight it."

Optional cleric if used:

"You're not finished."

Locked recovery output:

The worst of the damage fades.

Stats hint:

`(Type stats to check your condition.)`

Requirements:

- the player must experience healing or restored condition
- `stats`, `health`, and `hp` must be allowed during this beat
- onboarding should record first stats check

Done when:

- recovery teaches both survival and condition visibility

### TG-111 - Depart Safety-Net Beat

File targets:

- `systems/onboarding.py`
- `commands/cmd_depart.py`

Locked lines:

"If you're left like that--alone--"

"There are ways back."

`(Type depart if needed.)`

Requirements:

- onboarding must explain depart in-world, not as a manual page
- if possible, expose `depart preview` or equivalent safely during onboarding without requiring another death

Done when:

- the player leaves knowing a return mechanism exists

### TG-112 - Release Beat

File targets:

- `systems/onboarding.py`
- `typeclasses/onboarding_guide.py`
- `server/conf/at_server_startstop.py`
- `systems/first_area.py`

Locked final guide lines:

The guide studies you briefly.

"You'll survive."

"That's enough."

"Go."

Release behavior:

- move player to `Outer Yard`
- set `onboarding_step = "complete"`
- preserve starter equipment and healed state

Done when:

- release into the threshold zone feels like the first exhale after compression

## Ripcord Tasks

### TG-R1 - Add Skip Command

Add:

- `skiptraining`

Intent:

- immediate bypass for returning players

File targets:

- new command file if needed
- `commands/default_cmdsets.py`
- onboarding state helpers

### TG-R2 - Add Early In-World Skip Prompt

Add a single early line from the guide:

"If you've done this before--say so."

Rules:

- it must not interrupt the main opening beat
- it must appear early enough that returning players are not dragged through movement and gear again

### TG-R3 - Skip Behavior

Skip must:

- teleport player to `Outer Yard`
- grant starter gear appropriate to the current finalized character
- mark onboarding complete
- avoid penalties or nags

Done when:

- experienced players can skip cleanly with zero friction

## Command Surface Changes

The onboarding allow-list must expand from its current narrow set.

Required additions:

- `inventory`
- `inv`
- `i`
- `wear`
- `wield`
- `experience`
- `exp`
- `stats`
- `health`
- `hp`
- `depart`

Each command must only be allowed during the beat where it matters or after it has been introduced.

Rule:

- allowing a command is not enough
- the onboarding state must know whether its beat has been seen so copy and tests stay deterministic

## Room / Content Changes

The existing three-room onboarding slice is too small for the full player arc.

Required structural additions or repurposes:

- Intake Chamber
- Training Hall
- Preparation beat support in the same hall or a dedicated staging room
- Practice Yard or breach yard for escalation
- Recovery location or scripted recovery reset point

Minimum content additions:

- wearable starter armor or equivalent
- wieldable starter weapon
- deterministic breach enemy
- recovery NPC presence such as empath and optional cleric

## Data / State Tasks

The onboarding state payload must track at minimum:

- current step
- completed beats
- whether inventory was checked
- whether equipment was worn
- whether weapon was wielded
- whether experience was checked
- whether stats were checked
- whether depart guidance was shown
- whether skiptraining was used

Rule:

- state names should reflect beats, not raw commands, wherever possible

## DireTest Requirements

Extend `diretest.py` with locked scenarios:

- `training-move`
- `training-get`
- `training-equip`
- `training-equip-alias`
- `training-combat`
- `training-exp`
- `training-death`
- `training-recovery`
- `training-depart`
- `training-skip`
- `training-inventory-skip-nudge`

Each scenario must assert exact copy for the beat it protects.

At minimum:

- exact room text where the beat begins
- exact guide or NPC dialogue for the beat
- exact curated reinforcement line
- correct onboarding step transition
- correct inventory / state side effects

Regression retention:

- keep the current first-area tests
- add at least one end-to-end onboarding-to-first-area pass after the full training flow lands

## Recommended Execution Order

1. Expand the onboarding state machine and command allow-list.
2. Add the preparation beat with real wear / wield support.
3. Add the experience check beat.
4. Implement deterministic lethal escalation.
5. Implement recovery and stats awareness.
6. Add depart guidance.
7. Add skiptraining and skip path validation.
8. Rewrite DireTests to lock the whole training arc.
9. Re-run the first-area suite to confirm release continuity.

## Phase Gate

Before TG-106 through TG-112 proceed, Phase 1 must clear the locked validation gate in `trainingGroundsTestingMicrotasks.md`.

Rule:

- no new feature expansion for later beats until command forgiveness, hesitation escalation, flow continuity, and message integrity are verified against the live implementation

## Final Experience Target

The player should leave training thinking:

I moved.

I armed myself.

I learned something.

I lost.

I came back.

I can survive out there.

And the more important reaction:

What happens next?