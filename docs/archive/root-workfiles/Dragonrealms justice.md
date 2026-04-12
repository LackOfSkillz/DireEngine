Here’s the deep-dive summary, focused on the parts of DragonRealms’ justice system that are actually worth borrowing.

Core structure

DragonRealms justice is not just “guards attack criminals.” It is a layered civic system with justice zones, province-based jurisdiction, wanted status, capture, judge interaction, sentence/fine, property seizure, debt repayment, and item recovery. The JUSTICE verb tells you whether an area is enforced or lawless, wanted characters can be captured by guards over time, and RECALL WARRANT shows outstanding warrants.

A major historical design point is that the newer system shifted crimes away from abstract charge stacking and toward fine-based consequences tied to the crime itself, and it explicitly allowed all guilds to try escaping guards.

The important nuances
1. Justice is territorial, not global

DragonRealms has multiple justice types, including Standard Justice, Clan Justice, Dirge Justice, and lawless areas. Standard Justice is the normal city/province model; the others can behave differently. There are also jurisdiction quirks where one settlement may have its own jail/guards but still belong to a larger justice conglomerate.

Design takeaway: your system should be zone-based and authority-based, not one global “crime flag.”

2. Crimes are differentiated by category and severity

Under Standard Justice, DragonRealms distinguishes crimes like:

aiding and abetting,
disturbing the peace,
endangering the public,
forbidden practices like visible necromancy/sorcery in justice zones,
murder,
thievery from shops,
stealing from players,
breaking and entering.

The thievery page makes the theft ladder especially clear:

pickpocketing from NPCs is the lightest stealing offense,
pilfering from shops is more serious,
felony stealing from players is more serious still.

Design takeaway: do not use one generic “theft” crime. Split at minimum into:

petty theft / pickpocket,
shoplifting,
player theft,
burglary,
public magic / disturbing peace,
violent crime.
3. Capture is only part of the punishment loop

When arrested, your worn inventory is seized, you spend time incarcerated, then you face a judge and must PLEAD INNOCENT or PLEAD GUILTY. After judgment, debts must be paid to the arresting province before property is reclaimed from the guardhouse, where it is stored in a sack.

That is one of the best parts of the DR model:

the guard encounter is not the whole punishment,
the processing pipeline is the system.

Design takeaway: your instinct to do capture → judge → sentence is very DR-compatible.

4. Pleading is a real decision, not just flavor

At the judge:

PLEAD INNOCENT uses Charisma and other mental stats to try to beat the charge,
if it fails, the fine becomes higher than it would have been,
PLEAD GUILTY speeds things along and generally gives a slightly reduced fine.

There is also a DR-specific nuance for the stocks:

for petty crimes in Crossing, you can end up in the pillory/stocks instead of receiving a fine,
while there, you can do little besides speak,
other players can throw rotten tomatoes or snowballs at you,
PLEAD FOR RELEASE may let you out early, with no penalty for failure.

This is the closest official analogue to your idea, and it strongly supports it.

5. Stocks are used for low-level theft, not as the universal punishment

The justice page explicitly notes that for some stealing charges, you may be placed in the stocks instead of fined, and that this generally happens when the total fine is low.

Design takeaway: stocks should be a petty-crime sentence, not a fallback for everything.

6. Surrender matters

DragonRealms lets wanted characters SURRENDER GUARD, which can substantially reduce the fine and prevent being captured at a bad time.

Design takeaway: your justice system should include a voluntary surrender path. That creates agency and avoids “gotcha” arrests when the player is mid-task.

7. Victim reporting matters

If someone catches a thief stealing, they can go to a guard and use ACCUSE <person> THIEVERY. Success is not automatic; factors may include criminal history and Charisma. Traders and Thieves also have their own alternate accusation/retaliation pathways.

Design takeaway: witnessed crime should not always auto-convict. There is room for:

victim report,
witness report,
false accusation risk,
stat-modified adjudication later.
8. Shoplifting is its own discipline

The STEAL command in DR explicitly supports:

STEAL <item> for shops,
STEAL <player/npc> (coin/gem) for people.

Shop stealing difficulty is tied to the item’s value and weight, and after you hit a shop, that shopkeeper watches you more closely for about an hour.

That is a very important nuance:

shops are not just containers,
shops have a heightened suspicion memory.

Design takeaway: your shoplifting system should track suspicion per shop or per shopkeeper, not just use a single global theft cooldown.

9. Justice and PvP are linked for player theft

In DR, stealing from another player sets and locks your PvP stance Open for four hours.

You may or may not want that exact rule, but the design idea matters:

Design takeaway: stealing from players is not merely a property crime. It is also a consent/escalation boundary and should have stronger consequences than NPC theft.

10. Different justice regimes can punish very differently

Clan Justice is especially notable because shop theft can be punished by cutting off a hand with a long stun and heavy bleeding instead of the standard city-style court/fine flow.

Design takeaway: your system can support different authority cultures later:

civilized town justice,
brutal frontier justice,
guild justice,
trade-route justice,
outlaw/lawless areas.

That gives you huge world flavor without rewriting the whole engine.

11. Guards are more than arrest bots

A 2025 update added more active guard behavior:

they engage hostile creatures,
can stun/knock down/incapacitate,
drag corpses or stunned players to triage,
tend bleeding players in some cases.

That’s separate from criminal justice, but it reveals a subtle design point:

guards are a world actor type, not a one-purpose justice script.

Design takeaway: your guards should probably be a broad civic-enforcement NPC framework that can later support justice, defense, emergency response, escorting, and prison transport.

