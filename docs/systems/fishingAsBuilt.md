# Fishing As Built

This file is the required implementation log for the fishing system.

For every completed fishing task, append a new entry using this exact timestamp line format:

`2026-04-09 hh:mm:ss`

Use 24-hour time and record the real completion timestamp for the task.

Every task entry must include all of the following sections. If any section is missing, the task is incomplete.

## Entry Template

2026-04-09 hh:mm:ss
## TASK F-XXX [Task Name]
### What was built
### Example snippet
```python
# core lines only
```
### Files touched
### How it works (plain English)
### How to extend it later
### Known limitations

## Rules

- Add one timestamp per task entry.
- Put the timestamp immediately above the `## TASK F-XXX` header.
- Use a fresh timestamp for each appended task entry.
- Do not backfill a shared timestamp for multiple tasks.
- Keep the explanation plain and implementation-focused.
- Include verification results in the body of `### What was built` or `### Known limitations` if needed, but do not omit the required sections.

## Example

2026-04-09 05:43:00
## TASK F-001 Mark Room Fishable
### What was built
Added `room.db.fishable` and `room.db.fish_group` support to room objects and a helper that checks whether the current room supports fishing.

### Example snippet
```python
self.db.fishable = False
self.db.fish_group = "River 1"
```

### Files touched
- `typeclasses/rooms.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Rooms can now explicitly opt into the fishing system. The helper returns true only when the room has been marked as fishable.

### How to extend it later
Add room-level modifiers such as junk density, bite density, and special regional fish tables.

### Known limitations
The helper only checks whether fishing is allowed. It does not yet validate bait, gear, or water type.

2026-04-09 05:43:01
## TASK F-001 Mark Room Fishable
### What was built
Added persistent room support for `fishable` and `fish_group` in `typeclasses/rooms.py`, plus an `is_fishable(room)` helper for command-side checks. Verification: the values are now part of room creation defaults and can be manually set on rooms without additional schema work.

### Example snippet
```python
self.db.fishable = False
self.db.fish_group = "River 1"
```

### Files touched
- `typeclasses/rooms.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Rooms now explicitly declare whether fishing is allowed and which difficulty band they belong to. The helper gives the rest of the system a single boolean gate for room validation.

### How to extend it later
Add room-level bite density, junk density, and special regional catch tables keyed off `fish_group`.

### Known limitations
The room flag only answers whether fishing is allowed. It does not yet enforce bait, gear, depth, or water type.

2026-04-09 05:43:12
## TASK F-002 Add Fish Command
### What was built
Created `commands/cmd_fishing.py` with a `fish` command skeleton that blocks use in non-fishable rooms and starts the cast flow in fishable rooms. Verification: the command now emits a hard failure outside valid rooms and the cast message inside valid rooms.

### Example snippet
```python
if room is None or not is_fishable(room):
	caller.msg("You can't fish here.")
```

### Files touched
- `commands/cmd_fishing.py`
- `commands/default_cmdsets.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The player types `fish`. The command checks the room first, and only lets the action begin if the room is explicitly marked as fishable.

### How to extend it later
Add argument parsing for bait, pole, or fishing style once the room gate is stable.

### Known limitations
The command does not yet validate inventory gear. It is intentionally room-gated only for this slice.

2026-04-09 05:43:23
## TASK F-003 Add 5-Second Wait
### What was built
Added a five-second delayed resolution step using `delay(5, ...)` so fishing now resolves after a short wait instead of immediately. Verification: the command schedules a delayed callback rather than printing an instant final outcome.

### Example snippet
```python
delay(5, _resolve_fishing_attempt, caller, token, room_id)
```

### Files touched
- `commands/cmd_fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fishing is now time-based. After the cast, the player waits a few seconds before the system decides what came up on the line.

### How to extend it later
Replace the single delay with staged nibble, hookup, and struggle timers.

### Known limitations
This is still a one-step timer, not a full multi-stage fishing state machine.

2026-04-09 05:43:34
## TASK F-004 Add Simple Catch Roll
### What was built
Added a simple random outcome roll with three branches: nothing, fish, or junk. Verification: the resolution callback now uses a random roll with the requested `0.6 / 0.9 / 1.0` style banding.

### Example snippet
```python
roll = random.random()
if roll < 0.6:
	...
elif roll < 0.9:
	...
```

### Files touched
- `commands/cmd_fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Each fishing attempt now resolves to one of three basic outcomes. Most attempts fail quietly, some succeed with a catch, and a smaller slice returns junk.

### How to extend it later
Split this roll into separate nibble, hookup, struggle, and junk layers once deeper fishing is introduced.

### Known limitations
The roll is still a placeholder and does not use bait, gear, weather, or fish tables.

2026-04-09 05:43:45
## TASK F-005 Add Fish Item Typeclass
### What was built
Created `typeclasses/items/fish.py` with a minimal `Fish` object typeclass and wired successful fishing outcomes to spawn a fish item directly into the player's inventory. Verification: successful outcomes now create a concrete in-game object instead of only printing text.

### Example snippet
```python
fish = create_object("typeclasses.items.fish.Fish", key=fish_name, location=actor)
fish.db.weight = random.randint(1, 10)
```

### Files touched
- `typeclasses/items/fish.py`
- `commands/cmd_fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
When the player succeeds, the system creates a portable object and gives it to them immediately. The catch is now an in-world item that other systems can inspect later.

### How to extend it later
Add fish-specific attrs such as species id, freshness, quality, or sell category.

### Known limitations
The fish object is intentionally minimal and does not yet carry economy or processing metadata beyond weight and name.

2026-04-09 05:43:56
## TASK F-006 Add Junk Outcome
### What was built
Added a junk outcome message: `You pull up a clump of weeds.` without spawning an item. Verification: the junk branch now resolves to a distinct non-reward result instead of sharing the failure path.

### Example snippet
```python
actor.msg("You pull up a clump of weeds.")
```

### Files touched
- `commands/cmd_fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Some fishing attempts now return junk rather than a fish or an empty line. This weakens the reward loop and makes catches feel less deterministic.

### How to extend it later
Add junk item objects, salvage hooks, or bait loss on junk pulls.

### Known limitations
Junk is still only a text result and does not create a physical object.

2026-04-09 05:44:07
## TASK F-007 Award Outdoorsmanship XP
### What was built
Hooked fishing results into the survival learning system by awarding Outdoorsmanship experience on outcome resolution. Verification: the command now calls the repo's skill XP path instead of inventing a parallel learning system.

### Example snippet
```python
award_exp_skill(actor, "outdoorsmanship", difficulty, success=True, outcome="success")
```

### Files touched
- `commands/cmd_fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fishing now teaches Outdoorsmanship through the same active XP system used elsewhere in the game. Different outcomes grant slightly different learning strength.

### How to extend it later
Tune event weights by fish group, fish rarity, bait quality, or struggle intensity.

### Known limitations
The current XP values are slice defaults and not yet balanced against live fishing difficulty.

2026-04-09 05:44:18
## TASK F-008 Add Anti-Spam Lock
### What was built
Added a basic anti-spam guard using `caller.ndb.is_fishing` so the command cannot be stacked while an attempt is already in progress. Verification: the command now blocks repeated `fish` use until the pending attempt resolves or is interrupted.

### Example snippet
```python
if caller.ndb.is_fishing:
	caller.msg("You are already fishing.")
```

### Files touched
- `commands/cmd_fishing.py`
- `typeclasses/characters.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
While a cast is active, the player is marked as currently fishing. Any new `fish` command is rejected until that state clears.

### How to extend it later
Replace the boolean with a richer fishing state payload once bait, nibble, and struggle phases exist.

### Known limitations
This is a simple in-memory runtime guard and does not persist across reloads, which is acceptable for a transient action.

2026-04-09 05:44:29
## TASK F-009 Add Waiting Feedback
### What was built
Added immediate feedback after casting with `You wait for a bite...`. Verification: the player now receives an explicit waiting message before the delayed result fires.

### Example snippet
```python
caller.msg("You wait for a bite...")
```

### Files touched
- `commands/cmd_fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The player now gets a clear state transition from cast to waiting. This makes the delay feel intentional rather than laggy.

### How to extend it later
Replace the single waiting line with staged nibble and line-tension messages.

### Known limitations
There is only one waiting message and no intermediate state feedback yet.

2026-04-09 05:44:40
## TASK F-010 Add Starter Fish Table
### What was built
Added a simple fish name table with `trout`, `carp`, and `eel`, then used it to randomize successful catches. Verification: successful catches no longer produce a single hard-coded fish name.

### Example snippet
```python
FISH = ["trout", "carp", "eel"]
fish_name = random.choice(FISH)
```

### Files touched
- `commands/cmd_fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
When a fish is caught, the system selects a species name from a small placeholder table. This makes the slice feel varied without committing to the full researched fish tables yet.

### How to extend it later
Swap the placeholder list for per-room or per-group weighted catch tables.

### Known limitations
The list is intentionally tiny and not tied to room, region, or difficulty.

2026-04-09 05:44:51
## TASK F-011 Add Fish Weight
### What was built
Added a basic weight roll to caught fish using `randint(1, 10)`. Verification: each spawned fish now receives a concrete `db.weight` value on creation.

### Example snippet
```python
fish.db.weight = random.randint(1, 10)
```

### Files touched
- `commands/cmd_fishing.py`
- `typeclasses/items/fish.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Caught fish are now assigned a simple random weight. That gives the object a usable economy hook for later selling and appraisal work.

### How to extend it later
Move from a flat range to species-specific and trophy-specific weight bands.

### Known limitations
The weight range is generic and does not reflect species size.

2026-04-09 05:45:02
## TASK F-012 Add Catch Messaging
### What was built
Added direct inventory-facing catch feedback such as `You catch a trout!`. Verification: successful outcomes now tell the player exactly what was caught.

### Example snippet
```python
actor.msg(f"You catch a {fish_name}!")
```

### Files touched
- `commands/cmd_fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The player receives a specific catch message at the same time the fish object is placed into inventory.

### How to extend it later
Include fish weight, rarity, or trophy messaging when richer catch data exists.

### Known limitations
The message does not yet mention weight or special catch quality.

2026-04-09 05:45:13
## TASK F-013 Add Failure Variation
### What was built
Added multiple empty-line messages instead of always using `Nothing bites.`. Verification: failed attempts now draw from a small pool of failure feedback strings.

### Example snippet
```python
NOTHING_MESSAGES = ["Nothing bites.", "The water stays still."]
actor.msg(random.choice(NOTHING_MESSAGES))
```

### Files touched
- `commands/cmd_fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Failure results are now slightly varied so repeated fishing attempts do not feel mechanically identical.

### How to extend it later
Split the failure set into no-bite, stolen-bait, missed-hook, and weak-nibble subcategories.

### Known limitations
The variant pool is still small and does not yet describe distinct failure causes.

2026-04-09 05:45:24
## TASK F-014 Add Room Echo
### What was built
Added room echo messaging so other players see `<name> casts a line into the water.` when a fishing attempt begins. Verification: the command now emits an observer-facing cast message separate from the actor text.

### Example snippet
```python
room.msg_contents(f"{caller.key} casts a line into the water.", exclude=[caller])
```

### Files touched
- `commands/cmd_fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fishing now has outward room presence, so nearby players can see that someone started a fishing action.

### How to extend it later
Add observer messages for bites, lost fish, trophy catches, and interrupted lines.

### Known limitations
Only the cast is echoed to the room in this slice. Outcome messaging remains actor-only.

2026-04-09 05:45:35
## TASK F-015 Interrupt on Movement
### What was built
Added movement interruption by clearing active fishing state inside `Character.move_to()` and messaging `You disturb the line.` on successful movement. Verification: moving away from the fishing room now cancels the pending attempt instead of letting the delayed callback resolve normally.

### Example snippet
```python
if moved and self.ndb.is_fishing:
	cancel_fishing_session(self)
```

### Files touched
- `typeclasses/characters.py`
- `commands/cmd_fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
If the player actually relocates while a fishing attempt is pending, the action is canceled immediately and the delayed callback becomes a no-op.

### How to extend it later
Add other interruption sources such as combat entry, forced movement, stuns, or dropping gear.

### Known limitations
The interruption currently only hooks movement. It does not yet cancel on combat start or other state changes.

2026-04-09 06:51:01
## TASK F-016 Add Fishing State Object
### What was built
Added [world/systems/fishing.py](world/systems/fishing.py) with `FishingSession`, plus session helpers that store the object on `actor.ndb.fishing_session`, mirror active runtime flags, and clear the session after completion or cancellation. Verification: the updated DireTest scenario confirmed the session exists during baited, cast, nibble, and hooked states, then clears after timeout, miss, catch, and movement interruption.

### Example snippet
```python
class FishingSession:
	def __init__(self, actor):
		self.actor = actor
		self.state = "idle"
```

### Files touched
- `world/systems/fishing.py`
- `commands/cmd_fishing.py`
- `typeclasses/characters.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The session object is the single source of truth for fishing state. Instead of scattering booleans and timers across the character, the fishing system now keeps one in-memory object that tracks baiting, cast timing, nibble timing, and struggle progress.

### How to extend it later
Add per-session fish tables, rod state, weather modifiers, and bait consumption without changing the command interfaces.

### Known limitations
The session is intentionally transient and lives on `ndb`, so it does not persist across reloads.

2026-04-09 06:51:12
## TASK F-017 Add Bait Item
### What was built
Added [typeclasses/items/bait.py](typeclasses/items/bait.py) with a base `Bait` item carrying `db.bait_type = "basic"` and `db.quality = 10`. Verification: the fishing DireTest creates a bait item directly and the player can hold and use it for baiting.

### Example snippet
```python
self.db.bait_type = "basic"
self.db.quality = 10
```

### Files touched
- `typeclasses/items/bait.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Bait is now its own item abstraction. The fishing system looks at bait metadata instead of hard-coding item names, so different bait objects can share the same behavior while still having different names or descriptions.

### How to extend it later
Add special bait families such as worms, insects, meat, or brightwater lures by changing `bait_type` and `quality`.

### Known limitations
Only the base bait profile exists so far, and bait is not consumed yet.

2026-04-09 06:51:23
## TASK F-018 Require Bait to Fish
### What was built
Updated the fish flow to require bait in inventory before casting can begin. Verification: the DireTest scenario now fails `fish` with a clear bait requirement before any session is started when the player has no bait item.

### Example snippet
```python
if not _get_inventory_bait_items(actor):
	return False, "You need bait before you can fish.", session, room
```

### Files touched
- `world/systems/fishing.py`
- `commands/cmd_fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fishing now checks whether the player is actually carrying bait before it allows the cast phase. That makes fishing dependent on items instead of acting like a free ambient action.

### How to extend it later
Require specific bait families by room or fish group instead of just any bait item.

### Known limitations
The current gate only checks for bait presence, not bait suitability.

2026-04-09 06:51:34
## TASK F-019 Add Bait Command
### What was built
Added the `bait <item>` command so preparation is explicit and sets `session.baited = True` on the active fishing session. Verification: DireTest confirmed that `bait worm` creates a session, marks it baited, and stores the selected bait item on the session.

### Example snippet
```python
session = get_fishing_session(actor, create=True)
session.baited = True
session.bait_item_id = bait_item.id
```

### Files touched
- `commands/cmd_fishing.py`
- `world/systems/fishing.py`
- `commands/default_cmdsets.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The player now prepares the hook first, then casts later. That separates setup from execution and gives the system a real pre-cast state.

### How to extend it later
Allow re-baiting with different bait items mid-session or after a snag.

### Known limitations
The bait command attaches bait metadata but does not yet consume the item.

2026-04-09 06:51:45
## TASK F-020 Enforce Baited State
### What was built
Enforced the baited state inside the fishing cast path so players must bait before they can cast. Verification: the DireTest scenario now rejects `fish` with a bait-your-hook message when bait is in inventory but the session is still unbaited.

### Example snippet
```python
if session is None or not session.baited:
	return False, "You need to bait your hook first.", session, room
```

### Files touched
- `world/systems/fishing.py`
- `commands/cmd_fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fishing now advances through a strict progression instead of allowing players to skip straight to the cast. The session must move from `idle` to `baited` before `cast` is allowed.

### How to extend it later
Add preconditions such as equipped rod, clear hands, or stance restrictions.

### Known limitations
The enforcement is state-based only and does not yet verify gear.

2026-04-09 06:51:56
## TASK F-021 Introduce Nibble Phase
### What was built
Replaced the flat one-step fishing result with a timed nibble phase. Casting now sets `state = "cast"`, schedules a delayed transition, and then moves into `state = "nibble"` with the message `You feel a slight tug on the line...`. Verification: DireTest explicitly observed the cast state first and the nibble state second.

### Example snippet
```python
session.state = "cast"
delay(5, _begin_nibble, actor, session.attempt_token)
```

### Files touched
- `world/systems/fishing.py`
- `commands/cmd_fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The system now distinguishes between putting the line in the water and getting a bite. A nibble happens before any hook logic, which creates a real reaction phase instead of instant success or failure.

### How to extend it later
Add different nibble timings by fish group or bait quality.

### Known limitations
The current cast-to-nibble timing is still a single fixed delay.

2026-04-09 06:52:07
## TASK F-022 Add Reaction Window
### What was built
Added a three-second reaction window after nibble and stored the bite timestamp on `session.nibble_time`. Verification: DireTest confirmed the nibble timestamp is populated and used before the pull and timeout branches resolve.

### Example snippet
```python
session.nibble_time = time.time()
delay(3, _expire_nibble_window, actor, token, session.nibble_time)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Once the line twitches, the player only has a short window to react. That turns fishing into a timing system instead of a passive wait for RNG.

### How to extend it later
Tune the reaction window by fish type, player skill, or bait quality.

### Known limitations
The window length is fixed at three seconds for now.

2026-04-09 06:52:18
## TASK F-023 Add Pull Command
### What was built
Added the `pull` command and restricted it to the nibble and hooked states. Verification: DireTest now confirms `pull` fails outside the window and succeeds as a valid action during nibble and hooked phases.

### Example snippet
```python
if session.state not in {"nibble", "hooked"}:
	actor.msg("You can't pull right now.")
