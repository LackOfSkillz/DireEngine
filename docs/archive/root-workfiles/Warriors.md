WARRIOR PROGRESSION TABLE (CIRCLES 1–50)
Design Rules (Locked)
New ability every ~5 circles (dopamine hit)
Minor gains between (feel growth)
Power spikes are earned, not constant
Early game = access
Mid game = control
Late game = dominance
🥉 EARLY GAME (1–10) — “Learning to Fight”
Circle 1
Join Warrior Guild
Gain:
War Tempo system

Messaging:

You begin to feel the rhythm of battle.

Circle 3
Passive:
Minor fatigue reduction
Circle 5 ⭐
UNLOCK: Surge
First active ability

Dopamine moment:

You learn to channel your momentum into decisive action.

Circle 7
Improved tempo gain rate
Circle 10 ⭐
UNLOCK: Intimidate (Roar)
First battlefield presence ability
🟠 EARLY-MID (11–20) — “Finding Your Presence”
Circle 12
Passive:
balance recovery ↑
Circle 15 ⭐
UNLOCK: Rally (Roar)
First self-sustain buff
Circle 17
Tempo decay reduced in combat
Circle 20 ⭐
UNLOCK: Crushing Blow
First heavy impact attack
🟡 MID GAME (21–30) — “Controlling the Fight”
Circle 22
Passive:
weapon handling improvement (RT slightly reduced)
Circle 25 ⭐
UNLOCK: Press Advantage
Synergy with balance system
Circle 27
Improved resistance to balance damage
Circle 30 ⭐
UNLOCK: Sweep
First control ability (knockdown)

👉 This is a major power spike

🟢 MID-LATE (31–40) — “Dominating Space”
Circle 32
Passive:
fatigue resistance scaling with tempo
Circle 35 ⭐
UNLOCK: Second Wind
First survival recovery tool
Circle 37
Passive:
minor multi-target defense bonus
Circle 40 ⭐
UNLOCK: Whirl
First multi-target attack

👉 Big dopamine moment:

“I can fight groups now”

🔵 LATE GAME (41–50) — “Becoming the Storm”
Circle 42
Passive:
improved roar duration
Circle 45 ⭐
UNLOCK: Hold Ground
Anti-control anchor ability
Circle 47
Passive:
reduced penalty when overwhelmed
Circle 50 ⭐⭐⭐ (MAJOR MILESTONE)
UNLOCK: Frenzy
First peak-state ability

Messaging:

You stand at the edge of control—and step beyond it.

🧭 DESIGN NOTES (IMPORTANT)
🎯 Why This Works
1. Every 5 Circles = Reward

Players feel:

progress
anticipation
payoff
2. Systems Unlock in Order
Phase	What Unlocks
Early	resource + basic action
Mid	control + synergy
Late	dominance + survival
3. No System Overload Early

You avoided:

dumping roars + control + multi-target too soon
overwhelming new players
⚖️ Balance Philosophy
Warrior feels:
strong early
tactical mid
dangerous late

BUT:

never immortal
still collapses under bad decisions
🚨 What’s Missing (Next Layer)

We stopped at 50 intentionally.

Next tiers (later):

Execution (finisher)
War Cry (group play)
Unbreakable (elite defense)

👉 These belong in 50–100 progression
WARRIOR PROGRESSION MICRO TASKS (101–120)

Phase: Unlock System + Circle Gating + Feedback Loop

🥇 WARRIOR 101 — Add Circle Attribute

Add to character:

warrior_circle = 1
Default on guild join
🥇 WARRIOR 102 — Circle Display

Add to stats:

Warrior Circle: 7

🥇 WARRIOR 103 — Ability Unlock Table (Data Structure)

Create central config:

WARRIOR_UNLOCKS = {
    5: ["surge"],
    10: ["intimidate"],
    15: ["rally"],
    20: ["crush"],
    25: ["press"],
    30: ["sweep"],
    35: ["secondwind"],
    40: ["whirl"],
    45: ["hold"],
    50: ["frenzy"],
}
🥇 WARRIOR 104 — Ability Gating System
Before ability executes:

check:

if ability not unlocked → block

Fail message:

You have not yet learned how to do that.

🥇 WARRIOR 105 — Unlock Tracking Storage

Add to character:

unlocked_warrior_abilities = []
🥇 WARRIOR 106 — Level-Up Hook (Circle Gain)

