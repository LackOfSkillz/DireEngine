STATUS UPDATE - March 30, 2026

Implementation status: the prior death/favor work already covers the core death pipeline, corpse handling, Favor snapshots, depart branching, rejuvenation, resurrection, and consented corpse access described in the early cleric tasks. The cleric implementation now covers six shipped passes: first, persistent devotion, ritual-based `pray` support for clerics, devotion drift toward baseline, `commune` with first effects (`solace`, `ward`, `vigil`), a cleric profession subsystem resource for devotion, devotion-aware resurrection costs and failure pressure, and a locked `selfreturn` placeholder; second, corpse-focused cleric rites through `perceive <corpse>`, `preserve <corpse>`, and cleric `prepare <corpse>`, a corpse memory timer parallel to decay, preparation/preservation stacks that affect resurrection outcomes, a functional Theurgy training loop tied to rituals, communes, corpse rites, and resurrection, and devotion-based scaling for cleric spell preparation stability and spell power; third, an explicit soul-state layer with per-death soul strength, active soul decay on dead characters, recoverability loss when the soul fails, cleric `sense soul`, soul-aware resurrection gating, and live validation of the proper-resurrection / low-favor / no-favor-depart / soul-lost branches; fourth, imperfect resurrection quality tiers (`perfect`, `stable`, `fragile`, `flawed`), temporary post-resurrection penalties for weak returns, failure-driven soul/body degradation, and irrecoverable corpse handling that forces depart once the body can no longer sustain life; fifth, the first death-polish UX slice with richer corpse descriptions, randomized delayed death room emotes, ghost-state messaging, a persistent dead banner, improved Death's Sting labels and expiry text, expanded `death` output, a dedicated `corpse` command, and preview/confirmation flow on `depart`; sixth, the final death-polish and world-integration slice with admin death tools, region-aware recovery points, no-resurrection and dangerous/safe room flags, grave expiry and warnings, consent listing and expiration, anti-duplication/orphan cleanup protections, event hooks, and death analytics counters.

Validated live behavior now includes cleric devotion gain and ritual cooldowns, commune-based attunement recovery and warding, vigil-based corpse stabilization/condition improvement when consent allows corpse work, devotion drift on the global status tick, corpse perception output, memory extension through preserve, corpse preparation stacking, Theurgy XP gain through cleric actions, devotion-sensitive spell power differences, low-devotion resurrection blocking, active soul sensing output, no-favor resurrection rejection with depart fallback, soul-lost resurrection rejection, perfect and flawed resurrection outcomes with different penalties, failed rites that can render a body irrecoverable, consent listing, dead-state status output, corpse inspection, depart preview/confirmation flow, recovery-point depart routing, and no-resurrection zone blocking. Admin destructive-command validation is implemented and statically clean; external harness validation against the live SQLite server remained partially constrained by database locking.

Executive summary

DragonRealms Clerics are not “holy empaths.” Their core identity is divine mediation: they build devotion through rituals, spend it through communes, and use that divine standing to protect memory, find souls, and perform resurrection. The death system is built around a three-part chain: corpse condition, soul recoverability, and favor availability. Empaths handle the body before death and prepare corpses for return; Clerics handle memory protection, soul retrieval, and resurrection after death.

The most important distinction: favor is not devotion

There are two different “religious currencies” in DR, and keeping them separate is crucial.

Favors are a player-wide death-protection resource. They are gained through favor orbs and sacrificing unabsorbed experience, and they are mostly used to support DEPART and make resurrection possible. A character must have at least one favor to be resurrected by a Cleric, though Elanthipedia explicitly says 15 favors is the recommended minimum because more favors make resurrection easier and quicker. Favors are also consumed by departing, and certain departure modes require enough favors.

Devotion is specifically a Cleric resource. It represents the Cleric’s direct connection to the gods, is sustained by Cleric rituals, slowly drifts back toward neutral over time, and powers Communes. Devotion also affects Cleric spells including Benediction, Shield of Light, Resurrection, and Murrula’s Flames, and low devotion can disrupt or weaken them.

That distinction matters for your game design. In DR terms, the dead player brings the favor requirement; the Cleric brings the devotional fitness to perform the rite.

What Clerics actually are in DragonRealms

The Cleric profession page frames Clerics as the “primary conduit between mortals and the gods,” with magical strength tied to how faithfully they maintain divine favor through ritual practice. Their unique class play is built around rituals, communes, devotion management, and holy mediation, not around generic healing.