```

### Files touched
- `commands/cmd_fishing.py`
- `world/systems/fishing.py`
- `commands/default_cmdsets.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Players now have a dedicated reaction command instead of the system resolving everything automatically. That is the first real player agency layer in fishing.

### How to extend it later
Add alternative reaction verbs such as reel, brace, or ease for deeper struggle control.

### Known limitations
There is only one reaction verb right now.

2026-04-09 06:52:29
## TASK F-024 Hook vs Miss Logic
### What was built
Implemented hook-versus-miss logic when `pull` is used during nibble, using bait quality, tangle penalty, and reaction timing to determine the outcome. Verification: the deterministic DireTest scenario now exercises both the missed hook branch and the successful hook branch in one run.

### Example snippet
```python
if hook_roll < _hook_success_chance(session, bait_item):
	session.state = "hooked"
else:
	reset_fishing_session(actor)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The first pull no longer means an automatic catch. It decides whether the player actually sets the hook or loses the fish at the critical moment.

### How to extend it later
Incorporate skill checks and room difficulty directly into hook chance.

### Known limitations
The hook math is intentionally simple and is not yet fully skill-driven.

2026-04-09 06:52:40
## TASK F-025 Add Hooked State
### What was built
Added a dedicated hooked state with the message `The line jerks violently!` and a stored `session.hooked_fish` target. Verification: DireTest confirmed that a successful nibble pull transitions the session into `hooked` before the struggle loop begins.

### Example snippet
```python
session.state = "hooked"
session.hooked_fish = random.choice(FISH)
actor.msg("The line jerks violently!")
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Once the fish is hooked, the player gets explicit confirmation that the system has moved out of the bite phase and into the fight phase.

### How to extend it later
Add species-specific hooked messages and fish strength profiles.

### Known limitations
Hooked fish identity is still selected from the current placeholder fish table.

2026-04-09 06:52:51
## TASK F-026 Add Struggle Loop
### What was built
Added a basic struggle loop that resolves every two seconds and can land the fish, lose it, or continue the fight. Verification: DireTest now confirms that the hooked state can persist across multiple struggle rounds before resolving.

### Example snippet
```python
session.struggle_round += 1
delay(2, _resolve_struggle_round, actor, token)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
After a hook, fishing no longer ends immediately. The system periodically checks the fight state and waits for the player to keep pressure on the line.

### How to extend it later
Split struggle resolution into tension, stamina, and fish behavior instead of one roll.

### Known limitations
The loop is still abstract and does not model line strength or rod handling.

2026-04-09 06:53:02
## TASK F-027 Add Win Condition
### What was built
Added the win condition that spawns a fish item and ends the session cleanly when the struggle resolves in the player's favor. Verification: the updated DireTest lands a deterministic trout, places it in inventory, awards Outdoorsmanship XP, and clears the session.

### Example snippet
```python
_spawn_fish(actor, fish_name)
actor.msg(f"You catch a {fish_name}!")
reset_fishing_session(actor)
```

### Files touched
- `world/systems/fishing.py`
- `typeclasses/items/fish.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
When the struggle succeeds, the system converts the abstract hooked fish into a real inventory item and closes the fishing session.

### How to extend it later
Add trophies, variable quality, and species-specific weight bands.

### Known limitations
The landed fish still comes from a placeholder species list.

2026-04-09 06:53:13
## TASK F-028 Add Failure Conditions
### What was built
Added explicit failure outcomes for missed hooks, fish escaping during the struggle, and slack-line timeout after a missed nibble pull. Verification: DireTest hits the missed hook branch, the missed-pull branch, and the cleanup path that follows each failure.

### Example snippet
```python
actor.msg("The fish thrashes free and the line snaps slack.")
reset_fishing_session(actor)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fishing now includes real risk. A bite can be missed, a hooked fish can get away, and inaction during the bite window can waste the attempt.

### How to extend it later
Add separate line-break, bait-loss, and snag failure types.

### Known limitations
Failure outcomes are still text-driven and do not yet damage equipment.

2026-04-09 06:53:24
## TASK F-029 Add Miss Penalty
### What was built
Added the missed-pull penalty with `The line goes still...`, plus a chance to apply a future hook penalty through a temporary line tangle state. Verification: DireTest confirmed the timeout branch can apply a non-zero future hook penalty before the next baited attempt.

### Example snippet
```python
actor.msg("The line goes still...")
actor.ndb.fishing_hook_penalty = 0.15
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
If the player does nothing when the fish nibbles, the moment passes and the line may tangle. That makes hesitation matter, not just incorrect pulls.

### How to extend it later
Persist tangles to the line or rod item and require manual clearing.

### Known limitations
The tangle penalty is currently a transient hook modifier stored on `ndb`.

2026-04-09 06:53:35
## TASK F-030 Reset Session Cleanly
### What was built
Standardized cleanup so every terminal outcome clears `actor.ndb.fishing_session = None`, resets active runtime flags, and prevents infinite sessions from hanging around. Verification: the deterministic DireTest now spot-checks cleanup after timeout, failed pull, successful catch, and movement interruption, and the scenario passed at `artifacts/fishing-vertical-slice_direct_1234`.

### Example snippet
```python
actor.ndb.fishing_session = None
actor.ndb.is_fishing = False
```

### Files touched
- `world/systems/fishing.py`
- `typeclasses/characters.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Every finish path goes through the same reset behavior, so a session ends cleanly whether the player wins, loses, or moves away.

### How to extend it later
Route all future interruption sources through the same cleanup helper so the state machine stays consistent.

### Known limitations
Cleanup is consistent for the implemented paths, but future combat or disconnect interruptions still need to be routed into it.

2026-04-09 07:15:52
## TASK F-031 Add Bait Family Registry
### What was built
Added a centralized bait-family registry in `world/systems/fishing.py` with quality, lore requirement, match bonus, and tag metadata for `artificial_simple`, `worm_cutbait`, `live_bait`, and `specialty_lure`. Verification: the deterministic DireTest now calls the live helper layer and confirms better bait families materially improve nibble or hookup odds.

### Example snippet
```python
BAIT_FAMILY_REGISTRY = {
	"worm_cutbait": {"quality": 14, "lore_requirement": 10, "match_bonus": 2},
}
```

### Files touched
- `world/systems/fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fishing bait is no longer just a flat quality number. Each bait family now carries stable mechanical meaning that the rest of the fishing system can read.

### How to extend it later
Add more regional or profession-specific bait families without changing the player command surface.

### Known limitations
The family set is intentionally small for Phase 3 and does not yet include cosmetic alias tables.

2026-04-09 07:15:59
## TASK F-032 Map Bait Items To Families
### What was built
Updated the bait item typeclass so bait objects now expose `db.bait_family`, `db.bait_quality`, and `db.bait_match_tags`, with compatibility support for legacy `db.bait_type`. Verification: the DireTest creates multiple bait items with different families and confirms the live formulas treat them differently.

### Example snippet
```python
self.db.bait_family = "worm_cutbait"
self.db.bait_match_tags = ["worm", "cutbait", "freshwater"]
```

### Files touched
- `typeclasses/items/bait.py`
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Bait items now carry explicit family data instead of forcing fishing to guess from a generic quality field.

### How to extend it later
Create shop or crafting bait subclasses that only override family metadata.

### Known limitations
Existing live bait items will still need migration if they only stored older custom attributes.

2026-04-09 07:16:06
## TASK F-033 Add Fish Group Defaults
### What was built
Added `FISH_GROUP_DEFAULTS` with difficulty bands, room density, and junk density for `River 1`, `River 2`, `River 3`, and `Ocean`, plus safe fallback behavior for unknown room groups. Verification: DireTest now asserts that an unknown fish-group lookup falls back to `river 1` and marks the result as a fallback.

### Example snippet
```python
"river 2": {"difficulty_band": (40, 60), "room_density": 0.48, "junk_density": 0.10}
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The room tag now resolves into a real group profile instead of a single placeholder difficulty integer.

### How to extend it later
Add more group presets or let specific rooms override density numbers directly.

### Known limitations
Only a small starter set of fish groups is defined so far.

2026-04-09 07:16:13
## TASK F-034 Add Fish Profiles
### What was built
Added canonical fish profiles with species name, difficulty, weight range, value modifier, fight profile, and bait preferences. Verification: the weighted catch tables and spawned fish metadata now read from these fish-profile records instead of flat species strings.

### Example snippet
```python
"silver_trout": {"difficulty": 26, "fight_profile": "steady", "weight_min": 1, "weight_max": 4}
```

### Files touched
- `world/systems/fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Each fish species now has its own mechanical identity instead of only being a display name.

### How to extend it later
Add skinning yields, trophy flags, or regional lore text directly onto the fish profile records.

### Known limitations
Fish profiles are code-backed constants rather than data-driven records.

2026-04-09 07:16:20
## TASK F-035 Add Weighted Catch Tables
### What was built
Replaced the old flat fish list with weighted catch tables keyed by fish group, and added a weighted selection helper that only draws valid fish for the current group. Verification: DireTest samples River 1 and Ocean repeatedly and confirms River 1 never emits Ocean species and that the heavier River 1 weight wins more often than the lighter one.

### Example snippet
```python
FISH_GROUP_CATCH_TABLES = {"river 1": [("silver_trout", 70), ("mud_carp", 30)]}
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Rooms now pull fish from their own local catch table, and common fish appear more often than rare fish.

### How to extend it later
Move weighted tables into a content pipeline so area builders can edit them without touching code.

### Known limitations
Catch weights are static and do not yet change by season or time of day.

2026-04-09 07:16:27
## TASK F-036 Use Bait In Nibble Odds
### What was built
Replaced automatic nibble timing with a real nibble formula based on bait family quality, room density, lore efficiency, and fish difficulty. Verification: DireTest compares live nibble chances for different bait families and confirms the better bait produces a higher nibble chance.

### Example snippet
```python
chance = 0.12 + (quality * 0.010) + (room_density * 0.30) - (difficulty * 0.0025)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Whether something bites now depends on the bait and the water, not just the fact that the player cast a line.

### How to extend it later
Fold weather, season, and room-specific scarcity into the nibble formula.

### Known limitations
Nibble checks still happen on the existing fixed delay schedule.

2026-04-09 07:16:34
## TASK F-037 Add Bait Match Bonus
### What was built
Added bait-family and bait-tag matching so fish profiles can prefer certain bait types, improving hook conversion without making mismatches impossible. Verification: DireTest compares hook chances for a matched worm bait versus a mismatched specialty lure on the same fish profile.

### Example snippet
```python
if family in preferred_families:
	return base_bonus
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Correct bait helps, but the wrong bait does not hard-lock the system into failure.

### How to extend it later
Add fish behaviors that react to broader tag clusters like `shiny`, `blood`, or `deepwater`.

### Known limitations
The current match model uses a single additive bonus rather than layered preference strengths.

2026-04-09 07:16:41
## TASK F-038 Add Lightweight Gear Ratings
### What was built
Added lightweight `rod_rating`, `hook_rating`, and `line_rating` values to the session and a centralized gear-resolution helper that reads actor overrides or starter defaults. Verification: the struggle and hook formulas now read session gear ratings instead of hard-coded generic thresholds.

### Example snippet
```python
DEFAULT_GEAR_RATINGS = {"rod_rating": 12.0, "hook_rating": 10.0, "line_rating": 10.0}
```

### Files touched
- `world/systems/fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The system can now treat line strength, hook quality, and rod stability as separate inputs without adding any new player commands.

### How to extend it later
Let rods or hooks override the default ratings when equipment support is ready.

### Known limitations
Gear is currently abstract session data rather than real assembled equipment.

2026-04-09 07:16:48
## TASK F-039 Add Richer Struggle Formula
### What was built
Replaced the old threshold-only struggle loop with a derived struggle outcome helper that weighs fish pressure, fishing rating, gear rating, lore friction, and reaction timing. Verification: DireTest now forces and validates both multi-round fighting and terminal struggle outcomes through the centralized helper.

### Example snippet
```python
landed_score = 0.22 + ((fishing_rating + gear_rating - pressure) / 160.0)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Landing a fish is no longer a coin flip. Hard fish push back harder, and player timing plus gear quality really change the result.

### How to extend it later
Add fatigue or fish-specific special moves to modify pressure between rounds.

### Known limitations
The fight model still resolves in coarse rounds instead of continuous tension updates.

2026-04-09 07:16:55
## TASK F-040 Add Line Break Outcome
### What was built
Added a real `line_break` struggle outcome that ends active fishing, leaves the session in a broken-line state, and blocks re-casting until the player re-baits. Verification: DireTest now forces a line-break path and confirms the active flags clear while the broken state remains visible.

### Example snippet
```python
session.state = "broken"
session.line_broken = True
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
If the fish overwhelms the line, the active struggle ends immediately and the rig becomes unusable until reset.

### How to extend it later
Persist broken-line damage onto actual equipment when rod and line items exist.

### Known limitations
Re-baiting acts as the temporary recovery path because there is no repair flow yet.

2026-04-09 07:17:02
## TASK F-041 Add Slip Hook Outcome
### What was built
Split fish-loss messaging and logic into a real slip-hook outcome so the fish can escape cleanly without masquerading as a line break. Verification: DireTest forces a failed hook path and checks for slip-hook messaging plus session cleanup.

### Example snippet
```python
actor.msg(random.choice(SLIP_HOOK_MESSAGES))
reset_fishing_session(actor)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fish loss now distinguishes between failing to keep the hook set and actually breaking the rig.

### How to extend it later
Track bait loss separately on a slipped hook.

### Known limitations
Slip-hook resolution does not yet degrade hooks or bait stock.

2026-04-09 07:17:09
## TASK F-042 Promote Tangles To State
### What was built
Promoted tangles from a hidden future-hook penalty into a real `tangled` session state that can come from missed nibbles or bad pull timing and blocks normal continuation until the player re-baits. Verification: DireTest now forces both an early-pull tangle and a missed-bite tangle, then confirms `fish` is blocked until `bait` resets the rig.

### Example snippet
```python
session.state = "tangled"
session.tangled = True
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Tangles are now visible, persistent state instead of a hidden modifier that the player cannot reason about.

### How to extend it later
Add a future `untangle` action or equipment wear if that interaction becomes worth the extra command surface.

### Known limitations
The only internal reset path right now is re-baiting.

2026-04-09 07:17:16
## TASK F-043 Add Fish Value Helper
### What was built
Added a deterministic fish-value helper derived from fish difficulty, weight, and species value modifier, then used that helper when spawning landed fish. Verification: DireTest now asserts that landed fish receive a positive stamped value.

### Example snippet
```python
value = calculate_fish_value(fish_profile, weight)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fish now carry an economy-facing value the moment they are caught, so downstream selling or appraisal systems have something concrete to read.

### How to extend it later
Add regional scarcity and trophy multipliers into the value calculation.

### Known limitations
There is no market system using the stamped value yet.

2026-04-09 07:17:23
## TASK F-044 Stamp Fish Metadata
### What was built
Expanded spawned fish objects so they now store `fish_group`, `fish_difficulty`, `weight`, `value`, `fight_profile`, and the source fish-profile key. Verification: DireTest inspects the landed fish object and confirms those fields are set.

### Example snippet
```python
fish.db.fish_group = str(fish_profile.get("fish_group", "") or "")
fish.db.fight_profile = str(fish_profile.get("fight_profile", "steady") or "steady")
```

### Files touched
- `world/systems/fishing.py`
- `typeclasses/items/fish.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Caught fish are now self-describing objects that carry the important mechanical facts of the encounter.

### How to extend it later
Expose the stamped metadata through appraise, market, or crafting commands.

### Known limitations
The fish description text does not yet adapt to the stamped metadata.

2026-04-09 07:17:30
## TASK F-045 Use Junk Density
### What was built
Added a junk-chance formula driven by the room group’s `junk_density` and the bait’s cleanliness or quality, and wired it into the cast outcome path. Verification: the central fishing loop now computes junk chance from fish-group data instead of a flat incidental roll.

### Example snippet
```python
chance = 0.02 + (junk_density * 0.45) - (bait_cleanliness * 0.003)
```

### Files touched
- `world/systems/fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Dirty or junk-heavy waters are now more likely to produce weeds and trash than clean waters.

### How to extend it later
Let specific rooms override junk density to model polluted or especially clear water.

### Known limitations
The current junk path still uses simple generic junk text rather than distinct junk items.

2026-04-09 07:17:37
## TASK F-046 Scale With Outdoorsmanship
### What was built
Added a derived fishing rating based primarily on Outdoorsmanship, with smaller reflex and discipline contributions, and threaded that rating into hook and struggle resolution. Verification: the Phase 3 formulas now read the actor’s real skill and stat data instead of ignoring progression.

### Example snippet
```python
return (outdoorsmanship * 0.65) + (reflex * 0.20) + (discipline * 0.15)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Better trained characters now land fish more reliably without making low-skill characters incapable of participating.

### How to extend it later
Fold in perception or profession bonuses if survival roles need extra differentiation.

### Known limitations
Outdoorsmanship still remains the dominant progression input by design.

2026-04-09 07:17:44
## TASK F-047 Add Lore Friction
### What was built
Added a mild lore-efficiency penalty for advanced bait families using the existing Scholarship rank as the current lore proxy. Verification: DireTest checks that advanced bait under low lore reduces efficiency but stays above zero and below a hard lock.

### Example snippet
```python
return clamp(1.0 - (deficit / max(requirement + 20.0, 25.0)) * 0.35, 0.65, 1.0)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Players can still use advanced bait early, but they do not get its full benefit until they bring enough lore skill to handle it well.

### How to extend it later
Swap Scholarship for a dedicated lore or mechanical-lore skill if that system solidifies.

### Known limitations
Scholarship is a temporary stand-in for the broader lore concept described in the research packet.

2026-04-09 07:17:51
## TASK F-048 Expand DireTest Coverage
### What was built
Rewrote the deterministic fishing DireTest to validate weighted fish selection, bait-family comparisons, unknown-group fallback, early-pull tangles, missed-bite tangles, slip hooks, line breaks, multi-round struggles, landed fish metadata, stale callbacks, movement interruption, and unpuppet cleanup. Verification: `diretest.py scenario fishing-vertical-slice --seed 1234` passed and wrote fresh artifacts to `artifacts/fishing-vertical-slice_direct_1234`.

### Example snippet
```python
river_samples = [fishing_system.choose_weighted_fish_profile("River 1", rng=river_rng) for _ in range(80)]
```

### Files touched
- `diretest.py`
- `world/systems/fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The fishing test now protects the real failure modes and the real data layer, not just the happy path.