Create function:

gain_warrior_circle()
Increments circle
🥇 WARRIOR 107 — Unlock Trigger on Level-Up
On circle increase:
check unlock table
grant abilities
🥇 WARRIOR 108 — Unlock Messaging (CRITICAL)

When unlocking:

You have learned Surge.

For major abilities:

You have learned Crushing Blow. You feel your strikes carry new weight.

👉 This is your dopamine hit—don’t make it bland

🥇 WARRIOR 109 — Multi-Unlock Handling
If multiple unlocks at same circle:
show each cleanly
no message overlap
🥇 WARRIOR 110 — Passive Unlock Hooks
Some circles grant passives

Add structure:

WARRIOR_PASSIVES = {
    3: ["fatigue_reduction_1"],
    12: ["balance_recovery_1"],
    ...
}
🥇 WARRIOR 111 — Passive Application System
On unlock:
apply modifiers to character
Example:
reduce fatigue cost %
increase balance regen
🥇 WARRIOR 112 — Passive Messaging

You feel your endurance improving.

Keep it subtle—don’t overhype passives

🥇 WARRIOR 113 — Circle Progress Command

Command:

circle

Output:

current circle
next unlock preview

Example:

Circle 14
Next: Rally (Circle 15)

🥇 WARRIOR 114 — Next Unlock Preview Logic
Find next key in unlock table
Display cleanly
🥇 WARRIOR 115 — Lock Hidden Abilities
Prevent:
help listings
autocomplete
for locked abilities

👉 preserves discovery feel

🥇 WARRIOR 116 — Ability Categorization

Group abilities:

strikes
roars
survival

Used for:

help command
UI later
🥇 WARRIOR 117 — Help Command Integration
help warrior

Shows:

unlocked abilities only
grouped by type
🥇 WARRIOR 118 — Progression Debug Tool

Admin command:

setcircle <player> <value>

👉 critical for testing

🥇 WARRIOR 119 — Level-Up Test Scenario

Test:

set circle 4 → 5
verify:
surge unlocks
messaging triggers
command works
🥇 WARRIOR 120 — Persistence Check
Ensure:
circle saves
unlocks persist
passives persist

WARRIOR MICRO TASKS (121–140)

Phase: Tempo States + Berserk System (CORE UPGRADE)

🥇 WARRIOR 121 — War Tempo State Enum

Define states (not just text):

CALM
BUILDING
SURGING
FRENZIED
🥇 WARRIOR 122 — Tempo → State Mapping

Map % to state:

0–10 → CALM
10–40 → BUILDING
40–80 → SURGING
80–100 → FRENZIED
🥇 WARRIOR 123 — State Stored on Character

Add:

war_tempo_state
updates dynamically
🥇 WARRIOR 124 — State Update Hook
Trigger on:
tempo gain
tempo loss
Auto-update state
🥇 WARRIOR 125 — State-Based Modifiers (FIRST PASS)

Apply passive effects:

State	Effect
CALM	reduced tempo gain
BUILDING	normal
SURGING	+damage bonus
FRENZIED	+damage, -defense
🥇 WARRIOR 126 — State Messaging Feedback
On transitions:

You feel the fight rising in you.
You are fully engaged.
You are on the edge of losing control.

👉 This is feel, not fluff

🥇 WARRIOR 127 — Combat Resolver Integration
Modify:
hit chance
damage
based on state
🥇 WARRIOR 128 — Display State in Stats

Add:

Tempo State: Surging

🥇 WARRIOR 129 — Add Berserk System Scaffold

Create:

world/systems/warrior/berserk.py
🥇 WARRIOR 130 — Berserk Data Model

Each berserk has:

name
tempo cost (drain over time)
effects
duration (or sustain)
🥇 WARRIOR 131 — Add Command: Berserk
berserk <type>

Example:

berserk power
berserk stone
berserk speed
🥇 WARRIOR 132 — Berserk Validation
Requires:
minimum tempo threshold (e.g. 50%)
Fail:

You are not yet worked into a battle state.

🥇 WARRIOR 133 — Single Active Berserk Rule
Only ONE berserk active at a time
Activating new one:
cancels previous
🥇 WARRIOR 134 — Berserk: Power

Effect:

damage ↑
fatigue cost ↑
🥇 WARRIOR 135 — Berserk: Stone

Effect:

defense ↑
balance resistance ↑
movement ↓ (optional later)
🥇 WARRIOR 136 — Berserk: Speed