Their guild-specific skill is Theurgy, which is trained by a cycle Elanthipedia describes very clearly: rituals fill the devotion bucket, communes empty it, and that cycle trains the skill. Theurgy then affects commune cooldown, potency, or duration, and also speeds up Murrula’s Flames while helping with some advanced Cleric systems.

So the DR Cleric loop is not “cast holy spells in combat.” It is:

perform rituals to build devotion
spend devotion through communes and divine acts
maintain devotional state so major divine magic remains strong
use that spiritual standing for resurrection, memory protection, undead-facing utility, and other holy functions.
The death system in DragonRealms

The DR death system is more layered than a simple “HP reaches zero” rule. The death page notes characters can die from vitality loss, spirit loss, or sufficiently critical bodily damage, and death is no longer permanent. The key design point is that death branches depending on how you died and what resources are available afterward.

Branch 1: ordinary death with a recoverable soul

If the corpse has at least one favor, an Empath can heal the corpse until it can sustain life, and then a Cleric can find the soul in the spirit realm and return it with Soul Bonding and Resurrection. This route preserves some field experience, may preserve a temporarily memorized spell scroll, and avoids Death’s Sting.

Branch 2: death without enough favor

If the corpse has no favor, there is “nothing to guide a cleric to your soul,” making resurrection impossible. In that case the player must DEPART, with the usual penalties.

Branch 3: spirit death

If you die from spirit loss, the spirit is too weak for a Cleric to find, so resurrection is off the table; the only option is DEPART, though a Cleric can still protect memories.

That gives you a very important design lesson: DR death is not binary. It asks:

Is the corpse still viable?
Is the soul still reachable?
Does the dead player have favor?
Can the Cleric protect memory in time?
Empath and Cleric are intentionally separate in the death pipeline

This is one of the cleanest class boundaries in DR.

The death page explicitly says an Empath can heal the corpse until it can sustain life, while a Cleric finds and returns the soul through soul work and resurrection. Clerics can also use Rejuvenation to protect memories from decay while the body is waiting.

That means the actual survival chain is:

before death: Empath triage and stabilization
after death, before decay: Empath restores bodily viability, Cleric preserves memory
after that: Cleric performs soul recovery and resurrection.

For your game, that separation is absolutely worth preserving.

How resurrection actually works in DR

Resurrection is not a one-click revive. The Elanthipedia resurrection page describes a multi-step process.

A Cleric first perceives the body and checks that the corpse has at least one favor. If decay is becoming urgent, the Cleric may cast Vigil. The body is then prepared by repeatedly casting Rejuvenation until it has a “silver nimbus.” After that the Cleric prepares and casts Resurrection, then harnesses and infuses mana into the rite. The amount of mana required depends on the target’s circle and number of favors, ranging from roughly 60 to over 1000 mana.

That is hugely important for your design. In DR, resurrection is:

ritualized
time-sensitive
resource-intensive
easier when the dead player maintained favors.

It is not just “Cleric reaches corpse and presses rez.”

Corpse decay and memory protection

The resurrection page gives staged decay messaging ranging from “about a half hour” down to “about a minute,” and visible corpse deterioration messages escalate as the body worsens. Meanwhile, Rejuvenation protects memories from decaying and can even be refreshed. A dead Cleric with Infusion can also infuse memory on themselves at the cost of spirit.

This means DR actually has two timers after death:

body viability / decay
memory decay / skill loss protection.

That dual-timer structure is one of the strongest pieces you could borrow.

Death’s Sting and depart

If a player cannot or does not get resurrected, they DEPART. DR’s death page notes that resurrection avoids Death’s Sting, while departing can involve stronger penalties. The depart command also has multiple modes depending on favor, and special systems like Glyph of Warding can alter the cost. New characters get a limited number of favor-free safe departs early on.

From a design standpoint, that means DR treats resurrection as the preferred social recovery path, while depart is the fallback solo recovery path with worse consequences.

The favor system in more detail

Favors are awarded as blessings from the Immortals after players obtain an orb and fill it by sacrificing unabsorbed experience. The more favors or circles you already have, the more experience the next favor costs; Elanthipedia even says one circle is mechanically equivalent to one extra favor for cost scaling. Favors are mostly about insulating a character from death consequences and enabling better departure or resurrection options.