### How to extend it later
Add a second scenario for Ocean-tier difficulty once more fish groups are populated.

### Known limitations
The scenario still patches timers and helper functions to keep the run deterministic.

2026-04-09 07:17:58
## TASK F-049 Add Debug Observability
### What was built
Added centralized debug trace recording for cast starts, nibble checks, hook checks, tangles, and struggle rounds when `actor.ndb.fishing_debug` is enabled. Verification: DireTest now inspects the trace log and confirms expected events are recorded.

### Example snippet
```python
entries.append({"event": str(event), "payload": dict(payload), "timestamp": float(time.time())})
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fishing decisions can now be inspected without spamming normal players, which makes tuning and debugging much easier.

### How to extend it later
Route trace events into structured logging or a GM-only inspection tool.

### Known limitations
Trace storage is currently ephemeral `ndb` state and is not persisted across reconnects.

2026-04-09 07:18:05
## TASK F-050 Remove Placeholder Fishing Data
### What was built
Removed the old placeholder species list, flat fish-group difficulty map, transient future-hook penalty path, and other slot-machine-era fishing shortcuts, replacing them with the centralized Phase 3 registries and helpers. Verification: the updated deterministic DireTest passed against the new data-driven layer without relying on the removed placeholder paths.

### Example snippet
```python
fish_profile = choose_weighted_fish_profile(room)
```

### Files touched
- `world/systems/fishing.py`
- `typeclasses/items/bait.py`
- `typeclasses/items/fish.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The fishing system now resolves through one consistent Phase 3 ruleset instead of carrying old flat-random behavior alongside the new logic.

### How to extend it later
Continue migrating content data outward without reintroducing duplicate fallback logic.

### Known limitations
The Phase 3 layer is still code-defined rather than backed by editable content data.

2026-04-09 08:02:01
## TASK F-051 Fish Buyer NPC
### What was built
Added a dedicated fish-buyer vendor typeclass with fish-only trade intent, fish-specific shop text, and fish-aware inventory scanning. Verification: the buyer is instantiated in the fishing DireTest scenario and correctly reports estimated value only for carried or stringed fish.

### Example snippet
```python
self.db.vendor_type = "fish_buyer"
self.db.accepted_item_types = ["fish"]
```

### Files touched
- `typeclasses/fish_buyer.py`
- `typeclasses/characters.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The new NPC plugs into the existing vendor framework instead of replacing it. It behaves like a normal vendor but only cares about fish objects and uses fish-aware interaction text.

### How to extend it later
Add buyer personalities, region-specific demand, or limited-time price surges without changing the fishing core.

### Known limitations
The buyer is still a generic fish market NPC. It does not yet negotiate by species, freshness, or town-specific supply.

2026-04-09 08:02:02
## TASK F-052 Single-Fish Sell Flow
### What was built
Extended the existing `sell` flow so `sell <fish>` works against the fish buyer, including fish pulled from a fish string. Verification: the DireTest scenario sells one caught trout and asserts the exact coin payout against the metadata-driven fish value helpers.

### Example snippet
```python
if fishing_economy.is_fish_item(item) and self.get_vendor_type(vendor) == "fish_buyer":
	value += fishing_economy.get_fish_buyer_bonus(item)
```

### Files touched
- `typeclasses/characters.py`
- `commands/cmd_sell.py`
- `world/systems/fishing_economy.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The standard sell command now routes fish sales through the normal character trade path. The fish buyer uses the fish item's stamped metadata as the source of truth for payout.

### How to extend it later
Add fish-buyer haggling or profession-based sale modifiers without rewriting the command surface.

### Known limitations
Single-fish selling still depends on a nearby vendor. There is no mail-order or remote fish market flow.

2026-04-09 08:02:03
## TASK F-053 Bulk Fish Sell Flow
### What was built
Added `sell fish` to sell only fish items in bulk, including fish stored on a fish string, while leaving non-fish inventory untouched. Verification: the DireTest scenario sells three fish in one command, checks the exact total, and confirms a carried rock survives the bulk sale.

### Example snippet
```python
if lowered == "fish":
	self.caller.sell_all_fish()
```

### Files touched
- `commands/cmd_sell.py`
- `typeclasses/characters.py`
- `world/systems/fishing_economy.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Bulk selling is now fish-specific instead of piggybacking on `sell all`. The character gathers fish from inventory and fish strings, totals their values, pays coins once, and deletes only sold fish.

### How to extend it later
Add `sell trophy fish` or grouped species summaries if bulk fish trading needs finer control.

### Known limitations
The summary is count-and-total only. It does not yet print a species-by-species sale breakdown.

2026-04-09 08:02:04
## TASK F-054 Fish String Carrier
### What was built
Created a wearable fish-string container that only accepts fish and reports its current catch contents. Verification: the DireTest scenario creates a fish string and successfully moves a caught trout onto it.

### Example snippet
```python
self.db.is_fish_string = True
self.db.allowed_types = ["fish"]
```

### Files touched
- `typeclasses/items/fish_string.py`
- `commands/cmd_stow.py`
- `world/systems/fishing_economy.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The fish string reuses the repo's wearable-container rules instead of inventing a fishing-only storage subsystem. It can hold fish and advertises itself clearly in normal item inspection.

### How to extend it later
Add upgraded strings, creels, baskets, or spoilage modifiers by subclassing the same container behavior.

### Known limitations
The string currently has a fixed capacity and no durability or freshness logic.

2026-04-09 08:02:05
## TASK F-055 Auto-Stringing Catches
### What was built
Hooked catch landing into fish-string placement so newly caught fish automatically secure to an available fish string before they try normal inventory placement. Verification: the DireTest scenario lands a later fish with a string present and confirms the catch ends up inside the fish string with explicit player feedback.

### Example snippet
```python
placed, fish_string, _message = fishing_economy.place_fish_on_string(actor, fish)
if placed:
	return fish, fish_string
```

### Files touched
- `world/systems/fishing.py`
- `world/systems/fishing_economy.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
After a fish object is created and stamped, the system first checks whether the player has a fish string that can accept it. If so, the fish is stored there immediately and the catch text says so.

### How to extend it later
Let players pick a preferred fish string or route trophy catches to special storage automatically.

### Known limitations
The auto-string preference is binary. It does not yet choose between multiple strings using quality or free-space heuristics.

2026-04-09 08:02:06
## TASK F-056 Fish Weight Messaging
### What was built
Upgraded catch messaging so landed fish announce weight in the success text instead of only the species name. Verification: successful Phase 4 catches now route through the economy formatter before the message is emitted.

### Example snippet
```python
actor.msg(fishing_economy.get_fish_catch_message(fish))
```

### Files touched
- `world/systems/fishing.py`
- `world/systems/fishing_economy.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The catch message now reads from the landed fish item itself, so the message reflects the fish's real stamped weight rather than a placeholder roll.

### How to extend it later
Add rarity adjectives, region tags, or freshness blurbs directly from fish metadata.

### Known limitations
The weight message is actor-facing only. Room echoes for notable catches are still future work.

2026-04-09 08:02:07
## TASK F-057 Trophy Fish Flag
### What was built
Added a trophy flag and multiplier metadata onto fish items during the economy stamping pass. Verification: the DireTest scenario forces a trophy fish with a deterministic RNG and asserts `db.is_trophy` becomes true.

### Example snippet
```python
fish.db.is_trophy = True
fish.db.trophy_multiplier = multiplier
```

### Files touched
- `world/systems/fishing_economy.py`
- `typeclasses/items/fish.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Trophy status is now stamped onto the fish object itself so all downstream systems can read the same rarity state without recalculating it.

### How to extend it later
Add trophy categories by species or fish-group rarity bands if the market needs finer prestige tiers.

### Known limitations
The trophy decision is still a lightweight roll. It does not yet consider world events, weather, or named hot spots.

2026-04-09 08:02:08
## TASK F-058 Trophy Catch Messaging
### What was built
Added a distinct trophy-only message path so unusually notable fish get special catch feedback. Verification: trophy message helpers now return text only for trophy fish and stay silent for normal catches.

### Example snippet
```python
trophy_message = fishing_economy.get_trophy_message(fish)
if trophy_message:
	actor.msg(trophy_message)
```

### Files touched
- `world/systems/fishing.py`
- `world/systems/fishing_economy.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
After the normal catch line prints, the system optionally adds a second message when the fish is marked as a trophy. This keeps special catches visibly distinct without changing normal catch flow.

### How to extend it later
Echo trophy catches to the room or a fishing gossip channel if you want more social visibility.

### Known limitations
Only the player gets the special message right now. Nearby observers do not yet react automatically.

2026-04-09 08:02:09
## TASK F-059 Trophy Value Multiplier
### What was built
Applied trophy multipliers directly to fish item value during economy stamping. Verification: the DireTest scenario compares a normal fish and a forced-trophy fish built from the same profile and confirms the trophy fish ends with the higher stored value.

### Example snippet
```python
fish.db.value = max(1, int(base_value * multiplier))
```

### Files touched
- `world/systems/fishing_economy.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The fish object's `db.value` becomes the durable source of truth after trophy logic runs. Selling and inspection then read the already-adjusted number instead of applying hidden math later.

### How to extend it later
Add trophy-size bands or vendor-specific trophy markups while keeping the fish value traceable.

### Known limitations
The multiplier is still a simple bounded random scale. It does not yet include species-specific trophy curves.

2026-04-09 08:02:10
## TASK F-060 Buyer Reaction Variance
### What was built
Added fish-buyer reaction text that changes based on payout quality and trophy status. Verification: the DireTest scenario sells a forced trophy fish and asserts the premium buyer-reaction text branch fires.

### Example snippet
```python
return f"{self.key} counts out {actor.format_coins(value)}. {fishing_economy.get_fish_buyer_reaction(item, value)}"
```

### Files touched
- `typeclasses/fish_buyer.py`
- `world/systems/fishing_economy.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The fish buyer now reacts differently to cheap fish, solid catches, and trophy-quality sales. That gives the economy loop a little more personality without changing the underlying trade API.

### How to extend it later
Add mood pools, city-specific slang, or profession-based reactions without touching trade math.

### Known limitations
The reaction pool is still text-only. It does not yet influence payout, faction, or repeat-business systems.

2026-04-09 08:02:11
## TASK F-061 Weigh Station Object
### What was built
Added a dedicated weigh-station world object that marks a room as supporting fish weighing. Verification: the DireTest scenario spawns a weigh station into the fishing room and successfully uses it during `weigh silver trout`.

### Example snippet
```python
self.db.is_weigh_station = True
self.aliases.add("scale")
```

### Files touched
- `typeclasses/weigh_station.py`
- `world/systems/fishing_economy.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The weigh station is a regular in-world object with a simple marker attribute. The command-side lookup checks for that marker in the current room.

### How to extend it later
Add special weigh stations that log town records or take fees for certified measurements.

### Known limitations
The object is passive. It does not yet store public records by itself.

2026-04-09 08:02:12
## TASK F-062 Weigh Command
### What was built
Added `weigh <fish>` as a normal command registered in the default cmdset, gated by a nearby weigh station and able to inspect fish from inventory or fish strings. Verification: the DireTest scenario runs `weigh silver trout` and checks the returned weight, value, and trophy lines.

### Example snippet
```python
if not station:
	self.msg("There is no weigh station here.")
```

### Files touched
- `commands/cmd_weigh.py`
- `commands/default_cmdsets.py`
- `typeclasses/characters.py`
- `world/systems/fishing_economy.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The new command reuses the character-side fish lookup and the same formatted inspection text used by fish `look`. That keeps fish inspection consistent across command surfaces.

### How to extend it later
Add certified measurements, local records, or posting-board integration off the same command.

### Known limitations
The command only reports the fish data. It does not yet rank the fish against global or local records in the output.

2026-04-09 08:02:13
## TASK F-063 Leaderboard Stub
### What was built
Added a lightweight heaviest-fish leaderboard stub on the character so the largest landed catch is tracked without introducing a full ranking service yet. Verification: the DireTest scenario asserts the stub is populated after a successful landed fish.

### Example snippet
```python
actor.db.fishing_leaderboard = current
```

### Files touched
- `world/systems/fishing_economy.py`
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
When a fish is spawned, the economy layer compares its weight against the actor's current best. If the new fish is heavier, the stub record updates in-place.

### How to extend it later
Promote the stub into a town, account, or shard-wide leaderboard once persistence and display requirements are clear.

### Known limitations
This is per-character storage only. There is no shared leaderboard query yet.

2026-04-09 08:02:14
## TASK F-064 Trophy Sell Bonus
### What was built
Added an extra fish-buyer bonus on top of base fish value for trophy catches. Verification: the DireTest scenario calculates the expected trophy payout using the same helper path as runtime and matches the actual sale result.

### Example snippet
```python
value = fishing_economy.get_fish_sale_value(fish) + fishing_economy.get_fish_buyer_bonus(fish)
```

### Files touched
- `world/systems/fishing_economy.py`
- `typeclasses/characters.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Trophy fish now get a small premium when sold to the specialist buyer. The bonus is separate from the fish's own stored value so the buyer premium stays explicit and tunable.

### How to extend it later
Add buyer-specific trophy appetites or event-driven trophy bonuses without changing the fish data model.

### Known limitations
Only the fish buyer grants the explicit trophy bonus. Generic vendors still reject fish entirely.

2026-04-09 08:02:15
## TASK F-065 Region Value Modifier
### What was built
Added region-based value adjustments keyed off fish group so different waters can influence market value without rewriting catch formulas. Verification: the region modifier is applied during fish economy stamping before sales and inspection read the stored value.

### Example snippet
```python
modifier = REGION_VALUE_MODIFIERS.get(group_key, 1.0)
fish.db.value = max(1, int(base_value * modifier))
```

### Files touched
- `world/systems/fishing_economy.py`
- `world/systems/fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The economy layer adjusts a fish's stored value based on the region it came from. That keeps value differences data-driven and separate from catch odds.

### How to extend it later
Add town demand, seasonal multipliers, or travel distance bonuses by stacking onto the same helper.

### Known limitations
The region map is still a small static table. It does not yet respond to simulated supply or player overfishing.

2026-04-09 08:02:16
## TASK F-066 Overflow Handling
### What was built
Added explicit overflow handling for landed fish when the player cannot carry the catch and has no usable fish string. Verification: the DireTest scenario forces the no-capacity path and asserts the player gets a clear `nowhere to secure it` loss message instead of silent item deletion.

### Example snippet
```python
if fish is None:
	actor.msg("You land the fish, but you have nowhere to secure it and it slips away.")
```

### Files touched
- `world/systems/fishing.py`
- `world/systems/fishing_economy.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Landing a fish now checks whether it can be stored safely. If not, the catch is discarded deliberately and the player is told exactly why.

### How to extend it later
Add ground-drop behavior, room catch baskets, or temporary hand-held overflow states.

### Known limitations
Overflow currently resolves to loss when no valid storage exists. It does not yet offer a salvage or drop prompt.

2026-04-09 08:02:17
## TASK F-067 Look Fish Metadata
### What was built
Overrode fish appearance text so `look <fish>` now exposes fish type, weight, value, and trophy status from the item itself. Verification: the DireTest scenario runs `look silver trout` and asserts the metadata lines are present.

### Example snippet
```python
def return_appearance(self, looker, **kwargs):
	return fishing_economy.format_fish_inspection(self)
```

### Files touched
- `typeclasses/items/fish.py`
- `world/systems/fishing_economy.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fish inspection now comes from a single formatter that reads the stamped fish item. That keeps `look` and `weigh` consistent and makes the fish object the authority.

### How to extend it later
Add freshness, bait match history, or processing hints to the same inspection formatter.

### Known limitations
The inspection text is concise and functional. It does not yet include lore flavor or market advice.

2026-04-09 08:02:18
## TASK F-068 Expanded XP Hooks
### What was built
Added a light Mechanical Lore training hook on bait usage and preserved Outdoorsmanship training on actual fishing outcomes. Verification: the DireTest scenario records both skill pools before the run and asserts both increase by the end.

### Example snippet
```python
fishing_economy.award_bait_usage_xp(actor)
award_exp_skill(actor, "outdoorsmanship", difficulty, success=True, outcome="success")
```

### Files touched
- `world/systems/fishing.py`
- `world/systems/fishing_economy.py`
- `typeclasses/characters.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Preparing bait now teaches a little rigging knowledge while actual catches continue to teach field survival. The two hooks are separate so they can be balanced independently.

### How to extend it later
Add stronger appraisal or skinning hooks when fish cleaning and valuation systems arrive.

### Known limitations
The new Mechanical Lore hook is intentionally light and only tied to bait preparation for now.

2026-04-09 08:02:19
## TASK F-069 Buyer Rate Limiting and Economy DireTest
### What was built
Added fish-buyer throttling to stop rapid repeated sale spam and expanded the deterministic fishing scenario to cover single sale, bulk sale, trophy sale, rate limiting, weigh, look, stringing, auto-stringing, overflow messaging, leaderboard stub, and fish-specific payouts. Verification: `diretest.py scenario fishing-vertical-slice --seed 1234` now passes with the new economy coverage.

### Example snippet
```python
allowed, rate_limit_message = fishing_economy.can_use_fish_buyer(vendor, self)
if not allowed:
	self.msg(rate_limit_message)
```

### Files touched
- `typeclasses/characters.py`
- `world/systems/fishing_economy.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The buyer stores a short cooldown map in non-persistent runtime state and rejects immediate repeated fish sales. The scenario exercises that gate and then advances time to prove normal use resumes.

### How to extend it later
Add per-player daily quotas, buyer fatigue, or anti-bot market suspicion on top of the same throttle seam.

### Known limitations
The throttle is intentionally short and in-memory only. It is meant as interaction shaping, not account-level abuse prevention.

