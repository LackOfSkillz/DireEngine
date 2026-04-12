DragonRealms character creation is not classically “menu outside the game”, but it also is not fully diegetic/in-world in the way guild choice later is. Modern DR uses a Character Manager / limbo-world creation space where you choose name, sex, race, appearance, and starting location, and then you enter the world as a Commoner. You do not choose your guild during character creation; guild joining happens afterward, in the live game world.

The high-level DR creation flow

The documented modern flow is:

create character in the Character Manager
choose name
choose sex/gender
choose race
choose appearance/body features
choose starting location
enter the world as a Commoner
later, join a guild in-character in the actual world.

So the answer to your recollection is:

guild choice is definitely in-character and post-creation
race/appearance/name/start location are handled during character creation in a limbo-style manager space, not after full world entry.
Why it feels “in character”

The part you’re remembering is probably this: Elanthipedia’s new player guide says that when a character is first made, they are in a “limbo world” where they choose many of their traits. That means DR presents creation as an interactive game-space process rather than a pure detached launcher menu.

That gives it a hybrid feel:

not a modern MMO lobby wizard
not fully embodied roleplay in the live world either
more like a pre-world in-engine staging area.
What you choose during DR character creation

According to the Character Manager page, players choose:

name
sex
race
appearance
starting location

Premium/Platinum players can also choose age and date of birth. The same page lists detailed appearance features such as hair, eyes, skin, body, height, build, and more, depending on race.

That means DR chargen is heavily appearance-driven, much more than profession-driven at that stage. Profession identity comes later.

What you do not choose during DR character creation

You do not choose your guild during character creation. The new player guide states this directly, and the guild page confirms that adventurers begin as Commoners and may then choose membership in one of the active guilds afterward.

This is one of the most important structural lessons from DR:

identity is split

race/body/name first
guild/profession second

That is a big reason DR’s world feels more in-character than a standard “pick class on the setup screen” RPG.

Stats during DR creation

Another important DR behavior: starting stats are not random rolls anymore. The attributes page says that in January 2008, Simutronics removed random stat rolls, and new characters now start with what used to be a perfect roll, with starting stats determined by race. It also lists race-based starting stat spreads.

That means DR creation is not a “roll until you like the numbers” system. It is much more controlled:

race determines starting stat pattern
profession does not get chosen yet
later progression differentiates the character further.
Starting location and starter gear

The Character Manager page says that as of March 1, 2011, players could choose whether to start in The Crossing or Riverhaven. It also documents race-based starting gear, noting that all new characters start with a divine charm, a map, a weapon, leather body armor, a container, clothing, and an accessory, with specific items varying by race.

That is another strong DR pattern:

chargen establishes embodied identity
the world entry establishes place
guild choice establishes career
The real design lesson for DireMud

If you want DireMud to feel authentically DR-like, then the best takeaway is not “everything must be a menu” and also not “everything must be a pure roleplay scene.”

The stronger DR pattern is:

1. Character creation should feel like an interactive staging space

Not a sterile out-of-world form, but also not full in-world progression yet. DR’s “limbo world” is a good model.

2. Race/body/name are chosen first

This defines who the character is physically and socially.

3. Profession should be chosen later, in-world

This is the biggest DR-authenticity point. DR characters begin as Commoners and join a guild afterward.

4. Starting stats should be controlled, not rolled

DR’s modern system uses fixed race-based starting stats rather than random rolling.

My recommendation for your chargen polish

Based on this research, I would change course slightly from the system we were starting to build.

For DR fidelity, I would recommend:

keep a chargen space rather than a disconnected pregame wizard
let players choose:
name
race
appearance/body details
starting city/starting location
have them enter the world as a Commoner
then let them join Warrior / Thief / Empath / Cleric in-world through profession-specific locations or initiation flows

That would be much closer to DragonRealms than picking profession inside the initial creation pipeline.

Bottom line

Your memory was directionally right:

DragonRealms does not front-load guild/class choice into chargen
it does use a character-creation manager / limbo-world stage
and the stronger in-character identity move happens when the new character enters the world as a Commoner and later joins a guild.

Character Creation System = Flow + Validation + Assembly

Responsible for:

step progression
user input
validation
stat allocation
name handling
confirmation
final character assembly