Important operational facts:

minimum of 1 favor to be resurrected
15 favors is the recommended baseline
favors are consumed on DEPART
favors are also consumed when a Cleric self-resurrects with Murrula’s Flames
being sacrificed drains all favors and blocks resurrection.

This is a beautifully elegant design lever. Favor does three jobs at once:

it creates pre-death preparation behavior
it makes death recovery partially the dead player’s responsibility
it makes resurrection a cooperative act rather than a fully one-sided Cleric burden.
Devotion, rituals, communes, and why Clerics are not just corpse technicians

Clerics in DR are not defined only by resurrection. Their broader class engine is ritual → devotion → commune. The Cleric page says Clerics use COMMUNE in times of need, spending favor earned through devotion; the Devotion page clarifies that devotion is sustained by rituals and drifts over time, while the Theurgy page explains the training loop: rituals fill the devotion pool, communes spend it.

This is one of the most important findings in the whole dive: the DR Cleric is fundamentally a maintenance profession in spiritual terms. They have to keep up their rituals and relationship with the divine or their power decays. That gives them a strong noncombat identity and prevents resurrection from feeling like a free, always-ready service.

Murrula’s Flames and self-resurrection

DR also has Murrula’s Flames, a ritual spell that enables self-resurrection. It requires a ritual focus, may preserve some field experience and possibly a memorized spell scroll, and consumes a favor when used. It also interacts with Theurgy and has some bodily downside afterward, such as the full-body skin rash mentioned on the spell page.

This matters because it shows Clerics are not merely “rez others” support bots. They also occupy the profession space of personal divine defiance of death, but that power is still ritualized and not free.

What DR Cleric is really about in design terms

If I compress the profession to its design essence, it is:

Cleric = Devotion maintenance + divine petition + soul custody + memory protection + resurrection.

That is a different fantasy from:

Empath: body, pain, triage
Paladin: sanctified martial soul
Warrior: physical dominance
Ranger: environmental bond.
The most important implementation lessons for your game

If you want to capture the DR feel instead of just copying nouns, these are the critical lessons.

First, keep favor and Cleric devotion separate. One belongs to the dead player; the other belongs to the Cleric. DR’s structure depends on that split.

Second, resurrection should be a ritual pipeline, not a button. The DR process is body prep, memory protection, soul retrieval, and mana investment.

Third, death should branch by cause of death and resource state. Spirit death behaving differently from ordinary death is especially valuable because it gives you a way to make some deaths harder or impossible to reverse.

Fourth, corpse decay and memory decay should be distinct but related. That creates urgency and makes Clerics matter even before the final resurrection step.

Fifth, Clerics need a real daily/ongoing religious maintenance loop. DR gets that from rituals, devotion drift, communes, and Theurgy. Without that, a Cleric becomes just a rez vendor.

My recommendation for your build

For your game, the DR-faithful foundation would be:

Death system

critical death state
corpse object with decay timer
memory-loss timer
spirit-death branch
depart fallback.

Favor system

player-earned through sacrifice/preparation
required minimum for resurrection
more favor = easier / safer resurrection
consumed on fallback death recovery.

Cleric system

devotion meter
rituals to build devotion
communes to spend devotion
resurrection gated by devotional health
memory protection as a separate tool
self-resurrection as later/high-tier content.

Empath/Cleric split

Empath restores bodily viability
Cleric restores soul / memory / return to life.
Final assessment

The single biggest takeaway is this:

In DragonRealms, death is not solved by the Cleric alone. It is a cooperative system where the dead player’s prior preparation through favor, the Empath’s work on the body, and the Cleric’s devotional and ritual capacity over soul and memory all matter
Core Systems (NON-NEGOTIABLE)
Devotion (resource)
Ritual system (build devotion)
Commune system (spend devotion)
Resurrection pipeline
Memory protection
Favor interaction
Major Ability Domains
1. Rituals
daily / repeatable actions
build devotion
slow, non-combat loop
2. Communes
instant divine effects
consume devotion
“active power” layer
3. Spells
buffs (protection, light, etc.)
anti-undead
utility
4. Resurrection Suite
perceive corpse
protect memory
restore body/soul
5. Self-Resurrection (late game)
Murrula’s Flames equivalent

ART 1 — DEATH PIPELINE (CORE SYSTEM)
🥇 CLERIC 001 — Define Death Trigger
When:
vitality <= 0