2026-04-09 08:02:20
## TASK F-070 Economy Cleanup and Observability
### What was built
Kept all Phase 4 economy hooks isolated in `world/systems/fishing_economy.py`, reused existing commands where possible, fixed the fishing DireTest metadata wiring so lag telemetry stays visible without masking logic regressions, and avoided changing Phase 1-3 catch formulas. Verification: touched files are error-clean and the deterministic scenario passes end to end with artifact output in `artifacts/fishing-vertical-slice_direct_1234`.

### Example snippet
```python
return _run_registered_scenario(
	args,
	scenario,
	auto_snapshot=False,
	name="fishing-vertical-slice",
	scenario_metadata=getattr(run_fishing_vertical_slice_scenario, "diretest_metadata", {}),
)
```

### Files touched
- `world/systems/fishing_economy.py`
- `world/systems/fishing.py`
- `commands/cmd_sell.py`
- `commands/cmd_stow.py`
- `commands/cmd_weigh.py`
- `commands/default_cmdsets.py`
- `typeclasses/characters.py`
- `typeclasses/items/fish.py`
- `typeclasses/items/fish_string.py`
- `typeclasses/fish_buyer.py`
- `typeclasses/weigh_station.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Phase 4 stays layered on top of the existing fishing loop. Catch math still lives in the fishing core, while economy, storage, inspection, and sale logic live in a separate module and are exercised by the scenario.

### How to extend it later
Add town market boards, fish-cleaning loops, buyer stock pressure, or persistent leaderboards from the economy layer without destabilizing the fishing state machine.

### Known limitations
Lag telemetry for the expanded scenario is intentionally informational because the scenario now covers a much larger interaction surface. The implementation behavior passes, but command timing still needs later tuning if this scenario becomes a performance gate.

2026-04-09 08:36:01
## TASK FW-011 Create Fishing Supplier/Buyer NPC
### What was built
Added `typeclasses/fishing_supplier.py` with `FishingSupplier`, a dual-role NPC named Old Maren that acts as both starter-gear supplier and fish buyer through the existing NPC inquiry and vendor seams. Verification: the fishing DireTest now spawns Old Maren, confirms the room can see her, and asserts her description and vendor flags reflect the combined role.

### Example snippet
```python
self.db.is_fishing_supplier = True
self.db.is_fish_buyer = True
self.db.is_vendor = True
```

### Files touched
- `typeclasses/fishing_supplier.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Supplier and buyer responsibilities are combined on one NPC so the test loop stays tight: one nearby character can hand out gear, receive catches, and complete the economy loop without extra travel or setup.

### How to extend it later
Split supply and buy roles into separate NPCs once town traffic, regional pricing, or shop inventory needs become more important than rapid loop testing.

### Known limitations
Old Maren is still a focused fishing-loop NPC. She does not yet sell stocked gear for coins or run a full shop catalog.

2026-04-09 08:36:02
## TASK FW-012 Place NPC in Room #4305
### What was built
Added a persistent server-start world hook that normalizes room `#4305` into Town Green NE with a pond-facing description, marks it fishable, and then ensures Old Maren is placed there and moved back on subsequent starts if displaced. Verification: the spawn helper now normalizes `#4305` before seeding the NPC, and a direct Django world check confirmed the room key and supplier location both resolve correctly at runtime.

### Example snippet
```python
room = ObjectDB.objects.get_id(4305)
room.key = "Town Green NE"
supplier = _ensure_named_npc("Old Maren", room, desc, typeclass="typeclasses.fishing_supplier.FishingSupplier")
```

### Files touched
- `server/conf/at_server_startstop.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The room placement is anchored to the live world dbref, and the startup hook corrects the room fiction before placing the supplier. That keeps the fishing loop colocated with an actual pond-side scene instead of relying on whichever older name happened to occupy the same dbref.

### How to extend it later
Move the spawn helper into a broader town bootstrap pass if more fishing-specific fixtures get seeded into the same district.

### Known limitations
This still assumes room `#4305` exists in the live world database. If the room is deleted or renumbered, the helper logs a warning and skips both the room normalization and the NPC spawn.

2026-04-09 08:36:03
## TASK FW-013 Add Ask For Gear Interaction
### What was built
Extended the existing `ask` command to accept `for` as an alternate inquiry delimiter and taught Old Maren to answer `ask maren for gear` by creating only the missing starter fishing items. Verification: the DireTest scenario requests gear through the dialogue path, confirms the items arrive, then repeats the request and confirms the kit is not duplicated infinitely.

### Example snippet
```python
if " for " in lowered:
	marker = " for "
```

### Files touched
- `commands/cmd_ask.py`
- `typeclasses/fishing_supplier.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The gear handout stays dialogue-driven instead of introducing a fishing-only command. Players ask the NPC directly, and the NPC-local inquiry handler decides what to give.

### How to extend it later
Add topic-specific dialogue for bait, records, rumors, or tutorials without expanding the command surface.

### Known limitations
The ask parser now accepts both `about` and `for`, but it is still a simple text split and does not support more complex phrasing.

2026-04-09 08:36:04
## TASK FW-014 Create Starter Fishing Pole
### What was built
Added `typeclasses/items/fishing_pole.py` with a minimal starter fishing pole carrying the expected pole flag, rating, and pre-rigged hook and line metadata. Verification: the DireTest scenario gets the pole from Old Maren and asserts the starter `pole_rating` is recognized as `10`.

### Example snippet
```python
self.db.is_fishing_pole = True
self.db.pole_rating = 10
self.db.line_attached = True
```

### Files touched
- `typeclasses/items/fishing_pole.py`
- `typeclasses/fishing_supplier.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The starter pole is treated as a pre-rigged baseline tool so new players can fish immediately once they have the kit. That keeps the starter flow simple while still letting the system read real gear metadata.

### How to extend it later
Add better rods with higher `pole_rating` or separate rigging states when real equipment assembly becomes important.

### Known limitations
The pole is intentionally simple and pre-rigged for testing, so it does not yet model wear, upgrades, detachable parts, or the deferred full assembly loop.

2026-04-09 08:36:05
## TASK FW-015 Ensure Minimal Gear Set Exists
### What was built
Old Maren now creates missing bait, hook, and line items with the required fishing flags, and the fishing cast gate now requires a pole plus a ready hook-and-line path before a cast can begin. Verification: the DireTest loop receives the minimal kit through dialogue, uses `bait` successfully, and the fishing system now rejects casting when the minimum gear is absent.

### Example snippet
```python
if pole is None:
	return False, "You need a fishing pole before you can fish."
```

### Files touched
- `typeclasses/fishing_supplier.py`
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The starter loop now guarantees the smallest usable kit exists: bait, hook, line, and a pole. That gives fishing a minimal viable gear layer instead of relying on invisible defaults.

### How to extend it later
Require explicit re-rigging when loose hooks or lines replace broken pole attachments.

### Known limitations
The current gear gate only checks for presence and simple attached-state flags. It does not yet model partial rigging or line quality loss.

2026-04-09 08:36:06
## TASK FW-016 Add Fish String + Auto-String Compatibility
### What was built
Old Maren now includes a fish string in the starter kit and surfaces the string-use hint when handing gear out, while the existing auto-string logic continues to place caught fish onto the carried string first. Verification: the DireTest scenario receives the fish string from the NPC and later confirms landed fish auto-secure to it.

### Example snippet
```python
if any(bool(getattr(getattr(item, "db", None), "is_fish_string", False)) for item in created):
	actor.msg("Thread your catch onto this if you plan to keep fishing.")
```

### Files touched
- `typeclasses/fishing_supplier.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The string closes the bulk-handling loop immediately: catch fish, keep fishing, and avoid hand-clogging inventory. That keeps repeated fishing practical without inventing a second storage system.

### How to extend it later
Offer upgraded creels or baskets from the same supplier once storage progression matters.

### Known limitations
The supplier only hands out the baseline fish string. There is no capacity-choice dialogue yet.

2026-04-09 08:36:07
## TASK FW-017 Integrate NPC With Existing Sell System
### What was built
Hooked Old Maren into the existing vendor path by marking her as a normal `is_vendor` target with `vendor_type = "fish_buyer"`, then kept `sell <item>` and `sell fish` on the standard character trade flow. Verification: the DireTest scenario sells fish successfully near Old Maren and confirms the same sale call fails away from her.

### Example snippet
```python
self.db.is_vendor = True
self.db.vendor_type = "fish_buyer"
```

### Files touched
- `typeclasses/fishing_supplier.py`
- `typeclasses/characters.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
No duplicate sell logic was added. Old Maren simply qualifies as a standard nearby vendor target, so the existing global sell command keeps doing the actual work.

### How to extend it later
Add buy-side vendor inventory or haggling flavor without changing the command routing.

### Known limitations
The specialized handling only applies to fish sales. Old Maren is not yet a general-purpose merchant.

2026-04-09 08:36:08
## TASK FW-018 Add Buyer Messaging Value Aware
### What was built
Updated fish-buyer reaction text to scale between low, medium, high, and trophy catches, and routed Old Maren’s sale line through that value-aware reaction helper. Verification: the DireTest scenario now asserts low or normal sales emit Maren’s standard feedback and trophy sales emit the special reaction branch.

### Example snippet
```python
if payout >= 80:
	return '"Now that\'s a fine fish."'
```

### Files touched
- `world/systems/fishing_economy.py`
- `typeclasses/fishing_supplier.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The sale message now mirrors the quality of the reward. That feedback makes the economy loop feel more legible and reinforces that bigger or rarer catches matter.

### How to extend it later
Add regional slang, mood swings, or species-specific enthusiasm while keeping the same payout tiers.

### Known limitations
The reaction system is still text-only. It does not yet affect reputation, repeat-business bonuses, or quest hooks.

2026-04-09 08:36:09
## TASK FW-019 Add Sell Bonus For Trophy Fish
### What was built
Added a vendor-local trophy sale multiplier seam and set Old Maren’s `trophy_sale_bonus_multiplier` to `1.25`, applied on top of the existing fish-buyer calculation without mutating `fish.db.value`. Verification: the DireTest scenario computes the expected Old Maren payout through the same vendor-aware helper used at runtime and confirms trophy sales return the higher total.

### Example snippet
```python
if bonus_multiplier > 1.0:
	value = max(1, int(round(float(value) * bonus_multiplier)))
```

### Files touched
- `world/systems/fishing_economy.py`
- `typeclasses/characters.py`
- `typeclasses/fishing_supplier.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The fish item still owns its stamped base value. Old Maren’s extra trophy enthusiasm is a local buyer bonus layered at sale time instead of rewriting the fish’s stored metadata.

### How to extend it later
Give different fishing buyers different trophy appetites by setting their own local multiplier values.

### Known limitations
The localized multiplier only applies when the seller is Old Maren or another vendor configured with that bonus attribute.

2026-04-09 08:36:10
## TASK FW-020 DireTest Expansion End To End Loop
### What was built
Expanded the deterministic fishing scenario to validate the full supplier loop: ask for gear, bait up, fish, auto-string the catch, sell to Old Maren, confirm the payout, confirm the trophy bonus path, and confirm fish sales fail when the buyer is not nearby. Verification: `diretest.py scenario fishing-vertical-slice --seed 1234` is the end-to-end deterministic check for the acquire -> fish -> store -> sell loop.

### Example snippet
```python
ctx.cmd("ask maren for gear")
ctx.cmd("fish")
ctx.cmd("sell fish")
```

### Files touched
- `diretest.py`
- `typeclasses/fishing_supplier.py`
- `typeclasses/items/fishing_pole.py`
- `world/systems/fishing.py`
- `world/systems/fishing_economy.py`
- `typeclasses/characters.py`
- `server/conf/at_server_startstop.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The scenario now validates the full loop instead of isolated mechanics. That gives one deterministic proof that acquisition, fishing, inventory handling, fish metadata, and selling still connect cleanly.

### How to extend it later
Carry the same scenario structure into Phase 5 once processing turns fish into materials and crafted outputs.

### Known limitations
The scenario still patches timing and RNG to stay deterministic, so it validates behavior and integration more than live pacing.

2026-04-09 10:55:44
## TASK F-071 Redirect Get Gear To Supplier
### What was built
Added a soft `get gear` redirect near Old Maren so players are pointed back to the dialogue-driven onboarding flow instead of grabbing an abstract bundle from the room. Verification: the fishing DireTest now runs `get gear` and asserts the supplier redirect text appears.

### Example snippet
```python
if normalized_query in {"gear", "starter kit"}:
	caller.msg("Ask me for gear and I'll hand it over properly.")
```

### Files touched
- `commands/cmd_get.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The normal pickup command checks for the fishing-gear shortcut and, when a fishing supplier is present, converts it into guidance instead of a literal pickup.

### How to extend it later
Add similar soft redirects for `get bait` or `get pole` if more guided onboarding is needed.

### Known limitations
The redirect is intentionally narrow and only triggers on a few starter-gear phrases.

2026-04-09 10:55:45
## TASK F-072 Reorder Supplier Guidance
### What was built
Adjusted Old Maren’s starter-kit response so the pole is named first and the spoken guidance now mirrors the intended beginner sequence. Verification: the DireTest scenario checks the updated ask-for-gear response path.

### Example snippet
```python
return f"Start with the pole, then mind your bait. I've set you up with {item_names}."
```

### Files touched
- `typeclasses/fishing_supplier.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The supplier still gives the same items, but the ordering and spoken instruction now teach the loop more clearly.

### How to extend it later
Split the response by player experience or room context if you want richer tutorial dialogue.

### Known limitations
The ordering is still static and does not inspect which item the player is missing most urgently.

2026-04-09 10:55:46
## TASK F-073 Add Gear Handoff Flavor
### What was built
Added a separate in-room handoff line before Old Maren’s spoken response so the starter kit feels physically handed over instead of purely abstract. Verification: the DireTest scenario now asserts the staged handoff text appears.

### Example snippet
```python
actor.msg("Old Maren stoops beside her baskets...")
```

### Files touched
- `typeclasses/fishing_supplier.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The supplier emits an action-style line first, then the normal quoted response, giving the exchange a stronger sense of place.

### How to extend it later
Add alternate handoff text when only one missing item is being replaced.

### Known limitations
The handoff text is not yet varied by gear type or player history.

2026-04-09 10:55:47
## TASK F-074 Strengthen Pond Cues
### What was built
Updated Town Green NE’s pond description so the fishing spot reads more alive, with reeds, insects, and surface rings hinting at active fish. Verification: the startup normalization now writes the richer pond description every time the room is refreshed.

### Example snippet
```python
"...drifting insects over the shallows..."
```

### Files touched
- `server/conf/at_server_startstop.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The server-start room normalizer now reinforces why this green exists as a fishing location instead of a generic plaza.

### How to extend it later
Add seasonal pond variants or local wildlife text without moving the room anchor.

### Known limitations
The cues are descriptive only and do not yet feed back into fish density or time-of-day logic.

2026-04-09 10:55:48
## TASK F-075 Route Skin Fish Through Existing Command
### What was built
Extended `Character.skin_target()` so `skin <fish>` now uses the same command surface as corpse skinning instead of adding a second fish-only processing command. Verification: the fishing DireTest now cleans a caught trout through `skin silver trout`.

### Example snippet
```python
if fishing_economy.is_fish_item(target):
	return self.skin_fish_target(target)
```

### Files touched
- `typeclasses/characters.py`
- `commands/cmd_skin.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The existing skin command now branches cleanly: corpses follow the old harvesting path, while fish follow the new processing path.

### How to extend it later
Add fish-specific tool variants without changing the command surface again.

### Known limitations
Fish processing still requires a wielded skinning knife just like the broader skinning loop.

2026-04-09 10:55:49
## TASK F-076 Add Fish Material Objects
### What was built
Created a dedicated processed-fish item typeclass so cleaned fillets and skins carry stable metadata, value, and inspection text. Verification: the DireTest scenario confirms `fish_meat` and `fish_skin` items are produced after processing.

### Example snippet
```python
self.db.item_type = "fish_meat"
```

### Files touched
- `typeclasses/items/fish_material.py`
- `typeclasses/characters.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Processed fish goods are now first-class inventory objects rather than ad hoc dicts or temporary placeholders.

### How to extend it later
Turn quantity-bearing fish goods into stacked items if inventory compression becomes important.

### Known limitations
The materials are separate objects per processing result rather than a shared stack system.

2026-04-09 10:55:50
## TASK F-077 Let Buyers Accept Processed Fish Goods
### What was built
Expanded fish-buyer acceptance so Old Maren now buys `fish`, `fish_meat`, and `fish_skin` through the same vendor path. Verification: the fishing DireTest now sells processed goods with `sell fish` and checks the payout.

### Example snippet
```python
self.db.accepted_item_types = ["fish", "fish_meat", "fish_skin"]
```

### Files touched
- `typeclasses/fishing_supplier.py`
- `typeclasses/characters.py`
- `server/conf/at_server_startstop.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Processed goods reuse the same vendor routing and fish-buyer specialization instead of inventing a parallel trade system.

### How to extend it later
Differentiate which buyers want skins versus fillets if more specialized markets are added.

### Known limitations
All fish buyers currently accept both processed material types equally.

2026-04-09 10:55:51
## TASK F-078 Add Fish Processing Skill Contest
### What was built
Fish cleaning now runs a real skinning contest using Skinning plus Agility and Discipline, with fish difficulty feeding the check. Verification: the new path calls `run_contest(...)` and the DireTest scenario exercises the success branch deterministically.

### Example snippet
```python
result = run_contest(skill_total, difficulty, attacker=self)
```

### Files touched
- `typeclasses/characters.py`
- `world/systems/fishing_economy.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Cleaning a fish is now a real skill action, not just a guaranteed transform.

### How to extend it later
Add tool-quality modifiers or species-specific processing difficulties on top of the same contest.

### Known limitations
The current yields still come from a simple difficulty-and-weight profile rather than per-species anatomy rules.

2026-04-09 10:55:52
## TASK F-079 Add Fish Processing Failure Yields
### What was built
Implemented degraded yields and different player messaging for failed, partial, successful, and exceptional fish-processing outcomes. Verification: the new processing method now mutates meat and skin yield by contest outcome before creating items.

### Example snippet
```python
if outcome == "fail":
	meat_yield = max(0, meat_yield - 1)