What DragonRealms does especially well

The strongest parts to copy are:

1. Zone-based law

Crime matters where law exists, and not where it doesn’t.

2. Nonlethal consequence

For many crimes, the system is about interruption, embarrassment, debt, confiscation, and downtime, not death.

3. Public humiliation as sentence

Stocks are memorable because they create social consequences, not just numeric punishment.

4. Province-level debt and property recovery

The punishment continues after sentencing until the player clears the debt and collects their belongings.

5. Voluntary surrender

The player has a way to choose the timing of consequences.

What not to copy literally

I would not clone DR exactly in a first implementation.

I would avoid, for now:

province-specific debt offices and guardhouses as separate logistics,
extremely fragmented justice conglomerates,
PvP-open theft rules unless you deliberately want that social contract,
exotic justice types like amputating clan justice,
full innocent/guilty stat litigation on day one.

Those are good long-term enrichments, but they are not required for your first justice slice.

Best-fit DireMUD version

Based on what you described and what DR does well, I’d recommend this first model:

Justice layers
Lawless
Town Justice
later: Guild Justice, Trade Route Justice, Brutal/Frontier Justice
Crime tiers
petty theft
shoplifting
burglary
player theft
public disorder / unlawful magic
violent crime
Flow
witness or system detection
wanted flag
voluntary surrender option
guard capture
inventory seizure
judge scene
sentence:
fine,
stocks,
jail
release
debt/property recovery
Sentence guidance
low severity → stocks
mid severity → fine
high severity / repeats → jail
violent crimes later can escalate beyond that

This is slightly simpler than DR, but it preserves the best emotional beats.

Key nuance I would absolutely keep

If you only keep five DragonRealms justice nuances, keep these:

Justice is local.
Shops are more sensitive than random theft.
Surrender is a valid player choice.
Stocks are for petty humiliation, not universal punishment.
Judgment and property recovery matter as much as arrest.
Recommendation before microtasks

Before we write the next justice microtasks, I recommend we lock these design decisions explicitly:

Are fines paid immediately if the player has coin, or always deferred to a clerk?
Do you want surrender to reduce sentence severity, fine amount, or both?
Do you want judge outcomes to be deterministic by severity, or partially stat-based like DR’s pleading?
Do you want confiscated inventory returned automatically on release, or claimed from a jail clerk/locker?

My recommendation:

immediate coin check first,
surrender reduces severity by one step,
pleading exists but only affects fine/jail duration slightly,
belongings are returned in a sack on release for v1.
MICRO TASKS (3320–3339) — JUSTICE CORE (AEDAN FORMAT)
🟥 CAPTURE ENTRY (NO COMBAT)
3320 — ADD CAPTURE FLAGS

File: typeclasses/characters.py
Add default attributes (create if missing):

self.db.is_captured = False
self.db.confiscated_items = []
self.db.fine_amount = 0
self.db.fine_due = 0
self.db.collateral_locked = False
self.db.fine_due_timestamp = None

Success:

New characters have all fields initialized
No errors on login
3321 — MODIFY GUARD ENGAGE → CAPTURE

File: guard behavior file (where engage() or equivalent exists)

Replace attack logic with:

target.db.is_captured = True
target.db.in_combat = False
target.db.pursuers = []

Send message:

target.msg("The guard seizes you and binds your hands!")

Success:

Guard does NOT attack
Player is flagged is_captured = True
🟫 MOVEMENT LOCK
3322 — BLOCK MOVEMENT WHEN CAPTURED

File: movement handler (likely at_before_move or command)

Add:

if self.db.is_captured:
    self.msg("You are restrained and cannot move.")
    return False

Success:

Captured player cannot move
Non-captured player unaffected
🟩 CONFISCATION SYSTEM
3323 — CREATE STORAGE CONSTANT

File: new or existing config file

GUARD_STORAGE = "#STORAGE_ROOM_ID"

(Use real room ID)

Success:

Value exists and is accessible
3324 — CREATE confiscate_items() FUNCTION

File: utils/crime.py

def confiscate_items(character):
    items = list(character.contents)

    character.db.confiscated_items = []

    for item in items:
        character.db.confiscated_items.append(item.id)
        item.move_to(GUARD_STORAGE)

Success:

Items leave player inventory
IDs stored on character
3325 — CALL CONFISCATION ON CAPTURE

File: same as guard engage

Add:

from utils.crime import confiscate_items
confiscate_items(target)

Success:

Items removed immediately on capture
🟨 JUDGE ENTRY
3326 — DEFINE JUDGE ROOM

File: config/constants

JUDGE_ROOM = "#JUDGE_ROOM_ID"
3327 — MOVE PLAYER TO JUDGE

File: guard logic after capture

target.move_to(JUDGE_ROOM)
target.msg("You are dragged before a judge.")

Success:

Player appears in judge room
Message displays
🟦 SENTENCE GENERATION
3328 — READ BASE SEVERITY

File: new function or inline in judge logic

severity = character.db.crime_severity or 1
3329 — APPLY RANDOM MODIFIER
import random
modifier = random.randint(-1, 1)
severity = max(1, severity + modifier)

Success:

Severity varies slightly per sentence
🟥 SENTENCE TYPE
3330 — DETERMINE SENTENCE TYPE
if severity <= 2:
    sentence = "stocks"
elif severity <= 5:
    sentence = "fine"
else:
    sentence = "jail"

Store:

character.db.sentence_type = sentence
🟪 FINE CALCULATION
3331 — COMPUTE FINE
fine = severity * 20
character.db.fine_amount = fine
🟩 PAYMENT LOGIC
3332 — CHECK PLAYER GOLD
if character.db.gold >= fine:
    character.db.gold -= fine
    paid = True