→ character enters:

state = "critical"
🥇 CLERIC 002 — Critical State (NOT DEAD YET)
Player:
cannot act normally
can be stabilized
🥇 CLERIC 003 — Critical Messaging

You are on the brink of death.

🥇 CLERIC 004 — Bleed-Out Timer
Start timer (e.g. 30–60 seconds)
During:
wounds worsen
🥇 CLERIC 005 — Stabilize Hook (Empath Integration)
If:
stabilize used

→ stop bleed-out timer

👉 ties Empath into death pipeline

🥇 CLERIC 006 — Death Transition

If not stabilized:

state = "dead"
spawn:
corpse object
player becomes:
soul state
🥇 CLERIC 007 — Corpse Object Creation

Corpse stores:

corpse = {
    owner_id,
    decay_timer,
    favor_count,
    wound_state_snapshot
}
🥇 CLERIC 008 — Soul State System

Player becomes:

state = "soul"
cannot interact normally
limited perception (later expansion)
🥇 CLERIC 009 — Death Messaging

You feel yourself slip free of your body.

Room:

Gary collapses, lifeless.

🥇 CLERIC 010 — Corpse Decay Timer
Start decay (e.g. 5–10 minutes)
progressively worsens resurrection difficulty
🟡 PART 2 — FAVOR SYSTEM (PLAYER RESPONSIBILITY)
🥇 CLERIC 011 — Add Favor Attribute

To ALL characters:

favor = 0+
🥇 CLERIC 012 — Favor Requirement Check
Corpse must have:
favor >= 1

👉 or resurrection is impossible

🥇 CLERIC 013 — Favor Display

Add to stats:

Favor: 7

🥇 CLERIC 014 — Favor Consumption Hook (Future)
Placeholder:
on_depart:
    favor -= 1
🥇 CLERIC 015 — Favor Stored on Corpse
Snapshot favor at death
corpse uses this value
🟢 PART 3 — CLERIC PROFESSION ENTRY
🥇 CLERIC 016 — Create Cleric Profession Flag
Add "cleric" to profession system
🥇 CLERIC 017 — Create Cleric Guild
Join logic
Output:

You are now recognized as a Cleric.

🥇 CLERIC 018 — Devotion System Scaffold

Add to character:

devotion = 0–100

👉 this powers ALL cleric abilities later

🥇 CLERIC 019 — Add Command: “Pray” (FIRST RITUAL)

Command:

pray

Effect:

increases devotion slowly
🥇 CLERIC 020 — Pray Messaging

You offer a quiet prayer, strengthening your connection.

🧭 What You Now Have (After 20)

This is HUGE:

💀 Death System Exists
critical → bleedout → death → corpse → soul
🧍 Empath Integration Point Exists
stabilize can save before death
🪦 Corpse System Exists
decay timer
favor snapshot
⭐ Favor System Exists
resurrection gate
⛪ Cleric Has Begun
devotion introduced
ritual loop started
⚠️ Critical Design Notes

Do NOT:

allow instant resurrection yet
bypass favor requirement
skip corpse decay

👉 These are what make death meaningful

🔥 What Comes Next (021–040)

Now we build:

Resurrection pipeline (core Cleric identity)
Corpse preparation
Memory protection
Failure states
The Resurrection Pipeline (DR-authentic, multi-step, failure-aware)

This is the difference between:

“revive button”
and
a ritual that matters
🧱 DEATH + CLERIC MICRO TASKS (021–040)

Phase: Resurrection Core + Corpse Preparation + Memory Protection

🟣 PART 1 — CORPSE INTERACTION (CLERIC ENTRY POINT)
🥇 CLERIC 021 — Add Command: “Perceive Corpse”

Command:

perceive corpse
target corpse object
🥇 CLERIC 022 — Perceive Output

Displays:

The body is intact.
Favor: Present
Condition: Stable / Fading / Critical

👉 gives cleric decision data

🥇 CLERIC 023 — Corpse Condition States

Define:

INTACT
FADING
CRITICAL
DECAYING
based on decay timer
🥇 CLERIC 024 — Resurrection Viability Check
If:
condition too low OR
favor == 0
→ resurrection fails
🟡 PART 2 — MEMORY PROTECTION (CRITICAL DR SYSTEM)
🥇 CLERIC 025 — Add Command: “Preserve”