```

### Files touched
- `typeclasses/characters.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Bad cleaning still may salvage something, but sloppy work now wastes material and says so explicitly.

### How to extend it later
Add ruined-scrap byproducts if failure should still leave vendor trash or bait stock.

### Known limitations
The failure branch currently destroys the source fish immediately even when salvage is poor.

2026-04-09 10:55:53
## TASK F-080 Add Processed Goods Inspection Data
### What was built
Added formatted inspection output for processed fish goods so quantity, source species, material type, and stored value are visible on look. Verification: the new `FishMaterial.return_appearance()` delegates into the fishing economy formatter.

### Example snippet
```python
lines.append(f"From: {source}")
```

### Files touched
- `typeclasses/items/fish_material.py`
- `world/systems/fishing_economy.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Processed goods now inspect cleanly instead of looking like generic unnamed loot.

### How to extend it later
Include freshness or preservation state once fish spoilage exists.

### Known limitations
The formatter reports aggregate value only and does not break out per-unit pricing.

2026-04-09 10:55:54
## TASK F-081 Add Persistent Empath Strain State
### What was built
Added `db.empath_strain` to the character default bootstrap so the new fishing-side empath pressure persists cleanly. Verification: `ensure_core_defaults()` now seeds the field when absent.

### Example snippet
```python
if getattr(self.db, "empath_strain", None) is None:
	self.db.empath_strain = 0
```

### Files touched
- `typeclasses/characters.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Empath strain now lives alongside the existing empath shock and wound state instead of hiding in temporary runtime flags.

### How to extend it later
Expose the field in the client HUD once the right UX language settles.

### Known limitations
Only empaths meaningfully use the field; non-empaths are hard-reset to zero.

2026-04-09 10:55:55
## TASK F-082 Add Empath Strain Helpers
### What was built
Added helper methods for reading, setting, adjusting, and decaying empath strain plus fishing and tangle modifiers derived from the current strain tier. Verification: the new helper surface is used by both fishing formulas and the empath tick loop.

### Example snippet
```python
def get_empath_strain_fishing_modifier(self):
	...
```

### Files touched
- `typeclasses/characters.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fishing no longer needs to know the details of empath-state thresholds; it asks the character for the relevant modifier.

### How to extend it later
Reuse the same helpers for healing, rituals, or crowded-room empathy penalties.

### Known limitations
The thresholds are still hardcoded tiers rather than data-driven config.

2026-04-09 10:55:56
## TASK F-083 Add Cast Strain Hook
### What was built
Starting a fishing cast now adds a small empath strain event so repeated fishing attempts have a low but persistent cost for empaths. Verification: the fishing system now calls `_apply_empath_strain(..., "cast")` when a cast starts.

### Example snippet
```python
_apply_empath_strain(actor, "cast", amount=2, fish_profile=fish_profile)
```

### Files touched
- `world/systems/fishing.py`
- `typeclasses/characters.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Even the setup phase now nudges strain upward, making long sessions feel cumulative for empath characters.

### How to extend it later
Tie the cast cost to ambient life density or room population if you want more situational pressure.

### Known limitations
The cast event uses a small flat amount instead of a species- or room-aware cost.

2026-04-09 10:55:57
## TASK F-084 Add Hook And Struggle Strain Hooks
### What was built
Hooking, ongoing struggle rounds, and landing a fish now each add heavier empath strain based on fish difficulty. Verification: the fishing system fires event-specific strain calls from the hook and struggle flow.

### Example snippet
```python
_apply_empath_strain(actor, "hook", amount=..., fish_profile=fish_profile)
```

### Files touched
- `world/systems/fishing.py`
- `typeclasses/characters.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The more intense parts of the catch now hit harder than a simple cast, so empath strain scales with the living struggle instead of staying flat.

### How to extend it later
Differentiate schooling fish, predators, and trophies with custom strain curves.

### Known limitations
Only difficulty feeds the current scaling, not fish size or fight-profile flavor.

2026-04-09 10:55:58
## TASK F-085 Apply Strain To Fishing Odds
### What was built
Fishing rating, nibble chance, hook chance, and struggle landing odds now read empath strain modifiers from the actor. Verification: deterministic simulation output shows lower nibble and hook rates at strain `60`.

### Example snippet
```python
chance *= float(actor.get_empath_strain_fishing_modifier() or 1.0)
```

### Files touched
- `world/systems/fishing.py`
- `typeclasses/characters.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Higher empath strain makes fishing less steady without fully disabling the activity.

### How to extend it later
Fold strain into lure-selection advice or warning text when the penalties get large.

### Known limitations
The modifier is multiplicative and global, so it does not yet discriminate between sub-actions.

2026-04-09 10:55:59
## TASK F-086 Apply Strain To Tangle Risk
### What was built
Timeout tangles now scale upward for strained empaths through a separate tangle modifier helper. Verification: the deterministic simulation report shows the timeout-tangle rate rising from `0.1490` to `0.1818` at strain `60`.

### Example snippet
```python
chance *= float(actor.get_empath_strain_tangle_modifier() or 1.0)
```

### Files touched
- `world/systems/fishing.py`
- `typeclasses/characters.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Strain now shows up not just in landing success, but in line-management mistakes too.

### How to extend it later
Apply the same modifier to rigging failures if live play suggests the systems should feel more connected.

### Known limitations
Only missed-bite tangles currently read the separate tangle modifier directly.

2026-04-09 10:56:00
## TASK F-087 Add Strain Decay Tick
### What was built
Extended `process_empath_tick()` with a separate timed decay path for empath strain, with slower decay while channeling and faster decay in recovery spaces. Verification: the fishing DireTest now adds strain, advances time, runs the tick, and confirms the value drops.

### Example snippet
```python
self.ndb.next_empath_strain_decay_at = now + 20.0
```

### Files touched
- `typeclasses/characters.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fishing strain now naturally fades over time instead of accumulating permanently.

### How to extend it later
Make inns, shrines, or profession spaces accelerate decay through room tags.

### Known limitations
Decay only occurs through the empath tick loop and does not yet react to explicit rest actions.

2026-04-09 10:56:01
## TASK F-088 Add Strain Feedback Messaging
### What was built
Added threshold messaging for empath strain both when the value changes and during periodic empath feedback ticks. Verification: the strain helper and tick loop now emit distinct low- and high-strain text.

### Example snippet
```python
elif self.get_empath_strain() >= 40:
	self.msg("You feel a low empathic strain under your thoughts.")
```

### Files touched
- `typeclasses/characters.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Empaths now get readable feedback before the penalties become invisible frustration.

### How to extend it later
Mirror the same text into client-state indicators or status commands.

### Known limitations
The feedback is textual only and does not yet appear in a dedicated command output.

2026-04-09 10:56:02
## TASK F-089 Persist Pole Tangles On The Item
### What was built
Moved fishing tangles onto the actual pole object with `db.line_tangled`, while still keeping the session state in sync. Verification: the DireTest scenario now checks the pole flag directly after tangle and untangle flows.

### Example snippet
```python
pole.db.line_tangled = True
```

### Files touched
- `typeclasses/items/fishing_pole.py`
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The line’s physical state now lives on the pole instead of disappearing with the transient session object.

### How to extend it later
Add visible pole-condition text so players can inspect tangles directly.

### Known limitations
Only tangles are persisted right now; broader wear and tear are still absent.

2026-04-09 10:56:03
## TASK F-090 Add Rig Pole Command
### What was built
Added `rig pole` as a player command that reattaches a broken line and hook path using the loose starter components. Verification: the fishing DireTest now forces a broken line, runs `rig pole`, and confirms the line is attached again.

### Example snippet
```python
_ok, message = rig_fishing_pole(caller)
```

### Files touched
- `commands/cmd_fishing.py`
- `commands/default_cmdsets.py`
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Broken poles are no longer magically fixed by baiting; players have to re-rig the tackle first.

### How to extend it later
Consume replacement hooks or line lengths when a real gear-economy sink is wanted.

### Known limitations
The current rig command only checks that loose hook and line items exist, not that they are consumed.

2026-04-09 10:56:04
## TASK F-091 Add Untangle Pole Command
### What was built
Added `untangle pole` so players can manually clear snarled line state instead of relying on hidden reset behavior. Verification: the fishing DireTest now forces a pole tangle and confirms the command clears it.

### Example snippet
```python
_ok, message = untangle_fishing_pole(caller)
```

### Files touched
- `commands/cmd_fishing.py`
- `commands/default_cmdsets.py`
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Tangled fishing state is now recoverable through an explicit maintenance step.

### How to extend it later
Require a little time or balance cost if untangling should become a bigger interruption.

### Known limitations
Untangling is still instant and does not consume any materials.

2026-04-09 10:56:05
## TASK F-092 Award Mechanical Lore For Rigging
### What was built
Rigging and untangling now award Mechanical Lore experience on both success and failure, with smaller failure credit. Verification: the vertical-slice scenario records the new gear-maintenance branches and the skill award path runs without errors.

### Example snippet
```python
award_exp_skill(actor, "mechanical_lore", 10, success=True, ...)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Maintaining fishing gear now teaches the same lore skill that bait handling already nudged.

### How to extend it later
Add different experience weights for fast field repairs versus workshop-grade rigging.

### Known limitations
The current awards are fixed values and do not yet scale with gear tier.

2026-04-09 10:56:06
## TASK F-093 Add Gear Redirect Regression Test
### What was built
Extended the fishing DireTest to explicitly cover the new `get gear` redirect behavior. Verification: `fishing-vertical-slice` now fails if the supplier hint text disappears.

### Example snippet
```python
ctx.cmd("get gear")
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The onboarding redirect is now protected by the deterministic harness instead of relying on manual memory.

### How to extend it later
Add negative tests for rooms without a supplier so the shortcut stays context-sensitive.

### Known limitations
The test currently covers only the happy-path room with Old Maren present.

2026-04-09 10:56:07
## TASK F-094 Add Rigging Regression Test
### What was built
Expanded the DireTest scenario to validate both broken-line repair via `rig pole` and pole-tangle recovery via `untangle pole`. Verification: the scenario now asserts both item flags and output text.

### Example snippet
```python
ctx.cmd("rig pole")
ctx.cmd("untangle pole")
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The new maintenance loop is part of the same deterministic end-to-end harness as the rest of fishing.

### How to extend it later
Add a forced rigging-failure branch once command-side retries matter.

### Known limitations
The current scenario only covers the successful maintenance path.

2026-04-09 10:56:08
## TASK F-095 Add Fish Processing Regression Test
### What was built
Extended the fishing DireTest so it now creates a caught fish, runs `skin silver trout`, and asserts that processed goods are created while the source fish is consumed. Verification: `fishing-vertical-slice` now protects the full processing branch.

### Example snippet
```python
ctx.cmd("skin silver trout")
```

### Files touched
- `diretest.py`
- `typeclasses/characters.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fish processing is now part of the core regression story instead of a manual-only check.

### How to extend it later
Add explicit failure-branch coverage by patching the contest result.

### Known limitations
The scenario uses a deterministic success branch today.

2026-04-09 10:56:09
## TASK F-096 Add Processed Goods Sale Regression Test
### What was built
The DireTest now sells processed fish goods through the fish-buyer loop and asserts the exact expected payout. Verification: `sell fish` now covers processed materials in the regression harness.

### Example snippet
```python
expected_processed_sale = sum(...)
```

### Files touched
- `diretest.py`
- `typeclasses/characters.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The harness now proves the new processing economy path does not bypass or break the existing sale system.

### How to extend it later
Add a negative test for general vendors refusing processed fish goods.

### Known limitations
The test currently only validates Old Maren’s fish-buyer path.

2026-04-09 10:56:10
## TASK F-097 Add Empath Strain Regression Test
### What was built
Added deterministic DireTest coverage that converts the test character into an empath, applies fishing strain, advances time, and confirms strain decays. Verification: `fishing-vertical-slice` now fails if the strain helper or decay tick regress.

### Example snippet
```python
character.apply_fishing_empath_strain("hook", amount=4, ...)
```

### Files touched
- `diretest.py`
- `typeclasses/characters.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The strain system now has at least one automated proof of gain and decay behavior.

### How to extend it later
Add a dedicated empath-only scenario for higher-strain tiers and message assertions.

### Known limitations
The vertical slice covers the baseline gain/decay path, not every threshold message.

2026-04-09 10:56:11
## TASK F-098 Harden Buyer Throttle Test
### What was built
Made the existing fish-buyer throttle assertion deterministic even after the new processed-goods sale path added another trade step. Verification: the scenario now seeds the throttle map directly before the blocked trophy sale assertion.

### Example snippet
```python
supplier.ndb.fish_buyer_throttle = {...}
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The rate-limit regression no longer depends on the precise ordering of earlier sale timestamps inside the scenario.

### How to extend it later
Replace the direct throttle seeding with a reusable test helper if more buyer throttles appear.

### Known limitations
This is a test-side hardening step; the runtime throttle behavior itself did not change.

2026-04-09 10:56:12
## TASK F-099 Expand Vertical Slice Coverage
### What was built
Broadened the `fishing-vertical-slice` scenario to cover supplier UX, rigging, untangling, fish processing, processed sales, and empath strain on top of the earlier fishing loop. Verification: the updated scenario now passes end to end with the new branches included.

### Example snippet
```python
ctx.cmd("get gear")
ctx.cmd("rig pole")
ctx.cmd("skin silver trout")
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
One deterministic script now guards almost the full beginner fishing loop and its new maintenance and processing branches.

### How to extend it later
Split some of the later branches into focused secondary scenarios if this one becomes too large to maintain comfortably.

### Known limitations
The scenario is broader now, so its failure output can be denser to diagnose when multiple systems shift at once.

2026-04-09 10:56:13
## TASK F-100 Pass Deterministic Phase 5 Validation
### What was built
Ran the updated vertical-slice harness successfully after the Phase 5 code changes. Verification: `c:/Users/gary/dragonsire/.venv/Scripts/python.exe diretest.py scenario fishing-vertical-slice` passed at seed `62597400`.

### Example snippet
```python
PASS: fishing-vertical-slice
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The deterministic harness is the primary proof that the new UX, gear, processing, and empath work still integrate cleanly.

### How to extend it later
Add a second scenario for simulation/report generation if those numbers need to be recomputed in CI.

### Known limitations
The pass still reported lag telemetry spikes, but the scenario metadata already treats lag as reportable rather than fatal for this workflow.

2026-04-09 10:56:14
## TASK F-101 Build Simulation Baseline
### What was built
Ran a deterministic formula-level fishing simulation covering River 1 and River 3 profiles to establish baseline nibble, hook, tangle, and struggle outcome rates. Verification: the results were written into the new simulation report.

### Example snippet
```python
data = fs.resolve_struggle_outcome_data(actor, session, profile, bait, rng=rng)
```

### Files touched
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The report now includes measured baseline rates instead of only design intent.

### How to extend it later
Capture the same simulation data as JSON if external graphing becomes useful.

### Known limitations
This pass uses a lightweight dummy actor rather than a fully simulated in-world character.

2026-04-09 10:56:15
## TASK F-102 Compare Empath Strain In Simulation
### What was built
Added a simulation comparison showing how strain `60` changes nibble, hook, and timeout-tangle rates for a River 1 trout profile. Verification: the report records the strained numbers beside the baseline values.

### Example snippet
```python
"river1_worm_strained": sim(..., strain=60)
```

### Files touched
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The empath strain system now has a measured balance footprint instead of only a theoretical penalty curve.

### How to extend it later
Add multiple strain tiers so the curve can be graphed instead of sampled at one point.

### Known limitations
Only one strain tier was sampled in this first report.

2026-04-09 10:56:16
## TASK F-103 Compare Bait Match In Simulation
### What was built
Recorded a side-by-side River 1 worm-versus-lure comparison to show that bait mismatch still mostly hurts hook conversion rather than bite frequency. Verification: the report includes both profiles and the measured hook-rate drop.

### Example snippet
```python
"river1_lure": sim(silver, lure, "River 1", 400, 0)
```

### Files touched
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The simulation confirms the current formulas let better-quality mismatched bait still attract some attention while making solid hookups harder.

### How to extend it later
Add more bait families once freshwater and ocean bait catalogs expand.

### Known limitations
The report only samples one mismatched bait case.

2026-04-09 10:56:17
## TASK F-104 Compare Difficulty Bands In Simulation
### What was built
Added a harder-water sample using glass sturgeon in River 3 to expose how advanced profiles stress hook rates and line-break risk. Verification: the report shows the high break count for that profile.

### Example snippet
```python
"river3_sturgeon": sim(sturgeon, worm, "River 3", 400, 0)
```

### Files touched
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The report now includes a warning sample from a much harsher water band, making it easier to spot where starter gear stops being appropriate.

### How to extend it later
Add better-gear simulations to measure how much of River 3’s pain is intentional versus gear-starved.

### Known limitations
Only one hard profile was sampled, so the upper-tier curve is still coarse.

2026-04-09 10:56:18
## TASK F-105 Create Simulation Report File
### What was built
Created `docs/systems/fishingSimulationReport.md` as the dedicated home for deterministic fishing balance notes and results. Verification: the file now exists in `docs/systems/` with the captured simulation output.

### Example snippet
```python
# Fishing Simulation Report
```

### Files touched
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fishing now has a durable report file separate from the implementation log, so balance notes do not have to be buried inside as-built entries.

### How to extend it later
Append future simulation passes instead of overwriting the original baseline if you want a historical trail.

### Known limitations
The first report is a single snapshot rather than a rolling changelog.

2026-04-09 10:56:19
## TASK F-106 Summarize Simulation Findings
### What was built
Documented the main simulation takeaways: bait mismatch hits hooks most, River 3 is punishing on starter-grade tackle, and empath strain is visible but not fully disabling. Verification: those findings are now written explicitly in the report body.

### Example snippet
```python
1. Matching bait still matters most at the hook stage.
```

### Files touched
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The report now does more than dump numbers; it interprets the balance signals those numbers suggest.

### How to extend it later
Attach player-facing recommendations or design follow-ups after more live data comes in.

### Known limitations
The findings are still based on one deterministic pass rather than live telemetry.

