THIEF PHASE 1 — MARK + KHRI FOUNDATION

👉 No combat
👉 No thug yet
👉 No ambush
👉 We are building the decision + resource core

🧱 MICRO TASKS — THIEF 001–020 (AEDAN FORMAT)
🎯 GOAL
introduce Mark system (decision layer)
introduce Khri system (resource + buff engine)
integrate cleanly with existing:
stealth
steal
awareness
🟥 MARK SYSTEM (CORE DECISION LAYER)
THIEF 001 — ADD MARK STATE TO CHARACTER

File: typeclasses/characters.py

self.db.marked_target = None
self.db.mark_data = {}

Success:

attributes exist
no crashes on login
THIEF 002 — CREATE MARK COMMAND
mark <target>

File: commands/cmd_thief.py (create if needed)

THIEF 003 — VALIDATE TARGET
target = caller.search(self.args)

if not target:
    return

Success:

cannot mark invalid target
THIEF 004 — REQUIRE SAME ROOM
if target.location != caller.location:
    caller.msg("They are not here.")
    return
THIEF 005 — STORE MARK
caller.db.marked_target = target.id
THIEF 006 — GENERATE MARK DATA
import random

difficulty = random.randint(1, 100)

caller.db.mark_data = {
    "difficulty": difficulty,
    "timestamp": time.time()
}
THIEF 007 — OUTPUT MARK RESULT
caller.msg(f"You assess {target.key}. Difficulty: {difficulty}")
THIEF 008 — MARK TIMEOUT (BASIC)

Add check:

if time.time() - caller.db.mark_data["timestamp"] > 60:
    caller.db.marked_target = None
THIEF 009 — SAFE ACCESS HELPER

File: typeclasses/characters.py

def get_marked_target(self):
    if not self.db.marked_target:
        return None
    return search_object(self.db.marked_target)
THIEF 010 — HOOK INTO STEAL

File: commands/cmd_steal.py

Before difficulty calculation:

if caller.db.marked_target == target.id:
    difficulty -= 10
🟫 KHRI SYSTEM (RESOURCE ENGINE)
THIEF 011 — ADD KHRI STATE

File: typeclasses/characters.py

self.db.khri_pool = 100
self.db.khri_active = {}
THIEF 012 — CREATE KHRI COMMAND
khri <name>
THIEF 013 — DEFINE FIRST KHRI (CUNNING)

File: world/khri.py (CREATE)

KHRI = {
    "cunning": {
        "cost": 10,
        "effect": "steal_bonus"
    }
}
THIEF 014 — VALIDATE KHRI EXISTS
if name not in KHRI:
    caller.msg("Unknown khri.")
    return
THIEF 015 — CHECK RESOURCE
if caller.db.khri_pool < KHRI[name]["cost"]:
    caller.msg("You lack the focus.")
    return
THIEF 016 — ACTIVATE KHRI
caller.db.khri_active[name] = True
caller.db.khri_pool -= KHRI[name]["cost"]
THIEF 017 — APPLY EFFECT HOOK

File: steal logic

if "cunning" in caller.db.khri_active:
    difficulty -= 5
THIEF 018 — KHRI DECAY LOOP (BASIC)

File: tick/pulse system

caller.db.khri_pool = max(0, caller.db.khri_pool - 1)
THIEF 019 — KHRI CLEAR WHEN EMPTY
if caller.db.khri_pool == 0:
    caller.db.khri_active = {}
THIEF 020 — FEEDBACK MESSAGE
caller.msg("You focus inward, sharpening your instincts.")
🧠 HARD RULES (PHASE 1)

Aedan must NOT:

add more khri types
add stacking logic
add UI
add combat hooks
modify awareness system
create new resource systems
✅ VALIDATION CHECKLIST

After THIEF 020:

player can mark target
mark gives difficulty insight
mark improves steal success
player can khri cunning
khri reduces difficulty
khri drains over time
khri clears when empty
🔥 WHAT YOU JUST BUILT

This is:

Thief brain + engine

Not flashy—but critical.

THIEF PHASE 2 — TARGET MEMORY + KHRI EXPANSION
🧱 MICRO TASKS — THIEF 021–040 (AEDAN FORMAT)
🎯 GOAL
targets remember interactions
repeated theft becomes harder
player can read that state
khri becomes multi-effect system (controlled)
🟥 TARGET MEMORY SYSTEM (ANTI-EXPLOIT CORE)
THIEF 021 — ADD TARGET MEMORY STORAGE

File: typeclasses/characters.py (for NPCs + players)

self.db.theft_memory = {}
THIEF 022 — DEFINE MEMORY STRUCTURE
{
    "thief_id": {
        "count": int,
        "last_attempt": timestamp
    }
}
THIEF 023 — RECORD ATTEMPT ON STEAL

File: cmd_steal.py

mem = target.db.theft_memory.get(caller.id, {"count": 0})

mem["count"] += 1
mem["last_attempt"] = time.time()

target.db.theft_memory[caller.id] = mem
THIEF 024 — APPLY DIFFICULTY SCALING
mem = target.db.theft_memory.get(caller.id)

if mem:
    difficulty += mem["count"] * 5
THIEF 025 — CAP MEMORY EFFECT
difficulty += min(25, mem["count"] * 5)
THIEF 026 — MEMORY DECAY (TIME BASED)

File: utils/crime.py or pulse

if time.time() - mem["last_attempt"] > 600:
    mem["count"] = max(0, mem["count"] - 1)
THIEF 027 — CLEANUP ZERO MEMORY
if mem["count"] <= 0:
    del target.db.theft_memory[caller.id]
🟫 MARK SYSTEM UPGRADE (PLAYER INSIGHT)
THIEF 028 — ADD MEMORY READ TO MARK

File: mark command

mem = target.db.theft_memory.get(caller.id)
THIEF 029 — DISPLAY MEMORY STATE
if mem:
    caller.msg("They seem wary of you.")
else:
    caller.msg("They seem unsuspecting.")
THIEF 030 — SHOW RISK LEVEL
risk = difficulty // 20

caller.msg(f"Risk level: {risk}")
🟩 KHRI EXPANSION (CONTROLLED MULTI-BUFF)
THIEF 031 — LIMIT ACTIVE KHRI

File: character

self.db.khri_limit = 2
THIEF 032 — ENFORCE LIMIT
if len(caller.db.khri_active) >= caller.db.khri_limit:
    caller.msg("You cannot maintain more focus.")
    return
THIEF 033 — ADD SECOND KHRI: SIGHT

File: world/khri.py

"sight": {
    "cost": 10,
    "effect": "perception_bonus"
}
THIEF 034 — APPLY SIGHT EFFECT

File: awareness/detection logic

if "sight" in caller.db.khri_active:
    awareness_bonus += 5
THIEF 035 — KHRI STACKING (SIMPLE)

Ensure:

caller.db.khri_active = {
    "cunning": True,
    "sight": True
}
THIEF 036 — KHRI DRAIN PER ACTIVE

File: pulse