Command:

preserve <corpse>
🥇 CLERIC 026 — Preserve Effect
slows:
memory decay timer
extends resurrection window
🥇 CLERIC 027 — Memory Timer System

Add to corpse:

memory_timer
runs parallel to decay
🥇 CLERIC 028 — Memory Loss Consequence (HOOK)

If timer expires:

player suffers:
XP loss (later integration)
skill penalty (placeholder)
🥇 CLERIC 029 — Preserve Messaging

You shield the lingering memories from fading.

🟢 PART 3 — CORPSE PREPARATION (BODY READY)
🥇 CLERIC 030 — Add Command: “Prepare”

Command:

prepare corpse
🥇 CLERIC 031 — Prepare Effect
improves corpse condition:
boosts resurrection success chance
🥇 CLERIC 032 — Preparation Stacking
multiple prepares:
improve quality incrementally

👉 mimics DR “rejuvenation loop”

🥇 CLERIC 033 — Prepare Messaging

You restore coherence to the body.

🔵 PART 4 — RESURRECTION (CORE IDENTITY)
🥇 CLERIC 034 — Add Command: “Resurrect”

Command:

resurrect <corpse>
🥇 CLERIC 035 — Resurrection Requirements
Must have:
favor ≥ 1
corpse condition ≥ threshold
sufficient devotion
🥇 CLERIC 036 — Devotion Cost
resurrection consumes:
devotion -= value

👉 stronger cleric = more reliable

🥇 CLERIC 037 — Resurrection Success Calculation

Based on:

devotion level
corpse condition
time since death
🥇 CLERIC 038 — Resurrection Success Outcome

If success:

player returns to body
reduced wounds (not full heal)
🥇 CLERIC 039 — Resurrection Failure Outcome

If fail:

The connection falters.

corpse condition worsens
must retry or abandon
🥇 CLERIC 040 — Resurrection Messaging

Success:

Life returns as the soul finds its way back.

Room:

Gary stirs, breath returning.

🧭 What You Now Have

After 40 tasks:

💀 Full Death Pipeline
critical → death → corpse → soul
⭐ Favor Integration
resurrection gate enforced
⛪ Cleric Identity Core
perceive → preserve → prepare → resurrect
🧠 Memory System Exists
second timer (VERY important)
⚠️ Failure Exists
resurrection is NOT guaranteed
🔥 What Comes Next (041–060)

Now we add:

Soul interaction (Cleric finds soul, not just body)
Partial resurrection outcomes
Death penalties (properly scoped)
Depart system (fallback path)
⚠️ Critical Design Insight

Right now, your system has:

urgency + dependency + consequence

That is what DR gets right.

DEATH + CLERIC MICRO TASKS (041–060)

Phase: Soul System + Favor Depth + Depart (Fallback Path)

🟣 PART 1 — SOUL SYSTEM (CRITICAL)
🥇 CLERIC 041 — Soul State Data Expansion

When player dies:

soul = {
    "owner_id",
    "strength": 0–100,
    "location": "spirit_plane",
    "recoverable": True/False
}
🥇 CLERIC 042 — Soul Strength Initialization
Based on:
cause of death
recent damage
Example:
clean death → higher strength
catastrophic death → lower
🥇 CLERIC 043 — Soul Strength Decay
Over time:
soul["strength"] -= rate

👉 creates urgency beyond corpse decay

🥇 CLERIC 044 — Soul Loss Condition

If:

soul["strength"] <= 0

→

recoverable = False

👉 resurrection no longer possible

🥇 CLERIC 045 — Add Command: “Sense Soul”

Command:

sense soul <corpse>
🥇 CLERIC 046 — Sense Soul Output

The soul is strong / fading / barely present.

🥇 CLERIC 047 — Soul Requirement for Resurrection
Resurrection requires:
soul["recoverable"] == True
🟡 PART 2 — FAVOR SYSTEM (FULL INTEGRATION)
🥇 CLERIC 048 — Favor Affects Soul Strength
On death:
soul_strength += favor_bonus

👉 more favor = more time to recover

🥇 CLERIC 049 — Favor Affects Resurrection Difficulty
Higher favor:
increases success chance
reduces devotion cost
🥇 CLERIC 050 — Favor Threshold Tiers
Favor	Effect
0	cannot resurrect
1–5	difficult
6–15	normal
16+	easier
🥇 CLERIC 051 — Favor Consumption on Resurrection
On successful resurrection:
favor -= 1
🥇 CLERIC 052 — Favor Feedback Messaging