It should:

know nothing about how race works internally
only call:
apply_race(character, race_key)

👉 Think: orchestrator

🔌 THE ONLY INTEGRATION POINT (STRICT)

This is the only place these systems meet:

final_character = create_character()

apply_race(final_character, race_key)
apply_profession(final_character, profession_key)

That’s it.

⚠️ WHAT WE MUST FIX FROM OUR CURRENT PLAN

You correctly caught this:

“we stubbed some of this into race system”

That’s dangerous if not corrected.

❌ Things that DO NOT belong in race system:
chargen flow
stat allocation logic
UI commands
confirmation logic
starting gear
starting skills
✅ Race system ONLY contains:
definitions
lookup functions
modifiers
🧱 FINAL ARCHITECTURE (CLEAN SEPARATION)
systems/
  race/
    definitions.py
    hooks.py
    utils.py

  chargen/
    controller.py
    state.py
    validators.py
    flow.py

  character/
    creation.py  <-- integration point
🧠 HOW THEY WORK TOGETHER
Step 1 — Chargen builds a blueprint
chargen_state = {
    "name": "Kier",
    "race": "elf",
    "profession": "thief",
    "stats": {...}
}
Step 2 — Creation system executes assembly
character = create_character_base()

apply_race(character, "elf")
apply_profession(character, "thief")
apply_stats(character, stats)
apply_starting_gear(character)
Step 3 — Runtime systems take over

From that point on:

race system influences gameplay
chargen system is completely out of the picture
🧪 WHY THIS MATTERS FOR DIRETEST

If we do this right:

DireTest can:

spawn characters instantly
bypass chargen UI
inject race/profession cleanly
run deterministic simulations

If we do this wrong:

tests will depend on UI flow
harder to isolate bugs
harder to simulate builds
🧭 DESIGN PRINCIPLE (LOCK THIS)

Chargen creates a character.
Race defines how that character behaves.

Not the other way around.

⚠️ IMPORTANT DESIGN CHOICE (WE SHOULD DECIDE NOW)

Based on your DR research:

Do we:
Option A — Keep profession in chargen (current plan)
simpler
faster to build
less DR-authentic
Option B — DR-authentic model
chargen creates Commoner
profession chosen in-world later
My recommendation (based on your system maturity):

👉 Hybrid approach (BEST FOR YOU)

Keep profession selection in chargen for now (so systems work)
Architect it so profession selection can later be:
optional
deferred
moved into world

That means:

chargen supports profession
but doesn’t require it long-term

CHARGEN ARCHITECTURE LOCK (DIREMUD)
🎯 PRIMARY GOAL

Chargen is a temporary orchestration system that produces a valid character.
It does NOT define gameplay behavior.

🧱 SYSTEM SEPARATION (HARD BOUNDARIES)
1. 🧬 Race System (EXTERNAL)
owns:
stat modifiers
stat caps
learning modifiers
carry modifier
size
exposes ONLY:
get_race_definition(race_key)
apply_race(character, race_key)
must NOT:
know chargen exists
contain UI or flow logic
modify chargen state
2. 🧑‍🎭 Chargen System (THIS SYSTEM)
owns:
flow (steps)
input validation
temporary state
stat allocation
name handling
confirmation
produces:
character_blueprint
must NOT:
apply gameplay logic directly
modify runtime systems
contain race/profession logic internally
3. 🧍 Character Assembly System (INTEGRATION POINT)

This is the ONLY place where systems connect.

File:

systems/character/creation.py

Responsible for:

creating the actual Character object
applying:
race
profession
stats
gear
skills
🔌 DATA FLOW (LOCKED)
Step 1 — Chargen builds blueprint
character_blueprint = {
    "name": str,
    "race": str,
    "profession": str,
    "stats": dict,
    "description": str
}

No side effects. No DB writes.

Step 2 — Assembly executes creation
character = create_character_base(name)