Effect:

RT ↓
accuracy slight ↑
damage ↓
🥇 WARRIOR 137 — Berserk Drain System
While active:
tempo drains over time
If tempo hits 0:
berserk ends
🥇 WARRIOR 138 — Berserk Messaging

Start:

You give yourself over to the rhythm of battle.

End:

The fury fades, leaving you exposed.

🥇 WARRIOR 139 — Berserk + State Interaction
While berserking:
force minimum state = BUILDING or SURGING
Prevent dropping to CALM

👉 keeps momentum feeling

🥇 WARRIOR 140 — Berserk Test Scenario

Test:

Build tempo

Enter:

berserk power
Verify:
tempo drains
damage increases
cannot stack berserks
ends at 0 tempo
🧭 What This Fixes

You just upgraded Warrior from:

“resource-based fighter”

to:

state-driven combat system with active combat modes

🔥 What Changed (Important)
BEFORE
Tempo = fuel
AFTER
Tempo = state engine
Berserk = playstyle selector

👉 This is the core DR Barbarian feel

WARRIOR MICRO TASKS (141–160)

Phase: Roar Expansion + Rhythm + Pressure Systems

🥇 WARRIOR 141 — Expand Roar Registry Structure

Update roar system to support:

category (offense / defense / control / group)
stacking rules
target scope (self / single / multi)
🥇 WARRIOR 142 — Roar Category System

Define:

OFFENSIVE
DEFENSIVE
CONTROL
GROUP
🥇 WARRIOR 143 — Roar Slot Limitation
Limit:
1 offensive roar
1 defensive roar
1 control roar active at once

👉 prevents stacking abuse

🥇 WARRIOR 144 — Add Roar: “Disrupt”

Command:

roar disrupt

Effect:

reduces enemy balance recovery
minor accuracy penalty
🥇 WARRIOR 145 — Add Roar: “Challenge”

Command:

roar challenge

Effect:

increases enemy focus on Warrior (future AI hook)
slight self-defense bonus

👉 tank-style pressure hook

🥇 WARRIOR 146 — Add Roar: “Unnerving”

Command:

roar unnerving

Effect:

applies pressure state (new system)
reduces enemy effectiveness slightly
🥇 WARRIOR 147 — Pressure State System (NEW)

Add to characters:

pressure_level = 0–100
🥇 WARRIOR 148 — Pressure Gain Sources
Being roared at
Being hit repeatedly
Facing high-tempo Warrior
🥇 WARRIOR 149 — Pressure Effects

At thresholds:

Pressure	Effect
Low	none
Medium	slight accuracy loss
High	hesitation chance
Extreme	action delay chance
🥇 WARRIOR 150 — Pressure Decay
Slowly decays out of combat
faster decay when disengaged
🥇 WARRIOR 151 — Pressure Messaging

Examples:

You feel uneasy under the pressure.
The fight is getting to you.
You hesitate under the assault.

🥇 WARRIOR 152 — Combat Rhythm System (NEW)

Add:

combat_streak
increases while continuously fighting
🥇 WARRIOR 153 — Rhythm Gain Rules
gain streak when:
landing hits
being actively engaged
resets on:
disengage
long inactivity
🥇 WARRIOR 154 — Rhythm Effects
higher streak:
tempo gain ↑
fatigue cost ↓
slight accuracy ↑
🥇 WARRIOR 155 — Rhythm Loss Penalty

When streak breaks:

You lose your rhythm.

Effects:

temporary:
tempo gain reduced
slight performance dip

👉 THIS is key DR feel

🥇 WARRIOR 156 — Display Rhythm State

Add to stats/diagnose:

Combat Rhythm: Building / Flowing / Perfect

🥇 WARRIOR 157 — Roar: “Rallying Cry” (Group Hook)

Command:

roar rallying

Effect:

boosts allies (future)
increases own rhythm gain rate
🥇 WARRIOR 158 — Roar Scaling with Tempo
higher tempo:
stronger roar effects

👉 ties systems together

🥇 WARRIOR 159 — Combined System Interaction Check

Ensure:

pressure + rhythm + tempo all interact cleanly
no infinite scaling loops
🥇 WARRIOR 160 — Multi-System Combat Test

Test scenario:

Engage enemy group
Build rhythm
Use:
intimidate
disrupt
unnerving
Observe:
enemies weaken over time (pressure)
player becomes stronger (rhythm)