Your bond to the divine steadies your return.

🥇 CLERIC 053 — Low Favor Warning

When dying:

You feel unprepared for what comes next.

🔵 PART 3 — DEPART SYSTEM (FALLBACK PATH)
🥇 CLERIC 054 — Add Command: “Depart”

Command:

depart
🥇 CLERIC 055 — Depart Requirements
Requires:
favor ≥ 1 OR special condition (later)
🥇 CLERIC 056 — Depart Effect
player:
leaves soul state
respawns at safe location
🥇 CLERIC 057 — Depart Cost
consumes:
favor -= 1
🥇 CLERIC 058 — Depart Penalty
apply:
wound penalty
(future: XP penalty)
🥇 CLERIC 059 — Depart Messaging

You release your hold and return to the world, diminished.

🥇 CLERIC 060 — Full Death Branch Test

Test scenarios:

Scenario A — Proper Resurrection
high favor
strong soul
→ success
Scenario B — Low Favor

→ resurrection difficult or fails

Scenario C — No Favor

→ forced depart

Scenario D — Soul Lost

→ resurrection impossible

🧭 What You Now Have

After 60 tasks:

💀 Death is Fully Systemic
body (corpse)
soul (recoverability)
memory (decay)
favor (player responsibility)
⭐ Favor is Now REAL
affects:
resurrection success
soul durability
fallback options
⛪ Cleric Role is Complete Core
not just “revive”
but:
evaluate
prepare
manage risk
🚪 Fallback Exists
depart is:
worse
but reliable
⚖️ System Interaction (Important)

Now your game has:

Empath → prevents death
Cleric → reverses death
Favor → prepares for death
Depart → accepts death

👉 That’s a complete mortality system

🔥 FINAL PHASE (061–080)

Next we add:

Partial resurrection outcomes
Failure complications
Cleric devotion depth (ritual + commune expansion)
Self-resurrection (late system hook)
⚠️ Critical Design Insight

You now have:

Player responsibility (favor) + Class dependency (cleric)

That’s exactly what makes DR’s system work.

Right now:

Death works
Resurrection works

But it’s still too clean.

We now add:

Imperfect returns + Cleric depth (ritual/commune loop) + edge-case consequences

This is what separates:

a system
from
a world
🧱 DEATH + CLERIC MICRO TASKS (061–080)

Phase: Imperfect Resurrection + Devotion Depth + Cleric Identity Completion

🟣 PART 1 — PARTIAL / IMPERFECT RESURRECTION
🥇 CLERIC 061 — Add Resurrection Quality Result

On success, determine:

res_quality = {
    "perfect",
    "stable",
    "fragile",
    "flawed"
}
🥇 CLERIC 062 — Quality Calculation

Based on:

devotion
favor
corpse condition
soul strength
🥇 CLERIC 063 — Perfect Resurrection
minimal penalties
strong return
🥇 CLERIC 064 — Fragile Resurrection
apply:
temporary vitality cap reduction
increased fatigue
🥇 CLERIC 065 — Flawed Resurrection
apply:
wound carryover
possible temporary debuff:
“disoriented”
“unstable”
🥇 CLERIC 066 — Resurrection Quality Messaging

You return, but something feels off.

🟡 PART 2 — FAILURE CONSEQUENCES
🥇 CLERIC 067 — Failed Resurrection Penalty
On failure:
corpse condition worsens
soul strength drops

👉 repeated failure is dangerous

🥇 CLERIC 068 — Critical Failure Case
If:
corpse condition too low
→ becomes:
irrecoverable = True
🥇 CLERIC 069 — Irrecoverable Messaging

The body can no longer sustain life.

🥇 CLERIC 070 — Forced Depart Path
If irrecoverable:
player must:
depart
🟢 PART 3 — DEVOTION DEPTH (CLERIC CORE LOOP)
🥇 CLERIC 071 — Devotion Drift System
Over time:
devotion → baseline (neutral)

👉 forces maintenance

🥇 CLERIC 072 — Add Ritual Tiering

Expand “pray” into tiers:

pray
ritual focus
ritual devotion
stronger rituals:
more devotion gain
longer cooldown
🥇 CLERIC 073 — Ritual Cooldown System
prevents spam
encourages pacing
🥇 CLERIC 074 — Add Command: “Commune”