drain = len(caller.db.khri_active)

caller.db.khri_pool = max(0, caller.db.khri_pool - drain)
THIEF 037 — KHRI AUTO-DROP (GRACEFUL)
if caller.db.khri_pool <= 0:
    caller.msg("Your focus collapses.")
    caller.db.khri_active = {}
🟨 KHRI CONTROL COMMANDS
THIEF 038 — ADD COMMAND
khri stop <name>
THIEF 039 — IMPLEMENT STOP
if name in caller.db.khri_active:
    del caller.db.khri_active[name]
THIEF 040 — FEEDBACK
caller.msg(f"You release your focus on {name}.")
🧠 HARD RULES (PHASE 2)

Aedan must NOT:

add more than 2 khri
create UI systems
add combat effects
alter justice system
create permanent debuffs
✅ VALIDATION CHECKLIST

After THIEF 040:

repeated stealing becomes harder
targets “remember” player
memory decays over time
mark reveals target awareness state
player can run 2 khri
khri drains faster with stacking
player can stop khri manually
🔥 WHAT YOU JUST BUILT

This is:

The intelligence layer of thief

Before:

try → succeed/fail

Now:

evaluate → adapt → optimize
THIEF PHASE 3 — SLIP + ESCAPE + FAILURE CONTROL
🧱 MICRO TASKS — THIEF 041–060 (AEDAN FORMAT)
🎯 GOAL
introduce Slip (escape mechanic)
allow recovery after failure
reduce “fail = dead/caught”
reinforce stealth identity
🟥 SLIP SYSTEM (CORE ESCAPE TOOL)
THIEF 041 — ADD SLIP STATE

File: typeclasses/characters.py

self.db.last_slip_time = 0
self.db.slipping = False
THIEF 042 — CREATE COMMAND
slip

File: commands/cmd_thief.py

THIEF 043 — VALIDATE STATE
if caller.db.is_captured:
    caller.msg("You cannot slip while restrained.")
    return
THIEF 044 — ADD COOLDOWN CHECK
if time.time() - caller.db.last_slip_time < 10:
    caller.msg("You need a moment before slipping again.")
    return
THIEF 045 — EXECUTE SLIP
caller.db.slipping = True
caller.db.last_slip_time = time.time()
THIEF 046 — BREAK PURSUIT
caller.db.pursuers = []
caller.db.is_pursued = False
THIEF 047 — REDUCE DETECTION TEMPORARILY
caller.db.slip_bonus = 20
caller.db.slip_timer = time.time()
THIEF 048 — MESSAGE
caller.msg("You slip through the chaos, avoiding notice.")
THIEF 049 — SLIP DECAY

File: pulse system

if time.time() - caller.db.slip_timer > 5:
    caller.db.slip_bonus = 0
    caller.db.slipping = False
THIEF 050 — APPLY BONUS IN DETECTION

File: detection logic

stealth += caller.db.slip_bonus
🟫 FAILURE CONTROL (STEAL RECOVERY)
THIEF 051 — MODIFY STEAL FAILURE

Instead of immediate full failure:

if near_success:
    caller.msg("You falter but recover before being noticed.")
    return
THIEF 052 — DEFINE NEAR SUCCESS
if abs(roll + stealth - (awareness + 50)) < 10:
    near_success = True
THIEF 053 — REDUCE FAILURE PUNISHMENT

On near fail:

do NOT reveal
do NOT call guards
THIEF 054 — HARD FAILURE REMAINS

Only on full failure:

reveal
alert
guards

(no change to existing system)

🟩 ESCAPE INTERACTION (MOVEMENT)
THIEF 055 — MOVEMENT BREAK BONUS

On move after slip:

caller.db.slip_bonus += 5

(cap at reasonable level later)

THIEF 056 — MULTI-ROOM ESCAPE BOOST
caller.db.escape_chain += 1

Each move increases escape chance

THIEF 057 — RESET CHAIN
caller.db.escape_chain = 0

on:

being detected
combat start
🟨 STEALTH RECOVERY
THIEF 058 — AUTO-HIDE ATTEMPT AFTER SLIP
if caller.db.slipping:
    attempt_hide()

(Reuse existing hide logic)

THIEF 059 — FAIL SAFE

If hide fails:

caller.msg("You fail to fully disappear.")

(no harsh penalty)

🟦 SAFETY + STATE CLEANUP
THIEF 060 — ENSURE CLEAN RESET

On:

capture
jail
logout
caller.db.slipping = False
caller.db.slip_bonus = 0
caller.db.escape_chain = 0
🧠 HARD RULES (PHASE 3)

Aedan must NOT:

add teleportation
add instant invisibility
bypass justice system
remove guard tracking entirely
create new movement system
✅ VALIDATION CHECKLIST

After THIEF 060:

player can slip to escape pressure
slip breaks pursuit temporarily
slip improves stealth briefly
near-fail gives recovery chance
movement improves escape
system resets cleanly
🔥 WHAT YOU JUST BUILT

This is:

Survivability layer

Before:

thief works only when perfect

Now:

thief works under pressure

THIEF PHASE 4 — THUG + ROUGH (AGGRESSIVE PATH)
🧱 MICRO TASKS — THIEF 061–080 (AEDAN FORMAT)
🎯 GOAL
implement Thug (intimidation / theft prep)
implement Thug Rough (combat opener, Circle 20)
integrate with:
steal
combat
justice
alert system
🟥 THUG (INTIMIDATION SYSTEM)
THIEF 061 — ADD INTIMIDATION STATE

File: typeclasses/characters.py (applies to targets)

self.db.intimidated = False
self.db.intimidation_timer = 0
THIEF 062 — CREATE COMMAND
thug <target>
THIEF 063 — VALIDATE CONDITIONS
if caller.is_hidden():
    caller.msg("You cannot do that from the shadows.")
    return

if target.location != caller.location:
    return
THIEF 064 — APPLY INTIMIDATION
target.db.intimidated = True
target.db.intimidation_timer = time.time()
THIEF 065 — REVEAL CALLER
caller.reveal()
THIEF 066 — ALERT + CRIME IMPACT
caller.location.db.alert_level += 1
caller.db.crime_severity += 1
THIEF 067 — FEEDBACK
caller.msg(f"You pressure {target.key}, forcing hesitation.")
target.msg(f"{caller.key} threatens you!")
THIEF 068 — APPLY STEAL BONUS

File: steal logic

if target.db.intimidated:
    difficulty -= 10
THIEF 069 — INTIMIDATION DECAY

File: pulse system

if time.time() - target.db.intimidation_timer > 10:
    target.db.intimidated = False
THIEF 070 — NO STACKING
if target.db.intimidated:
    return
🟫 THUG ROUGH (COMBAT OPENER — CIRCLE 20)
THIEF 071 — ADD ROUGH STATE
self.db.roughed = False
self.db.rough_timer = 0
THIEF 072 — CREATE COMMAND
thug rough <target>
THIEF 073 — REQUIRE PROFESSION + RANK
if caller.db.profession != "thief" or caller.db.profession_rank < 20:
    caller.msg("You lack the experience to do that.")
    return
