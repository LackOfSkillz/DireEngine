You’ve already locked that professions belong after the skill framework/progression layer and inside the identity layer in your roadmap, so this is the point where research needs to turn into a build plan, not class-fantasy brainstorming. Your current blueprint is here: DireMud blueprint.

The most important thing DragonRealms gets right is that “profession” is not just a class with spells. It is a package of four things: a skillset priority profile, circle requirements, one or more signature subsystems, and guild-only abilities. Officially, DR skills are grouped into five skillsets—Armor, Weapons, Lore, Survival, and Magic—and guild placement in those skillsets changes learning speed and advancement pressure. Players start as Commoners and then join one of eleven active guilds.

So the key design takeaway for DireMUD is this:

Do not build professions as isolated talent trees.

Build them as:

skill weighting,
progression gates,
signature resource/subsystem,
profession-only verbs/abilities,
world hooks.

That is the DR pattern in its useful form.

DragonRealms profession roster and what each one actually is

Barbarian is the weapon-primary, anti-magic martial guild. Its skillset profile is Weapon primary, Armor/Survival secondary, Lore/Magic tertiary. Its signature subsystem is Inner Fire, with ability families like berserks, forms, meditations, and roars, plus anti-magic resistance, Whirlwind, War Stomp, and an Expertise-based combat identity.

Bard is a lore-primary hybrid built around performance and sound. Its profile is Lore primary; Magic/Weapon secondary; Survival/Armor tertiary. Its guild abilities include vocal and instrumental technique, playacting, bardic whistling and screams, showmanship, segue, and bardic magic tied to voice and sound. Bardic Lore is the guild’s distinctive knowledge/performance identity.

Cleric is the holy magic-primary priest. Its profile is Magic primary; Lore/Weapon secondary; Survival/Armor tertiary. The core profession system is Devotion feeding Communes, with additional identity around alignment, infusion, rituals, and favor with the gods.

Empath is a lore-primary healer/support profession. Its profile is Lore primary; Survival/Magic secondary; Weapon/Armor tertiary. Its defining abilities are Touch, Diagnose, Transfer/Take wounds, Link variants, and Perceive Health. This is not “just healer spells”; it is a body-state and injury-transfer profession.

Moon Mage is the lunar magic-primary fate/transport specialist. Its profile is Magic primary; Lore/Survival secondary; Weapon/Armor tertiary. Its distinct systems are lunar attunement, astrology, prediction, astral travel, recall heavens, alignment, time sense, and anti-locate/backtrace style utility.

Necromancer is an advanced survival-primary outlier. Its profile is Survival primary; Lore/Magic secondary; Weapon/Armor tertiary. Its signature system is Thanatology, which supports corpse rituals, self-healing, undead creation, and taboo magic; it is also governed by Outrage, which models social and divine consequences.

Paladin is the armor-primary holy warrior. Its profile is Armor primary; Lore/Weapon secondary; Magic/Survival tertiary. Its core identity is code-driven: soul state, conviction, lead, glyphs, protect, and smite. Public docs also make clear that soul quality and honor behavior directly affect ability access and power.

Ranger is the survival-primary wilderness hunter. Its profile is Survival primary; Weapon/Armor secondary; Magic/Lore tertiary. Its signature features are the ranger bonus, scouting/tracking, animal companions, beseeches, trail utility, ranged identity, and wilderness affinity.

Thief is the survival-primary stealth criminal. Its profile is Survival primary; Weapon/Lore secondary; Armor/Magic tertiary. Its guild abilities include Khri, Blindside, Sign, Passages, Voice Throw, Slip, Contact, lockpick carving, poison resistance, and Mark. This is a stealth/social-control profession more than a pure DPS class.

Trader is a lore-primary economic profession. Its profile is Lore primary; Survival/Armor secondary; Weapon/Magic tertiary. Its profession mechanics include caravans, contract/commodity trading, market advantages, trader markets, hirelings, ledgers, shops, and other commerce systems. This is closer to a simulation/economy profession than a combat profession.

Warrior Mage is the elemental magic-primary battle caster. Its profile is Magic primary; Lore/Weapon secondary; Survival/Armor tertiary. Its signature subsystem is Summoning and elemental alignment/charge, plus conjured weapons and strong elemental offense.

