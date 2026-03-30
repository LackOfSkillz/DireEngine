STATUS UPDATE — March 30, 2026

Implementation status: DEATH-001 through DEATH-120 are complete in the current codebase.

Validated live during the final production-layer pass:

- resurrection now requires favor and consumes favor on success
- resurrection has explicit failure messaging
- favor tiers affect resurrection quality
- `rejuvenate`, `uncurse`, and `consent` are implemented
- corpse/grave coin retention, grave damage tracking, and consented recovery are implemented
- new-player death protection is implemented through a centralized resolver

The final death-polish and world-integration layer is now implemented in code as well, including corpse/death UX polish, admin death tooling, region-aware recovery-point resolution, no-resurrection and dangerous/safe room flags, grave expiry and warnings, consent listing/expiration, anti-duplication protections for corpse/grave generation, and death event logging/analytics hooks. That final layer has static validation in this workspace; a fresh live gameplay verification pass is still recommended.

DragonRealms’ death system is not just “you die and come back.” It is a layered penalty-and-recovery system built around:

corpse state and corpse decay,
favors,
depart choices,
item recovery via graves,
Death’s Sting,
field-exp recovery,
and strong social interdependence with Empaths and especially Clerics.

For your game, that matters because DR’s death loop is doing several jobs at once:

punishing reckless play,
encouraging preparation,
preserving meaningful rescue gameplay,
creating demand for support professions,
and making death costly without making it purely character-deleting.
What the DR death loop actually is

At a high level, when a character dies, there are several possible outcomes:

wait for recovery help,
have the corpse treated and then resurrected,
or use DEPART and accept penalties/costs.

Historically, death included rank loss, but the September 12, 2025 overhaul changed that. DR removed direct skill-rank loss from death and replaced it with a field experience penalty/debt that reduces future exp gains until paid back. That means the modern DR system is now more about temporary efficiency loss and recovery friction than permanent advancement loss.

The core components
1) Favors are the backbone

Favors are blessings from the Immortals. They are used to:

qualify for resurrection,
reduce death penalties,
and unlock better DEPART options.

Key details:

You need at least 1 favor to be resurrected by a cleric.
The wiki explicitly says 1 favor is only the absolute minimum, while a much healthier operating floor is around 15 favors.
A favor is consumed when you DEPART, and also when a cleric uses Murrula’s Flames.

Favors are obtained through favor orbs, altar rituals, and sacrifice of unabsorbed experience into the orb. The more favors or circles you already have, the more experience it takes to fill another orb.

2) Depart is the self-service recovery path

DEPART revives you at the nearest depart point, but its cost and item retention depend on favors. The modern options are:

DEPART GRAVE: 1 favor, lose coins, items go to grave
DEPART COINS: 2 favors, keep coins
DEPART ITEMS: 2 favors, keep items
DEPART FULL: 3 favors, keep both items and coins

Typing plain DEPART auto-selects based on favor count:

3+ favors → DEPART FULL
2 favors → DEPART ITEMS
1 or less → DEPART GRAVE

That structure is extremely important design-wise: DR ties resource prep to quality of death recovery.

3) Death’s Sting is the temporary performance penalty

Death’s Sting is the main post-depart combat/stat penalty. Before the 2025 rework it was softer and tied more loosely to favor ratio. After the rework, it became much more explicit:

base duration: 1 hour
reduced by 1.5 minutes per favor, up to 20 favors
minimum duration: 30 minutes
base stat penalty: 20%
reduced by 0.5% per favor, up to 20 favors
minimum severity: 10%

It can be:

avoided by proper resurrection,
shortened/removed by cleric support like Uncurse,
or fully removed by strong enough alyssum tea.

This is one of the smartest parts of DR’s design: death does not just say “you lost stuff.” It says, “you are back, but compromised.”

4) Experience penalty replaced skill-rank loss

This is the big 2025 modern change.

Now, when you die, your field exp is tallied into a bit penalty/debt. After you return to life, exp gains are reduced by 50% until that debt is repaid. If you die again before clearing it, it stacks.

This is a cleaner design than direct rank loss because:

it hurts,
it preserves consequence,
but it avoids the uniquely demoralizing feeling of seeing actual ranks go backward.
5) Resurrection is the premium recovery path

Cleric resurrection is the “best” recovery path because it bypasses or mitigates the harshest depart penalties.

Modern behavior:

Resurrection removes previous-depart bit penalty.
It can restore up to 100% of field exp depending on the corpse’s favors.
Fully rejuvenating the corpse gives a base 50% exp restoration.
Beyond that, you gain +2% per favor over 25, reaching full restoration at full rejuve + 50 favors.

There are strong corpse-prep interactions here:

Rejuvenation before depart restores 50% of field exp on depart.
Fully restored corpses matter.
The system rewards rescue effort, not just the final spell cast.
6) Corpse decay creates time pressure

A dead character leaves a corpse that can decay. The resurrection page includes visible decay stages and timing cues, such as “about a half hour,” “less than a half hour,” “a few minutes,” and “about a minute.”

That timer matters because DR wants death to create:

urgency,
rescue gameplay,
and triage decisions.
7) Graves and item recovery are now their own system

The September 2025 update also overhauled graves:

graves no longer spit out items automatically,
only the owner and/or consented designee can dig them,
only the owner, consented targets, and certain Rangers can even see them,
digging creates a recovery bundle,
item damage begins below 10% and rises by 1% every 2 hours unrecovered, capped around 66%.

That means DR split “return to life” from “recover your gear.” Those are now related but distinct friction loops.

The support-profession dependency

This is the social heart of the system.

Empaths

Empaths are part of death recovery because major wounds on a corpse often need to be healed first before proper resurrection workflow can happen. That dependence is mentioned in DR player documentation and community guidance, and it fits the longstanding in-game recovery loop.

Clerics

Clerics are the true soul-recovery class:

Uncurse reduces/removes Death’s Sting effects,
Rejuvenation improves corpse condition and protects exp,
Resurrection restores the dead properly,
Murrula’s Flames is another resurrection-related tool with its own favor cost and outcomes.

So DR death is not just a punishment system. It is a class ecosystem system.

What DR is doing design-wise

Here’s the real design pattern under the hood.

DR death has five layers of consequence
Immediate interruption — you died, hunt stopped.
Recovery logistics — corpse, rescue, travel, timer.
Economic/material cost — favors, possible coin loss, grave recovery, item damage.
Performance penalty — Death’s Sting.
Progress penalty — reduced exp gains until debt is paid.

That layering is why it feels meaningful without relying on hard permadeath.

What I would preserve for DireMud

I would not copy DR literally. I would preserve its structure.

Keep
corpse state
time-limited rescue window
separate “return to life” vs “recover items”
favor-like preparation resource
temporary combat/stat penalty after bad recovery
support-class dependency for premium recovery
exp debt instead of direct skill-rank loss
Be careful with
too much corpse micromanagement,
too much item loss,
hard mandatory waiting,
death punishment that is so steep it makes players log off.
My recommendation for your implementation direction

For your game, I’d model death as three recovery tiers:

Tier 1: Assisted resurrection

Best result.

requires corpse intact
requires empath-style wound stabilization
requires cleric-style resurrection
no or minimal sting
restores most or all field XP debt
avoids grave/item complications
Tier 2: Prepared self-recovery

Middle result.

consume favor-equivalent
revive at shrine/altar
moderate sting
items maybe retained based on resource spend
partial exp restoration possible if corpse had been stabilized first
Tier 3: Bad death / unprepared recovery

Worst non-permadeath result.

no favors or insufficient support
maximum sting
heavy exp debt
item recovery required from corpse/grave
possible gear wear or degradation

That gives you the DR feel without cloning DR.

Most important takeaways for Aedan microtasks

The death system should be broken into these engineering slices:

Death state machine
alive
dead/corpse
departed
resurrected
recovered from grave
Corpse system
corpse object
decay timer
wound/severity state
recoverability flags
Favor system integration
minimum for resurrection
spend on depart modes
reduce sting severity/duration
Depart system
grave / items / coins / full modes
spawn at nearest recovery point
initialize post-death penalties
Death’s Sting system
timed debuff
stat effectiveness penalties
removable/reducible by support abilities
Experience debt system
snapshot field exp on death
apply post-return exp tax
clear or reduce on good recovery
Rescue pipeline
empath treatment hooks
cleric rejuvenation hooks
cleric resurrection resolution
Grave / item recovery
grave ownership
consent rules
item bundling
decay/damage over time
Newbie protection
charm / protected death band
first-X deaths safer
remove as player graduates
Special-case profession hooks
necromancer-style alternative
ranger grave-visibility style perks
trader-style recovery modifiers if you want analogous design later

The single biggest lesson from DR is this:

Death is not one mechanic. It is a connected subsystem that binds combat, progression, economy, religion, support classes, and social dependency together.

DEATH SYSTEM — MICROTASKS 001–020 (FOUNDATION LAYER)
🎯 PHASE GOAL

Establish:

death state
corpse creation
basic depart loop
minimal penalties

At the end of these 20:
👉 Player can die → become corpse → depart → revive with penalty

🧱 STATE MACHINE + CORE STRUCTURE
DEATH-001 — Add Life State Enum

Objective: Introduce canonical life states

Add to character:

ALIVE
DEAD
DEPARTED

Requirements:

Stored on character.db.life_state
Default = ALIVE
DEATH-002 — Add is_alive() Helper

Objective: Standardize checks

Create method:

def is_alive(self):
    return self.db.life_state == "ALIVE"
DEATH-003 — Block Commands When Dead

Objective: Prevent normal interaction

If DEAD:

Block:
movement
combat
most commands

Allow:

look
say (optional, ghost-style)
depart
DEATH-004 — Hook Death Into Combat System

Objective: Trigger death cleanly

When HP <= 0:

call:
character.at_death()
DEATH-005 — Implement at_death()

Objective: Central death handler

Must:

set life_state = DEAD
stop combat
clear target
trigger corpse creation (next task)
🪦 CORPSE SYSTEM (MINIMAL v1)
DEATH-006 — Create Corpse Object Type

File:

typeclasses/objects/corpse.py

Attributes:

owner_id
owner_name
death_timestamp
DEATH-007 — Spawn Corpse on Death

Objective: Physical death presence

On death:

create corpse in room
link to player
DEATH-008 — Move Inventory to Corpse

Objective: Item separation

On death:

move all inventory → corpse

(leave worn/equipped for later refinement)

DEATH-009 — Move Player to “Ghost State”

Objective: Separate body from player

Options:

either:
leave player in room (non-interactive)
OR move to “death layer” (preferred later)

For now:
👉 keep player in room but flagged DEAD

DEATH-010 — Add Corpse Description

Objective: Immersion + clarity

Example:

The lifeless body of Kier lies here.
⏳ CORPSE TIMER (BASIC)
DEATH-011 — Add Corpse Decay Timer Field

Add:

decay_time = now + X minutes

Do NOT implement decay yet—just store it.

DEATH-012 — Add Corpse Ownership Check

Objective: Security

Method:

corpse.is_owner(player)

Returns True if player owns corpse

🔁 DEPART SYSTEM (CORE LOOP)
DEATH-013 — Create CmdDepart

Command:

depart

Only usable when:

player is DEAD
DEATH-014 — Basic Depart Flow

On use:

remove corpse? (NO, leave for now)
revive player
move to safe location
DEATH-015 — Set Life State to ALIVE on Depart
life_state = ALIVE
DEATH-016 — Restore Minimal Health

On depart:

restore to small % HP (e.g. 30%)
DEATH-017 — Apply Temporary Death Penalty (Stub)

Add:

db.death_sting = True
db.death_sting_end = now + 10 minutes

(No effect yet—just tracking)

DEATH-018 — Messaging System for Death/Depart

Add messaging:

On death:

You have died.

Room:

Kier collapses and goes still.

On depart:

You feel your spirit pulled back into your body.
🧪 EARLY PENALTY STRUCTURE
DEATH-019 — Block Skill Gain While Dead

If DEAD:

no XP gain
no skill checks
DEATH-020 — Add Death Debug Command

Command:

die

Purpose:

force death for testing
✅ END STATE AFTER TASK 020

You now have:

✔ Death trigger
✔ Corpse creation
✔ Inventory drop
✔ Player death state
✔ Depart command
✔ Basic revive
✔ Placeholder penalty system

⚠️ WHAT IS INTENTIONALLY NOT BUILT YET

We are not doing yet:

favors
item retention rules
grave system
corpse decay/destruction
resurrection
empath healing
exp penalty system
Death’s Sting effects (only stubbed)

Those come next.

DEATH SYSTEM — MICROTASKS 021–040 (CONSEQUENCE LAYER)
🎯 PHASE GOAL

At the end of this set:

👉 Death becomes a resource-managed decision
👉 Players choose recovery quality
👉 Corpses become time-sensitive
👉 Penalties become mechanically real

🟡 FAVOR SYSTEM (FOUNDATION)
DEATH-021 — Add Favor Attribute

Add to character:

db.favors = 0

Also add:

db.max_favors = 20  # initial cap (tunable later)
DEATH-022 — Add Favor Getter/Setter Helpers

Methods:

def get_favors(self):
    return self.db.favors or 0

def add_favors(self, amount):
    self.db.favors = min(self.get_favors() + amount, self.db.max_favors)

def spend_favors(self, amount):
    if self.get_favors() >= amount:
        self.db.favors -= amount
        return True
    return False
DEATH-023 — Add Favor Debug Command

Command:

favor <amount>

Purpose:

grant/remove favors for testing
DEATH-024 — Display Favors in Score/Stats

Update existing stats output:

Favors: X / max
🔁 DEPART SYSTEM — MODES
DEATH-025 — Expand CmdDepart Syntax

Support:

depart
depart grave
depart items
depart full
DEATH-026 — Define Favor Costs

Hardcode (for now):

Mode	Cost
grave	1
items	2
full	3
DEATH-027 — Auto-Select Default Depart Mode

If player types just depart:

3+ favors → full
2 favors → items
1 or less → grave
DEATH-028 — Implement Favor Deduction on Depart

On successful depart:

spend_favors(cost)

If not enough favors:

downgrade mode automatically
DEATH-029 — Implement Item Retention Logic

On depart:

grave:
items stay on corpse
items:
return inventory to player
full:
return inventory
(coins later)
DEATH-030 — Add Depart Messaging Per Mode

Examples:

You claw your way back to life, leaving your possessions behind.
You return to life, your belongings restored to you.
🪦 CORPSE → GRAVE TRANSITION
DEATH-031 — Add Corpse Decay Timer Logic

Now activate decay:

after X minutes (start with 10–15):
corpse transforms into grave
DEATH-032 — Create Grave Object Type

File:

typeclasses/objects/grave.py

Attributes:

owner_id
stored_items
creation_time
DEATH-033 — Convert Corpse → Grave on Expiry

On decay:

delete corpse
create grave
move items into grave container
DEATH-034 — Hide Grave From Other Players (Basic)

Only visible to:

owner

(permissions later expanded)

DEATH-035 — Add CmdRecover (from Grave)

Command:

recover

Requirements:

must be owner
must be in same room

Effect:

transfer items → player
delete grave
⚡ DEATH’S STING — REAL IMPLEMENTATION
DEATH-036 — Define Death’s Sting Variables

On character:

db.death_sting_active = True/False
db.death_sting_end = timestamp
db.death_sting_severity = float (0.1–0.2)
DEATH-037 — Calculate Sting Based on Favors

Formula (simple v1):

base = 0.20
reduction = min(favors, 20) * 0.005
severity = max(0.10, base - reduction)
DEATH-038 — Apply Sting to Combat Calculations

Hook into combat system:

reduce:
hit chance
evasion
damage

Example:

effective_skill *= (1 - severity)
DEATH-039 — Add Sting Timer Processing

Each tick/pulse:

check if expired
if expired:
remove sting
message player
DEATH-040 — Add Sting Status Command

Command:

death

Output:

You are suffering from Death's Sting.
Severity: Moderate
Time remaining: 8 minutes
✅ END STATE AFTER TASK 040

You now have:

✔ Favor system (resource loop started)
✔ Multiple recovery paths
✔ Item loss vs retention decisions
✔ Corpse → grave lifecycle
✔ Recover command
✔ Real combat penalty (Death’s Sting)

⚠️ WHAT STILL ISN’T BUILT (ON PURPOSE)

We are still holding back:

resurrection (Cleric system)
empath corpse preparation
exp debt system
grave decay/damage
coin handling
consent/permissions for others
anti-griefing protections
🧠 DESIGN CHECKPOINT

At this stage your system now has:

👉 Preparation loop (favors)
👉 Risk (death)
👉 Choice (depart mode)
👉 Consequence (item loss + sting)
👉 Recovery loop (corpse/grave)

This is now structurally aligned with DR.

DEATH SYSTEM — MICROTASKS 041–060 (SYSTEM INTEGRATION LAYER)
🎯 PHASE GOAL

At the end of this block:

👉 Death impacts progression (XP efficiency)
👉 Corpses have condition states
👉 Resurrection becomes a superior path
👉 Support professions have mechanical hooks
👉 Repeated deaths escalate consequences

🧠 EXP DEBT SYSTEM (CORE PROGRESSION PENALTY)
DEATH-041 — Add Experience Debt Attribute

On character:

db.exp_debt = 0
DEATH-042 — Capture Field Experience on Death