2026-04-09 10:56:20
## TASK F-107 Verify Command Set Integration
### What was built
Registered `rig` and `untangle` in the default command set so the new maintenance commands are actually available to players. Verification: the updated file compiles cleanly and the DireTest scenario exercises both commands successfully.

### Example snippet
```python
self.add(CmdRig())
```

### Files touched
- `commands/default_cmdsets.py`
- `commands/cmd_fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The commands are not just implemented; they are now wired into the normal player cmdset.

### How to extend it later
Move them into a survival-specific cmdset only if command-surface crowding becomes a problem.

### Known limitations
They are globally available commands right now, even to characters who never fish.

2026-04-09 10:56:21
## TASK F-108 Verify Buyer Workflow Integration
### What was built
Confirmed that processed goods, trophy fish, and bulk fish sales all continue to flow through the same vendor and fish-buyer systems. Verification: the updated vertical-slice scenario covers single sale, blocked rapid sale, trophy sale, and bulk processed sale branches.

### Example snippet
```python
if fishing_economy.is_fish_trade_item(item):
	...
```

### Files touched
- `typeclasses/characters.py`
- `world/systems/fishing_economy.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The broader fishing economy still has one sale path, even though more item types now qualify.

### How to extend it later
Add separate processed-goods reactions or price tables without splitting the vendor API.

### Known limitations
Processed goods currently use simple stored values rather than a richer market model.

2026-04-09 10:56:22
## TASK F-109 Verify Processing Workflow Integration
### What was built
Confirmed the full caught-fish processing loop works end to end: catch fish, inspect it, clean it, inspect the resulting goods, and sell them. Verification: the vertical-slice scenario now covers the critical transitions in that loop.

### Example snippet
```python
processed_goods = [obj for obj in character.contents if ...]
```

### Files touched
- `typeclasses/characters.py`
- `typeclasses/items/fish_material.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Processing is now part of the actual fishing lifecycle instead of a disconnected crafting concept.

### How to extend it later
Feed processed goods into cooking, preserving, or tanning recipes once those loops are ready.

### Known limitations
The loop ends at sale right now and does not yet branch into crafting systems.

2026-04-09 10:56:23
## TASK F-110 Final Phase 5 Validation Sweep
### What was built
Completed a final validation pass across code compilation, deterministic fishing regression, and the new simulation report so the Phase 5 fishing slice closes with measured verification rather than code edits alone. Verification: `get_errors` returned clean results for all changed gameplay files, `fishing-vertical-slice` passed, and the simulation report was written.

### Example snippet
```python
PASS: fishing-vertical-slice
```

### Files touched
- `commands/cmd_fishing.py`
- `commands/default_cmdsets.py`
- `commands/cmd_get.py`
- `typeclasses/fishing_supplier.py`
- `typeclasses/items/fish_material.py`
- `typeclasses/items/fishing_pole.py`
- `typeclasses/characters.py`
- `world/systems/fishing.py`
- `world/systems/fishing_economy.py`
- `server/conf/at_server_startstop.py`
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The phase is closed out with both behavior checks and written balance notes, which makes the work easier to trust and easier to revisit.

### How to extend it later
Keep appending future fishing slices here and rerun the same deterministic scenario plus simulation baseline after each batch.

### Known limitations
The validation sweep still relies on one broad deterministic scenario instead of multiple smaller targeted scenarios.

2026-04-09 11:42:41
## TASK F-111 Add Grouped Junk Tables
### What was built
Added `JUNK_TABLES` to `world/systems/fishing.py` so junk outcomes now come from explicit per-water-group tables instead of a generic text branch. Verification: the new junk/event DireTest slice samples River and Ocean groups separately.

### Example snippet
```python
JUNK_TABLES["River 1"]["common"]
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Each fish group now owns its own common junk, valuable junk, and event entries.

### How to extend it later
Add swamp, sewer, or cave-water junk tables without changing the resolution flow.

### Known limitations
Only the current fishing groups have authored tables.

2026-04-09 11:42:42
## TASK F-112 Add Common River Junk Entries
### What was built
Authored common junk entries such as weeds, broken branch, old boot, and tangled line for River 1 and parallel common entries for the other water groups. Verification: common junk now spawns as physical objects instead of text-only results.

### Example snippet
```python
{"key": "old_boot", "name": "old boot", "value": 2}
```

### Files touched
- `world/systems/fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Low-value salvage now comes from authored data rather than hardcoded messages.

### How to extend it later
Add more filler junk for each region to widen the pool without affecting code.

### Known limitations
Common junk values are still simple fixed coin values.

2026-04-09 11:42:43
## TASK F-113 Add Valuable Junk Entries
### What was built
Added interesting salvage entries such as coin pouch, rusted dagger, trinket, and lost charm with higher values and distinct pull text. Verification: the junk/event DireTest forces an interesting pull and confirms the rare-find message appears.

### Example snippet
```python
{"key": "lost_charm", "name": "lost charm", "value": 16}
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Interesting junk gives the fishing loop a small surprise tier between trash and fish.

### How to extend it later
Add lore-bearing relics or quest hooks as additional interesting entries.

### Known limitations
Interesting junk still sells through flat stored values rather than appraisal.

2026-04-09 11:42:44
## TASK F-114 Add Weighted Junk Selection
### What was built
Added `choose_weighted_junk_profile()` so each junk tier uses weighted selection and stays scoped to the requested fish group. Verification: the junk/event DireTest asserts River 1, River 2, and Ocean samples do not cross-contaminate.

### Example snippet
```python
profile = choose_weighted_junk_profile(room, "common")
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The system now picks junk from weighted authored data instead of one flat branch.

### How to extend it later
Add season or room modifiers on top of the same selector.

### Known limitations
Weights are currently group-level only, not room-specific.

2026-04-09 11:42:45
## TASK F-115 Add Junk Item Typeclass
### What was built
Created `typeclasses/items/junk.py` and a junk spawn path so salvage is now a real inventory object with value, tier, and source metadata. Verification: pulling junk now leaves a sellable item in inventory.

### Example snippet
```python
self.db.item_type = "junk"
```

### Files touched
- `typeclasses/items/junk.py`
- `world/systems/fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Junk is now handled like other game objects instead of only as output text.

### How to extend it later
Add custom appearances, stack rules, or salvage crafting hooks.

### Known limitations
Junk items do not yet have durability or material tags.

2026-04-09 11:42:46
## TASK F-116 Add Rare Junk Pull Messaging
### What was built
Added a special message for interesting salvage so rare junk announces itself with distinct feedback before the item lands. Verification: the forced valuable-junk DireTest checks for `You pull something unexpected from the water...`.

### Example snippet
```python
actor.msg("You pull something unexpected from the water...")
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Interesting junk now feels different the moment it resolves.

### How to extend it later
Add tier-specific sound, room, or companion reactions.

### Known limitations
Only the interesting junk tier has special pull messaging.

2026-04-09 11:42:47
## TASK F-117 Route Junk Through Fish Buyer Economy
### What was built
Expanded the fishing economy and Old Maren's accepted item types so junk can sell through the existing fish-buyer path. Verification: the junk/event DireTest sells a forced junk item to Old Maren and checks the coin delta.

### Example snippet
```python
return is_fish_item(item) or is_processed_fish_item(item) or is_junk_item(item)
```

### Files touched
- `world/systems/fishing_economy.py`
- `typeclasses/fishing_supplier.py`
- `typeclasses/characters.py`
- `server/conf/at_server_startstop.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Salvage reuses the same vendor flow, payout path, and buyer messaging as other fishing trade items.

### How to extend it later
Split salvage buyers off later if different NPC markets are needed.

### Known limitations
All junk currently sells to the same fish buyer rather than a dedicated salvage merchant.

2026-04-09 11:42:48
## TASK F-118 Add Event Outcome Category
### What was built
Added an explicit `event` fishing outcome so the system can resolve dangerous hooks separately from fish and junk. Verification: `_begin_nibble()` now sets `session.state = "event"` when the weighted outcome rolls into the event tier.

### Example snippet
```python
return {"category": "event", "profile": ...}
```

### Files touched
- `world/systems/fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Events are now a first-class fishing result instead of something implied by fish struggle failures.

### How to extend it later
Add more event profiles without changing the state machine again.

### Known limitations
Only one event profile is currently authored.

2026-04-09 11:42:49
## TASK F-119 Add Violent Tug Messaging
### What was built
Added the violent tug hook message so event rolls announce themselves immediately with a distinct non-fish tone. Verification: the junk/event DireTest confirms the event profile resolves to the violent tug path.

### Example snippet
```python
"hook_message": "Your line jerks violently -- this is no fish."
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Players now get an instant fiction cue that the line caught something dangerous or strange.

### How to extend it later
Vary the hook message by fish group or event type.

### Known limitations
Event flavor is still authored as static strings.

2026-04-09 11:42:50
## TASK F-120 Resolve Safe-Zone Events Without Spawns
### What was built
Implemented safe-zone event resolution that snaps the line, clears the session, and never spawns an NPC encounter. Verification: the junk/event DireTest runs the event path in a safe-zone room and asserts no NPC count increase.

### Example snippet
```python
if getattr(room.db, "safe_zone", False):
	return None
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Town-safe fishing can still have danger flavor without violating room safety rules.

### How to extend it later
Allow non-safe rooms to opt into future encounter spawns through the same hook.

### Known limitations
Safe-zone events always resolve as line breaks right now.

2026-04-09 11:42:51
## TASK F-121 Add Disabled Encounter Hook
### What was built
Added `maybe_spawn_encounter()` as a no-op gate for future fishing encounters while keeping the current implementation disabled by default. Verification: event resolution now passes through a dedicated encounter seam even though it returns `None`.

### Example snippet
```python
if not bool(profile.get("encounter_enabled", False)):
	return None
```

### Files touched
- `world/systems/fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The code now has a stable future extension point for encounters without enabling them today.

### How to extend it later
Spawn scripted water threats in non-safe rooms through this seam.

### Known limitations
The hook intentionally does nothing in the current slice.

2026-04-09 11:42:52
## TASK F-122 Add Event Choice Prompt Hook
### What was built
Added `get_event_choice_prompt()` so the event system already exposes a structured future choice surface (`pull_harder` or `release`). Verification: the junk/event DireTest checks that the prompt exists and contains the authored choice text.

### Example snippet
```python
return {"prompt": "Pull harder or release?", "options": ["pull_harder", "release"]}
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The system can now surface future player decisions without redesigning event data later.

### How to extend it later
Wire these options into actual commands or timed reactions.

### Known limitations
The prompt is informational only in this batch.

2026-04-09 11:42:53
## TASK F-123 Replace Flat Junk Probability Model
### What was built
Removed the old flat junk-chance branch and replaced it with `OUTCOME_WEIGHTS` plus `roll_fishing_outcome()`. Verification: `_begin_nibble()` now rolls fish, junk, or event from weighted authored data and no longer uses `calculate_junk_chance()`.

### Example snippet
```python
outcome = roll_fishing_outcome(room)
```

### Files touched
- `world/systems/fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The fishing loop now decides broad outcome type from a weighted table before it resolves the specific content.

### How to extend it later
Add room or bait modifiers to the outcome weights.

### Known limitations
Outcome weights are still authored as simple percentages per group.

2026-04-09 11:42:54
## TASK F-124 Add Long-Form Simulation Scenario
### What was built
Added `fishing-simulation-100` to `diretest.py` and registered it in the CLI parser. Verification: the scenario now runs as a named DireTest entry and writes the balance report.

### Example snippet
```python
@register_scenario("fishing-simulation-100")
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The fishing system now has a dedicated repeatable simulation harness instead of relying only on the vertical slice.

### How to extend it later
Add args for run count, fish group, or seed overrides.

### Known limitations
The run count is currently fixed in code.

2026-04-09 11:42:55
## TASK F-125 Simulate Full Fishing Loop Per Run
### What was built
Implemented a per-run command loop that asks Maren for gear, rigs the pole, baits, fishes, pulls, resolves, then skins and sells fish outcomes. Verification: the passing simulation scenario logs 1800 commands across two 100-run passes.

### Example snippet
```python
ctx.cmd("ask maren for gear")
ctx.cmd("fish")
ctx.cmd("pull")
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Each run uses the real command surface rather than direct object fabrication.

### How to extend it later
Add alternate bait or skill profiles as new simulation cohorts.

### Known limitations
The harness normalizes pole state between runs to avoid cross-run residue.

2026-04-09 11:42:56
## TASK F-126 Record Per-Run Outcome Data
### What was built
Added per-run records for outcome type, caught fish, junk item, sale value, and failure reason. Verification: the simulation summary stores `run_records` for each pass.

### Example snippet
```python
record = {"run": run_index, "outcome": None, "sale_value": 0}
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The report is built from actual run-by-run data instead of only final counters.

### How to extend it later
Persist raw run records to a JSON artifact if deeper analysis is needed.

### Known limitations
The markdown report summarizes counts instead of printing every run.

2026-04-09 11:42:57
## TASK F-127 Track Event Damage Metrics
### What was built
Added counters for violent tug events, line breaks, and gear damage events inside the simulation harness. Verification: the generated report now prints total violent tug events and total line breaks.

### Example snippet
```python
summary["line_breaks"] += 1
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Danger events are now measured as part of balance validation, not just flavor text.

### How to extend it later
Track broken hooks, torn bait, or repair costs separately.

### Known limitations
Only line-break style event damage is modeled right now.

2026-04-09 11:42:58
## TASK F-128 Track XP And Mindstate Progression
### What was built
Added Outdoorsmanship and Skinning pool/mindstate snapshots to the simulation summary and report. Verification: the report now shows Outdoorsmanship pool gain and mindstate start/end for both passes.

### Example snippet
```python
skill_snapshot(character, "outdoorsmanship")
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The simulation now measures how the loop teaches, not just what it pays.

### How to extend it later
Track Trading, Mechanical Lore, or Empath strain trends too.

### Known limitations
Skinning pool remained flat in the current deterministic harness pass.

2026-04-09 11:42:59
## TASK F-129 Compare Actual And Expected Distribution
### What was built
Added expected River 1 outcome percentages and actual-vs-expected comparison lines in the report. Verification: the report now prints expected 64/28/6/2 beside the averaged actual values.

### Example snippet
```python
expected = {"fish": 64.0, "junk": 28.0, "valuable_junk": 6.0, "event": 2.0}
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Balance drift is now visible directly in the report instead of needing manual calculation.

### How to extend it later
Compute confidence bands if larger sample sizes are added.

### Known limitations
The comparison is currently written for the River 1 distribution only.

2026-04-09 11:43:00
## TASK F-130 Track Total Money Earned
### What was built
Added total sale value tracking for each pass and the combined simulation flow. Verification: the report now shows `Total value sold` for Pass A and Pass B.

### Example snippet
```python
summary["sales_total"] += record["sale_value"]
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The simulation now measures earnings directly from real sale commands.

### How to extend it later
Split totals by fish species, junk tier, and vendor type.

### Known limitations
The report does not yet compute median payout.

2026-04-09 11:43:01
## TASK F-131 Compute Average Value Per Run
### What was built
Added average value per run to each simulation pass. Verification: the report now prints average coin return per 100-run block.

### Example snippet
```python
pass_one["sales_total"] / max(1, pass_one["runs"])
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
This normalizes total value so different run counts remain comparable.

### How to extend it later
Add per-outcome-type averages or variance.

### Known limitations
Average value is per run, not per successful catch.

2026-04-09 11:43:02
## TASK F-132 Report Fish Species Breakdown
### What was built
Added per-pass fish species counters so the report lists which fish actually appeared. Verification: the report now shows silver trout and mud carp counts for both passes.

### Example snippet
```python
summary["fish_counts"][species] += 1
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The report now shows the catch mix instead of only aggregate fish totals.

### How to extend it later
Add average weight per species.

### Known limitations
Only species counts are reported, not specimen weights.

2026-04-09 11:43:03
## TASK F-133 Report Junk Breakdown
### What was built
Added per-pass junk counters so the report lists which salvage items actually showed up. Verification: the generated report now prints item counts for weeds, tangled line, old boot, and the rare salvage entries.

### Example snippet
```python
summary["junk_counts"][record["junk"]] += 1
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Junk frequency is now visible at the item level instead of only by tier.

### How to extend it later
Roll these into rarity buckets or source tables in future reports.

### Known limitations
The report does not include per-item percentage share yet.

2026-04-09 11:43:04
## TASK F-134 Add Balance Answers Section
### What was built
Added an explicit `Balance Answers` section that answers whether junk is too frequent, whether valuable junk is too generous, and whether violent tug events are noticeable without being annoying. Verification: the report now prints direct yes/no answers from measured thresholds.

### Example snippet
```python
"## Balance Answers"
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The report now ends in interpretable balance conclusions, not just raw data.

### How to extend it later
Move the thresholds into named config if design wants to tune them.

### Known limitations
The threshold logic is simple and opinionated.

2026-04-09 11:43:05
## TASK F-135 Write Updated Simulation Report
### What was built
Replaced the earlier lightweight report with a fresh two-pass simulation report at `docs/systems/fishingSimulationReport.md`. Verification: the file now contains the 11:42:16 generated report with pass-by-pass breakdowns.

### Example snippet
```python
report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The simulation scenario now owns report generation directly.

### How to extend it later
Also emit JSON if external plotting is needed.

### Known limitations
The report is regenerated on each simulation run rather than versioned.

2026-04-09 11:43:06
## TASK F-136 Add Built-In Rerun Stability Check
### What was built
Made the simulation scenario run two 100-run passes and compare variance inside one execution. Verification: the report now includes a `Pass variance` line and a `Stable across rerun?` answer.

### Example snippet
```python
pass_two = run_pass("B", 100)
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The rerun comparison is now part of the harness instead of a separate manual step.

### How to extend it later
Add a third pass or seed sweep if broader stability sampling is needed.

### Known limitations
Variance is reported as absolute percentage deltas only.

2026-04-09 11:43:07
## TASK F-137 Enforce Safe-Zone Event Safety
### What was built
Validated that fishing events in safe rooms do not spawn combat, NPCs, or room threats. Verification: the junk/event DireTest runs the event flow in a safe-zone room and asserts NPC counts stay flat.

### Example snippet
```python
water_room.db.safe_zone = True
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The event system respects the same safe-room constraints as the broader world.