Command:

commune <type>
🥇 CLERIC 075 — Commune Effects (FIRST SET)

Examples:

restore small devotion burst (feedback loop)
minor protection buff
corpse stabilization boost

👉 consumes devotion

🥇 CLERIC 076 — Commune Cost
devotion -= value
🥇 CLERIC 077 — Devotion Threshold Effects
Low devotion:
weaker resurrection
higher failure chance
🥇 CLERIC 078 — Devotion Messaging

Your connection feels distant.
The divine answers clearly.

🔵 PART 4 — SELF-RESURRECTION HOOK (LATE SYSTEM)
🥇 CLERIC 079 — Add Placeholder: “Self Return”

Command:

self return
locked behind:
high devotion
favor cost

👉 DO NOT fully implement yet

🥇 CLERIC 080 — Full System Validation

Test:

Scenario A — Clean Resurrection
high devotion + high favor
→ strong return
Scenario B — Weak Cleric

→ fragile/flawed return

Scenario C — Multiple Failures

→ corpse becomes irrecoverable

Scenario D — No Cleric

→ depart required

🧭 FINAL RESULT — DEATH + CLERIC SYSTEM (COMPLETE CORE)

You now have:

💀 Death System (FULL)
critical → bleedout → corpse → soul → decay
⭐ Favor System (MEANINGFUL)
affects:
success
time window
fallback options
⛪ Cleric System (REAL)
devotion loop (ritual ↔ commune)
resurrection pipeline
memory protection
failure handling
⚠️ Imperfection Layer
resurrection not guaranteed
outcomes vary
repeated failure has consequences
🔁 Full Survival Chain
Avoid damage → Warrior / Ranger / Thief
Manage damage → Empath
Reverse death → Cleric
Accept loss → Depart
🧠 Honest Assessment

You now have:

👉 ~95–100% of DR death + cleric system depth

This is:

rare in MUD design
extremely powerful if tuned well

DEATH POLISH A — MICROTASKS 081–100 (UX + IMMERSION)
🎯 GOAL

Make death feel:

clear
weighty
readable
intentional
🪦 CORPSE & DEATH PRESENCE
DEATH-081 — Improve Corpse Descriptions by Condition

Expand corpse descriptions dynamically:

Fresh:

The body lies still, warmth not yet fully gone.

Degrading:

The body shows signs of decay.

Damaged:

The corpse is marred by time and neglect.

Ruined:

The remains are barely recognizable.

DEATH-082 — Add Name + Recognition Variants

If player is known:

The body of Kier lies here.

If not:

The body of a fallen adventurer lies here.

Hook into future reputation system.

DEATH-083 — Add Death Emote Variants

Instead of one message, randomize:

Kier collapses suddenly, life leaving their body.
Kier staggers, then falls motionless.
Kier crumples to the ground.
DEATH-084 — Add Room Silence Beat (Micro Delay)

After death:

delay 0.5–1.5s before room message

This creates a subtle “impact pause.”

👻 PLAYER EXPERIENCE WHILE DEAD
DEATH-085 — Add Ghost-State Messaging

On death:

You feel yourself slipping free from your body.
DEATH-086 — Add “You Are Dead” Persistent Banner

On every prompt or command:

[You are dead. Type DEPART to return.]
DEATH-087 — Add Limited Ghost Interaction Flavor

Optional:

allow:
look
say (whisper-like: “faint echo”)

Example:

Your voice echoes faintly, barely heard.
⚡ DEATH’S STING UX
DEATH-088 — Add Severity Labels

Map severity:

Value	Label
10%	Mild
15%	Moderate
20%	Severe
DEATH-089 — Add Sting Expiry Messaging

On expiration:

You feel the last of death’s grip release you.
DEATH-090 — Add Combat Feedback Under Sting

In combat:

You feel sluggish from your recent death.

(only occasionally—don’t spam)

📊 DEATH STATUS VISIBILITY
DEATH-091 — Expand death Command Output

Show:

state
favors
sting severity + time
exp debt
last recovery type
DEATH-092 — Add “Corpse Status” View

Command:

corpse

Shows:

condition
time until decay
location (if remote tracking enabled later)
🔁 DEPART UX
DEATH-093 — Add Depart Preview Before Execution