apply_race(character, blueprint["race"])
apply_profession(character, blueprint["profession"])
apply_stats(character, blueprint["stats"])
apply_starting_gear(character)
apply_skills(character)
Step 3 — Runtime takes over
chargen is discarded
only character object persists
⚠️ HARD RULES (NON-NEGOTIABLE)
❌ Chargen must NEVER:
write directly to Character DB fields
apply race modifiers manually
apply learning modifiers
set carry capacity
calculate derived stats (HP, fatigue, etc.)
✅ Chargen ONLY:
collects inputs
validates inputs
builds blueprint
calls assembly
🧠 BLUEPRINT CONTRACT (STRICT)

This is the ONLY allowed interface:

character_blueprint = {
    "name": str,
    "race": str,
    "profession": str,
    "stats": {
        "strength": int,
        "agility": int,
        "reflex": int,
        "intelligence": int,
        "wisdom": int,
        "stamina": int
    },
    "description": str
}

No additional fields allowed in v1.

🔄 FLOW CONTROL MODEL

Chargen is a state machine, not a free-form command system.

Allowed states:
[
    "name",
    "race",
    "profession",
    "stats",
    "description",
    "confirm"
]

Transitions:

forward only on valid input
backward via back
no skipping
🧾 NAME SYSTEM (LOCKED)
reserved during chargen
released on:
cancel
timeout
success
revalidated at final creation
📊 STAT SYSTEM (CHARGEN SIDE)

Chargen:

starts from BASE_STATS
applies race modifiers ONLY for preview
allows point allocation
enforces:
min floor
max starting ceiling
pool usage

Chargen does NOT:

enforce stat caps (runtime does)
apply derived effects
🎒 GEAR / SKILLS (SEPARATION)

Chargen:

does NOT assign gear
does NOT assign skills

Assembly system:

handles all gear and skill initialization
🧪 DIRETEST COMPATIBILITY (REQUIRED)

Chargen must support:

create_character_from_template(template)

Which:

bypasses flow
builds blueprint directly
passes through same assembly pipeline

👉 Guarantees:

identical results
no divergence between manual and automated creation
🧠 PROFESSION HANDLING (HYBRID LOCK)

We are locking:

profession is selected during chargen (for now)
but system must allow:
profession = None

Future:

supports DR-style “Commoner first”
⚠️ FAILURE HANDLING (ATOMIC)

If any step fails during final creation:

no character persists
blueprint remains intact
error returned
user can retry
🧭 FILE STRUCTURE (LOCKED)
systems/
  race/
    definitions.py
    hooks.py

  chargen/
    controller.py
    state.py
    validators.py
    flow.py

  character/
    creation.py
🧠 DESIGN PRINCIPLE (FINAL LOCK)

Chargen is a builder
Race is a modifier system
Character assembly is the executor

✅ WHAT THIS FIXES

This architecture guarantees:

✔ No system coupling
✔ No duplicate logic
✔ Clean testability
✔ DireTest compatibility
✔ Future flexibility (Commoner model)

CHARGEN POLISH — MICROTASKS 001–020 (STRICT, ARCH LOCKED)
🎯 PHASE GOAL

At the end of this set:

✔ Chargen builds a clean blueprint (no side effects)
✔ No race/profession logic leaks into chargen
✔ Assembly is the only system creating characters
✔ Fully DireTest-compatible

🧱 CHARGEN CORE REFACTOR
CHARGEN-001 — Create Blueprint Data Structure (LOCKED)

File:

systems/chargen/state.py

Define:

class CharacterBlueprint:
    name: str
    race: str
    profession: str | None
    stats: dict
    description: str

No additional fields allowed.

CHARGEN-002 — Remove All Direct Character DB Writes from Chargen

Search entire chargen system.

Remove ANY usage of:

character.db.*

Chargen must NEVER modify a Character object.

CHARGEN-003 — Create ChargenState Wrapper

Structure:

class ChargenState:
    blueprint: CharacterBlueprint
    current_step: str
    points_remaining: int
    reserved_name: str | None

This replaces all loose dict usage.

CHARGEN-004 — Initialize Blueprint with Empty Defaults

On chargen start:

blueprint = CharacterBlueprint(
    name=None,
    race=None,
    profession=None,
    stats={},
    description=None
)

No implicit values.

CHARGEN-005 — Enforce State Machine Controller

All commands must pass through:

ChargenController.handle_input(command, args)

No direct command execution outside controller.

CHARGEN-006 — Centralize Step Validation Logic

Create:

validate_step_input(step, input)