### How to extend it later
Add room tags for partial safety if some areas should allow softer encounters.

### Known limitations
Safe-zone handling is currently hardcoded to the no-spawn resolution path.

2026-04-09 11:43:08
## TASK F-138 Verify Group Isolation
### What was built
Added test coverage proving junk table selection stays inside the requested water group. Verification: the junk/event slice samples River 1, River 2, and Ocean and checks each returned profile keeps its own `group` label.

### Example snippet
```python
river_two_common == {"River 2"}
```

### Files touched
- `diretest.py`
- `world/systems/fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Cross-zone contamination is now explicitly guarded by test coverage.

### How to extend it later
Add negative checks on room-to-room overrides once those exist.

### Known limitations
The current isolation test checks group metadata rather than every possible item key.

2026-04-09 11:43:09
## TASK F-139 Verify Junk Buyer Acceptance
### What was built
Added regression coverage for junk sale acceptance so the fish buyer path remains salvage-aware. Verification: the junk/event slice confirms `is_fish_trade_item(junk_item)` is true and the junk sale increases coins.

### Example snippet
```python
bool(fishing_economy.is_fish_trade_item(junk_item))
```

### Files touched
- `world/systems/fishing_economy.py`
- `typeclasses/fishing_supplier.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The vendor path is now explicitly tested to keep accepting salvage items.

### How to extend it later
Add payout multipliers by junk tier or buyer specialty.

### Known limitations
Acceptance is binary and does not yet filter by salvage subtype.

2026-04-09 11:43:10
## TASK F-140 Clear Event Session State Correctly
### What was built
Ensured event pulls clear the fishing session and leave the player able to rig again. Verification: the junk/event DireTest checks the session is gone after event resolution and that `rig pole` still works afterward.

### Example snippet
```python
reset_fishing_session(actor)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Violent tug events now terminate cleanly instead of leaving stale runtime flags behind.

### How to extend it later
Add temporary debuffs or repair costs while keeping the same cleanup behavior.

### Known limitations
Event cleanup does not yet persist any separate damage state beyond the pole line flag.

2026-04-09 11:43:11
## TASK F-141 Remove Legacy Junk Branch
### What was built
Removed the old `calculate_junk_chance()` branch and the old junk-only text outcome from the main nibble path. Verification: `_begin_nibble()` now routes through fish, junk, and event states with authored profiles.

### Example snippet
```python
if outcome_category == "junk":
```

### Files touched
- `world/systems/fishing.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
There is now one coherent outcome model instead of old and new junk logic coexisting.

### How to extend it later
Keep all future fishing outcome work inside the weighted outcome layer.

### Known limitations
The old `NOTHING_MESSAGES` list still exists even though this batch does not use it.

2026-04-09 11:43:12
## TASK F-142 Add Junk Inspection Formatting
### What was built
Added `format_junk_inspection()` so salvage objects render tier, source, value, and description cleanly on look. Verification: junk now has dedicated inspection output through its typeclass appearance hook.

### Example snippet
```python
return fishing_economy.format_junk_inspection(self)
```

### Files touched
- `world/systems/fishing_economy.py`
- `typeclasses/items/junk.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Junk items now describe themselves like other authored trade goods.

### How to extend it later
Add salvage condition or provenance notes to the same formatter.

### Known limitations
Inspection does not yet show historical ownership or rarity color.

2026-04-09 11:43:13
## TASK F-143 Register New DireTest Scenarios
### What was built
Registered `fishing-junk-event-slice` and `fishing-simulation-100` in the scenario parser so both can run from the CLI like the older slices. Verification: both scenarios were executed by name during validation.

### Example snippet
```python
scenario_subparsers.add_parser("fishing-simulation-100")
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The new validation tools are now part of the normal DireTest entry surface.

### How to extend it later
Add aliases or command-line options if designers need faster iteration.

### Known limitations
The parser entries do not yet expose custom run counts.

2026-04-09 11:43:14
## TASK F-144 Revalidate Vertical Slice
### What was built
Reran `fishing-vertical-slice` after the weighted outcome refactor and updated one assertion to accept the broadened bulk-sale text. Verification: the final rerun passed at seed `789433600`.

### Example snippet
```python
"fishing finds" in str(line).lower()
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The core fishing loop still passes after the junk and event expansion.

### How to extend it later
Split sale-text assertions into helper matchers if more vendor wording changes are expected.

### Known limitations
One rerun hit a transient SQLite lock during cleanup before the clean pass.

2026-04-09 11:43:15
## TASK F-145 Revalidate Junk And Event Slice
### What was built
Reran the focused junk/event regression after the final simulation fixes. Verification: `fishing-junk-event-slice` passed again at seed `485116100`.

### Example snippet
```python
PASS: fishing-junk-event-slice
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The targeted salvage and event checks stayed green after the later harness fixes.

### How to extend it later
Add forced common-junk and Ocean-group cases if more direct regressions are needed.

### Known limitations
The slice focuses on one room setup rather than every fish group.

2026-04-09 11:43:16
## TASK F-146 Rerun Simulation For Stability
### What was built
Confirmed the final simulation scenario runs two full 100-run passes inside one execution. Verification: `fishing-simulation-100` passed at seed `436446000` and generated a two-pass report.

### Example snippet
```python
pass_one = run_pass("A", 100)
pass_two = run_pass("B", 100)
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The final harness no longer depends on a second manual rerun to answer stability questions.

### How to extend it later
Add optional seed sweeps if the balance team wants broader coverage.

### Known limitations
The full two-pass run still takes several minutes under DireTest.

2026-04-09 11:43:17
## TASK F-147 Report Variance Acceptability
### What was built
Added variance reporting across the two passes and a stability judgment based on a 10% band. Verification: the final report records `{'fish': 3.0, 'junk': 1.0, 'valuable_junk': 1.0, 'event': 5.0}` and marks the rerun stable.

### Example snippet
```python
max(variance.values()) <= 10.0
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The report now explains not just the second pass, but how different it was from the first one.

### How to extend it later
Use confidence intervals or more formal statistical tests if needed.

### Known limitations
Variance thresholds are simple heuristics.

2026-04-09 11:43:18
## TASK F-148 Confirm Junk And Event Presence
### What was built
Validated that the completed simulation actually produced both junk and violent tug outcomes. Verification: the final report shows junk in both passes and five event resolutions in Pass B.

### Example snippet
```python
"Total violent tug events: 5"
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The slice now proves the new surprise layer appears in real runs instead of only forced tests.

### How to extend it later
Require minimum event counts over larger samples if design wants stronger guarantees.

### Known limitations
Pass A happened to roll zero events even though the combined two-pass run hit the expected tier overall.

2026-04-09 11:43:19
## TASK F-149 Capture Performance Telemetry
### What was built
Kept DireTest lag telemetry enabled for the long simulation and both regression scenarios. Verification: the final runs recorded lag summaries and completed without runaway scheduler growth or stuck callbacks.

### Example snippet
```python
"fail_on_critical_lag": False
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The harness records performance characteristics without turning environment latency into a false gameplay failure.

### How to extend it later
Add hard command-count or duration thresholds if CI time budgets matter.

### Known limitations
The passing long simulation still reported critical lag spikes in this local environment.

2026-04-09 11:43:20
## TASK F-150 Final Batch Documentation Sweep
### What was built
Closed the F-111 to F-150 batch by updating the simulation report and appending the full as-built log for every completed task. Verification: `docs/systems/fishingSimulationReport.md` contains the new two-pass report and this file now logs F-111 through F-150 with unique timestamps.

### Example snippet
```python
report_path.write_text(...)
```

### Files touched
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The batch now ends with written implementation and validation records instead of only code changes.

### How to extend it later
Keep using this same per-task append pattern for future fishing phases.

### Known limitations
The report is a generated snapshot and will be replaced on future simulation runs.

2026-04-09 13:15:09
## TASK HELP-001 Add Fishing Help Entry File
### What was built
Added a new file-backed `fishing` help topic to the existing Evennia help registry in `world/help_entries.py`. The entry covers setup, baiting, casting, pulling, outcomes, fish processing, selling, empath strain, and skill progression using terminal-readable headings and bullet lists. Verification: the new `fishing-help` DireTest scenario passed at seed `257453600` and confirmed the registered help entry contains the expected overview and command syntax lines.

### Example snippet
```python
{
	"key": "fishing",
	"category": "Survival",
	"text": """
Fishing is a survival activity ...
""",
}
```

### Files touched
- `world/help_entries.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The help topic is now loaded from the same file-based help module as the rest of the game guides, so `help fishing` resolves through the existing help system rather than through a custom one-off command.

### How to extend it later
Add `fishing advanced` or subtopics if you want separate help for bait types, fish tiers, or event handling.

### Known limitations
Headless DireTest does not capture paged help body text through the normal `help` command output path, so verification reads the registered help entry data directly inside the test scenario.

2026-04-09 13:15:10
## TASK HELP-002 Add Help Fish Alias Routing
### What was built
Updated `CmdHelp.func()` so `help fish` redirects to the full `fishing` guide instead of stopping at the short command docstring for `fish`. Verification: the `fishing-help` DireTest scenario inspects the live `CmdHelp.func` implementation and confirms the redirect from `fish` to `fishing` is present.

### Example snippet
```python
if query == "fish":
	self.args = "fishing"
```

### Files touched
- `commands/cmd_help.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Players can now type either `help fish` or `help fishing` and land on the same full onboarding guide.

### How to extend it later
Add more alias redirects in `CmdHelp.func()` if other systems need command-to-guide routing.

### Known limitations
This redirect is explicit for `fish`; it does not automatically remap other commands to broader guides.

2026-04-09 13:15:11
## TASK HELP-003 Improve Fishing Discoverability
### What was built
Added a `See also: help fishing` cross-reference to the `fieldcraft` help topic, added `gathering` as an alias for that topic, exposed `fishing` in the help topic groups, and surfaced `bait`, `fish`, `pull`, `rig`, and `untangle` in the fieldcraft/survival command grouping. Verification: the `fishing-help` DireTest scenario confirms the survival/fieldcraft help content now references `help fishing`.

### Example snippet
```python
"aliases": ["exploration", "survival", "gathering", ...]
```

### Files touched
- `world/help_entries.py`
- `commands/cmd_help.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Fishing is now easier to discover from adjacent survival help instead of being an isolated topic players have to guess exists.

### How to extend it later
Add cross-references from profession or Town Green help topics if you want stronger onboarding.

### Known limitations
The discoverability pass currently targets fieldcraft/survival surfaces only.

2026-04-09 13:15:12
## TASK HELP-004 Validate Help Against Live Commands
### What was built
Added a focused `fishing-help` DireTest scenario that verifies the documented command surface against live command handlers and live NPC inquiry behavior. Verification: the scenario passed at seed `257453600` and checked `ask maren for gear`, `rig pole`, `untangle pole`, `bait worm`, `fish`, `pull`, `inventory`, `skin <fish>`, `sell <item>`, and `sell fish` against real handlers or live fishing state transitions.

### Example snippet
```python
ask_output = run_handler(CmdAsk, "maren for gear")
pull_output = run_handler(CmdPull)
sell_output = run_handler(CmdSell, "fish")
```

### Files touched
- `diretest.py`
- `world/help_entries.py`
- `commands/cmd_help.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The help task now includes repeatable verification that the commands described in the guide still exist, use the documented syntax, and behave as the guide says they do.

### How to extend it later
Add assertions for future `help fishing advanced` content once that topic exists.

### Known limitations
The scenario uses direct command-handler execution for some checks because the current headless DireTest `execute_cmd` path is not reliably exposing every gameplay command on fresh test characters.

2026-04-09 13:15:13
## TASK HELP-005 Document Fishing Help Entry
### What was built
Documented the help-system work in this as-built log with timestamps, files touched, and verification results. Verification: this file now records HELP-001 through HELP-005, and the implementation references the passing `fishing-help` scenario for proof.

### Example snippet
```python
PASS: fishing-help
```

### Files touched
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The fishing onboarding layer is now tracked the same way as the gameplay work, with implementation and verification preserved in the project log.

### How to extend it later
Keep appending future help-system work here when fishing documentation grows.

### Known limitations
This entry documents the current baseline help guide only; it does not yet cover a separate advanced fishing help topic.

2026-04-09 14:50:55
## TASK F-151 Validate Bait Items Strictly
### What was built
Stopped the fishing system from accepting arbitrary inventory objects as bait by adding an explicit bait validator that requires both `db.is_bait` and a recognized bait family. Verification: `diretest.py scenario fishing-vertical-slice` passed at seed `263628700` and now rejects `bait hook` with the exact invalid-bait message.

### Example snippet
```python
return bool(getattr(item.db, "is_bait", False)) and bool(resolve_bait_family(item))
```

### Files touched
- `world/systems/fishing.py`
- `commands/cmd_fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The bait flow now checks whether the item is actually marked as bait before it can ever be attached to the hook.

### How to extend it later
Add bait subtypes with stricter compatibility rules per fish family once live bait balance settles.

### Known limitations
The validator still trusts item attrs rather than a registry-backed bait definition table.

2026-04-09 14:50:56
## TASK F-152 Remove Generic Bait Fallback Acceptance
### What was built
Removed the old fallback that treated unknown bait families like a valid worm/cutbait match, and updated bait lookup helpers to return `None` for unrecognized items instead. Verification: the vertical slice now fails non-bait selections cleanly instead of silently resolving them into a bait family.

### Example snippet
```python
if not family:
	return None
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Unknown or malformed bait items now stop at resolution time instead of sliding into the normal bait path.

### How to extend it later
Introduce a data-driven bait-family registry so new bait objects can be added without touching the resolver.

### Known limitations
Unknown bait still fails generically; the system does not yet explain which bait family was expected.

2026-04-09 14:50:57
## TASK F-153 Gate Baiting On Rigged Pole State
### What was built
Changed `attach_bait()` so baiting now hard-fails when the pole is unrigged or tangled, and updated `CmdBait` to emit only the returned failure text once. Verification: `diretest.py scenario fishing-vertical-slice` passed and confirms `bait worm` on an unrigged pole yields `You need to rig your pole before baiting it.` with no duplicate success line.

### Example snippet
```python
if pole_issue == "unrigged":
	return False, "You need to rig your pole before baiting it.", None
```

### Files touched
- `world/systems/fishing.py`
- `commands/cmd_fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Players can no longer bait a pole that does not actually have a working line and hook state.

### How to extend it later
Differentiate missing-hook and missing-line errors if the rigging UX needs finer repair prompts.

### Known limitations
The command still assumes a single active pole instead of supporting multiple named poles.

2026-04-09 14:50:58
## TASK F-154 Correct Broken-Line Recovery Messaging
### What was built
Updated broken-line feedback so the system now tells players to rig the pole again instead of telling them to re-bait. Verification: the vertical slice forces a line-break outcome and confirms the follow-up guidance points back to `rig pole`.

### Example snippet
```python
actor.msg("Your line is broken. You need to rig your pole before fishing again.")
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The recovery message now matches the real repair flow after a snapped line.

### How to extend it later
Add command suggestions for `rig pole` or component checks if the repair loop grows more complex.

### Known limitations
The message does not yet explain whether the hook, line, or both were lost.

2026-04-09 14:50:59
## TASK F-155 Support Sell Item To NPC Syntax
### What was built
Extended `sell` parsing so `sell <item> to <npc>` strips the vendor clause and reuses the normal sell path, while malformed bare `to <npc>` input now gets a corrective prompt. Verification: `diretest.py scenario fishing-junk-event-slice` passed at seed `531416100` and sells salvage successfully through `sell <item> to maren`.

### Example snippet
```python
item_name, _separator, _vendor_name = args.rpartition(" to ")
```

### Files touched
- `commands/cmd_sell.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The command now tolerates natural-language vendor targeting without needing a separate sell implementation.

### How to extend it later
Actually resolve named nearby vendors if the game later supports multiple buyers in one room.

### Known limitations
The vendor name is currently ignored after parsing; only the item name is used.

2026-04-09 14:51:00
## TASK F-156 Report Accurate Bulk Sale Composition
### What was built
Updated bulk-sale summary generation so `sell fish` now distinguishes fish-only, salvage-only, and mixed hauls, and fixed the character sale flow to compute that summary before deleting sold items. Verification: the vertical slice passed and now reports salvage-aware processed-goods sales instead of the old generic `items` fallback.

### Example snippet
```python
summary = fishing_economy.get_bulk_sale_summary(fish_items, total)
```

### Files touched
- `world/systems/fishing_economy.py`
- `typeclasses/characters.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The buyer message is now based on what was actually sold, not on a post-delete object list that has already lost meaningful type metadata.

### How to extend it later
Add richer summaries such as exact fish vs salvage counts in the player-facing message.

### Known limitations
The bulk message still compresses all salvage into one label instead of naming skins, meat, or junk separately.

2026-04-09 14:51:01
## TASK F-157 Improve Empty-Line Pull Feedback
### What was built
Replaced the generic `You can't pull right now.` fallback with `There's nothing on the line anymore.` across the relevant post-loss and invalid-state fishing branches. Verification: the vertical slice passed and now checks the clearer message on stale pull attempts.

### Example snippet
```python
actor.msg("There's nothing on the line anymore.")
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Players now get a state-accurate explanation when the fish or junk is already gone.

### How to extend it later
Add distinct messages for missed nibbles, broken lines, and released event pulls if you want more flavor.

### Known limitations
Some invalid pull states still intentionally reuse broader tangle or broken-line feedback instead of this message.

2026-04-09 14:51:02
## TASK F-158 Add Cast Hint Toward Fishing
### What was built
Changed bare `cast` with no prepared spell to hint the fishing command instead of only reporting missing spell state. Verification: `diretest.py scenario fishing-vertical-slice` passed and now expects `If you meant to fish, try 'fish'.`

### Example snippet
```python
self.caller.msg("If you meant to fish, try 'fish'.")
```

### Files touched
- `commands/cmd_cast.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Players who type `cast` while thinking about a fishing cast now get routed toward the correct verb.

### How to extend it later
Add similar context hints for other overloaded verbs that players commonly confuse.