👉 Fight should feel like momentum shift

🧭 What You Just Added (This is Big)

You now have:

🔥 Real Barbarian Identity Systems
Tempo → internal state
Berserk → mode selection
Roars → battlefield shaping
Rhythm → flow mastery
Pressure → enemy destabilization

WARRIOR MICRO TASKS (161–180)

Phase: Exhaustion + Overextension + Long-Fight Degradation

🥇 WARRIOR 161 — Exhaustion Attribute

Add to character:

exhaustion = 0–100
🥇 WARRIOR 162 — Exhaustion Gain Sources

Increase exhaustion when:

using high-cost abilities (crush, whirl, frenzy)
sustaining berserk
being in combat for extended time
🥇 WARRIOR 163 — Exhaustion Decay System
Slowly decays:
out of combat (fast)
in combat (very slow)
🥇 WARRIOR 164 — Exhaustion Thresholds
Level	Effect
0–20	none
20–40	mild fatigue increase
40–70	noticeable penalties
70–90	severe degradation
90–100	near collapse
🥇 WARRIOR 165 — Exhaustion Effects (Core)

Apply scaling penalties:

fatigue cost ↑
tempo gain ↓
balance recovery ↓
🥇 WARRIOR 166 — Exhaustion Messaging

Dynamic feedback:

You begin to feel the strain.
Your body is faltering.
You are nearing collapse.

🥇 WARRIOR 167 — Ability Exhaustion Cost Tagging

Each ability gets:

exhaustion_cost

Example:

surge → low
crush → medium
whirl → high
frenzy → very high
🥇 WARRIOR 168 — Berserk Exhaustion Interaction
While berserking:
exhaustion gain rate increases significantly

👉 prevents permanent berserk abuse

🥇 WARRIOR 169 — Frenzy Exhaustion Spike
On frenzy end:
large exhaustion increase

👉 reinforces risk

🥇 WARRIOR 170 — Overextension Trigger

If:

exhaustion > 90
→ trigger Overextended state
🥇 WARRIOR 171 — Overextended State Effects
severe penalties:
accuracy ↓
defense ↓
action delay chance
🥇 WARRIOR 172 — Overextended Messaging

You have pushed yourself too far.

🥇 WARRIOR 173 — Collapse Chance

At extreme exhaustion:

chance to:
stagger (lose turn)
forced kneel (mini prone)

👉 makes overuse dangerous

🥇 WARRIOR 174 — Recovery Ability: “Recover”

Command:

recover
🥇 WARRIOR 175 — Recover Effect
reduces exhaustion significantly
applies RT
cannot be used in high-pressure combat (optional rule)
🥇 WARRIOR 176 — Recover Messaging

You force yourself to steady your breathing.

🥇 WARRIOR 177 — Exhaustion Display

Add to stats:

Exhaustion: 62 (Strained)

🥇 WARRIOR 178 — System Interaction Check

Ensure:

exhaustion interacts with:
tempo
rhythm
fatigue
no infinite loops
🥇 WARRIOR 179 — Long Combat Test Scenario

Test:

Engage prolonged fight
Use:
berserk
whirl
frenzy
Observe:
exhaustion rises
performance drops
recovery becomes necessary
🥇 WARRIOR 180 — Balance Safeguard Hooks

Add config:

exhaustion_gain_rates
exhaustion_penalties
recovery_rates

👉 allows tuning without rewriting systems

🧭 FINAL RESULT — WARRIOR SYSTEM (COMPLETE)

Now you have:

🔥 Core Systems (All Present)
Internal Engine
War Tempo (state-driven)
Berserk modes
Combat Rhythm
External Impact
Roars (multi-type system)
Pressure / fear system
Combat Mechanics
Balance
Fatigue
Weapon identity
Survivability
Second Wind
Hold Ground
Recovery tools
Risk Layer
Exhaustion
Overextension
Collapse potential
⚖️ What This Means

Your Warrior is now:

strong in 1v1 ✅
viable in small groups ✅
vulnerable to swarm ✅
skill-expressive ✅
not infinitely sustainable ✅
🧠 Honest Assessment

Compared to DragonRealms Barbarian:

👉 You are now ~90–95% there in SYSTEM DEPTH

What’s missing (and intentionally deferred):

specialization paths (later game)
mastery trees
PvP tuning nuance