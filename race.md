RACE SYSTEM DESIGN LOCK (DIREMUD)
🎯 DESIGN GOALS (NON-NEGOTIABLE)
Races provide bias, not dominance
All professions viable for all races
Differences scale over time (not front-loaded)
No hidden mechanics (everything must be inspectable/debuggable)
System must be deterministic and testable (DireTest-ready)
🧱 CORE SYSTEM COMPONENTS

Every race MUST define:

race = {
    "name": str,
    "stat_modifiers": dict,
    "stat_caps": dict,
    "learning_modifiers": dict,
    "size": str,
    "carry_modifier": float,
    "description": str,
}

No additional fields in v1.

📊 STAT SYSTEM (LOCKED INTERFACE)

We are using these stats:

STATS = [
    "strength",
    "agility",
    "reflex",
    "intelligence",
    "wisdom",
    "stamina"
]
⚖️ STAT MODIFIER RULES (STRICT)
Allowed Range:
Each stat modifier must be between:
-2 to +2
Total Modifier Budget:
Sum of all modifiers MUST be:
0 (±1 tolerance max)

👉 Prevents power creep

🧠 STAT CAPS (LONG-TERM DIFFERENTIATION)

Each race defines stat caps, not just starting bias.

Global Base Cap:
BASE_STAT_CAP = 100
Race Cap Rules:
Each stat cap:
95 – 110 range
Total cap budget must remain balanced

👉 This ensures:

long-term identity
no early-game imbalance
📈 LEARNING MODIFIERS (CRITICAL SYSTEM)
Skill Categories (LOCKED)
SKILL_CATEGORIES = [
    "combat",
    "survival",
    "magic",
    "stealth",
    "lore"
]
Modifier Rules
Range:
0.85 – 1.15
1.0 = baseline
<1 = slower learning

1 = faster learning

Constraint

Total learning modifiers must average to:

1.0 ± 0.05

👉 No race globally learns faster

📏 SIZE SYSTEM (LOCKED)
SIZE_CATEGORIES = [
    "small",
    "medium",
    "large"
]
Effects

Size affects:

base carry capacity
future combat interactions (reach, etc.)
stealth visibility (future)
🏋️ CARRY MODIFIER (TIES INTO WEIGHT SYSTEM)

Each race defines:

carry_modifier = float

Range:

0.8 – 1.3

Applied to:

max_carry_weight
🧬 RACE DEFINITIONS (LOCKED SET)
🧍 HUMAN (BASELINE)
{
    "name": "Human",
    "stat_modifiers": {all: 0},
    "stat_caps": {all: 100},
    "learning_modifiers": {all: 1.0},
    "size": "medium",
    "carry_modifier": 1.0
}
🧝 ELF
{
    "stat_modifiers": {
        "strength": -1,
        "agility": +2,
        "reflex": +1,
        "intelligence": +1,
        "wisdom": 0,
        "stamina": -1
    },
    "stat_caps": {
        "strength": 95,
        "agility": 110,
        "reflex": 108,
        "intelligence": 105,
        "wisdom": 100,
        "stamina": 95
    },
    "learning_modifiers": {
        "combat": 0.95,
        "survival": 1.0,
        "magic": 1.15,
        "stealth": 1.05,
        "lore": 1.05
    },
    "size": "medium",
    "carry_modifier": 0.9
}
🧔 DWARF
{
    "stat_modifiers": {
        "strength": +2,
        "agility": -1,
        "reflex": -1,
        "intelligence": 0,
        "wisdom": 0,
        "stamina": +2
    },
    "stat_caps": {
        "strength": 110,
        "agility": 95,
        "reflex": 95,
        "intelligence": 100,
        "wisdom": 100,
        "stamina": 110
    },
    "learning_modifiers": {
        "combat": 1.15,
        "survival": 1.05,
        "magic": 0.9,
        "stealth": 0.9,
        "lore": 1.0
    },
    "size": "medium",
    "carry_modifier": 1.2
}
🦶 HALFLING
{
    "stat_modifiers": {
        "strength": -1,
        "agility": +2,
        "reflex": +2,
        "intelligence": 0,
        "wisdom": 0,
        "stamina": -1
    },
    "stat_caps": {
        "strength": 95,
        "agility": 110,
        "reflex": 110,
        "intelligence": 100,
        "wisdom": 100,
        "stamina": 95
    },
    "learning_modifiers": {
        "combat": 0.95,
        "survival": 1.05,
        "magic": 0.95,
        "stealth": 1.15,
        "lore": 1.0
    },
    "size": "small",
    "carry_modifier": 0.8
}
🧠 GNOME
{
    "stat_modifiers": {
        "strength": -1,
        "agility": +1,
        "reflex": 0,
        "intelligence": +2,
        "wisdom": +1,
        "stamina": -1
    },
    "stat_caps": {
        "strength": 95,
        "agility": 105,
        "reflex": 100,
        "intelligence": 110,
        "wisdom": 105,
        "stamina": 95
    },
    "learning_modifiers": {
        "combat": 0.95,
        "survival": 1.0,
        "magic": 1.1,
        "stealth": 1.0,
        "lore": 1.15
    },
    "size": "small",
    "carry_modifier": 0.9
}
🐺 GOR'TOGH
{
    "stat_modifiers": {
        "strength": +2,
        "agility": -2,
        "reflex": -1,
        "intelligence": -1,
        "wisdom": 0,
        "stamina": +2
    },
    "stat_caps": {
        "strength": 110,
        "agility": 95,
        "reflex": 95,
        "intelligence": 95,
        "wisdom": 100,
        "stamina": 110
    },
    "learning_modifiers": {
        "combat": 1.15,
        "survival": 1.05,
        "magic": 0.85,
        "stealth": 0.85,
        "lore": 0.95
    },
    "size": "large",
    "carry_modifier": 1.3
}
🐉 S’KRA MUR
{
    "stat_modifiers": {
        "strength": +1,
        "agility": 0,
        "reflex": 0,
        "intelligence": 0,
        "wisdom": +1,
        "stamina": +1
    },
    "stat_caps": {
        "strength": 105,
        "agility": 100,
        "reflex": 100,
        "intelligence": 100,
        "wisdom": 105,
        "stamina": 105
    },
    "learning_modifiers": {
        "combat": 1.05,
        "survival": 1.1,
        "magic": 1.0,
        "stealth": 0.95,
        "lore": 1.0
    },
    "size": "medium",
    "carry_modifier": 1.1
}
🐾 KALDAR
{
    "stat_modifiers": {
        "strength": +2,
        "agility": 0,
        "reflex": 0,
        "intelligence": -1,
        "wisdom": 0,
        "stamina": +1
    },
    "stat_caps": {
        "strength": 110,
        "agility": 100,
        "reflex": 100,
        "intelligence": 95,
        "wisdom": 100,
        "stamina": 105
    },
    "learning_modifiers": {
        "combat": 1.1,
        "survival": 1.05,
        "magic": 0.95,
        "stealth": 0.95,
        "lore": 1.0
    },
    "size": "medium",
    "carry_modifier": 1.15
}
⚠️ FINAL SYSTEM RULES
❌ No race:
exceeds modifier budget
dominates all categories
breaks learning balance
✅ Every race:
has strengths
has weaknesses
supports all professions
🔌 REQUIRED HOOKS (FOR FUTURE)

Must exist but NOT implemented yet:

get_race_stat_modifier(race, stat)
get_race_learning_modifier(race, category)
get_race_carry_modifier(race)
🧠 FINAL LOCK

This system is now:

DR-authentic ✔
balanced ✔
deterministic ✔
testable ✔
extensible ✔

CHARACTER CREATION — MICROTASKS 001–020 (STRICT)
🎯 PHASE GOAL

At the end of this set:

✔ Player can create a character via controlled flow
✔ Race + profession applied correctly
✔ Stats initialized deterministically
✔ Character spawns in valid state
✔ System is scriptable (DireTest-ready)

🧱 CORE CHARACTER CREATION PIPELINE
CHAR-001 — Create Character Creation Controller

File:

systems/chargen/controller.py

Responsibilities:

manage step-by-step creation flow
store temporary state
validate inputs
finalize character