The real DR model, simplified

If you strip away lore and 25 years of content, DR professions are built from a repeatable pattern:

one primary skillset and two secondary ones that shape learning and advancement,
one signature profession subsystem or resource, like Inner Fire, Devotion, Thanatology, Soul/Conviction, Prediction, or Trading,
profession-only verbs that change how the character interacts with combat, travel, economy, healing, or stealth,
social/world consequences for using that profession, especially for Paladins, Necromancers, Traders, and Thieves.

That is the part worth borrowing.

The part not worth copying 1:1 is DR’s sheer breadth. If you try to build all eleven at once, you’ll get a wide but fake system. Your roadmap’s own “vertical slice / layered complexity / no dead systems” rules argue against that.

Recommendation for DireMUD: what to build first

I would not start with all eleven professions.

I would start with four anchor professions:

Barbarian equivalent: pure martial / anti-magic / combat resource
Thief equivalent: stealth / awareness / crime
Empath equivalent: healing / body-state / support
Warrior Mage equivalent: offensive magic / elemental resource

That gives you one profession anchored in each of the most important gameplay pillars you already care about: combat, crime, recovery/support, and magic. It also avoids front-loading Trader and Necromancer, which are both mechanically expensive and system-hungry.

Phase outline for DireMUD professions
Phase P1 — Profession foundation

Goal: professions exist as data, not hardcoded conditionals.

Build:

profession definitions
skillset weighting model
commoner state
guild join/leave hooks
profession flags on character

Deliverable:

player can be Commoner or join a profession
stats and abilities reflect profession identity
Phase P2 — Skillset integration

Goal: professions affect progression immediately.

Build:

primary/secondary/tertiary skillset weights
profession-based XP gain modifiers
profession-based advancement requirements
profession-specific required mastery skill placeholders

Deliverable:

two characters training the same action do not learn identically if professions differ
Phase P3 — Signature subsystem layer

Goal: every profession has one unique engine.

Build one subsystem per starter profession:

martial resource
stealth focus/khri-like focus
healing link/body-state resource
magic charge/attunement resource

Deliverable:

profession changes how you play, not just what title you wear
Phase P4 — First playable ability slice

Goal: each profession gets 2–3 verbs that matter now.

Example slice:

martial: berserk / roar / anti-magic stance
thief: hide bonus / mark / blindside
empath: diagnose / transfer / mend
mage: charge / cast bolt / ward

Deliverable:

each profession can do something another cannot do in the current playable loop
Phase P5 — Profession progression

Goal: advancement pressure feels profession-shaped.

Build:

circle/rank requirements by skillset
trainer unlocks
ability prerequisites
profession-specific milestone quests or tests

Deliverable:

advancement is gated by profession behavior, not just generic XP totals
Phase P6 — World hooks

Goal: professions matter in the world simulation.

Build:

guild trainers and halls
profession reactions from NPCs
basic legality / taboo / honor rules
shop/service/world affordances by profession

Deliverable:

world treats a thief, healer, and sanctioned caster differently
Phase P7 — Expansion professions

Goal: widen only after the first four are stable.

Add next:

Ranger
Paladin
Bard
Trader

Leave for later:

Moon Mage
Cleric
Necromancer

That order is about implementation risk, not coolness.

Task outline under those phases
Track A — Data and rules
profession registry
skillset weight table
profession metadata schema
commoner default state
join/leave validation
profession-aware command hooks
Track B — Progression integration
profession XP modifier hooks
profession circle requirement table
required-skill checks
mastery/profession-skill scaffolding
advancement messaging
Track C — Ability framework
profession ability base class
cooldown/resource hooks
passive vs active ability categories
ability unlock prerequisites
profession-specific command routing
Track D — World integration
guild NPCs
join quest/test hooks
legality/taboo flags
faction/reputation reactions
profession services
Track E — UI/state integration
character panel profession display
profession resource bar
ability list panel
cooldown/state packets
profession-specific prompt/status text
My blunt recommendation

Do not ask Aedan to “implement professions.”

Ask him to implement this sequence:

profession data model
skillset weighting
commoner → guild join flow
one signature subsystem
three abilities for one profession
repeat for the next profession

That is the disciplined path.