else:
    paid = False
3333 — STORE UNPAID STATE
if not paid:
    character.db.fine_due = fine
🟨 COLLATERAL LOCK
3334 — LOCK ITEMS IF UNPAID
if not paid:
    character.db.collateral_locked = True
    character.db.fine_due_timestamp = time.time()
🟦 RETURN ITEMS (PAID ONLY)
3335 — CREATE SACK OBJECT
sack = create_object("typeclasses.objects.Object")
sack.key = "a rough burlap sack"
3336 — MOVE ITEMS INTO SACK
for item_id in character.db.confiscated_items:
    item = search_object(item_id)[0]
    item.move_to(sack)

sack.move_to(character)
3337 — MESSAGE
character.msg("The guard returns your belongings in a sack.")
🟥 STOCKS HANDLING
3338 — MOVE TO STOCKS
if sentence == "stocks":
    character.move_to(STOCKS_ROOM)
    character.db.in_stocks = True
🟪 JAIL HANDLING
3339 — SET JAIL TIMER
if sentence == "jail":
    character.db.jail_timer = random.randint(600, 900)
🧠 HARD RULES (NON-NEGOTIABLE)

Aedan must NOT:

create new systems outside listed files
rename existing attributes
refactor unrelated code
add features not explicitly listed
implement liquidation yet
implement merchant lockout yet
✅ VALIDATION CHECKLIST (YOU CAN TEST QUICKLY)

After 3339:

Guard captures instead of attacks
Player cannot move
Items removed immediately
Player appears in judge room
Sentence varies slightly
If paid → sack returned
If unpaid → no items returned
Stocks/jail assignment works

MICRO TASKS (3340–3359) — COLLATERAL + LIQUIDATION + MERCHANT LOCKOUT
🎯 GOAL
unpaid fines persist
confiscated items act as collateral
48-hour timer triggers liquidation
liquidation reduces (not clears) debt
merchants refuse service until debt cleared
🟥 TIME TRACKING (REAL-WORLD TIMER)
3340 — IMPORT TIME SAFELY

File: utils/crime.py (or shared utility file)

import time

Success:

No duplicate imports
No runtime errors
3341 — ENSURE TIMESTAMP IS STORED ON UNPAID FINE

File: where fine is assigned (from 3334)

Verify this exists (DO NOT duplicate):

character.db.fine_due_timestamp = time.time()

Success:

Timestamp is set only when fine is unpaid
🟫 COLLATERAL STATE VALIDATION
3342 — ADD HELPER: has_unpaid_fine()

File: typeclasses/characters.py

def has_unpaid_fine(self):
    return bool(self.db.fine_due and self.db.fine_due > 0)

Success:

Returns True only when fine_due > 0
3343 — ADD HELPER: get_confiscated_items()
from evennia.utils.search import search_object

def get_confiscated_items(self):
    items = []
    for item_id in self.db.confiscated_items or []:
        result = search_object(item_id)
        if result:
            items.append(result[0])
    return items

Success:

Returns valid object list
Does not crash on missing items
🟨 LIQUIDATION CHECK SYSTEM
3344 — CREATE FUNCTION: check_liquidation()

File: utils/crime.py

def check_liquidation(character):

Stub only for now.

Success:

Function exists
No logic yet
3345 — ADD TIME CHECK LOGIC
elapsed = time.time() - (character.db.fine_due_timestamp or 0)

if elapsed < 172800:  # 48 hours
    return

Success:

No liquidation before 48 hours
3346 — REQUIRE UNPAID FINE
if not character.has_unpaid_fine():
    return
🟦 LIQUIDATION EXECUTION
3347 — GET COLLATERAL ITEMS
items = character.get_confiscated_items()
3348 — CALCULATE LIQUIDATION VALUE
value = len(items) * 5  # flat low value per item

(No item pricing system yet — DO NOT add one)

3349 — REDUCE FINE
character.db.fine_due = max(0, character.db.fine_due - value)
3350 — DELETE ITEMS (SOLD)
for item in items:
    item.delete()
3351 — CLEAR CONFISCATED LIST
character.db.confiscated_items = []
character.db.collateral_locked = False
3352 — MESSAGE PLAYER (IF ONLINE)
if character.sessions:
    character.msg("Your confiscated belongings have been sold to cover part of your fine.")
🟪 MERCHANT LOCKOUT
3353 — ADD HELPER: can_trade()

File: typeclasses/characters.py

def can_trade(self):
    return not self.has_unpaid_fine()
3354 — ENFORCE IN SHOP NPC

File: shopkeeper logic

Add:

if not character.can_trade():
    character.msg("The shopkeeper refuses to deal with you until your debts are settled.")
    return False
🟩 FINE PAYMENT COMMAND
3355 — CREATE COMMAND
pay fine
3356 — IMPLEMENT PAYMENT
if not caller.has_unpaid_fine():
    caller.msg("You have no outstanding fines.")
    return

if caller.db.gold < caller.db.fine_due:
    caller.msg("You do not have enough coin.")
    return

caller.db.gold -= caller.db.fine_due
caller.db.fine_due = 0
3357 — RETURN ITEMS (IF STILL HELD)
items = caller.get_confiscated_items()

if items:
    sack = create_object("typeclasses.objects.Object")
    sack.key = "a rough burlap sack"

    for item in items:
        item.move_to(sack)

    sack.move_to(caller)