THIEF 074 — VALIDATE TARGET
if target.location != caller.location:
    return
THIEF 075 — APPLY ROUGH EFFECT
target.db.roughed = True
target.db.rough_timer = time.time()
THIEF 076 — INITIATE COMBAT
caller.db.in_combat = True
target.db.in_combat = True
THIEF 077 — APPLY DAMAGE MODIFIER

File: combat resolution

if target.db.roughed:
    damage *= 1.1

(Keep within 1.1–1.15 range)

THIEF 078 — ALERT + GUARD RESPONSE
caller.location.db.alert_level += 2
call_guards(caller.location, caller)
THIEF 079 — ROUGH DECAY
if time.time() - target.db.rough_timer > 8:
    target.db.roughed = False
THIEF 080 — FEEDBACK
caller.msg(f"You slam into {target.key}, throwing them off balance!")
target.msg("You are caught off guard and exposed!")
🧠 HARD RULES (PHASE 4)

Aedan must NOT:

allow stacking intimidation or rough
allow rough from stealth
allow rough without cooldown (reuse ability cooldown system)
bypass justice system
add extra damage systems
✅ VALIDATION CHECKLIST

After THIEF 080:

player can intimidate targets
intimidation improves steal success
intimidation increases risk
player can use thug rough at Circle 20
rough initiates combat
rough increases incoming damage
both effects decay properly
🔥 WHAT YOU JUST BUILT

This is:

Dual-identity thief

Stealth Path
mark → khri → steal → slip
Aggressive Path
thug → rough → combat → chaos
🎯 WHAT THIS UNLOCKS
meaningful player choice
different playstyles
risk/reward spectrum
deeper combat integration
THIEF PHASE 5 — AMBUSH + STEALTH COMBAT
🧱 MICRO TASKS — THIEF 081–100 (AEDAN FORMAT)
🎯 GOAL
enable combat from stealth
reward positioning + preparation
differentiate from “rough”
reinforce stealth identity
🟥 AMBUSH CORE SYSTEM
THIEF 081 — ADD AMBUSH STATE

File: typeclasses/characters.py

self.db.ambushing = False
self.db.last_ambush_time = 0
THIEF 082 — CREATE COMMAND
ambush <target>
THIEF 083 — REQUIRE STEALTH
if not caller.is_hidden():
    caller.msg("You must be hidden to ambush.")
    return
THIEF 084 — VALIDATE TARGET
if target.location != caller.location:
    return
THIEF 085 — COOLDOWN CHECK
if time.time() - caller.db.last_ambush_time < 10:
    caller.msg("You need to recover before striking again.")
    return
THIEF 086 — INITIATE AMBUSH
caller.db.ambushing = True
caller.db.last_ambush_time = time.time()
THIEF 087 — BREAK STEALTH
caller.reveal()
THIEF 088 — INITIATE COMBAT
caller.db.in_combat = True
target.db.in_combat = True
🟫 AMBUSH EFFECTS
THIEF 089 — DAMAGE BONUS

File: combat resolution

if caller.db.ambushing:
    damage *= 1.25
THIEF 090 — APPLY STAGGER
target.db.staggered = True
target.db.stagger_timer = time.time()
THIEF 091 — STAGGER EFFECT

File: combat loop

if target.db.staggered:
    target_accuracy -= 10
THIEF 092 — STAGGER DECAY
if time.time() - target.db.stagger_timer > 5:
    target.db.staggered = False
THIEF 093 — AMBUSH RESET
caller.db.ambushing = False

(after first attack resolution)

🟩 MARK + AMBUSH SYNERGY
THIEF 094 — BONUS IF MARKED
if caller.db.marked_target == target.id:
    damage *= 1.1
THIEF 095 — BONUS IF KHRI ACTIVE
if "cunning" in caller.db.khri_active:
    damage *= 1.05
🟨 FAILURE CASE
THIEF 096 — FAILED AMBUSH

If detection beats stealth:

caller.msg("You fail to find the opening!")
caller.reveal()
THIEF 097 — PARTIAL FAILURE
damage *= 0.75

(no stagger applied)

🟦 ALERT + JUSTICE
THIEF 098 — LAW ZONE CHECK
if not caller.location.is_lawless():
    caller.location.db.alert_level += 1
THIEF 099 — OPTIONAL GUARD RESPONSE

Only if:

high severity
or repeat offense
if caller.db.crime_severity > threshold:
    call_guards()
🟪 FEEDBACK
THIEF 100 — AMBUSH MESSAGE
caller.msg(f"You strike from the shadows at {target.key}!")
target.msg("Something hits you from nowhere!")
caller.location.msg_contents(
    f"{caller.key} suddenly appears, striking {target.key}!",
    exclude=[caller, target]
)
🧠 HARD RULES (PHASE 5)

Aedan must NOT:

allow ambush without stealth
allow repeated ambush stacking
bypass combat system
create instant kill mechanics
add positional grid systems
✅ VALIDATION CHECKLIST

After THIEF 100:

ambush requires stealth
ambush breaks stealth
ambush deals increased damage
ambush applies stagger
ambush interacts with mark + khri
ambush differs from rough
🔥 WHAT YOU JUST BUILT

This is:

Full Thief Combat Identity

You now have TWO combat openers:
🟦 Ambush (Stealth)
high reward
requires setup
controlled
🟥 Rough (Aggressive)
immediate
loud
risky
🧠 FINAL STATE OF THIEF

You now have a complete profession loop:

observe → mark → khri → choose path

→ stealth path → ambush → slip → vanish
→ aggressive path → thug → rough → fight → escape

THIEF PHASE 7 — POSITIONING + ATTENTION + DISGUISE
🧱 MICRO TASKS — THIEF 121–140 (AEDAN FORMAT)
🎯 GOAL
add positioning state (lightweight)
add attention/distracted system
add disguise system (controlled)
integrate with:
stealth
theft
guards
social perception
🟥 POSITIONING SYSTEM (LIGHTWEIGHT, NOT GRID)
THIEF 121 — ADD POSITION STATE

File: typeclasses/characters.py

self.db.position_state = "neutral"  
# values: neutral, advantaged, exposed
THIEF 122 — SET DEFAULT ON LOGIN
self.db.position_state = "neutral"
THIEF 123 — ADVANTAGE FROM STEALTH

File: hide success

caller.db.position_state = "advantaged"
THIEF 124 — EXPOSED ON FAILURE

File: steal / ambush fail

caller.db.position_state = "exposed"
THIEF 125 — RESET ON TIME

File: pulse

caller.db.position_state = "neutral"

(after short duration ~5–10s equivalent)

THIEF 126 — APPLY POSITION BONUS

File: steal / ambush

if caller.db.position_state == "advantaged":
    difficulty -= 10

if caller.db.position_state == "exposed":
    difficulty += 10