On death:

calculate current field exp (unabsorbed)

Store:

db.exp_debt += current_field_exp
DEATH-043 — Clear Field Experience on Death

After capture:

clear field exp pool
DEATH-044 — Apply XP Gain Penalty While in Debt

Hook into XP gain system:

If:

db.exp_debt > 0

Then:

xp_gain *= 0.5

(50% reduction like DR)

DEATH-045 — Reduce Debt Over Time

Each time XP is gained:

debt_reduction = xp_gained
db.exp_debt -= debt_reduction

Clamp at 0.

DEATH-046 — Display Debt in Stats

Add to stats:

Experience Debt: X
DEATH-047 — Add Messaging for Debt State

Examples:

You feel your recent death weighing on your progress.
You feel your mind clearing as your experience debt fades.
🪦 CORPSE CONDITION SYSTEM
DEATH-048 — Add Corpse Condition Attribute

On corpse:

db.condition = 0–100

On creation:

condition = 100
DEATH-049 — Add Condition Decay Over Time

Every tick:

condition -= decay_rate

Start simple:

e.g. 1 per minute
DEATH-050 — Add Condition Tiers

Define:

Condition	State
75–100	Fresh
50–74	Degrading
25–49	Damaged
0–24	Ruined
DEATH-051 — Reflect Condition in Description

Example:

The body shows signs of decay.
✝️ RESURRECTION PIPELINE (CORE)
DEATH-052 — Add Resurrection Command (Stub)

Command:

resurrect <target>

Requirements:

target must be corpse

(No gating yet—this is a system hook)

DEATH-053 — Validate Resurrection Eligibility

Check:

corpse exists
corpse has owner
owner is still dead
DEATH-054 — Restore Player From Corpse

On success:

move player to corpse location
set ALIVE
delete corpse
DEATH-055 — Reduce Death’s Sting on Resurrection

Instead of full sting:

severity *= 0.5
duration *= 0.5
DEATH-056 — Restore Partial Experience Based on Condition

Formula:

restore_percent = corpse.condition / 100
restored_exp = exp_debt * restore_percent

Then:

exp_debt -= restored_exp
🩸 EMPATH HOOKS (PRE-RES SUPPORT)
DEATH-057 — Add Stabilize Command (Empath Hook)

Command:

stabilize <corpse>

Effect:

corpse.condition += X (cap at 100)
DEATH-058 — Prevent Further Decay if Stabilized

Add:

db.stabilized = True

If stabilized:

slow or pause decay
DEATH-059 — Add Messaging for Stabilization
You carefully tend to the corpse, slowing its decay.
☠️ MULTI-DEATH ESCALATION
DEATH-060 — Stack Death Penalties

If player dies while:

has exp_debt OR
has active death_sting

Then:

increase:
exp_debt multiplier (e.g. +25%)
sting severity +2–5%
✅ END STATE AFTER TASK 060

You now have:

✔ EXP debt replacing rank loss
✔ XP penalty loop
✔ Corpse condition system
✔ Resurrection pipeline (functional)
✔ Empath pre-support system
✔ Multi-death escalation

⚠️ WHAT’S STILL MISSING (FINAL LAYER)

We are now very close to full DR parity, but still missing:

favor requirement for resurrection (critical)
resurrection spell tiers (cleric depth)
grave item damage system
coin loss system
consent / permission systems
anti-abuse safeguards
resurrection location logic (shrines, altars)
🧠 DESIGN CHECKPOINT (IMPORTANT)

At this point your system now enforces:

👉 Preparation (favors)
👉 Risk (death)
👉 Recovery strategy (depart vs rescue)
👉 Social dependency (empath + cleric)
👉 Progression impact (XP debt)
👉 Escalation (multi-death stacking)

This is structurally equivalent to DragonRealms.

DEATH SYSTEM — MICROTASKS 061–080 (PRODUCTION LAYER)
🎯 PHASE GOAL

At the end of this block:

👉 Resurrection requires favors
👉 Cleric-style recovery has depth
👉 Graves become a real recovery loop
👉 Death is harder to abuse or grief
👉 New players are protected from brutal onboarding failures

🟡 FAVOR GATING + RESURRECTION RULES
DEATH-061 — Require Minimum Favor for Resurrection

Add resurrection validation rule:

player must have at least 1 favor
if not:
resurrection fails
corpse remains

Message:

Your spirit cannot be called back. You lack the favor required.
DEATH-062 — Consume Favor on Successful Resurrection