3358 — CLEAR COLLATERAL STATE
caller.db.confiscated_items = []
caller.db.collateral_locked = False
caller.db.fine_due_timestamp = None
3359 — CONFIRMATION MESSAGE
caller.msg("You pay your fine. Your standing is restored.")
🧠 HARD RULES (DO NOT BREAK)

Aedan must NOT:

implement item value system
add economy balancing
add interest rates
create new inventory systems
modify existing shop system beyond gate check
✅ VALIDATION CHECKLIST

After 3359:

unpaid fine persists after release
items are held as collateral
after 48 hours → items deleted + fine reduced
player can pay fine manually
items returned if still present
merchants refuse service if fine unpaid
🔥 What You Just Built

This is now:

A persistent economic justice system

Players will feel:

risk
loss
recovery
consequences over time

MICRO TASKS (3360–3379) — JUDGE + PLEADING
🎯 GOAL
player can plead guilty or innocent
surrender reduces punishment
judge outcome slightly variable
system remains predictable
🟥 SURRENDER SYSTEM
3360 — CREATE COMMAND
surrender
3361 — VALIDATE STATE

File: command file

if not caller.is_criminal():
    caller.msg("You are not wanted.")
    return
3362 — APPLY SURRENDER FLAG
caller.db.surrendered = True
3363 — TRIGGER CAPTURE FLOW
call_guards(caller.location, caller)
caller.msg("You surrender yourself to the authorities.")
3364 — REDUCE SEVERITY ON SURRENDER

Hook into sentence calculation

if character.db.surrendered:
    severity = max(1, severity - 1)
🟫 JUDGE STATE MACHINE
3365 — ADD FLAG

File: typeclasses/characters.py

self.db.awaiting_plea = False
3366 — SET FLAG ON JUDGE ENTRY

File: judge entry logic

character.db.awaiting_plea = True

Message:

character.msg("The judge looks down at you. 'How do you plead?'")
🟩 PLEAD COMMAND
3367 — CREATE COMMAND
plead <guilty|innocent>
3368 — VALIDATE STATE
if not caller.db.awaiting_plea:
    caller.msg("No one is asking for your plea.")
    return
🟨 PLEAD GUILTY
3369 — APPLY EFFECT
caller.db.plea = "guilty"
caller.db.awaiting_plea = False
3370 — REDUCE PENALTY

Hook into fine calculation:

if character.db.plea == "guilty":
    fine = int(fine * 0.8)
3371 — MESSAGE
"You admit your guilt. The judge nods."
🟦 PLEAD INNOCENT
3372 — APPLY EFFECT
caller.db.plea = "innocent"
caller.db.awaiting_plea = False
3373 — RESOLUTION CHECK
import random

roll = random.randint(1, 100)

if roll > 70:
    verdict = "cleared"
else:
    verdict = "failed"
3374 — HANDLE SUCCESS (RARE)
if verdict == "cleared":
    caller.db.crime_flag = False
    caller.db.fine_due = 0

Message:

"The judge frowns, then waves you off. 'Insufficient evidence.'"
3375 — HANDLE FAILURE
if verdict == "failed":
    fine = int(fine * 1.2)

Message:

"The judge scowls. 'Your lies cost you more dearly.'"
🟪 RESET PLEA STATE
3376 — CLEAR FLAGS
caller.db.plea = None
caller.db.surrendered = False
🟩 FLOW CONTROL
3377 — DELAY SENTENCE UNTIL PLEA

Ensure sentencing only happens AFTER:

plea resolved
or timeout (future hook)
🟨 TIMEOUT SAFETY
3378 — AUTO DEFAULT

If no plea after short delay:

caller.db.plea = "guilty"
caller.db.awaiting_plea = False
🟦 FINAL MESSAGE
3379 — SENTENCE ANNOUNCEMENT
caller.msg(f"The judge passes sentence: {sentence}.")
🧠 HARD RULES

Aedan must NOT:

add stat systems (charisma checks etc.)
add dialogue trees
create NPC interaction framework
add timers beyond simple fallback
alter sentencing pipeline
✅ VALIDATION CHECKLIST

After 3379:

surrender reduces severity
judge asks for plea
player can choose guilty/innocent
guilty reduces fine
innocent sometimes clears (rare)
innocent failure increases fine
system proceeds cleanly
🔥 What You Just Built

This is now:

A player-influenced justice system

Not:

automatic punishment

But:

interactive consequence

MICRO TASKS (3380–3399) — STOCKS + SOCIAL SYSTEM
🎯 GOAL
stocks are interactive
other players/NPCs can engage
humiliation is visible but controlled
no grief systems introduced
🟥 STOCKS STATE ENFORCEMENT
3380 — ADD FLAG (IF NOT EXISTS)

File: typeclasses/characters.py

self.db.in_stocks = False
3381 — BLOCK MOVEMENT IN STOCKS

File: movement hook

if self.db.in_stocks:
    self.msg("You are locked in the stocks.")
    return False
3382 — BLOCK ABILITIES IN STOCKS

File: ability execution entry point

if character.db.in_stocks:
    character.msg("You cannot do that while restrained in the stocks.")
    return
🟫 STOCKS ROOM IDENTIFICATION
3383 — ADD ROOM FLAG

File: typeclasses/rooms.py

self.db.is_stocks = False
3384 — MARK STOCKS ROOM

Builder or setup file

room.db.is_stocks = True
🟩 TOMATO THROW SYSTEM
3385 — CREATE COMMAND
throw tomato <target>
3386 — VALIDATE TARGET IN STOCKS
if not target.db.in_stocks:
    caller.msg("They are not in the stocks.")
    return