🟫 ATTENTION SYSTEM (TARGET STATE)
THIEF 127 — ADD ATTENTION STATE
self.db.attention_state = "idle"
# values: idle, distracted, alert
THIEF 128 — SET DISTRACTED FROM THUG
target.db.attention_state = "distracted"
THIEF 129 — SET ALERT ON FAILURE
target.db.attention_state = "alert"
THIEF 130 — APPLY ATTENTION MODIFIERS

File: steal logic

if target.db.attention_state == "distracted":
    difficulty -= 10

if target.db.attention_state == "alert":
    difficulty += 15
THIEF 131 — ATTENTION DECAY

File: pulse

if time.time() - last_change > 10:
    target.db.attention_state = "idle"
THIEF 132 — MARK SHOWS ATTENTION

File: mark output

caller.msg(f"Attention: {target.db.attention_state}")
🟩 DISGUISE SYSTEM (IDENTITY LAYER)
THIEF 133 — ADD DISGUISE STATE

File: typeclasses/characters.py

self.db.disguised = False
self.db.disguise_name = None
self.db.disguise_profession = None
THIEF 134 — CREATE COMMAND
disguise <name>
THIEF 135 — APPLY DISGUISE
caller.db.disguised = True
caller.db.disguise_name = args
THIEF 136 — OVERRIDE DISPLAY NAME

File: name display logic

if obj.db.disguised:
    return obj.db.disguise_name
THIEF 137 — BLOCK IN COMBAT
if caller.db.in_combat:
    caller.msg("You cannot disguise yourself right now.")
    return
THIEF 138 — BREAK DISGUISE ON ACTION

On:

ambush
rough
being hit
caller.db.disguised = False
caller.db.disguise_name = None
THIEF 139 — GUARD RECOGNITION CHECK

File: guard logic

if target.db.disguised:
    recognition_penalty = 20

(does NOT prevent detection, only delays)

THIEF 140 — FEEDBACK
caller.msg("You adjust your appearance, blending into a new identity.")
🧠 HARD RULES (PHASE 7)

Aedan must NOT:

create full positional grid system
allow disguise to clear warrants
allow disguise during combat
allow permanent disguise
bypass justice logic
✅ VALIDATION CHECKLIST

After THIEF 140:

stealth grants positional advantage
failure creates exposure penalty
targets can be distracted or alert
attention affects steal difficulty
mark reveals attention
player can disguise identity
disguise changes visible name
disguise breaks on combat/action
guards are slightly delayed by disguise
🔥 WHAT YOU JUST BUILT

This is:

The “alive” layer of Thief

Before:

systems were mechanical

Now:

timing matters
positioning matters
perception matters
identity matters
🧠 FINAL STATE (IMPORTANT)

You now have:

🧠 Decision
mark
attention
⚙️ Engine
khri
🎭 Identity
disguise
🧭 Positioning
advantaged / exposed
🕵️ Stealth + Combat
ambush / rough
🏃 Escape
slip + passages

THIEF PHASE 8 — POLISH PASS (RT-LITE + FEEL + PACING)
🧱 MICRO TASKS — THIEF 141–160 (AEDAN FORMAT)
🎯 GOAL
introduce roundtime-lite (action lock)
prevent spam behavior
add tension between actions
improve moment-to-moment feel
🟥 RT-LITE (ACTION LOCK SYSTEM)
THIEF 141 — ADD ROUND TIME FIELD

File: typeclasses/characters.py

self.db.roundtime = 0
THIEF 142 — ADD HELPER
def is_in_rt(self):
    return time.time() < self.db.roundtime
THIEF 143 — BLOCK ACTIONS IN RT

File: command base (or per command if needed)

if caller.is_in_rt():
    caller.msg("You are still recovering.")
    return
THIEF 144 — APPLY RT ON STEAL
caller.db.roundtime = time.time() + 2
THIEF 145 — APPLY RT ON AMBUSH
caller.db.roundtime = time.time() + 3
THIEF 146 — APPLY RT ON ROUGH
caller.db.roundtime = time.time() + 3
THIEF 147 — APPLY RT ON SLIP
caller.db.roundtime = time.time() + 2
🟫 VARIABLE RT (SKILL EXPRESSION)
THIEF 148 — REDUCE RT WITH POSITION
if caller.db.position_state == "advantaged":
    rt -= 1
THIEF 149 — INCREASE RT ON FAILURE
if failure:
    rt += 1
THIEF 150 — CLAMP RT
rt = max(1, min(rt, 5))
🟩 ACTION FEEDBACK (IMPORTANT FOR FEEL)
THIEF 151 — ADD RT MESSAGE
caller.msg(f"You must wait {rt} seconds to act again.")
THIEF 152 — SHORT RECOVERY MESSAGE
caller.msg("You regain your footing.")

(trigger when RT ends — optional simple check)

🟨 MICRO-TENSION SYSTEM
THIEF 153 — ADD “COMMITMENT WINDOW” FLAG
self.db.recent_action = True
self.db.recent_action_timer = time.time()
THIEF 154 — APPLY RISK AFTER ACTION

File: steal / thug / ambush

if caller.db.recent_action:
    detection += 5
THIEF 155 — CLEAR RECENT ACTION
if time.time() - caller.db.recent_action_timer > 3:
    caller.db.recent_action = False
🟦 FLOW SMOOTHING (ANTI-CLUNK)
THIEF 156 — ALLOW MARK DURING RT
# mark should NOT be blocked by RT
THIEF 157 — ALLOW KHRI DURING RT
# khri activation allowed during RT
THIEF 158 — BLOCK HEAVY ACTIONS ONLY

Ensure RT blocks:

steal
ambush
rough
slip

But NOT:

mark
khri
look/search
🟥 COMBAT ENTRY SMOOTHING
THIEF 159 — PREVENT DOUBLE INITIATION
if caller.db.in_combat:
    skip re-initiation
THIEF 160 — GRACE WINDOW AFTER AMBUSH
caller.db.post_ambush_grace = True

During grace (~2s):

reduced incoming damage
🧠 HARD RULES (PHASE 8)

Aedan must NOT:

create global combat system changes
add animation systems
introduce tick scheduler changes
create new stat systems
override existing cooldown systems
✅ VALIDATION CHECKLIST

After THIEF 160:

actions have short recovery time
player cannot spam steal/ambush
positioning affects recovery speed
failure increases recovery time
mark/khri still feel responsive
actions feel weighted, not instant
🔥 WHAT YOU JUST BUILT

This is:

Tension + pacing layer

Before:

fast, mechanical, spammy

Now:

deliberate
risky
controlled
satisfying
🧠 FINAL STATE OF YOUR THIEF

You now have:

🧠 Intelligence
mark
memory
attention
⚙️ Engine
khri
🎭 Identity
disguise
🧭 Positioning
advantaged / exposed
🕵️ Execution
ambush / thug / rough
🏃 Survival
slip + passages
⏱️ Feel
RT-lite pacing
commitment windows

👉 This is now:

A complete, DR-faithful, system-driven Thief profession
THIEF PHASE 1 — MARK + KHRI FOUNDATION

👉 No combat
👉 No thug yet
👉 No ambush
👉 We are building the decision + resource core

🧱 MICRO TASKS — THIEF 001–020 (AEDAN FORMAT)
🎯 GOAL
introduce Mark system (decision layer)
introduce Khri system (resource + buff engine)
integrate cleanly with existing:
stealth
steal
awareness
🟥 MARK SYSTEM (CORE DECISION LAYER)
THIEF 001 — ADD MARK STATE TO CHARACTER

File: typeclasses/characters.py

self.db.marked_target = None
self.db.mark_data = {}

Success:

attributes exist
no crashes on login
THIEF 002 — CREATE MARK COMMAND
mark <target>

File: commands/cmd_thief.py (create if needed)

THIEF 003 — VALIDATE TARGET
target = caller.search(self.args)

if not target:
    return

Success:

cannot mark invalid target
THIEF 004 — REQUIRE SAME ROOM
if target.location != caller.location:
    caller.msg("They are not here.")
    return
THIEF 005 — STORE MARK
caller.db.marked_target = target.id
THIEF 006 — GENERATE MARK DATA
import random

difficulty = random.randint(1, 100)

caller.db.mark_data = {
    "difficulty": difficulty,
    "timestamp": time.time()
}
THIEF 007 — OUTPUT MARK RESULT
caller.msg(f"You assess {target.key}. Difficulty: {difficulty}")
THIEF 008 — MARK TIMEOUT (BASIC)

Add check:

if time.time() - caller.db.mark_data["timestamp"] > 60:
    caller.db.marked_target = None
THIEF 009 — SAFE ACCESS HELPER

File: typeclasses/characters.py

def get_marked_target(self):
    if not self.db.marked_target:
        return None
    return search_object(self.db.marked_target)
THIEF 010 — HOOK INTO STEAL

File: commands/cmd_steal.py

Before difficulty calculation:

if caller.db.marked_target == target.id:
    difficulty -= 10
🟫 KHRI SYSTEM (RESOURCE ENGINE)
THIEF 011 — ADD KHRI STATE

File: typeclasses/characters.py

self.db.khri_pool = 100
self.db.khri_active = {}
THIEF 012 — CREATE KHRI COMMAND
khri <name>
THIEF 013 — DEFINE FIRST KHRI (CUNNING)

File: world/khri.py (CREATE)

KHRI = {
    "cunning": {
        "cost": 10,
        "effect": "steal_bonus"
    }
}
THIEF 014 — VALIDATE KHRI EXISTS
if name not in KHRI:
    caller.msg("Unknown khri.")
    return
THIEF 015 — CHECK RESOURCE
if caller.db.khri_pool < KHRI[name]["cost"]:
    caller.msg("You lack the focus.")
    return
THIEF 016 — ACTIVATE KHRI
caller.db.khri_active[name] = True
caller.db.khri_pool -= KHRI[name]["cost"]
THIEF 017 — APPLY EFFECT HOOK

File: steal logic

if "cunning" in caller.db.khri_active:
    difficulty -= 5
THIEF 018 — KHRI DECAY LOOP (BASIC)

File: tick/pulse system

caller.db.khri_pool = max(0, caller.db.khri_pool - 1)
THIEF 019 — KHRI CLEAR WHEN EMPTY
if caller.db.khri_pool == 0:
    caller.db.khri_active = {}
THIEF 020 — FEEDBACK MESSAGE
caller.msg("You focus inward, sharpening your instincts.")
🧠 HARD RULES (PHASE 1)

Aedan must NOT:

add more khri types
add stacking logic
add UI
add combat hooks
modify awareness system
create new resource systems
✅ VALIDATION CHECKLIST

After THIEF 020:

player can mark target
mark gives difficulty insight
mark improves steal success
player can khri cunning
khri reduces difficulty
khri drains over time
khri clears when empty
🔥 WHAT YOU JUST BUILT

This is:

Thief brain + engine

Not flashy—but critical.

THIEF PHASE 2 — TARGET MEMORY + KHRI EXPANSION
🧱 MICRO TASKS — THIEF 021–040 (AEDAN FORMAT)
🎯 GOAL
targets remember interactions
repeated theft becomes harder
player can read that state
khri becomes multi-effect system (controlled)
🟥 TARGET MEMORY SYSTEM (ANTI-EXPLOIT CORE)
THIEF 021 — ADD TARGET MEMORY STORAGE

File: typeclasses/characters.py (for NPCs + players)

self.db.theft_memory = {}
THIEF 022 — DEFINE MEMORY STRUCTURE
{
    "thief_id": {
        "count": int,
        "last_attempt": timestamp
    }
}
THIEF 023 — RECORD ATTEMPT ON STEAL

File: cmd_steal.py

mem = target.db.theft_memory.get(caller.id, {"count": 0})

mem["count"] += 1
mem["last_attempt"] = time.time()

target.db.theft_memory[caller.id] = mem
THIEF 024 — APPLY DIFFICULTY SCALING
mem = target.db.theft_memory.get(caller.id)

if mem:
    difficulty += mem["count"] * 5
THIEF 025 — CAP MEMORY EFFECT
difficulty += min(25, mem["count"] * 5)
THIEF 026 — MEMORY DECAY (TIME BASED)

File: utils/crime.py or pulse

if time.time() - mem["last_attempt"] > 600:
    mem["count"] = max(0, mem["count"] - 1)
THIEF 027 — CLEANUP ZERO MEMORY
if mem["count"] <= 0:
    del target.db.theft_memory[caller.id]
🟫 MARK SYSTEM UPGRADE (PLAYER INSIGHT)
THIEF 028 — ADD MEMORY READ TO MARK

File: mark command

mem = target.db.theft_memory.get(caller.id)
THIEF 029 — DISPLAY MEMORY STATE
if mem:
    caller.msg("They seem wary of you.")
else:
    caller.msg("They seem unsuspecting.")
THIEF 030 — SHOW RISK LEVEL
risk = difficulty // 20

caller.msg(f"Risk level: {risk}")
🟩 KHRI EXPANSION (CONTROLLED MULTI-BUFF)
THIEF 031 — LIMIT ACTIVE KHRI

File: character

self.db.khri_limit = 2
THIEF 032 — ENFORCE LIMIT
if len(caller.db.khri_active) >= caller.db.khri_limit:
    caller.msg("You cannot maintain more focus.")
    return
THIEF 033 — ADD SECOND KHRI: SIGHT

File: world/khri.py

"sight": {
    "cost": 10,
    "effect": "perception_bonus"
}
THIEF 034 — APPLY SIGHT EFFECT

File: awareness/detection logic

if "sight" in caller.db.khri_active:
    awareness_bonus += 5
THIEF 035 — KHRI STACKING (SIMPLE)

Ensure:

caller.db.khri_active = {
    "cunning": True,
    "sight": True
}
THIEF 036 — KHRI DRAIN PER ACTIVE

File: pulse