Used by ALL steps.

No duplicated validation logic.

🧾 NAME SYSTEM (CORRECTED)
CHARGEN-007 — Move Name Reservation into ChargenState Only

Store reservation in:

state.reserved_name

Do NOT write to DB or global registry directly here.

CHARGEN-008 — Create Name Reservation Service

File:

systems/chargen/validators.py

Function:

reserve_name(name) -> bool
release_name(name)

Chargen calls this service—does not manage registry itself.

CHARGEN-009 — Validate Name Without Side Effects First

Validation order:

format check
availability check
THEN reserve

Never reserve invalid names.

CHARGEN-010 — Revalidate Name at Final Assembly Only

Chargen must NOT assume reservation is still valid.

Final check occurs ONLY in:

systems/character/creation.py
🧬 RACE SYSTEM INTEGRATION (CLEAN)
CHARGEN-011 — Replace Any Race Logic with Lookup Only

Chargen may ONLY call:

get_race_definition(race_key)

Allowed use:

preview stats only
CHARGEN-012 — Prohibit Applying Race Effects in Chargen

Chargen must NOT:

apply carry modifier
apply learning modifiers
apply stat caps

Only preview stat modifiers.

CHARGEN-013 — Add Race Preview Function

Function:

preview_race_stats(base_stats, race_key)

Returns:

preview_stats

Used only for display.

📊 STAT SYSTEM (CLEAN SEPARATION)
CHARGEN-014 — Separate Base Stats from Allocated Stats

Store:

state.base_stats
state.allocated_points

Final blueprint stats computed only at confirm.

CHARGEN-015 — Prevent Direct Stat Mutation

All stat changes must go through:

apply_stat_allocation(state, stat, amount)

No direct dictionary edits allowed.

CHARGEN-016 — Add Final Stat Assembly Function
final_stats = build_final_stats(state)

Combines:

base stats
race modifiers (preview only)
allocated points

Returns clean dict.

CHARGEN-017 — Do NOT Clamp to Race Caps in Chargen

Chargen only enforces:

min floor
max starting ceiling

Race caps enforced later in runtime.

🧑‍🎭 PROFESSION HANDLING (FUTURE SAFE)
CHARGEN-018 — Allow profession to be None

Validation must allow:

profession = None

Only enforce if required by flow config.

CHARGEN-019 — Move Profession Logic OUT of Chargen

Chargen must NOT:

assign skills
assign gear
apply bonuses

Only store:

blueprint.profession
🧱 FINALIZATION HANDOFF
CHARGEN-020 — Replace Confirm with Blueprint Handoff

On confirm:

Chargen must call:

create_character_from_blueprint(blueprint)

Located in:

systems/character/creation.py

Chargen must NOT:

create character directly
assign stats
assign gear
✅ END STATE AFTER CHARGEN-020

You now have:

✔ Fully decoupled chargen system
✔ Clean blueprint-driven creation
✔ No race/profession leakage
✔ Deterministic stat handling
✔ Centralized validation
✔ Proper system boundaries

CHARGEN POLISH — MICROTASKS 021–040 (STRICT)
🎯 PHASE GOAL

At the end of this set:

✔ Chargen has a clean guided flow
✔ Players can review and edit safely
✔ Appearance entry is structured
✔ Errors are clear and deterministic
✔ Aedan has admin/debug hooks

🧭 FLOW + PROMPT SYSTEM
CHARGEN-021 — Create Step Prompt Renderer

File:

systems/chargen/flow.py

Create:

render_step_prompt(state) -> str

It must return the exact prompt text for the current step.

No validation logic in this function.

CHARGEN-022 — Define Canonical Step Prompt Text

Create a locked prompt map for:

name
race
profession
stats
description
confirm

All prompts must come from one centralized constant table.

No inline prompt strings elsewhere in chargen.

CHARGEN-023 — Show Prompt After Every Successful Step Advance

When a valid step completes and state advances:

automatically render the next step prompt

Do not require the player to type chargen to continue.

CHARGEN-024 — Re-Show Current Prompt After Validation Failure

If input fails validation:

show error message
then re-render the current step prompt

Do not advance or silently drop the player into an undefined state.

CHARGEN-025 — Add Help Command Within Chargen