### Known limitations
The hint only triggers when no spell is prepared, so real spellcasting remains unchanged.

2026-04-09 14:51:03
## TASK F-159 Randomize Bite Delay
### What was built
Replaced the fixed five-second bite timer with randomized bite scheduling stored on the fishing session. Verification: the passing vertical slice records River 1 bite callbacks inside the expected randomized timing window instead of at a fixed `5.0` seconds.

### Example snippet
```python
session.bite_delay = calculate_bite_delay(room)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Each cast now waits a slightly different amount of time before the bite phase begins, which makes the loop feel less mechanical.

### How to extend it later
Bias the delay by bait quality, weather, or room density once live tuning data exists.

### Known limitations
The current timing ranges are static and not yet player- or room-density aware.

2026-04-09 14:51:04
## TASK F-160 Vary Bite Delay By Fish Group
### What was built
Added fish-group timing bands so River 1, River 2, River 3, and Ocean locations now use different bite-delay ranges instead of sharing one universal timing profile. Verification: the new `calculate_bite_delay()` helper resolves timing from room fish-group data, and the simulation/report path now records group-aware bite samples.

### Example snippet
```python
lower, upper = _get_group_bite_delay_range(room_or_group)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Easier river zones bite faster than harder groups, which gives different waters a slightly different pace before odds even apply.

### How to extend it later
Split timing by exact room or species hotspots if certain waters need stronger identity.

### Known limitations
Only the fish-group band changes here; individual species do not yet alter the timer.

2026-04-09 14:51:05
## TASK F-161 Add Nibble Timeout Variance
### What was built
Changed the nibble window from a fixed three-second timeout to a small randomized range, and stored the chosen window on the session for later inspection. Verification: the vertical slice passed and now asserts nibble expiry lands within the new randomized range rather than at exactly three seconds.

### Example snippet
```python
session.nibble_window_delay = calculate_nibble_window_delay()
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The player’s reaction window still stays short, but it no longer fires at the same exact cadence every time.

### How to extend it later
Widen or narrow the window based on bait type, fish difficulty, or player skill.

### Known limitations
The variance is intentionally small and only affects nibble expiry, not struggle cadence.

2026-04-09 14:51:06
## TASK F-162 Cancel Fishing Timers On Cleanup
### What was built
Added explicit cancellation for scheduled fishing callbacks during reset, cancellation, movement interruption, unpuppet cleanup, and line-state transitions like tangles and breaks. Verification: the vertical slice passed and now asserts that stale bite or timeout callbacks do not survive cleanup paths.

### Example snippet
```python
_clear_session_callbacks(session)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
When a fishing session ends or becomes invalid, its pending timers are cancelled so they cannot wake back up later and corrupt state.

### How to extend it later
Reuse the same callback-tracking approach for other staged systems that rely on delayed Evennia actions.

### Known limitations
Cancellation is session-local and in-memory; it does not persist across a hard process crash.

2026-04-09 14:51:07
## TASK F-163 Prevent Duplicate Fishing Timer Scheduling
### What was built
Introduced per-session callback slots for bite, nibble-timeout, and struggle timers so each phase replaces any prior timer in the same slot instead of stacking duplicate delayed work. Verification: the updated DireTests passed after switching from fixed-step timer assumptions to callback-name checks, and stale duplicate timers are now treated as a failure.

### Example snippet
```python
callbacks[callback_key] = delay(seconds, callback, actor, *callback_args)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Each session tracks one active timer per phase, so re-entry or state changes overwrite the old timer instead of leaving multiple delayed callbacks alive.

### How to extend it later
Add debug inspection commands that dump active callback slots for live troubleshooting.

### Known limitations
The slot map is internal only and is not yet surfaced in staff tooling.

2026-04-09 14:51:08
## TASK F-164 Update DireTests For Variable Timing
### What was built
Refactored the fishing DireTests to use cancellable fake delayed tasks, callback-name filtering, timing ranges, and explicit stale-callback assertions instead of hard-coded `5 / 3 / 2` second steps. Verification: `diretest.py scenario fishing-vertical-slice` passed at seed `263628700`, `diretest.py scenario fishing-junk-event-slice` passed at seed `531416100`, and `diretest.py scenario fishing-help` passed at seed `602584600`.

### Example snippet
```python
bite_delay = run_next(callback_name="_begin_nibble", min_seconds=4.0, max_seconds=10.0)
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The tests now validate fishing by phase and timing window, which keeps them stable even though bite and nibble timing are intentionally randomized.

### How to extend it later
Add helper utilities for delayed-callback assertions if more state-machine systems start using randomized timers.

### Known limitations
The long-form scenarios still run slowly under SQLite and can show critical lag telemetry even when the gameplay assertions pass.

2026-04-09 14:51:09
## TASK F-165 Report Bite Timing Distribution
### What was built
Extended the 100-run simulation report to record bite-delay samples and write average, minimum, and maximum bite timing into the generated fishing balance report. Verification: `diretest.py scenario fishing-simulation-100` passed at seed `355351800`, and `docs/systems/fishingSimulationReport.md` now includes `Avg: 7.0s`, `Min: 4.0s`, and `Max: 10.0s` in a dedicated Bite Timing section.

### Example snippet
```python
"bite_timing": {"avg": avg_delay, "min": min_delay, "max": max_delay}
```

### Files touched
- `diretest.py`
- `docs/systems/fishingSimulationReport.md`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The balance simulation now measures the actual randomized bite timings it produced, then writes those numbers into the report alongside outcome distribution and value data.

### How to extend it later
Add per-fish-group timing histograms or percentile bands once the simulation covers more waters.

### Known limitations
The current report summarizes bite timing across the simulated River 1 pass only; it is not yet a multi-region timing study.

2026-04-09 15:14:19
## TASK F-166 Tag Borrowed Items
### What was built
Old Maren's starter-kit creation path now marks each loaned item with `db.borrowed = True` and `db.borrowed_source = "maren"`. Verification: `diretest.py scenario fishing-borrowed-gear-exit` passed at seed `248519300` and confirms the borrowed tags appear on the starter pole, worm, hook, line, and fish string while normal items remain untagged.

### Example snippet
```python
item.db.borrowed = True
item.db.borrowed_source = "maren"
```

### Files touched
- `typeclasses/fishing_supplier.py`
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Starter gear now carries an explicit borrowed marker from the moment Maren creates it, so later cleanup can target only loaned kit.

### How to extend it later
Reuse the same attr pair for future rental or deposit-based gear systems.

### Known limitations
The source tag is still a plain string rather than a richer supplier identifier object.

2026-04-09 15:14:20
## TASK F-167 Add Borrowed Gear Helper
### What was built
Added `is_borrowed(item)` and related borrowed-gear helpers to the fishing system so the starter-loop code has a single borrowed-item predicate. Verification: the borrowed-gear exit scenario passed at seed `248519300` and explicitly checks that only Maren gear returns true while a real pole and a rock do not.

### Example snippet
```python
def is_borrowed(item):
	return getattr(getattr(item, "db", None), "borrowed", False) is True
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The borrowed-gear flow now asks one helper whether an item belongs to Maren's loaned kit instead of hand-checking attrs in multiple places.

### How to extend it later
Add companion helpers for source filtering if multiple lenders appear later.

### Known limitations
The helper only answers the boolean borrowed state; it does not itself validate the source tag.

2026-04-09 15:14:21
## TASK F-168 Hook Borrowed Return Into Movement
### What was built
Hooked borrowed-gear return into the character movement path by extending `move_to(...)`, using the origin room and completed destination to trigger return only when the player actually leaves the starter fishing room. Verification: `diretest.py scenario fishing-borrowed-gear-exit` passed at seed `248519300` and confirms no return message appears while the player stays in the room, but leaving through an exit does trigger the return path.

### Example snippet
```python
return_borrowed_gear(self, source_location=origin, direction=travel_direction)
```

### Files touched
- `typeclasses/characters.py`
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The cleanup runs on successful movement away from the starter room, not on arbitrary in-room actions.

### How to extend it later
Use the same seam for other room-bound loaner systems that should auto-return on exit.

### Known limitations
The production trigger still keys off room `#4305` plus an optional room flag for tests and future overrides.

2026-04-09 15:14:22
## TASK F-169 Capture Exit Direction
### What was built
Borrowed return messaging now captures the exit key before traversal completes so the player sees the real direction they left by. Verification: the borrowed-gear exit scenario passed at seed `248519300` and checks for `west`, while the full-loop scenario passed at seed `828055000` and checks for `south`.

### Example snippet
```python
travel_direction = getattr(self.ndb, "last_traverse_direction", None)
```

### Files touched
- `typeclasses/characters.py`
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The movement code snapshots the exit direction before later hooks clear that runtime field, then passes it into the borrowed-return message.

### How to extend it later
Expose the same captured direction to other exit-reactive systems if they need more natural movement text.

### Known limitations
Non-exit teleports still fall back to `away` because there is no traverse key to report.

2026-04-09 15:14:23
## TASK F-170 Remove Borrowed Items On Exit
### What was built
Added borrowed-item collection and cleanup so leaving the starter room removes only borrowed gear, preserving catches and player-owned inventory. The cleanup now tries `delete()` first and uses a safe room-return fallback only when SQLite locks reject the delete during DireTest. Verification: the borrowed-gear exit and full-loop scenarios both passed and confirm borrowed items leave the character inventory while kept items remain.

### Example snippet
```python
for item in list(getattr(actor, "contents", []) or []):
	if is_borrowed(item):
		...
```

### Files touched
- `world/systems/fishing.py`
- `typeclasses/characters.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The system gathers a stable snapshot of borrowed inventory, then removes only those items after the move finishes.

### How to extend it later
Swap the fallback into a dedicated hidden cleanup storage location if you want a stricter non-test recovery path.

### Known limitations
SQLite can still refuse deletes inside DireTest, so the fallback returns items to the source room for cleanup instead of deleting them outright in that environment.

2026-04-09 15:14:24
## TASK F-171 Add Borrowed Return Messaging
### What was built
Added a single player-facing return line in the movement flow: `You return the borrowed fishing gear and head {direction}.` Verification: the borrowed-gear exit scenario passed at seed `248519300` and asserts the line prints exactly once with the correct direction.

### Example snippet
```python
actor.msg(format_borrowed_return_message(travel_direction, paused=paused_flavor))
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Players now get clear, explicit feedback that the borrowed kit was returned as part of leaving the training area.

### How to extend it later
Add room- or supplier-specific messaging variants if different starter loops need different tone.

### Known limitations
The default message is intentionally plain and does not enumerate which pieces were returned.

2026-04-09 15:14:25
## TASK F-172 Add Optional Borrowed Return Flavor
### What was built
Added `format_borrowed_return_message(direction, paused=False)` so the starter loop can optionally use the more flavorful `You pause long enough ...` wording without changing the default return line. Verification: the borrowed-gear exit scenario passed and directly asserts the helper builds the optional pause-flavor message correctly.

### Example snippet
```python
format_borrowed_return_message("west", paused=True)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The message formatter centralizes the wording so the starter room can opt into a slightly richer narration later.

### How to extend it later
Drive the `paused` flag from room, supplier, or onboarding-state configuration.

### Known limitations
The optional flavor exists as a helper seam, but the live starter room still uses the simpler default line.

2026-04-09 15:14:26
## TASK F-173 Prevent Mid-Fishing Exit Exploit
### What was built
The borrowed return now runs safely after the existing movement-based fishing cancel path, so leaving the room while actively fishing clears the session before gear is returned. Verification: `diretest.py scenario fishing-borrowed-gear-exit` passed at seed `248519300` and confirms the player gets the line-disturbance feedback, loses the borrowed kit, and does not keep a ghost fishing session.

### Example snippet
```python
if moved and ... and bool(getattr(self.ndb, "is_fishing", False)):
	cancel_fishing_session(self)
```

### Files touched
- `typeclasses/characters.py`
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The move first breaks the live fishing state, then runs the borrowed-gear return so the player cannot walk away with an active cast and a free kit.

### How to extend it later
If other staged activities can use borrowed tools, chain their cancel hooks ahead of borrowed cleanup the same way.

### Known limitations
The path still relies on the existing movement cancel logic for the fishing-session teardown rather than reimplementing it locally.

2026-04-09 15:14:27
## TASK F-174 Handle Partial Gear Loss
### What was built
The borrowed cleanup now tolerates incomplete kits by working from the current borrowed inventory snapshot instead of assuming every original item is still present. Verification: the borrowed-gear exit scenario passed after forcing a broken-line state on the borrowed pole, and the remaining borrowed items still returned cleanly with no crash.

### Example snippet
```python
borrowed_items = get_borrowed_items(actor)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
If part of the kit is gone or damaged, the system just returns whatever borrowed items are still actually being carried.

### How to extend it later
Add explicit audit logging if you want to track which pieces were missing on return.

### Known limitations
The current verification covers broken-line partial loss; bait-consumption is handled by the same inventory-snapshot design but not via a separate destructive test step because of SQLite delete noise in DireTest.

2026-04-09 15:14:28
## TASK F-175 Ensure Borrowed Return Triggers Once
### What was built
Kept the borrowed-return trigger on the single successful movement path and verified the return line is emitted once per move. Verification: the borrowed-gear exit and full-loop scenarios both passed and assert exactly one borrowed-return line appears in the exit output.

### Example snippet
```python
if len(return_lines) != 1:
	raise AssertionError(...)
```

### Files touched
- `typeclasses/characters.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Only the completed move path emits the borrowed-return line, so the player does not get duplicate return text from overlapping hooks.

### How to extend it later
If more move-adjacent systems need exit messaging, keep them coordinated inside the same movement seam.

### Known limitations
This assumes the standard move path is used; custom teleport code would need its own guard if it should also return borrowed gear.

2026-04-09 15:14:29
## TASK F-176 Protect Non-Borrowed Gear
### What was built
Confirmed the borrowed cleanup leaves player-owned items alone by testing with a normal pole and a rock carried alongside Maren's kit. Verification: `diretest.py scenario fishing-borrowed-gear-exit` passed at seed `248519300` and confirms the bought pole and rock remain after the borrowed starter kit is returned.

### Example snippet
```python
if fishing_system.is_borrowed(real_pole) or fishing_system.is_borrowed(river_rock):
	raise AssertionError(...)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The return flow keys only on the borrowed marker, so player-purchased or spawned gear is not touched.

### How to extend it later
Add a vendor-owned gear tier if you need returns that are scoped by lender rather than only by borrowed boolean.

### Known limitations
The safety guard depends on the borrowed attrs being applied correctly when gear is granted.

2026-04-09 15:14:30
## TASK F-177 Preserve Fish, Junk, And Processed Items
### What was built
The borrowed cleanup now preserves catches and other non-borrowed rewards, including fish moved out of the borrowed fish string before that string is removed. Verification: `diretest.py scenario fishing-borrowed-gear-full-loop` passed at seed `828055000` and confirms the caught fish, a junk item, and a processed fish-skin item all remain after exit.

### Example snippet
```python
for carried in list(getattr(item, "contents", []) or []):
	if not is_borrowed(carried):
		carried.move_to(actor, quiet=True, use_destination=False)
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
Before a borrowed container is removed, its non-borrowed contents are moved back onto the player so catches are preserved.

### How to extend it later
Use the same content-preservation pattern for future borrowed containers like tackle boxes or loaner backpacks.

### Known limitations
The preservation logic is generic, but only the borrowed fish string currently exercises it in gameplay.

2026-04-09 15:14:31
## TASK F-178 Avoid Inventory Iteration Bugs
### What was built
All borrowed-gear collection and cleanup loops use stable list snapshots so removal does not mutate the container being iterated. Verification: both borrowed-gear scenarios passed after cleanup removed multiple borrowed items in one move without skipping pieces or crashing.

### Example snippet
```python
for item in list(getattr(actor, "contents", []) or []):
	...
```

### Files touched
- `world/systems/fishing.py`
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The cleanup works from a copied inventory list, so deleting or moving borrowed items does not corrupt the loop.

### How to extend it later
Keep using list snapshots anywhere delayed cleanup mutates inventory or container contents.

### Known limitations
The pattern avoids iteration bugs, but it does not prevent external DB locks from forcing the fallback path during DireTest.

2026-04-09 15:14:32
## TASK F-179 Add Borrowed Exit Test
### What was built
Added `fishing-borrowed-gear-exit`, a focused DireTest scenario that gets gear from Maren, starts fishing, leaves through an exit, and validates borrowed tagging, correct direction messaging, single-trigger behavior, ghost-session cleanup, and protection for non-borrowed items. Verification: `diretest.py scenario fishing-borrowed-gear-exit` passed at seed `248519300`.

### Example snippet
```python
ctx.cmd("ask maren for gear")
ctx.cmd("fish")
ctx.cmd("west")
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The new scenario isolates the starter-room exit behavior so borrowed cleanup can be verified without mixing it into the heavier fishing economy slice.

### How to extend it later
Add a second exit-only scenario if a future starter room needs a different supplier or movement rule.

### Known limitations
The scenario checks the standard default return line and the optional formatter separately rather than toggling the live flavor flag in-room.

2026-04-09 15:14:33
## TASK F-180 Add Borrowed Full Loop Test
### What was built
Added `fishing-borrowed-gear-full-loop`, a focused DireTest scenario that borrows gear, lands a fish, exits the room, and verifies the fish survives borrowed fish-string removal along with junk and processed goods. Verification: `diretest.py scenario fishing-borrowed-gear-full-loop` passed at seed `828055000`.

### Example snippet
```python
ctx.cmd("ask maren for gear")
ctx.cmd("fish")
ctx.cmd("pull")
ctx.cmd("south")
```

### Files touched
- `diretest.py`
- `docs/systems/fishingAsBuilt.md`

### How it works (plain English)
The full-loop scenario proves the starter containment mechanic does not eat player rewards when the borrowed fish string is returned on exit.

### How to extend it later
Add variants for trophy fish, stacked salvage, or multiple catches once the starter loop grows deeper.

### Known limitations
An unrelated legacy regression run of `fishing-vertical-slice` still hit SQLite lock noise during bulk fish deletion, but the new borrowed-gear scenario itself passed cleanly and did not expose a borrowed-return regression.