3387 — VALIDATE SAME ROOM
if target.location != caller.location:
    return
3388 — EXECUTE THROW
caller.msg(f"You throw a tomato at {target.key}!")
target.msg(f"{caller.key} throws a tomato at you!")
caller.location.msg_contents(f"{caller.key} pelts {target.key} with a tomato!", exclude=[caller, target])
3389 — ADD LIGHT COOLDOWN

Reuse existing cooldown system

cooldowns["tomato"] = now + 2
🟨 NPC PARTICIPATION (LIGHT AMBIENCE)
3390 — ADD AMBIENT EVENT HOOK

File: stocks room or global tick

if room.db.is_stocks:
3391 — RANDOM NPC ACTION
import random

if random.random() < 0.1:
    room.msg_contents("A passerby jeers at the prisoners in the stocks.")
🟦 PLAYER FEEDBACK LOOP
3392 — MESSAGE ON ENTRY
character.msg("You are locked into the public stocks. All can see your shame.")
3393 — PERIODIC MESSAGE

On tick:

character.msg("The crowd watches you.")

(low frequency, DO NOT spam)

🟥 EARLY RELEASE (OPTIONAL ACTION)
3394 — CREATE COMMAND
plead release
3395 — VALIDATE STATE
if not caller.db.in_stocks:
    return
3396 — RANDOM CHANCE RELEASE
import random

if random.randint(1, 100) > 70:
    caller.db.in_stocks = False
3397 — MESSAGES

Success:

"The guard relents and releases you early."

Failure:

"The guard ignores your pleas."
🟪 RELEASE CLEANUP
3398 — ON STOCKS EXIT
caller.db.in_stocks = False
3399 — MOVE TO EXIT LOCATION
caller.move_to(STOCKS_EXIT)
caller.msg("You are released from the stocks.")
🧠 HARD RULES

Aedan must NOT:

add damage from tomatoes
add inventory for tomatoes
create grief mechanics
allow targeting outside stocks
allow infinite spam (cooldown required)
✅ VALIDATION CHECKLIST

After 3399:

player cannot move while in stocks
abilities blocked
other players can throw tomatoes
NPCs occasionally react
player receives humiliation feedback
early release sometimes works
release returns player to normal
🔥 What You Just Built

This is:

Social consequence system

Not punishment.

Not mechanics.

👉 Player-driven interaction

🎯 What This Enables
emergent RP
player storytelling
reputation systems later
public consequences

MICRO TASKS (3400–3419) — LAW + JURISDICTION
🎯 GOAL
define law zones
enforce justice only in those zones
allow lawless areas
support future expansion (guild/clan justice)
🟥 LAW TYPE ENUM
3400 — DEFINE LAW TYPES

File: world/law.py (CREATE FILE)

LAW_STANDARD = "standard"
LAW_NONE = "none"
3401 — OPTIONAL FUTURE TYPES (DEFINE ONLY)
LAW_GUILD = "guild"
LAW_FRONTIER = "frontier"

(NO LOGIC YET)

🟫 ROOM LAW FLAG
3402 — ADD LAW FIELD

File: typeclasses/rooms.py

self.db.law_type = LAW_STANDARD
3403 — ADD HELPER
def get_law_type(self):
    return self.db.law_type or LAW_STANDARD
🟩 LAWLESS ZONES
3404 — MARK LAWLESS ROOMS

Builder file

room.db.law_type = LAW_NONE
3405 — ADD HELPER

File: typeclasses/rooms.py

def is_lawless(self):
    return self.get_law_type() == LAW_NONE
🟨 CRIME GATING BY LAW
3406 — MODIFY CRIME FLAGGING

File: wherever crime_flag is set

Wrap with:

if not caller.location.is_lawless():
    caller.db.crime_flag = True
3407 — MODIFY SEVERITY INCREASE
if not caller.location.is_lawless():
    caller.db.crime_severity += 1
🟦 GUARD RESPONSE GATING
3408 — MODIFY call_guards()

File: utils/crime.py

Add at top:

if room.get_law_type() == LAW_NONE:
    return
3409 — BLOCK PURSUIT FROM LAWLESS AREAS
if player.location.is_lawless():
    return
🟥 JUSTICE PROCESS GATING
3410 — BLOCK CAPTURE IN LAWLESS

File: guard engage logic

if target.location.is_lawless():
    return
🟪 PLAYER FEEDBACK
3411 — ADD ENTRY MESSAGE (LAWLESS)

File: room entry hook

if room.is_lawless():
    caller.msg("You feel the absence of law here.")
3412 — ADD ENTRY MESSAGE (LAW ZONE)
if not room.is_lawless():
    caller.msg("The presence of law is felt here.")
🟩 JUSTICE COMMAND
3413 — CREATE COMMAND
justice
3414 — OUTPUT CURRENT LAW
law = caller.location.get_law_type()

caller.msg(f"Justice in this area: {law}")
🟨 SHOP INTERACTION WITH LAW
3415 — SHOPLIFTING STILL WORKS IN LAWLESS

Ensure:

no crime flag
no guards

(verify existing logic respects this)

🟦 STEALTH INTERACTION
3416 — REMOVE STEALTH PENALTY IN LAWLESS
if room.is_lawless():
    skip criminal stealth penalties
🟥 ALERT SYSTEM GATING
3417 — BLOCK ALERT ESCALATION IN LAWLESS
if room.is_lawless():
    return
🟪 SAFETY
3418 — ENSURE DEFAULT LAW EXISTS
if not room.db.law_type:
    room.db.law_type = LAW_STANDARD