Command:

help

While in chargen, it must show chargen-specific help only:

available commands
current step
how to go back
how to cancel

It must not dump full game help.

🧾 REVIEW + EDITING CONTROLS
CHARGEN-026 — Add Review Command

Command:

review

Output must show current blueprint values:

name
race
profession
current preview stats
points remaining
description preview

No editing occurs here.

CHARGEN-027 — Add Edit Command

Command:

edit <step>

Allowed step targets:

name
race
profession
stats
description

It must move the player back to that step and invalidate only downstream dependent fields as required.

CHARGEN-028 — Define Downstream Invalidation Rules

When editing:

changing name invalidates only name confirmation
changing race invalidates:
stat preview
stat allocation totals
changing profession does not invalidate stats
changing stats does not invalidate name/race/profession
changing description invalidates only description

These rules must be implemented centrally, not ad hoc.

CHARGEN-029 — Reset Stat Allocation Automatically on Race Change

If race is changed after stats were allocated:

restore point pool to full
clear allocated stat points
recompute preview from base + new race modifiers

No carryover allowed.

CHARGEN-030 — Require Re-Confirm After Any Edit

If any step is edited after reaching confirm:

set blueprint back to unconfirmed state
return to the edited step
require fresh confirm
🧍 APPEARANCE / DESCRIPTION FLOW (DR-INSPIRED)
CHARGEN-031 — Replace Freeform Description Step with Structured Appearance Fields

Chargen should no longer store only a single raw description input at this step.

Create temporary appearance fields in state:

build
height
hair
eyes
skin

These are chargen-only fields until final description assembly.

CHARGEN-032 — Define Allowed Appearance Values (LOCKED TABLES)

Create centralized tables for each field.

Example structure:

APPEARANCE_OPTIONS = {
    "build": [...],
    "height": [...],
    "hair": [...],
    "eyes": [...],
    "skin": [...]
}

All values must be explicit and enumerable.
No freeform user text for these fields in v1.

CHARGEN-033 — Create Appearance Entry Commands

Commands:

build <value>
height <value>
hair <value>
eyes <value>
skin <value>

These commands are only valid during the description/appearance phase.

CHARGEN-034 — Enforce Complete Appearance Before Confirm

All five appearance fields must be present before chargen may advance to confirm.

Reject incomplete appearance step with a clear list of missing fields.

CHARGEN-035 — Create Final Description Assembly Function

Create:

build_description_from_appearance(state) -> str

This function must produce the final blueprint description string from the selected appearance fields.

No inline string composition elsewhere.

CHARGEN-036 — Store Final Description Only in Blueprint

When appearance is complete:

assemble final description string
store it in:
blueprint.description

Do not write to Character.
Do not persist partial appearance selections outside chargen state.

📊 STAT STEP UX POLISH
CHARGEN-037 — Add Stat Summary Output After Every Allocation

After a successful stat <name> <amount>:

show all current preview stats
show points remaining

This output must be centralized through a single formatter.

CHARGEN-038 — Add Reset Confirmation for Stat Reset

Command:

resetstats

Must require explicit confirmation:

resetstats confirm

No accidental reset allowed.

CHARGEN-039 — Add “remaining points required” Error Text

If player attempts to leave stats step early, output exactly:

You must assign all remaining stat points before continuing.

Use this same text everywhere this condition is enforced.

🛠️ ADMIN / DEBUG SUPPORT
CHARGEN-040 — Add Chargen Debug Inspect Command

Admin command:

@chargeninspect <account_or_session>

Output must show:

current step
reserved name
blueprint contents
appearance selections
points remaining
last validation error if available

Read-only only. No editing from this command.

✅ END STATE AFTER CHARGEN-040

You now have:

✔ guided step prompts
✔ safe review/edit flow
✔ structured DR-style appearance entry
✔ deterministic description assembly
✔ clearer stat UX
✔ admin/debug inspection

🧠 WHAT THIS IMPROVES

This moves chargen from:

functional
to
usable
inspectable
harder to break
much closer to a real in-engine character creation experience

CHARGEN POLISH — MICROTASKS 041–060 (STRICT)
🎯 PHASE GOAL

At the end of this set:

✔ Chargen survives disconnects
✔ No orphan or broken sessions
✔ Account linkage is clean
✔ Supports future Commoner model
✔ Fully testable + resettable
✔ No exploit paths

🔌 SESSION LIFECYCLE MANAGEMENT
CHARGEN-041 — Bind ChargenState to Account, Not Session

Chargen state must be stored on:

account.db.chargen_state

NOT:

session object
temporary memory-only structures

This allows reconnect recovery.

CHARGEN-042 — Restore Chargen on Reconnect

On login:

if account.db.chargen_state exists:
resume chargen at stored step
re-render current prompt

Do NOT restart chargen.

CHARGEN-043 — Block Game Entry While Chargen Active

If chargen is active:

block access to normal commands
restrict input to chargen commands only

Message:

You are still creating your character.
CHARGEN-044 — Add Explicit Chargen Exit Lock

Prevent:

entering world
switching characters
using non-chargen commands

Until:

chargen completes OR
chargen is canceled
🔁 TIMEOUT + RECOVERY
CHARGEN-045 — Add Soft Timeout Warning

At:

25 minutes inactivity

Send warning:

Your character creation session will expire soon.
CHARGEN-046 — Add Hard Timeout Enforcement

At:

30 minutes inactivity
cancel chargen
release name
clear state
CHARGEN-047 — Preserve Last Input Timestamp

Store:

state.last_activity_timestamp

Update on every valid command.

🧾 ACCOUNT ↔ CHARACTER HANDOFF
CHARGEN-048 — Link Character to Account Only After Success

Character must NOT be added to account’s playable characters list until:

full assembly succeeds
all validation passes
CHARGEN-049 — Prevent Partial Character Registration

If creation fails:

character must NOT appear in account
no ghost entries allowed
CHARGEN-050 — Add Post-Creation Cleanup

After successful creation:

delete account.db.chargen_state
release name reservation
clear temp data
🧑‍🌾 COMMONER-FUTURE SUPPORT (IMPORTANT)
CHARGEN-051 — Allow Profession to Be Optional in Flow

Chargen flow must support configuration:

REQUIRE_PROFESSION = True  # default

If set to False:

skip profession step entirely
CHARGEN-052 — Handle Profession = None in Blueprint

Blueprint must support:

profession = None

Assembly must handle safely.

CHARGEN-053 — Create Stub for In-World Profession Assignment

Create placeholder function:

assign_profession_in_world(character, profession)

No implementation required yet.

Hook must exist.

🧪 DIRETEST INTEGRATION (FINALIZED)
CHARGEN-054 — Add Chargen Fixture Templates

Create templates:

CHARGEN_TEMPLATES = [
    {"race": "human", "profession": "warrior"},
    {"race": "elf", "profession": "thief"},
    {"race": "dwarf", "profession": "cleric"},
    {"race": "halfling", "profession": "empath"}
]

Used by DireTest.

CHARGEN-055 — Add Deterministic Character Factory

Function:

create_test_character(template)

Must:

bypass UI
use blueprint
pass through full assembly pipeline
CHARGEN-056 — Add Chargen Regression Test Hook

Function:

validate_chargen_output(character, template)

Checks:

race applied
stats match expected
profession applied
gear assigned
description exists
🛡️ EXPLOIT PREVENTION
CHARGEN-057 — Prevent Duplicate Stat Allocation via Race Swap Exploit

If player:

allocates stats
switches race
attempts to preserve allocation

System must:

fully reset stat allocation
restore pool

No carryover allowed.

CHARGEN-058 — Prevent Multi-Session Chargen Abuse

If account starts chargen:

block starting another chargen session simultaneously

Message:

You already have an active character creation session.
CHARGEN-059 — Prevent Command Injection During Chargen

Chargen input must:

reject unknown commands
reject system/admin commands
whitelist only chargen commands
CHARGEN-060 — Add Chargen Invariant Check

Create invariant:

blueprint must be complete before confirm
no null fields allowed
stat totals valid
race/profession valid

If violated:

block confirm
log error
✅ END STATE AFTER CHARGEN-060

You now have:

✔ fully persistent chargen sessions
✔ reconnect-safe flow
✔ clean account/character separation
✔ Commoner-ready architecture
✔ DireTest integration hooks
✔ exploit protections