No UI logic allowed here.

CHAR-002 — Define Creation State Object

Create structure:

chargen_state = {
    "name": None,
    "race": None,
    "profession": None,
    "stats": {},
    "confirmed": False
}

Must exist separately from Character object.

CHAR-003 — Enforce Creation Step Order (STRICT)

Order MUST be:

name
race
profession
stats
confirmation

No skipping allowed.

CHAR-004 — Create Name Input Handler

Command:

name <value>

Rules:

must be unique
length: 3–20 characters
alphabetic only

Reject invalid input.

CHAR-005 — Create Race Selection Command

Command:

race <race_name>

Rules:

must match locked race list
case-insensitive match
store canonical race key
CHAR-006 — Validate Race Selection

Reject if:

Invalid race.

List valid options in error message.

CHAR-007 — Create Profession Selection Command

Command:

profession <name>

Allowed:

warrior
thief
empath
cleric
CHAR-008 — Validate Profession Selection

Reject invalid values with:

Invalid profession.
📊 STAT INITIALIZATION SYSTEM
CHAR-009 — Define Base Stat Template (LOCKED)
BASE_STATS = {
    "strength": 10,
    "agility": 10,
    "reflex": 10,
    "intelligence": 10,
    "wisdom": 10,
    "stamina": 10
}
CHAR-010 — Apply Race Modifiers to Stats

On race selection:

final_stat = BASE + race_modifier

Do NOT apply caps yet.

CHAR-011 — Enforce Minimum Stat Floor

All stats must be:

>= 5

Clamp if needed.

CHAR-012 — Enforce Maximum Stat Ceiling (INITIAL)

All starting stats must be:

<= 20

Even if modifiers exceed.

CHAR-013 — Store Finalized Starting Stats

Save into:

chargen_state["stats"]

No randomness allowed.

🧑‍🎭 FINALIZATION PIPELINE
CHAR-014 — Create Confirmation Command

Command:

confirm

Displays summary:

name
race
profession
stats
CHAR-015 — Require Explicit Confirmation

Reject character creation unless:

chargen_state["confirmed"] == True
CHAR-016 — Create Character Object

On confirm:

instantiate Evennia Character
assign:
name
race
profession
stats
CHAR-017 — Apply Race System Hooks

Set on character:

db.race
db.stat_caps
db.learning_modifiers
db.size
db.carry_modifier

Must match race definition exactly.

CHAR-018 — Apply Profession Initialization Hook

Call:

apply_profession_template(character)

(Already exists or will be extended)

CHAR-019 — Assign Starting Location

Set:

character.location = START_ROOM

Define constant:

START_ROOM = "limbo"  # placeholder
CHAR-020 — Initialize Core Systems

On creation, initialize:

db.hp
db.max_hp
db.fatigue
db.balance
db.attunement
db.coins = 0
db.bank_coins = 0
db.vault_items = []

No missing fields allowed.

✅ END STATE AFTER CHAR-020

You now have:

✔ Full deterministic character creation pipeline
✔ Race system fully applied
✔ Profession integrated
✔ Valid starting character state
✔ No randomness / no ambiguity
✔ Fully scriptable (DireTest-ready)


CHARACTER CREATION — MICROTASKS 001–020 (STRICT)
🎯 PHASE GOAL

At the end of this set:

✔ Player can create a character via controlled flow
✔ Race + profession applied correctly
✔ Stats initialized deterministically
✔ Character spawns in valid state
✔ System is scriptable (DireTest-ready)

🧱 CORE CHARACTER CREATION PIPELINE
CHAR-001 — Create Character Creation Controller

File:

systems/chargen/controller.py

Responsibilities:

manage step-by-step creation flow
store temporary state
validate inputs
finalize character

No UI logic allowed here.

CHAR-002 — Define Creation State Object

Create structure:

chargen_state = {
    "name": None,
    "race": None,
    "profession": None,
    "stats": {},
    "confirmed": False
}

Must exist separately from Character object.

CHAR-003 — Enforce Creation Step Order (STRICT)

Order MUST be:

name
race
profession
stats
confirmation

No skipping allowed.

CHAR-004 — Create Name Input Handler