🟩 DEBUG
3419 — LOG LAW TYPE ON ENTRY (DEBUG ONLY)
print(f"{caller} entered {room} with law={room.get_law_type()}")
🧠 HARD RULES

Aedan must NOT:

create faction systems yet
create reputation systems
modify justice pipeline logic
add guards to lawless zones
create new crime systems
✅ VALIDATION CHECKLIST

After 3419:

lawless areas allow crime without flag
guards do not respond in lawless areas
justice system does not trigger in lawless areas
players receive clear feedback on zone type
justice command reports correctly
🔥 What You Just Built

This is:

World rule segmentation

Before:

same rules everywhere

Now:

location matters
🎯 What This Enables Next
smuggling routes
outlaw towns
safe trade zones
faction-controlled regions

MICRO TASKS (3420–3439) — WARRANTS + MEMORY (AEDAN FORMAT)
🎯 GOAL
crimes belong to regions, not global state
warrants persist across rooms in same region
guards react based on stored history
leaving area does not clear consequences
🟥 REGION SYSTEM
3420 — ADD REGION FIELD TO ROOM

File: typeclasses/rooms.py

self.db.region = "default_region"
3421 — ADD HELPER
def get_region(self):
    return self.db.region or "default_region"
3422 — SET REGION IN BUILDER

File: world builder

room.db.region = "brookhollow"

Success:

All rooms in town share same region string
🟫 CHARACTER WARRANT STORAGE
3423 — ADD WARRANT DICT

File: typeclasses/characters.py

self.db.warrants = {}
3424 — WARRANT STRUCTURE

Document (DO NOT change later):

{
    "brookhollow": {
        "severity": int,
        "timestamp": float
    }
}
🟩 ADD WARRANT ON CRIME
3425 — MODIFY CRIME FLAGGING

File: wherever crime occurs

region = caller.location.get_region()

entry = caller.db.warrants.get(region, {"severity": 0, "timestamp": time.time()})

entry["severity"] += 1
entry["timestamp"] = time.time()

caller.db.warrants[region] = entry
3426 — KEEP GLOBAL FLAG (DO NOT REMOVE)
caller.db.crime_flag = True

(Global flag still used for immediate logic)

🟨 GUARD REACTION USING WARRANTS
3427 — MODIFY GUARD TARGETING

File: guard logic

region = self.location.get_region()
warrant = target.db.warrants.get(region)

if warrant:
    engage target
3428 — SCALE AGGRESSION
severity = warrant["severity"]

if severity >= 3:
    immediate capture
🟦 WARRANT DECAY
3429 — ADD DECAY FUNCTION

File: utils/crime.py

def decay_warrants(character):
3430 — IMPLEMENT DECAY
for region, data in character.db.warrants.items():
    elapsed = time.time() - data["timestamp"]

    if elapsed > 3600:  # 1 hour
        data["severity"] = max(0, data["severity"] - 1)
3431 — REMOVE CLEARED WARRANTS
if data["severity"] <= 0:
    del character.db.warrants[region]
🟥 JUSTICE COMMAND UPDATE
3432 — EXTEND justice COMMAND
for region, data in caller.db.warrants.items():
    caller.msg(f"{region}: severity {data['severity']}")
🟪 GUARD MEMORY (LIGHT IMMERSION)
3433 — ADD MESSAGE

On guard spotting wanted player:

self.msg_contents(f"{self.key} recognizes {target.key}!")
🟩 CROSS-ROOM PERSISTENCE
3434 — ENSURE WARRANTS ARE NOT CLEARED ON MOVE

Audit:

NO code should reset warrants on movement

Success:

moving rooms does not clear warrants
🟨 REGION-SPECIFIC JUSTICE
3435 — MODIFY CAPTURE FLOW

Only trigger if warrant exists in region:

if not target.db.warrants.get(region):
    return
🟦 LAWLESS INTERACTION
3436 — WARRANTS STILL EXIST IN LAWLESS

DO NOT delete warrants in lawless areas

But:

guards do not act there
🟥 OPTIONAL DEBUG
3437 — LOG WARRANT CREATION
print(f"[WARRANT] {caller} in {region} severity={entry['severity']}")
🟪 SAFETY
3438 — ENSURE WARRANT DICT EXISTS
if not caller.db.warrants:
    caller.db.warrants = {}
3439 — SAFE ACCESS

Always use:

caller.db.warrants.get(region)
🧠 HARD RULES

Aedan must NOT:

remove global crime_flag
merge warrants into single value
add database tables
create faction logic
auto-clear warrants on logout
✅ VALIDATION CHECKLIST

After 3439:

committing crime creates region-specific warrant
guards only react in that region
leaving region avoids guards (but does not clear warrant)
returning region triggers guard response again
warrants decay over time
justice command shows regional crimes
🔥 What You Just Built

This is:

Persistent world memory

Before:

crime = local event

Now:

crime = regional consequence
🎯 What This Enables Next
bounty systems
cross-region smuggling
faction law differences
corruption/bribery

MICRO TASKS (3440–3459) — BOUNTIES + GUARD SCALING + CORRUPTION (AEDAN FORMAT)
🎯 GOAL
warrants create bounties
guards scale response based on severity
players can bribe to reduce consequences
system supports future corruption/factions
🟥 BOUNTY SYSTEM (PER REGION)
3440 — ADD BOUNTY FIELD TO WARRANT

File: typeclasses/characters.py

Update structure (DO NOT rename keys):

{
    "severity": int,
    "timestamp": float,
    "bounty": int
}
3441 — INITIALIZE BOUNTY ON CRIME