🧠 WHAT YOU JUST COMPLETED

This is now:

A production-grade, DR-inspired, system-safe character creation pipeline

Not:

a prototype
not a menu hack
not a fragile flow
🚀 WHAT THIS UNLOCKS

Now you can safely:

✔ onboard real players
✔ simulate full gameplay loops
✔ run DireTest scenarios with valid characters
✔ begin true balance testing

LAST INTAKE ONBOARDING LOCK (DIREMUD)
🎯 CORE GOAL

Replace menu-feeling chargen with a fully in-world onboarding scenario where:

the player learns by doing
identity is established through physical interaction
urgency drives pacing
mistakes teach without trapping the player
the player exits feeling capable, equipped, and curious

This onboarding scenario is now the canonical target for the next creation/onboarding phase.

SCENARIO PREMISE

The player arrives late to an abandoned training compound just before a minor goblin incursion hits.

Two NPC roles drive the experience:

Mentor
competent, impatient, efficient
not warm, not cruel
respects action over questions

Gremlin Assistant
eager, unreliable, disruptive by design
causes small controlled mistakes
exists to create friction that resolves into understanding

⚠️ LOCKED EXPERIENCE PILLARS

Do not break these:

No menus. All identity and tutorial beats must happen through physical spaces, objects, NPCs, and commands.

One action = one lesson.

Urgency must push the player forward without making objectives unclear.

The player must never get stuck.

Gremlin mistakes must never create failure states.

The tutorial must not feel sterile, safe, or obviously fake.

CHARACTER CREATION MODEL (LOCKED)

Creation is now split into four in-world parts:

1. Race
identity anchor
stat hook

2. Physical Traits
structured preset choices only

3. Generated Description
system-built from selected traits

4. Name
final commitment near the end of onboarding

Profession is explicitly NOT chosen here.

All new players still enter the world as Commoners.

⚠️ ORDER IS LOCKED

Race must come before gear and combat because it informs:

identity
mentor tone
later stat/progression hooks

UPDATED ROOM FLOW (LOCKED)

01 Wake Room
02 Intake Hall
03 Lineup Platform
04 Mirror Alcove
05 Gear Rack Room
06 Weapon Cage
07 Training Yard
08 Supply Shack
09 Vendor Stall
10 Breach Corridor
11 Outer Gate
   optional branch: Secret Tunnel

Each room must teach one primary lesson.

Each room should also contain one reward hook, shortcut, or payoff where practical.

ROOM PURPOSES

Wake Room
introduce urgency
mentor takes control immediately
player learns to look and orient

Intake Hall
gender selection
gremlin creates first friction point

Lineup Platform
race selection through physical stations
no race menu allowed

Mirror Alcove
trait-based appearance selection only
no free text allowed

Gear Rack Room
clothing and armor basics
gremlin can hand over the wrong item
mentor correction teaches equipment intent

Weapon Cage
first real choice with tone and combat implications

Training Yard
weak goblin encounter
mentor only intervenes if truly needed

Supply Shack
self-recovery / healing lesson

Vendor Stall
buy/sell lesson
token awareness begins here or earlier

Breach Corridor
pressure spike
small goblin breach or aftermath
player learns awareness under stress

Outer Gate
release into live world
final reward turn-in or confirmation

Secret Tunnel
optional exploration branch
shortcut or bonus reward

RACE SELECTION MODEL (ROOM 03)

The Lineup Platform uses physical stations instead of a choice menu.

Examples:

human station
elf station
dwarf station

Interaction model:

stand at human
stand at elf
stand at dwarf

This must:

validate the player is in the lineup room
validate the target race exists in the canonical race registry
store the canonical race key
lock race for the rest of onboarding unless an explicit future override flow is added

Mentor tone target:

Pick what you are. Not what you think looks impressive.

APPEARANCE MODEL (ROOM 04)

Freeform descriptions are not allowed.

Trait commands are preset-only and room-gated.

Locked trait table for onboarding v1:

APPEARANCE = {
  "hair_style": ["short", "long", "tied", "shaved"],
  "hair_color": ["black", "brown", "blonde", "red"],
  "build": ["lean", "average", "broad"],
  "height": ["short", "average", "tall"],
  "eyes": ["brown", "blue", "green", "gray"],
}

