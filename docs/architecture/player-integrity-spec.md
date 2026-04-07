# Player Integrity Spec

## Purpose

This document defines the minimum behavioral contract for a valid player character in DireEngine.

It mirrors the enforced DireTest lifecycle scenarios so design intent, engine behavior, and regression coverage stay aligned.

This is not a narrative onboarding doc. It is a systems contract.

## Canonical Scenarios

The current integrity contract is enforced by these DireTest scenarios:

- `e2e-full-lifecycle-all-races`
- `e2e-failure-cases`

Those scenarios are authoritative for the behaviors listed below.

## Happy-Path Contract

A valid player lifecycle must support all current playable races moving through this sequence without state corruption:

1. Character creation
2. Onboarding entry
3. Required onboarding progression
4. Gear acquisition and equip flow
5. Combat initiation and completion
6. Death and corpse creation
7. Resurrection and recovery
8. First-area entry
9. Live-game command usability

For every race, the engine must guarantee:

- character creation succeeds through the real account-backed pipeline
- the character enters the onboarding start room in a valid alive state
- onboarding progression cannot silently skip required stages
- required onboarding gear can be acquired and equipped through real commands
- the onboarding combat step completes through the real combat path
- death produces a valid corpse in the expected room
- resurrection restores a living, playable character
- first-area threshold state initializes on live entry
- the character arrives in `Outer Yard` as the current live-game landing state

## Persistence Contract

The lifecycle contract also requires persistence integrity across death and resurrection.

The engine must guarantee:

- every valid player character has a structured identity object
- the structured identity object contains a renderable appearance payload
- equipped weapon identity is preserved across the happy-path death loop
- carried inventory does not silently disappear across resurrection
- carried inventory does not duplicate across resurrection
- worn onboarding gear remains valid across death and recovery
- structured identity does not silently change across death and recovery
- recovery metadata is recorded as `resurrection`

For adversarial cases where the player intentionally drops the weapon before death, the engine must guarantee:

- the dropped weapon remains a room object rather than being lost
- the dropped weapon is not duplicated by death or resurrection handling
- the dropped weapon can be recovered and re-equipped after resurrection

## Cleanup Contract

A character that completes onboarding and enters the live game must no longer behave like an onboarding-locked character.

The engine must guarantee:

- onboarding completion is still recorded
- onboarding runtime state is no longer active
- onboarding command blocks no longer affect normal live-game commands
- the character is not still considered to be in onboarding after live entry
- no onboarding-only scripts remain attached to the character

The practical post-lifecycle checks are:

- `inventory` works
- `look` works
- invalid get targets fail normally rather than through onboarding lock messages
- the character still has a non-empty rendered appearance description

## Adversarial Contract

The failure suite defines the minimum safe-failure behavior for malformed or out-of-order progression.

### Invalid Command Spam

During onboarding, arbitrary invalid commands must not:

- crash the character state
- move the character unexpectedly
- kill the character
- corrupt onboarding progression

### Skip Equip Attempt

If the player tries to advance before equipping correctly, the engine must:

- keep the character in the required onboarding step
- prevent room progression
- avoid falsely setting onboarding completion

### Drop Weapon Before Death

If the player drops the training weapon before dying, the engine must:

- still produce a valid death state and corpse
- preserve worn gear correctly
- avoid re-equipping or duplicating the dropped weapon automatically
- allow the weapon to be recovered and used again after resurrection

### Early Death During Onboarding

If the player dies before onboarding is complete, the engine must:

- produce a valid corpse in the actual current room
- resurrect the player into the actual interrupted stage location
- preserve the current onboarding stage rather than resetting or falsely completing it
- allow the player to resume, finish onboarding, and still reach the first area cleanly

## Isolation Contract

DireEngine uses persistent shared rooms during onboarding and first-area flows.

Because of that, integrity testing must also enforce world hygiene.

The test harness must guarantee:

- leaked corpses are cleaned between destructive lifecycle runs
- dropped room objects from prior runs are cleaned between destructive lifecycle runs
- test characters and helper NPCs do not remain in shared onboarding rooms

This is not optional. Persistent room contamination creates false failures and masks real state bugs.

## Current Verified Scope

As of the current passing scenario set, the integrity spec is verified for:

- all 11 current races
- real onboarding flow
- real command routing
- real death and corpse systems
- real resurrection helpers
- real first-area transition state
- happy-path lifecycle completion
- selected adversarial recovery paths

## Not Yet Covered

The following are important but not yet part of the enforced integrity contract:

- simultaneous onboarding by multiple live characters in shared rooms
- race-specific slot incompatibility or gear-shape edge cases
- failed resurrection branches
- missing corpse branches
- looted corpse recovery branches
- partial stabilization or degraded resurrection outcomes
- random or fuzzed command injection over long onboarding sessions

These are future integrity-spec expansion candidates, not implied guarantees.

## Operational Rule

Any engine change that affects creation, onboarding, equipment, death, resurrection, or first-area entry must preserve this contract.

If a code change breaks a documented invariant here, one of two things must happen:

1. The engine is fixed so the invariant remains true.
2. This document and the corresponding DireTest scenarios are deliberately updated together to reflect a new intended contract.

Changing one without the other is a regression risk.