File: crime creation logic

entry["bounty"] = entry.get("bounty", 0) + 10
3442 — SCALE BOUNTY WITH SEVERITY
entry["bounty"] += entry["severity"] * 5

Success:

bounty increases with repeat offenses
🟫 BOUNTY QUERY COMMAND
3443 — CREATE COMMAND
bounty
3444 — OUTPUT PLAYER BOUNTIES
for region, data in caller.db.warrants.items():
    caller.msg(f"{region}: bounty {data.get('bounty', 0)}")
🟩 GUARD SCALING (RESPONSE INTENSITY)
3445 — MODIFY call_guards()

File: utils/crime.py

Add:

severity = culprit.db.warrants.get(room.get_region(), {}).get("severity", 1)
3446 — SCALE NUMBER OF GUARDS
max_guards = min(3, severity)

Only spawn/move up to max_guards

3447 — SCALE BEHAVIOR
if severity >= 5:
    immediate capture (skip warning)
🟨 GUARD WARNING PHASE
3448 — ADD WARNING MESSAGE (LOW SEVERITY)
if severity < 3:
    guard.msg_contents(f"{guard.key} shouts: Halt!")
3449 — DELAY CAPTURE SLIGHTLY
# add short delay or second tick before capture

(No new system—use existing tick)

🟦 BRIBERY SYSTEM
3450 — CREATE COMMAND
bribe <amount>
3451 — VALIDATE TARGET GUARD
guard = next(obj for obj in room.contents if getattr(obj.db, "is_guard", False))

Fail if none.

3452 — VALIDATE PLAYER GOLD
if caller.db.gold < amount:
    caller.msg("You don't have that much coin.")
    return
3453 — SUCCESS CHECK
import random

roll = random.randint(1, 100)