When typing depart:

You have 2 favors.

Available options:
- depart grave (cost: 1)
- depart items (cost: 2) [default]

Type DEPART <mode> to choose.
DEATH-094 — Add Confirmation for High-Cost Depart

If using 3 favors:

This will consume 3 favors. Continue? (yes/no)
DEATH-095 — Add Failure Feedback on Invalid Depart

Clear messaging:

no corpse
invalid state
insufficient favors
🧪 DEBUG / ADMIN VISIBILITY
DEATH-096 — Add Admin Death Inspect Command

Command:

@deathinspect <player>

Shows full state:

corpse ID
timers
flags
debt
favors
permissions
DEATH-097 — Add Force Corpse Decay Command
@decaycorpse <corpse>

For testing grave transition.

DEATH-098 — Add Force Resurrection Command
@res <player>

Bypasses all requirements.

🎯 EDGE CASE POLISH
DEATH-099 — Prevent Double Corpse Creation

Ensure:

only one corpse per death event
DEATH-100 — Prevent Ghost Duplication Bugs

Ensure:

no duplicate player instances
no split state between corpse/player
🟥 DEATH POLISH B — MICROTASKS 101–120 (WORLD + LOGIC)
🎯 GOAL

Make death:

spatially consistent
world-aware
systemically fair
🗺️ RECOVERY LOCATION LOGIC
DEATH-101 — Create Recovery Point System

Define:

each region has a recovery location

Examples:

shrine
temple
graveyard
DEATH-102 — Add Nearest Recovery Resolver

Function:

get_nearest_recovery_point(character)
DEATH-103 — Move Departed Player to Recovery Point

On depart:

move to nearest valid recovery node
DEATH-104 — Add Region-Based Recovery Overrides

Some areas:

override default recovery location

Example:

dungeon → outside entrance
city → central temple
⛔ ZONE RULES
DEATH-105 — Add No-Resurrection Zones

Flag rooms:

no_resurrection = True

Blocks resurrection attempts.

DEATH-106 — Add Dangerous Zone Flags

Zones that:

increase corpse decay rate
increase grave damage
DEATH-107 — Add Safe Zone Flags

Zones that:

slow decay
reduce penalties
🪦 GRAVE WORLD INTEGRATION
DEATH-108 — Add Grave Description Variants by Location

Example:

Forest:

A shallow grave marked by disturbed earth.

City:

A small marker stone stands over a fresh grave.
DEATH-109 — Add Grave Persistence Timer

After X hours:

grave disappears permanently
DEATH-110 — Add Warning Before Grave Expiry

Message player:

You feel your connection to your lost possessions fading.
🔐 CONSENT + SOCIAL SYSTEM
DEATH-111 — Show Consent List

Command:

consent

Displays allowed players.

DEATH-112 — Notify on Consent Use

If someone interacts:

Merril begins assisting with your remains.
DEATH-113 — Add Consent Expiration Option

Optional:

consent expires after time or logout
⚖️ ANTI-ABUSE LOGIC
DEATH-114 — Prevent Corpse Blocking

Ensure corpses:

don’t block exits
don’t prevent movement
DEATH-115 — Prevent Infinite Grave Hoarding

Limit:

1 active grave per player
DEATH-116 — Auto-Cleanup Orphaned Corpses

If:

player deleted / invalid
→ remove corpse
DEATH-117 — Prevent Combat on Corpses

No attacking corpses (unless future necro systems)

🧠 SYSTEM INTEGRATION HOOKS
DEATH-118 — Add Event Hooks

Fire events:

on_character_death
on_depart
on_resurrection
on_grave_created
on_grave_recovered
DEATH-119 — Add Logging for Death Events

Log:

cause of death
location
recovery type
time to recover
DEATH-120 — Add Analytics Counters

Track:

deaths per player
avg recovery time
favor usage
% of resurrection vs depart
✅ FINAL STATE AFTER POLISH A + B

You now have:

✔ Full DR-style death system
✔ Strong UX feedback
✔ Clear player decision points
✔ Spatial/world integration
✔ Anti-grief protections
✔ Admin/debug tooling
✔ Analytics hooks

🧠 HONEST ASSESSMENT

At this point:

👉 Your death system is more structured than stock DragonRealms
👉 And cleaner for modern implementation

You avoided:

opaque mechanics
hidden penalties
inconsistent recovery