Command model:

set hair style short
set hair color black
set build lean
set height tall
set eyes green

Generated description target format:

A tall, lean human with short black hair and green eyes.

Store the final generated text in:

character.db.description

until finalization, temporary appearance selections may live in onboarding/chargen state.

⚠️ DO NOT:

allow free text
allow paragraph writing
allow arbitrary appearance values
allow the player to leave the mirror step before all required traits are set

GREMLIN SYSTEM (LOCKED)

The gremlin is a controlled disruption system, not comic relief.

Allowed gremlin beats:

gives wrong item
misreads instruction
triggers early movement or small pressure beat

Every gremlin beat must resolve like this:

mistake → mentor correction → player action → understanding

Never:

softlock the player
destroy required progress items
start an unwinnable combat state

REWARD MODEL (LOCKED)

Players earn:

tokens for completed tutorial beats
starter gear slightly better than normal early junk
currency
consumables

Final reward:

token turn-in for an upgrade or bonus before release to the main world

This must be worthwhile enough that veterans do not resent replaying the sequence.

SUCCESS CRITERIA

For new players:

core systems understood in under 15 minutes
they feel capable rather than confused
it feels like play, not instruction

For returning players:

they do not feel slowed down
rewards make replay defensible

For the system:

no dead time
no blocked progression
no unclear objectives

IMPLEMENTATION ALIGNMENT WITH CURRENT CODEBASE

Current repo state already provides:

Commoner-first finalization support
race-aware creation pipeline
structured appearance groundwork
startup-built onboarding/tutorial rooms

Next implementation passes must move the player-facing flow away from OOC-only chargen commands and into room-gated onboarding verbs/NPC hooks while preserving the clean blueprint/finalization boundary in:

systems/chargen/
systems/character/creation.py

ONBOARDING MICROTASKS (LOCKED)

🟩 ONB-400 — Add Race Field
character.db.race = None only until onboarding selection resolves.

🟩 ONB-401 — Create Race Selection Command
Command:
stand at <race>

Validate:

player is in Lineup Platform
race exists

🟩 ONB-402 — Lock Race After Selection
Once selected during onboarding, race cannot be changed within the same run.

🟦 ONB-403 — Create Appearance Trait Storage
Store temporary selections as:

character.db.appearance = {
  "hair_style": None,
  "hair_color": None,
  "build": None,
  "height": None,
  "eyes": None,
}

or the equivalent onboarding-state field if we keep temporary state off Character until final commit.

🟦 ONB-404 — Create Trait Command
Command:
set <trait> <value>

Validate:

trait allowed
value allowed
room is Mirror Alcove

🟦 ONB-405 — Auto Description Builder Function
Create:

def build_description(char):
  return f"A {char.db.appearance['height']}, {char.db.appearance['build']} {char.db.race} with {char.db.appearance['hair_style']} {char.db.appearance['hair_color']} hair and {char.db.appearance['eyes']} eyes."

Centralize this logic.

🟦 ONB-406 — Require Completion Before Progress
Player cannot leave Mirror Alcove until all required traits are filled.

🟦 ONB-407 — Mentor Validation Hook
Mentor checks missing traits and prompts the player with short corrective lines.

🟨 ONB-408 — Move Name Selection Near End
Name becomes final commitment near the end of onboarding, after identity and competence have been established.

🟨 ONB-409 — Build Token Reward Loop
Award tokens across steps and support final turn-in at Outer Gate.

🟨 ONB-410 — Add Secret Tunnel Branch
Optional exploration branch with shortcut, bonus reward, or small lore payoff.

RECOMMENDED IMPLEMENTATION ORDER

1. Convert the built tutorial area to the locked room flow and names.
2. Add onboarding state and room-gated progression flags.
3. Implement gender, race-station, and trait-selection commands.
4. Gate room exits until required onboarding steps are complete.
5. Add mentor and gremlin trigger hooks.
6. Add token rewards, vendor lesson, and breach escalation.
7. Move final name commitment and live-world release to Outer Gate.

FINAL EXPERIENCE TARGET

The player should leave thinking:

That was chaotic, but I handled it.
I think I can survive out there.