drain = len(caller.db.khri_active)

caller.db.khri_pool = max(0, caller.db.khri_pool - drain)
THIEF 037 — KHRI AUTO-DROP (GRACEFUL)
if caller.db.khri_pool <= 0:
    caller.msg("Your focus collapses.")
    caller.db.khri_active = {}
🟨 KHRI CONTROL COMMANDS
THIEF 038 — ADD COMMAND
khri stop <name>
THIEF 039 — IMPLEMENT STOP
if name in caller.db.khri_active:
    del caller.db.khri_active[name]
THIEF 040 — FEEDBACK
caller.msg(f"You release your focus on {name}.")
🧠 HARD RULES (PHASE 2)

Aedan must NOT:

add more than 2 khri
create UI systems
add combat effects
alter justice system
create permanent debuffs
✅ VALIDATION CHECKLIST

After THIEF 040:

repeated stealing becomes harder
targets “remember” player
memory decays over time
mark reveals target awareness state
player can run 2 khri
khri drains faster with stacking
player can stop khri manually
🔥 WHAT YOU JUST BUILT

This is:

The intelligence layer of thief

Before:

try → succeed/fail

Now:

evaluate → adapt → optimize
THIEF PHASE 3 — SLIP + ESCAPE + FAILURE CONTROL
🧱 MICRO TASKS — THIEF 041–060 (AEDAN FORMAT)
🎯 GOAL
introduce Slip (escape mechanic)
allow recovery after failure
reduce “fail = dead/caught”
reinforce stealth identity
🟥 SLIP SYSTEM (CORE ESCAPE TOOL)
THIEF 041 — ADD SLIP STATE

File: typeclasses/characters.py

self.db.last_slip_time = 0
self.db.slipping = False
THIEF 042 — CREATE COMMAND
slip

File: commands/cmd_thief.py

THIEF 043 — VALIDATE STATE
if caller.db.is_captured:
    caller.msg("You cannot slip while restrained.")
    return
THIEF 044 — ADD COOLDOWN CHECK
if time.time() - caller.db.last_slip_time < 10:
    caller.msg("You need a moment before slipping again.")
    return
THIEF 045 — EXECUTE SLIP
caller.db.slipping = True
caller.db.last_slip_time = time.time()
THIEF 046 — BREAK PURSUIT
caller.db.pursuers = []
caller.db.is_pursued = False
THIEF 047 — REDUCE DETECTION TEMPORARILY
caller.db.slip_bonus = 20
caller.db.slip_timer = time.time()
THIEF 048 — MESSAGE
caller.msg("You slip through the chaos, avoiding notice.")
THIEF 049 — SLIP DECAY

File: pulse system

if time.time() - caller.db.slip_timer > 5:
    caller.db.slip_bonus = 0
    caller.db.slipping = False
THIEF 050 — APPLY BONUS IN DETECTION

File: detection logic

stealth += caller.db.slip_bonus
🟫 FAILURE CONTROL (STEAL RECOVERY)
THIEF 051 — MODIFY STEAL FAILURE

Instead of immediate full failure:

if near_success:
    caller.msg("You falter but recover before being noticed.")
    return
THIEF 052 — DEFINE NEAR SUCCESS
if abs(roll + stealth - (awareness + 50)) < 10:
    near_success = True
THIEF 053 — REDUCE FAILURE PUNISHMENT

On near fail:

do NOT reveal
do NOT call guards
THIEF 054 — HARD FAILURE REMAINS

Only on full failure:

reveal
alert
guards

(no change to existing system)

🟩 ESCAPE INTERACTION (MOVEMENT)
THIEF 055 — MOVEMENT BREAK BONUS

On move after slip:

caller.db.slip_bonus += 5

(cap at reasonable level later)

THIEF 056 — MULTI-ROOM ESCAPE BOOST
caller.db.escape_chain += 1

Each move increases escape chance

THIEF 057 — RESET CHAIN
caller.db.escape_chain = 0

on:

being detected
combat start
🟨 STEALTH RECOVERY
THIEF 058 — AUTO-HIDE ATTEMPT AFTER SLIP
if caller.db.slipping:
    attempt_hide()

(Reuse existing hide logic)

THIEF 059 — FAIL SAFE

If hide fails:

caller.msg("You fail to fully disappear.")

(no harsh penalty)

🟦 SAFETY + STATE CLEANUP
THIEF 060 — ENSURE CLEAN RESET

On:

capture
jail
logout
caller.db.slipping = False
caller.db.slip_bonus = 0
caller.db.escape_chain = 0
🧠 HARD RULES (PHASE 3)

Aedan must NOT:

add teleportation
add instant invisibility
bypass justice system
remove guard tracking entirely
create new movement system
✅ VALIDATION CHECKLIST

After THIEF 060:

player can slip to escape pressure
slip breaks pursuit temporarily
slip improves stealth briefly
near-fail gives recovery chance
movement improves escape
system resets cleanly
🔥 WHAT YOU JUST BUILT

This is:

Survivability layer

Before:

thief works only when perfect

Now:

thief works under pressure

THIEF PHASE 4 — THUG + ROUGH (AGGRESSIVE PATH)
🧱 MICRO TASKS — THIEF 061–080 (AEDAN FORMAT)
🎯 GOAL
implement Thug (intimidation / theft prep)
implement Thug Rough (combat opener, Circle 20)
integrate with:
steal
combat
justice
alert system
🟥 THUG (INTIMIDATION SYSTEM)
THIEF 061 — ADD INTIMIDATION STATE

File: typeclasses/characters.py (applies to targets)

self.db.intimidated = False
self.db.intimidation_timer = 0
THIEF 062 — CREATE COMMAND
thug <target>
THIEF 063 — VALIDATE CONDITIONS
if caller.is_hidden():
    caller.msg("You cannot do that from the shadows.")
    return

if target.location != caller.location:
    return
THIEF 064 — APPLY INTIMIDATION
target.db.intimidated = True
target.db.intimidation_timer = time.time()
THIEF 065 — REVEAL CALLER
caller.reveal()
THIEF 066 — ALERT + CRIME IMPACT
caller.location.db.alert_level += 1
caller.db.crime_severity += 1
THIEF 067 — FEEDBACK
caller.msg(f"You pressure {target.key}, forcing hesitation.")
target.msg(f"{caller.key} threatens you!")
THIEF 068 — APPLY STEAL BONUS

File: steal logic

if target.db.intimidated:
    difficulty -= 10
THIEF 069 — INTIMIDATION DECAY

File: pulse system

if time.time() - target.db.intimidation_timer > 10:
    target.db.intimidated = False
THIEF 070 — NO STACKING
if target.db.intimidated:
    return
🟫 THUG ROUGH (COMBAT OPENER — CIRCLE 20)
THIEF 071 — ADD ROUGH STATE
self.db.roughed = False
self.db.rough_timer = 0
THIEF 072 — CREATE COMMAND
thug rough <target>
THIEF 073 — REQUIRE PROFESSION + RANK
if caller.db.profession != "thief" or caller.db.profession_rank < 20:
    caller.msg("You lack the experience to do that.")
    return