On successful resurrection:

spend 1 favor

This should occur only after full validation succeeds.

DEATH-063 — Add Resurrection Failure Messaging

Create explicit messages for:

no favors
corpse too damaged
target already alive
invalid corpse owner link

This prevents silent failure and helps debugging.

DEATH-064 — Add Favor Threshold Bonuses to Resurrection

Add basic scaling:

1–9 favors → weak recovery
10–24 favors → moderate recovery
25+ favors → strong recovery

Effects may improve:

exp debt restoration
death sting reduction
post-resurrection HP %
✝️ CLERIC RECOVERY DEPTH
DEATH-065 — Add Rejuvenate Command

Command:

rejuvenate <corpse>

Effect:

improves corpse condition
increases later resurrection outcome

This is distinct from stabilize:

stabilize = preserve
rejuvenate = improve
DEATH-066 — Cap Rejuvenation by Skill Check Hook

Do not hardcode profession power yet.

Add hook:

get_rejuvenation_strength(actor, corpse)

Return value determines condition gain.

This lets Aedan tie it into Cleric skill/spell systems later without rewrite.

DEATH-067 — Add Uncurse Command

Command:

uncurse <target>

Effect:

reduces active Death’s Sting duration and/or severity

Do not fully remove by default yet.

DEATH-068 — Add Uncurse Scaling Hook

Add helper:

reduce_death_sting(target, power)

This allows future Cleric spell scaling.

Example:

low power → reduce duration
medium power → reduce duration + severity
high power → fully clear sting
DEATH-069 — Track Recovery Source Metadata

On revival, store:

db.last_recovery_type = "depart" | "resurrection"
db.last_recovery_helper = <name/id>
db.last_recovery_time = timestamp

Useful for:

analytics
debugging
future achievements / social rewards
🪦 GRAVE + ITEM CONSEQUENCE LAYER
DEATH-070 — Add Stored Coin Field to Corpse/Grave

On death:

separate carried currency from inventory items

Store:

db.stored_coins = amount
DEATH-071 — Implement Coin Retention by Depart Mode

On depart:

grave → coins remain with grave
items → items return, coins remain
full → items and coins return

This completes the recovery-mode decision loop.

DEATH-072 — Add Grave Coin Recovery

Update recover command so it restores:

stored items
stored coins

Then deletes grave.

DEATH-073 — Add Grave Item Damage Field

Each item placed in grave gets metadata:

grave_damage = 0

Do not apply actual durability loss yet—track first.

DEATH-074 — Increase Grave Damage Over Time

Every grave interval:

increment grave_damage on stored items

Example:

+1% every 2 hours
capped at a configurable maximum
DEATH-075 — Apply Damage on Recovery Hook

When recovering grave items:

call item hook:
item.at_grave_recovery(grave_damage)

This allows future equipment durability systems to integrate cleanly.

🔐 CONSENT + PERMISSION RULES
DEATH-076 — Add Corpse/Grave Access Permissions

Add permission structure:

db.recovery_allowed = [owner_id]

Only allowed characters can:

view grave
recover contents
use corpse actions if required
DEATH-077 — Add Consent Command

Command:

consent <player>
withdraw consent <player>

Allows owner to designate who may assist with corpse/grave recovery.

This should work while alive and while dead if ghost interaction is allowed.

DEATH-078 — Restrict Non-Owner Recovery Interaction

Enforce:

non-owner cannot recover
non-consented user cannot manipulate grave contents
optional: non-consented user cannot even see grave details
🛡️ ANTI-GRIEF + NEW PLAYER PROTECTION
DEATH-079 — Add New Player Death Protection Flag

Add:

db.death_protection = True

Initial behavior while active:

reduced or no exp debt
reduced sting
first few deaths auto-upgrade depart outcome

This should be removable later by:

circle threshold
time played
quest milestone
DEATH-080 — Add Death Protection Resolver

Create helper:

get_death_protection_state(character)

This centralizes all safety logic.

Use it to modify:

exp debt
sting severity
depart favor cost
item/coin retention rules
✅ END STATE AFTER TASK 080

You now have a death system with:

✔ life/death state machine
✔ corpse creation and decay
✔ grave transition and recovery
✔ favors
✔ depart modes
✔ Death’s Sting
✔ exp debt
✔ stabilization and rejuvenation hooks
✔ resurrection pipeline
✔ coin/item consequence logic
✔ consent and recovery permissions
✔ newbie protection