threshold = 50 - (amount // 10)

success = roll > threshold
3454 — ON SUCCESS
caller.db.gold -= amount

region = caller.location.get_region()

if region in caller.db.warrants:
    caller.db.warrants[region]["severity"] = max(0, caller.db.warrants[region]["severity"] - 2)

Message:

"The guard pockets your coin and looks the other way."
3455 — ON FAILURE
caller.db.gold -= amount

caller.msg("The guard sneers: 'Trying to bribe an officer?'")

Increase severity:

caller.db.warrants[region]["severity"] += 1
🟥 GUARD MEMORY EXTENSION
3456 — ADD FLAG
guard.db.bribe_attempted = True
3457 — MODIFY FUTURE REACTION
if guard.db.bribe_attempted:
    lower success chance on next bribe

(simple modifier only)

🟪 WARRANT DECAY ALSO REDUCES BOUNTY
3458 — MODIFY decay_warrants()
data["bounty"] = max(0, data["bounty"] - 5)
🟩 SAFETY
3459 — ENSURE BOUNTY KEY EXISTS
entry.setdefault("bounty", 0)
🧠 HARD RULES

Aedan must NOT:

create economy system
add player bounty hunting yet
add UI changes
create faction systems
add persistent corruption trees
✅ VALIDATION CHECKLIST

After 3459:

crimes generate bounty
bounty scales with repeated offenses
guards respond more aggressively with higher severity
players can attempt bribes
bribes can succeed or fail
failed bribes worsen situation
bounty decays over time
🔥 What You Just Built

This is:

Incentive layer

Before:

crime = risk

Now:

crime = risk + reward + manipulation
🎯 What This Enables Next
bounty hunters (players or NPCs)
corruption networks
faction-controlled law enforcement
black market systems

MICRO TASKS (3460–3479) — PLAYER BOUNTY HUNTERS + CONTRACTS (AEDAN FORMAT)
🎯 GOAL
players can see bounties
players can accept contracts
players can capture criminals
system pays out rewards
🟥 BOUNTY BOARD (WORLD OBJECT)
3460 — CREATE OBJECT TYPE

File: typeclasses/objects.py (or new file if needed)

Add:

class BountyBoard(DefaultObject):
    pass
3461 — PLACE IN WORLD

Builder file

board = create_object("typeclasses.objects.BountyBoard")
board.key = "a bounty board"
board.location = <TOWN_SQUARE>
🟫 LIST BOUNTIES
3462 — CREATE COMMAND
bounties
3463 — REQUIRE BOARD IN ROOM
board = next(obj for obj in room.contents if obj.key == "a bounty board")

Fail if none.

3464 — LIST ACTIVE WARRANTS
for player in all_characters:
    for region, data in player.db.warrants.items():
        if data["bounty"] > 0:
            caller.msg(f"{player.key} — {data['bounty']} coins")
🟩 CONTRACT ACCEPTANCE
3465 — CREATE COMMAND
accept bounty <player>
3466 — VALIDATE TARGET
target = search_player(name)
if not target:
    return
3467 — STORE CONTRACT
caller.db.active_bounty = target.id
3468 — CONFIRM
caller.msg(f"You accept the bounty on {target.key}.")
🟨 TRACKING TARGET
3469 — ADD HELPER

File: typeclasses/characters.py

def get_bounty_target(self):
    if not self.db.active_bounty:
        return None
    return search_object(self.db.active_bounty)
3470 — SIMPLE LOCATION HINT
caller.msg(f"Last known region: {target.location.get_region()}")

(No tracking system yet)

🟦 CAPTURE BY PLAYER
3471 — ADD COMMAND
capture <target>
3472 — VALIDATE CONDITIONS
if not target.is_criminal():
    caller.msg("They are not wanted.")
    return

if not target.db.is_captured:
    caller.msg("They must already be subdued.")
    return
3473 — COMPLETE CAPTURE
target.move_to(JUDGE_ROOM)
🟥 REWARD SYSTEM
3474 — PAY BOUNTY
region = caller.location.get_region()

data = target.db.warrants.get(region)

reward = data.get("bounty", 0)

caller.db.gold += reward
3475 — CLEAR WARRANT
del target.db.warrants[region]
3476 — CLEAR CONTRACT
caller.db.active_bounty = None
3477 — MESSAGE
caller.msg(f"You receive {reward} coins for the capture.")
🟪 SAFETY
3478 — PREVENT MULTIPLE CLAIMS
if not target.db.warrants.get(region):
    return
3479 — ENSURE ONE ACTIVE CONTRACT
if caller.db.active_bounty:
    caller.msg("You are already pursuing a bounty.")
    return
🧠 HARD RULES

Aedan must NOT:

add tracking systems (no GPS/pathing)
add PvP combat system
add UI changes
allow multiple bounty stacking
allow instant capture without prior state
✅ VALIDATION CHECKLIST

After 3479:

bounty board exists
players can view bounties
players can accept one bounty
players can track target region
players can capture target (if subdued)
players receive payout
warrant is cleared
🔥 What You Just Built

This is:

Player-driven enforcement system

Before:

system enforces law

Now:

players enforce law
🎯 What This Enables
bounty hunter playstyle
emergent PvP
criminal vs hunter dynamics
economy loops


MICRO TASKS (3480–3499) — TRACKING + ESCAPE COUNTERPLAY (AEDAN FORMAT)
🎯 GOAL
hunters get better tracking (but not perfect)
criminals get tools to evade
contracts become dynamic, not trivial
🟥 IMPROVED TARGET TRACKING (NON-GPS)
3480 — STORE LAST KNOWN LOCATION

File: typeclasses/characters.py

Add:

self.db.last_known_region = None
3481 — UPDATE ON WARRANT CHANGE

File: crime assignment logic

caller.db.last_known_region = caller.location.get_region()
3482 — UPDATE ON MOVEMENT (IF WANTED)

File: movement hook

if self.db.warrants:
    self.db.last_known_region = self.location.get_region()
🟫 TRACK COMMAND (REPLACES SIMPLE HINT)
3483 — CREATE COMMAND
track
3484 — VALIDATE CONTRACT
target = caller.get_bounty_target()

if not target:
    caller.msg("You are not tracking anyone.")
    return
3485 — PROVIDE REGION HINT
region = target.db.last_known_region

caller.msg(f"Your target was last seen in {region}.")
🟩 TRACK UNCERTAINTY (ANTI-GPS)
3486 — ADD RANDOM DRIFT
import random

if random.randint(1, 100) < 30:
    caller.msg("Your information may be outdated.")
🟨 CRIMINAL COUNTERPLAY — LAY LOW (UPGRADE)
3487 — MODIFY EXISTING COMMAND: lay low

Add:

caller.db.last_known_region = None
3488 — REDUCE WARRANT SEVERITY
for region in caller.db.warrants:
    caller.db.warrants[region]["severity"] = max(0, caller.db.warrants[region]["severity"] - 1)
3489 — MESSAGE
"You keep a low profile and obscure your trail."
🟦 TRACK BLOCKING (HARD COUNTER)
3490 — ADD FLAG
self.db.is_hidden_from_tracking = False
3491 — APPLY IN LAWLESS AREAS

File: movement hook

if self.location.is_lawless():
    self.db.is_hidden_from_tracking = True
3492 — CLEAR WHEN RETURNING TO LAW ZONE
if not self.location.is_lawless():
    self.db.is_hidden_from_tracking = False
3493 — MODIFY TRACK COMMAND
if target.db.is_hidden_from_tracking:
    caller.msg("Your target has gone to ground. You cannot find them.")
    return
🟥 CONTRACT FAILURE CONDITIONS
3494 — TARGET CLEARS WARRANT
if not target.db.warrants:
    caller.db.active_bounty = None
    caller.msg("Your bounty is no longer valid.")
3495 — TARGET LOGOUT (TEMPORARY HANDLING)
if not target.sessions:
    caller.msg("Your target has gone to ground.")

(No contract cancel yet)

🟪 MULTIPLE HUNTER SAFETY
3496 — PREVENT DUPLICATE PAYOUTS

Before reward:

if not target.db.warrants.get(region):
    return
🟩 ESCAPE FEEDBACK
3497 — CRIMINAL MESSAGE ON TRACK ATTEMPT (OPTIONAL DEBUG)
target.msg("You feel like someone is hunting you.")

(low frequency, optional)

🟨 TRACK COOLDOWN
3498 — ADD COOLDOWN
caller.ndb.cooldowns["track"] = now + 5
🟦 SAFETY
3499 — ENSURE SAFE TARGET ACCESS
if not target or not target.location:
    return
🧠 HARD RULES

Aedan must NOT:

implement exact location tracking
add pathfinding
add minimap/GPS systems
remove uncertainty
allow tracking in lawless zones
✅ VALIDATION CHECKLIST

After 3499:

hunters can track region (not exact room)
tracking is sometimes uncertain
criminals can obscure trail
lawless areas break tracking
contracts can fail naturally
system supports cat-and-mouse gameplay
🔥 What You Just Built

This is:

Predator vs prey loop

Before:

hunter always wins eventually

Now:

both sides have tools
🎯 What This Enables
long chases
ambushes
safe zones
smuggling routes
criminal strategy