THIEF 074 — VALIDATE TARGET
if target.location != caller.location:
    return
THIEF 075 — APPLY ROUGH EFFECT
target.db.roughed = True
target.db.rough_timer = time.time()
THIEF 076 — INITIATE COMBAT
caller.db.in_combat = True
target.db.in_combat = True
THIEF 077 — APPLY DAMAGE MODIFIER

File: combat resolution

if target.db.roughed:
    damage *= 1.1

(Keep within 1.1–1.15 range)

THIEF 078 — ALERT + GUARD RESPONSE
caller.location.db.alert_level += 2
call_guards(caller.location, caller)
THIEF 079 — ROUGH DECAY
if time.time() - target.db.rough_timer > 8:
    target.db.roughed = False
THIEF 080 — FEEDBACK
caller.msg(f"You slam into {target.key}, throwing them off balance!")
target.msg("You are caught off guard and exposed!")
🧠 HARD RULES (PHASE 4)

Aedan must NOT:

allow stacking intimidation or rough
allow rough from stealth
allow rough without cooldown (reuse ability cooldown system)
bypass justice system
add extra damage systems
✅ VALIDATION CHECKLIST

After THIEF 080:

player can intimidate targets
intimidation improves steal success
intimidation increases risk
player can use thug rough at Circle 20
rough initiates combat
rough increases incoming damage
both effects decay properly
🔥 WHAT YOU JUST BUILT

This is:

Dual-identity thief

Stealth Path
mark → khri → steal → slip
Aggressive Path
thug → rough → combat → chaos
🎯 WHAT THIS UNLOCKS
meaningful player choice
different playstyles
risk/reward spectrum
deeper combat integration
THIEF PHASE 5 — AMBUSH + STEALTH COMBAT
🧱 MICRO TASKS — THIEF 081–100 (AEDAN FORMAT)
🎯 GOAL
enable combat from stealth
reward positioning + preparation
differentiate from “rough”
reinforce stealth identity
🟥 AMBUSH CORE SYSTEM
THIEF 081 — ADD AMBUSH STATE

File: typeclasses/characters.py

self.db.ambushing = False
self.db.last_ambush_time = 0
THIEF 082 — CREATE COMMAND
ambush <target>
THIEF 083 — REQUIRE STEALTH
if not caller.is_hidden():
    caller.msg("You must be hidden to ambush.")
    return
THIEF 084 — VALIDATE TARGET
if target.location != caller.location:
    return
THIEF 085 — COOLDOWN CHECK
if time.time() - caller.db.last_ambush_time < 10:
    caller.msg("You need to recover before striking again.")
    return
THIEF 086 — INITIATE AMBUSH
caller.db.ambushing = True
caller.db.last_ambush_time = time.time()
THIEF 087 — BREAK STEALTH
caller.reveal()
THIEF 088 — INITIATE COMBAT
caller.db.in_combat = True
target.db.in_combat = True
🟫 AMBUSH EFFECTS
THIEF 089 — DAMAGE BONUS

File: combat resolution

if caller.db.ambushing:
    damage *= 1.25
THIEF 090 — APPLY STAGGER
target.db.staggered = True
target.db.stagger_timer = time.time()
THIEF 091 — STAGGER EFFECT

File: combat loop

if target.db.staggered:
    target_accuracy -= 10
THIEF 092 — STAGGER DECAY
if time.time() - target.db.stagger_timer > 5:
    target.db.staggered = False
THIEF 093 — AMBUSH RESET
caller.db.ambushing = False

(after first attack resolution)

🟩 MARK + AMBUSH SYNERGY
THIEF 094 — BONUS IF MARKED
if caller.db.marked_target == target.id:
    damage *= 1.1
THIEF 095 — BONUS IF KHRI ACTIVE
if "cunning" in caller.db.khri_active:
    damage *= 1.05
🟨 FAILURE CASE
THIEF 096 — FAILED AMBUSH

If detection beats stealth:

caller.msg("You fail to find the opening!")
caller.reveal()
THIEF 097 — PARTIAL FAILURE
damage *= 0.75

(no stagger applied)

🟦 ALERT + JUSTICE
THIEF 098 — LAW ZONE CHECK
if not caller.location.is_lawless():
    caller.location.db.alert_level += 1
THIEF 099 — OPTIONAL GUARD RESPONSE

Only if:

high severity
or repeat offense
if caller.db.crime_severity > threshold:
    call_guards()
🟪 FEEDBACK
THIEF 100 — AMBUSH MESSAGE
caller.msg(f"You strike from the shadows at {target.key}!")
target.msg("Something hits you from nowhere!")
caller.location.msg_contents(
    f"{caller.key} suddenly appears, striking {target.key}!",
    exclude=[caller, target]
)
🧠 HARD RULES (PHASE 5)

Aedan must NOT:

allow ambush without stealth
allow repeated ambush stacking
bypass combat system
create instant kill mechanics
add positional grid systems
✅ VALIDATION CHECKLIST

After THIEF 100:

ambush requires stealth
ambush breaks stealth
ambush deals increased damage
ambush applies stagger
ambush interacts with mark + khri
ambush differs from rough
🔥 WHAT YOU JUST BUILT

This is:

Full Thief Combat Identity

You now have TWO combat openers:
🟦 Ambush (Stealth)
high reward
requires setup
controlled
🟥 Rough (Aggressive)
immediate
loud
risky
🧠 FINAL STATE OF THIEF

You now have a complete profession loop:

observe → mark → khri → choose path

→ stealth path → ambush → slip → vanish
→ aggressive path → thug → rough → fight → escape

THIEF PHASE 7 — POSITIONING + ATTENTION + DISGUISE
🧱 MICRO TASKS — THIEF 121–140 (AEDAN FORMAT)
🎯 GOAL
add positioning state (lightweight)
add attention/distracted system
add disguise system (controlled)
integrate with:
stealth
theft
guards
social perception
🟥 POSITIONING SYSTEM (LIGHTWEIGHT, NOT GRID)
THIEF 121 — ADD POSITION STATE

File: typeclasses/characters.py

self.db.position_state = "neutral"  
# values: neutral, advantaged, exposed
THIEF 122 — SET DEFAULT ON LOGIN
self.db.position_state = "neutral"
THIEF 123 — ADVANTAGE FROM STEALTH

File: hide success

caller.db.position_state = "advantaged"
THIEF 124 — EXPOSED ON FAILURE

File: steal / ambush fail

caller.db.position_state = "exposed"
THIEF 125 — RESET ON TIME

File: pulse

caller.db.position_state = "neutral"

(after short duration ~5–10s equivalent)

THIEF 126 — APPLY POSITION BONUS

File: steal / ambush

if caller.db.position_state == "advantaged":
    difficulty -= 10

if caller.db.position_state == "exposed":
    difficulty += 10