Command:

name <value>

Rules:

must be unique
length: 3–20 characters
alphabetic only

Reject invalid input.

CHAR-005 — Create Race Selection Command

Command:

race <race_name>

Rules:

must match locked race list
case-insensitive match
store canonical race key
CHAR-006 — Validate Race Selection

Reject if:

Invalid race.

List valid options in error message.

CHAR-007 — Create Profession Selection Command

Command:

profession <name>

Allowed:

warrior
thief
empath
cleric
CHAR-008 — Validate Profession Selection

Reject invalid values with:

Invalid profession.
📊 STAT INITIALIZATION SYSTEM
CHAR-009 — Define Base Stat Template (LOCKED)
BASE_STATS = {
    "strength": 10,
    "agility": 10,
    "reflex": 10,
    "intelligence": 10,
    "wisdom": 10,
    "stamina": 10
}
CHAR-010 — Apply Race Modifiers to Stats

On race selection:

final_stat = BASE + race_modifier

Do NOT apply caps yet.

CHAR-011 — Enforce Minimum Stat Floor

All stats must be:

>= 5

Clamp if needed.

CHAR-012 — Enforce Maximum Stat Ceiling (INITIAL)

All starting stats must be:

<= 20

Even if modifiers exceed.

CHAR-013 — Store Finalized Starting Stats

Save into:

chargen_state["stats"]

No randomness allowed.

🧑‍🎭 FINALIZATION PIPELINE
CHAR-014 — Create Confirmation Command

Command:

confirm

Displays summary:

name
race
profession
stats
CHAR-015 — Require Explicit Confirmation

Reject character creation unless:

chargen_state["confirmed"] == True
CHAR-016 — Create Character Object

On confirm:

instantiate Evennia Character
assign:
name
race
profession
stats
CHAR-017 — Apply Race System Hooks

Set on character:

db.race
db.stat_caps
db.learning_modifiers
db.size
db.carry_modifier

Must match race definition exactly.

CHAR-018 — Apply Profession Initialization Hook

Call:

apply_profession_template(character)

(Already exists or will be extended)

CHAR-019 — Assign Starting Location

Set:

character.location = START_ROOM

Define constant:

START_ROOM = "limbo"  # placeholder
CHAR-020 — Initialize Core Systems

On creation, initialize:

db.hp
db.max_hp
db.fatigue
db.balance
db.attunement
db.coins = 0
db.bank_coins = 0
db.vault_items = []

No missing fields allowed.

✅ END STATE AFTER CHAR-020

You now have:

✔ Full deterministic character creation pipeline
✔ Race system fully applied
✔ Profession integrated
✔ Valid starting character state
✔ No randomness / no ambiguity
✔ Fully scriptable (DireTest-ready)

This block completes:

stat allocation (controlled, not chaotic)
starting gear
starting skills
appearance
DireTest hooks
preventing broken early-game states

Still strict, no ambiguity, no Aedan guesswork.

🟩 CHARACTER CREATION — MICROTASKS 021–040 (STRICT)
🎯 PHASE GOAL

At the end of this set:

✔ Player has meaningful stat distribution
✔ Character starts with correct gear
✔ Skills initialized properly
✔ No invalid or broken builds
✔ Fully testable via DireTest

📊 STAT ALLOCATION SYSTEM (CONTROLLED)
CHAR-021 — Add Stat Point Pool (LOCKED)

Define:

STAT_POOL = 10

Player may distribute 10 additional points.

CHAR-022 — Create Stat Allocation Command

Command:

stat <stat_name> <amount>

Example:

stat strength 2
CHAR-023 — Validate Stat Names (STRICT)

Allowed:

["strength", "agility", "reflex", "intelligence", "wisdom", "stamina"]

Reject invalid:

Invalid stat.
CHAR-024 — Validate Allocation Limits

Rules:

cannot exceed remaining pool
cannot assign negative values
cannot exceed max starting cap (20)
CHAR-025 — Track Remaining Points

Store:

chargen_state["points_remaining"]

Display after each allocation:

Points remaining: X
CHAR-026 — Allow Stat Reallocation Before Confirm

Command:

resetstats

Resets:

stats back to base + race
pool restored
CHAR-027 — Prevent Confirmation with Unspent Points

If:

points_remaining > 0

Block confirm:

You must assign all stat points.
🎒 STARTING GEAR SYSTEM
CHAR-028 — Define Profession Gear Templates (LOCKED)

Create mapping:

STARTING_GEAR = {
    "warrior": [...],
    "thief": [...],
    "empath": [...],
    "cleric": [...]
}
CHAR-029 — Warrior Starting Gear (LOCKED)
[
    "broadsword",
    "leather_armor",
    "boots",
    "belt",
    "backpack"
]
CHAR-030 — Thief Starting Gear (LOCKED)
[
    "dagger",
    "lockpick",
    "leather_armor",
    "cloak",
    "gem_pouch",
    "backpack"
]
CHAR-031 — Empath Starting Gear (LOCKED)
[
    "staff",
    "robes",
    "herb_pouch",
    "backpack"
]
CHAR-032 — Cleric Starting Gear (LOCKED)
[
    "mace",
    "robes",
    "holy_symbol",
    "backpack"
]
CHAR-033 — Assign Gear on Creation

On confirm:

spawn each item
move to character inventory
CHAR-034 — Auto-Wear Starter Equipment

Automatically:

wear armor
wield weapon (if applicable)
📚 STARTING SKILL SYSTEM
CHAR-035 — Define Starting Skill Template (LOCKED)

Each profession starts with:

BASE_SKILLS = {
    "all": 10
}

Profession bonuses applied separately.

CHAR-036 — Apply Profession Skill Bonuses

Example:

PROFESSION_SKILLS = {
    "warrior": {"combat": 20},
    "thief": {"stealth": 20},
    "empath": {"magic": 20},
    "cleric": {"magic": 20}
}
CHAR-037 — Initialize Skill Data Structure

On character:

db.skills = {
    "combat": value,
    "survival": value,
    "magic": value,
    "stealth": value,
    "lore": value
}
🧍 APPEARANCE SYSTEM
CHAR-038 — Add Description Command During Chargen

Command:

describe <text>

Stores:

chargen_state["description"]
CHAR-039 — Apply Description on Creation

Set:

character.db.desc = chargen_state["description"]

Default if empty:

A newly arrived adventurer.
🧪 DIRETEST INTEGRATION (CRITICAL)
CHAR-040 — Add Chargen Script Interface

Create function:

create_character_from_template(template)

Template includes:

{
    "name": str,
    "race": str,
    "profession": str,
    "stats": dict
}

Must:

bypass command flow
still enforce all validation rules
produce identical result as manual creation
✅ END STATE AFTER CHAR-040

You now have:

✔ Controlled stat allocation (no RNG chaos)
✔ Balanced starting characters
✔ Profession-aligned gear
✔ Skill initialization
✔ Appearance support
✔ Fully scriptable chargen (DireTest-ready

We are now locking:

chargen flow control
edge-case validation
persistence safety
starting locations
tutorial hooks
anti-exploit protections

Still strict. Still no Aedan guesswork.

🟩 CHARACTER CREATION — MICROTASKS 041–060 (STRICT)
🎯 PHASE GOAL

At the end of this set:

✔ Chargen flow is robust
✔ Partial/broken characters cannot leak into game
✔ Starting locations are controlled
✔ Name handling is safe
✔ Tutorial/onboarding hooks exist
✔ DireTest can create and tear down characters reliably

🧭 CHARGEN FLOW CONTROL
CHAR-041 — Add Chargen Status Command

Command:

chargen

Output must show:

current step
chosen name
chosen race
chosen profession
current stats
points remaining
description status
whether ready to confirm

No editing occurs here. Status only.

CHAR-042 — Add Current Step Tracker

Store in chargen state:

chargen_state["current_step"]

Allowed values:

["name", "race", "profession", "stats", "description", "confirm"]

Must update only through controller logic.

CHAR-043 — Reject Out-of-Order Commands

If player tries a command outside the current step, reject with:

You are not on that step yet.

No auto-advance. No silent correction.

CHAR-044 — Auto-Advance Only After Valid Input

After successful completion of a step:

controller advances to next step automatically

After failed validation:

remain on same step
CHAR-045 — Add Back Command

Command:

back

Behavior:

move back exactly one step
preserve previously entered valid data unless overwritten later

Cannot move back before name.

🧾 NAME SAFETY + RESERVATION
CHAR-046 — Add Temporary Name Reservation

When a valid name is chosen:

reserve it in chargen session state
prevent concurrent use by another active chargen session

Reservation must be released on:

cancel
timeout
successful final creation
CHAR-047 — Add Chargen Cancel Command

Command:

cancel

Behavior:

destroy chargen_state
release name reservation
return player to pre-chargen state or disconnect-safe state
CHAR-048 — Add Chargen Timeout

If chargen session is inactive for:

CHARGEN_TIMEOUT_MINUTES = 30

Then:

cancel session
release reservation
log timeout event

No character object created.

CHAR-049 — Revalidate Name at Final Confirm

On final confirm:

recheck uniqueness before character creation
if conflict exists, fail confirm and return player to name step

No duplicate characters allowed.

🧱 PERSISTENCE SAFETY
CHAR-050 — Do Not Create Character Object Until Final Confirm

Hard rule:

no persistent Character object may exist before final confirm succeeds

Chargen state must remain separate and temporary.

CHAR-051 — Make Character Creation Atomic

Finalization must occur in a single controlled transaction path:

validate all required fields
create character
apply race data
apply profession data
apply stats
apply skills
assign gear
set location
mark creation complete

If any step fails:

destroy partial character
return error
preserve chargen state for retry
CHAR-052 — Add Finalization Failure Logging

On any failed finalize:

write structured error log including:
name
race
profession
current chargen state
traceback/error message

No silent failures.

CHAR-053 — Add Required Field Validator

Before finalize, enforce presence of:

name
race
profession
stats
points_remaining == 0
description field present (can be defaulted)
confirmed == True

Reject if any missing.

🗺️ STARTING LOCATION CONTROL
CHAR-054 — Replace Placeholder Start Room with Profession-Aware Resolver

Create function:

get_start_room(profession)

Locked return values for v1:

warrior → START_ROOM_WARRIOR
thief → START_ROOM_THIEF
empath → START_ROOM_EMPATH
cleric → START_ROOM_CLERIC

If specific rooms do not yet exist:

all may temporarily map to same fallback room
resolver function is still mandatory
CHAR-055 — Define Start Room Constants

Create constants:

START_ROOM_FALLBACK
START_ROOM_WARRIOR
START_ROOM_THIEF
START_ROOM_EMPATH
START_ROOM_CLERIC

Hard rule:

no inline room lookup strings in creation logic
CHAR-056 — Add Safe Fallback If Start Room Missing

If profession-specific room not found:

place character in START_ROOM_FALLBACK
log warning

Do not fail character creation due to missing room.

🎓 TUTORIAL / ONBOARDING HOOKS
CHAR-057 — Add First-Login Flag

On newly created character:

db.is_new_character = True

This flag is required for tutorial and onboarding systems later.

CHAR-058 — Add Intro Message Hook

On first successful spawn, call:

run_new_character_intro(character)

Stub is acceptable, but hook is mandatory.

This hook must not contain chargen logic.

CHAR-059 — Add Starter Pack Summary Message

After creation, send player summary including:

race
profession
weapon/gear received
start location
next suggested command(s)

This message must be deterministic and profession-aware.

🧪 DIRETEST + ADMIN SUPPORT
CHAR-060 — Add Character Teardown Helper for Tests

Create function:

destroy_test_character(character)

Requirements:

safe removal of test-created character
cleanup inventory/items created during chargen
cleanup reservations or temp state if present
no effect on non-test characters unless explicitly flagged

This is mandatory for DireTest repeatability.

✅ END STATE AFTER CHAR-060

You now have:

✔ Full step-controlled chargen flow
✔ Name reservation and timeout protection
✔ Atomic creation safety
✔ Profession-based start location support
✔ Tutorial hooks
✔ Test-safe teardown path

🧠 WHAT THIS FINISHES

At this point, your character creation system is no longer a prototype.

It is now:

deterministic
safe
scriptable
extensible
production-viable

RACE INTEGRATION — MICROTASKS 061–080 (STRICT)
🎯 PHASE GOAL

At the end of this set:

✔ Race affects encumbrance
✔ Race affects learning rates
✔ Race caps enforced in progression
✔ Race visible to player systems
✔ DireTest can validate race behavior

⚖️ WEIGHT + ENCUMBRANCE INTEGRATION
RACE-061 — Apply Carry Modifier to Max Weight

Modify:

max_carry_weight

Formula:

max_carry_weight = base_carry_weight * race.carry_modifier

Must be applied:

on character creation
on login (recalculate)
RACE-062 — Prevent Direct Override of Carry Modifier

Carry modifier must ONLY come from:

character.db.race

Reject any external overrides.

RACE-063 — Update Encumbrance Calculation

Ensure:

encumbrance_ratio = total_weight / max_carry_weight

reflects race modifier immediately.

RACE-064 — Add Race Impact Messaging (Encumbrance)

If character is:

small race and heavily loaded:
The load feels especially burdensome for your size.
large race and lightly loaded:
You handle the weight with ease.

Trigger thresholds:

80% encumbrance

<30% encumbrance
📈 LEARNING SYSTEM INTEGRATION
RACE-065 — Apply Learning Modifier Hook

Modify skill gain:

final_xp = base_xp * race.learning_modifiers[category]

Must apply in:

all skill learning systems
no exceptions
RACE-066 — Enforce Category Mapping

Every skill MUST map to one of:

["combat", "survival", "magic", "stealth", "lore"]

Reject undefined categories.

RACE-067 — Prevent Stacking Exploits

Learning modifiers must:

apply once only
not stack with themselves
RACE-068 — Add Debug Output Hook

Admin command:

@racemods

Displays:

learning modifiers
carry modifier
stat caps

Required for debugging.

🧠 STAT CAP ENFORCEMENT
RACE-069 — Enforce Stat Caps on Level-Up / Training

Whenever stats increase:

if stat > race.stat_caps[stat]:
    stat = race.stat_caps[stat]

No overflow allowed.

RACE-070 — Prevent Over-Cap Allocation Anywhere

Must enforce caps in:

chargen
stat increases
buffs (future-safe)
RACE-071 — Add Cap Feedback Messaging

If player hits cap:

You cannot improve that attribute further.
🧾 PLAYER VISIBILITY
RACE-072 — Add Race to SCORE Command

Display:

Race: Elf

Must appear near:

profession
level/circle
RACE-073 — Add Race to LOOK (Self)

When player looks at self:

You are an Elf.
RACE-074 — Add Race to LOOK (Others)

Example:

An elf stands here.

Must be lowercase for descriptive text.

RACE-075 — Standardize Race Name Formatting

Internal:

"elf"

Display:

Elf

No inconsistencies allowed.

🧪 DIRETEST INTEGRATION
RACE-076 — Add Race Test Fixture Templates

Create predefined builds:

TEST_RACES = [
    "human",
    "elf",
    "dwarf",
    "halfling",
    "gnome",
    "gor_togh",
    "s_kra_mur",
    "kaldar"
]

Used in:

balance simulations
scenario tests
RACE-077 — Add Race Validation Test Hook

Function:

validate_race_application(character)

Checks:

stat modifiers applied
caps correct
learning modifiers present
carry modifier correct
RACE-078 — Add Cross-Race Balance Scenario

DireTest scenario:

same profession
same stats
different races

Compare:

encumbrance
xp gain
combat outcome
RACE-079 — Add Race Impact Logging

During simulations log:

race,
encumbrance_ratio,
xp_rate,
combat_effectiveness

Used for balance reports.

RACE-080 — Add Race Consistency Invariant

Invariant rule:

race data must match canonical race definition at all times

If mismatch:

fail test immediately
✅ END STATE AFTER RACE-080

You now have:

✔ Race fully integrated into gameplay systems
✔ Learning system influenced by race
✔ Encumbrance influenced by race
✔ Stat caps enforced correctly
✔ Player-visible race identity
✔ DireTest compatibility