🟫 ATTENTION SYSTEM (TARGET STATE)
THIEF 127 — ADD ATTENTION STATE
self.db.attention_state = "idle"
# values: idle, distracted, alert
THIEF 128 — SET DISTRACTED FROM THUG
target.db.attention_state = "distracted"
THIEF 129 — SET ALERT ON FAILURE
target.db.attention_state = "alert"
THIEF 130 — APPLY ATTENTION MODIFIERS

File: steal logic

if target.db.attention_state == "distracted":
    difficulty -= 10

if target.db.attention_state == "alert":
    difficulty += 15
THIEF 131 — ATTENTION DECAY

File: pulse

if time.time() - last_change > 10:
    target.db.attention_state = "idle"
THIEF 132 — MARK SHOWS ATTENTION

File: mark output

caller.msg(f"Attention: {target.db.attention_state}")
🟩 DISGUISE SYSTEM (IDENTITY LAYER)
THIEF 133 — ADD DISGUISE STATE

File: typeclasses/characters.py

self.db.disguised = False
self.db.disguise_name = None
self.db.disguise_profession = None
THIEF 134 — CREATE COMMAND
disguise <name>
THIEF 135 — APPLY DISGUISE
caller.db.disguised = True
caller.db.disguise_name = args
THIEF 136 — OVERRIDE DISPLAY NAME

File: name display logic

if obj.db.disguised:
    return obj.db.disguise_name
THIEF 137 — BLOCK IN COMBAT
if caller.db.in_combat:
    caller.msg("You cannot disguise yourself right now.")
    return
THIEF 138 — BREAK DISGUISE ON ACTION

On:

ambush
rough
being hit
caller.db.disguised = False
caller.db.disguise_name = None
THIEF 139 — GUARD RECOGNITION CHECK

File: guard logic

if target.db.disguised:
    recognition_penalty = 20

(does NOT prevent detection, only delays)

THIEF 140 — FEEDBACK
caller.msg("You adjust your appearance, blending into a new identity.")
🧠 HARD RULES (PHASE 7)

Aedan must NOT:

create full positional grid system
allow disguise to clear warrants
allow disguise during combat
allow permanent disguise
bypass justice logic
✅ VALIDATION CHECKLIST

After THIEF 140:

stealth grants positional advantage
failure creates exposure penalty
targets can be distracted or alert
attention affects steal difficulty
mark reveals attention
player can disguise identity
disguise changes visible name
disguise breaks on combat/action
guards are slightly delayed by disguise
🔥 WHAT YOU JUST BUILT

This is:

The “alive” layer of Thief

Before:

systems were mechanical

Now:

timing matters
positioning matters
perception matters
identity matters
🧠 FINAL STATE (IMPORTANT)

You now have:

🧠 Decision
mark
attention
⚙️ Engine
khri
🎭 Identity
disguise
🧭 Positioning
advantaged / exposed
🕵️ Stealth + Combat
ambush / rough
🏃 Escape
slip + passages

THIEF PHASE 8 — POLISH PASS (RT-LITE + FEEL + PACING)
🧱 MICRO TASKS — THIEF 141–160 (AEDAN FORMAT)
🎯 GOAL
introduce roundtime-lite (action lock)
prevent spam behavior
add tension between actions
improve moment-to-moment feel
🟥 RT-LITE (ACTION LOCK SYSTEM)
THIEF 141 — ADD ROUND TIME FIELD

File: typeclasses/characters.py

self.db.roundtime = 0
THIEF 142 — ADD HELPER
def is_in_rt(self):
    return time.time() < self.db.roundtime
THIEF 143 — BLOCK ACTIONS IN RT

File: command base (or per command if needed)

if caller.is_in_rt():
    caller.msg("You are still recovering.")
    return
THIEF 144 — APPLY RT ON STEAL
caller.db.roundtime = time.time() + 2
THIEF 145 — APPLY RT ON AMBUSH
caller.db.roundtime = time.time() + 3
THIEF 146 — APPLY RT ON ROUGH
caller.db.roundtime = time.time() + 3
THIEF 147 — APPLY RT ON SLIP
caller.db.roundtime = time.time() + 2
🟫 VARIABLE RT (SKILL EXPRESSION)
THIEF 148 — REDUCE RT WITH POSITION
if caller.db.position_state == "advantaged":
    rt -= 1
THIEF 149 — INCREASE RT ON FAILURE
if failure:
    rt += 1
THIEF 150 — CLAMP RT
rt = max(1, min(rt, 5))
🟩 ACTION FEEDBACK (IMPORTANT FOR FEEL)
THIEF 151 — ADD RT MESSAGE
caller.msg(f"You must wait {rt} seconds to act again.")
THIEF 152 — SHORT RECOVERY MESSAGE
caller.msg("You regain your footing.")

(trigger when RT ends — optional simple check)

🟨 MICRO-TENSION SYSTEM
THIEF 153 — ADD “COMMITMENT WINDOW” FLAG
self.db.recent_action = True
self.db.recent_action_timer = time.time()
THIEF 154 — APPLY RISK AFTER ACTION

File: steal / thug / ambush

if caller.db.recent_action:
    detection += 5
THIEF 155 — CLEAR RECENT ACTION
if time.time() - caller.db.recent_action_timer > 3:
    caller.db.recent_action = False
🟦 FLOW SMOOTHING (ANTI-CLUNK)
THIEF 156 — ALLOW MARK DURING RT
# mark should NOT be blocked by RT
THIEF 157 — ALLOW KHRI DURING RT
# khri activation allowed during RT
THIEF 158 — BLOCK HEAVY ACTIONS ONLY

Ensure RT blocks:

steal
ambush
rough
slip

But NOT:

mark
khri
look/search
🟥 COMBAT ENTRY SMOOTHING
THIEF 159 — PREVENT DOUBLE INITIATION
if caller.db.in_combat:
    skip re-initiation
THIEF 160 — GRACE WINDOW AFTER AMBUSH
caller.db.post_ambush_grace = True

During grace (~2s):

reduced incoming damage
🧠 HARD RULES (PHASE 8)

Aedan must NOT:

create global combat system changes
add animation systems
introduce tick scheduler changes
create new stat systems
override existing cooldown systems
✅ VALIDATION CHECKLIST

After THIEF 160:

actions have short recovery time
player cannot spam steal/ambush
positioning affects recovery speed
failure increases recovery time
mark/khri still feel responsive
actions feel weighted, not instant
🔥 WHAT YOU JUST BUILT

This is:

Tension + pacing layer

Before:

fast, mechanical, spammy

Now:

deliberate
risky
controlled
satisfying
🧠 FINAL STATE OF YOUR THIEF

You now have:

🧠 Intelligence
mark
memory
attention
⚙️ Engine
khri
🎭 Identity
disguise
🧭 Positioning
advantaged / exposed
🕵️ Execution
ambush / thug / rough
🏃 Survival
slip + passages
⏱️ Feel
RT-lite pacing
commitment windows

👉 This is now:

A complete, DR-faithful, system-driven Thief profession

