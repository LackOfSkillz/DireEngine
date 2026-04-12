Empath DB Audit

This section replaces the earlier high-level interpretation with a database-backed audit of the Empath profession and guild. Source material came from the running Direlore PostgreSQL database, primarily the raw_pages, sections, page_metadata, entities, canon_professions, and profession_skills tables.

Scope note

The normalized profession tables are incomplete for Empath. canon_professions and profession_skills contain the profession shell, but profession_spells, profession_abilities, and facts do not currently carry the full profession payload. The detailed source of truth for Empath behavior currently lives in the raw scraped page corpus stored in the database.

Verified profession identity

- canon_professions identifies Empath as profession id 15 with source entity id 753.
- The canonical description is that Empaths are highly attuned to other living creatures, can heal the wounds of others, and risk losing healing ability temporarily or permanently if they harm or kill living creatures.
- The profession page classifies Empath as Lore primary, Magic and Survival secondary, and Weapon and Armor tertiary.
- Empaths use Life mana.
- The profession page lists the special abilities as Heal, Shift, Link, and Manipulate.

What the DB says the class actually is

The raw profession and healing pages are consistent on one point: Empath is not built around target-first direct healing. It is built around diagnosis, transfer, and self-risk.

- Healing begins with TOUCH to establish a diagnostic link.
- The Empath then TAKES wounds, scars, vitality loss, poison, disease, and even part of another Empath's shock onto their own body.
- The Empath heals those injuries on themselves with healing spells and related tools.

That transfer loop is the core of the profession. If Dragonsire wants the DragonRealms feel, this is the mechanic that has to survive translation.

Guild structure and locations

The profession page and guildhall pages identify five guildhall locations:

- Crossing, led by Salvur Siksa
- Riverhaven, led by Nebela Mentrade
- Shard, led by K'miriel Lystrandoniel
- Aesry
- Hibarnhvidar

The profession page also states that the leadership of the Empaths' Guild is collectively known as the Khalaen.

The Crossing guildhall page is especially useful as a model for guild experience. It includes:

- a courtyard garden
- guildleader's office
- library
- infirmary
- empath-only sitting room
- entrance into the Healerie / triage complex
- combat wing for defensive and healing training
- lecture hall and viewing area
- multiple color-coded treatment areas

That matters because the guild is not just a trainer room. In source material it is a social, medical, instructional, and triage space.

Joining experience and early guild onboarding

I did not find a dedicated modern "joining ritual" page in the database comparable to a full scripted initiation walkthrough. What the DB does support is the early join flow and first-guild experience.

- The current Guide to Being an Empath in Elanthia says that when you first join the guild you are given a lesson on how to heal and are taught Heal Wounds.
- That same guide describes the expected starter loop as TOUCH patient, TAKE wound, then heal the wound on yourself.
- The older obsolete guide says that if you spoke to a guildleader you had already begun, and in that era specifically names Annael in Crossing as the person a novice likely talked to.

So the strongest source-backed conclusion is:

- the profession experience begins with guildleader onboarding, not a dramatic rite page preserved in the DB
- the actual initiation content is practical medical training: first link, first transfer, first self-heal

Core guild abilities

The profession page's Guild Abilities section and the dedicated ability pages make the class structure very clear.

Touch

- TOUCH creates the diagnostic link.
- It reveals wounds, vitality, poison, and disease.
- It is the gateway ability for later systems such as Shift and Link.

Transfer / Take

- TAKE is the core healing action.
- It supports wounds, scars, vitality, poison, disease, and empathic shock.
- The healing page documents optional syntax for partial transfer and speed control.
- Low skill causes slower transfers and more fragile links.

Wound reduction and wound redirection

- The healing page states that highly skilled Empaths can automatically reduce the severity of wounds they transfer.
- It also identifies wound redirection as an advanced form of taking that changes the destination of transferred wounds.

Perceive Health

- Empath-only sensing ability.
- Trains Empathy and Attunement.
- Detects life essences, including health state, poison, disease, low vitality, and whether something is living, undead, or a construct.
- Range appears to improve with combined Empathy and Attunement.
- Hidden or invisible beings can still be sensed if they are in range, though not always identified.
- There is a 20 second cooldown.

Link

- Requires an existing diagnostic link.
- Lets the Empath temporarily borrow part of another character's knowledge in a chosen skill.
- Costs fatigue and concentration to maintain.
- Multiple outgoing links are possible for the initiating Empath, but a target can only be under one such link.
- Both parties must remain in the same room.

Persistent Link

- Requirement listed as 300 Empathy.
- Converts a normal diagnostic link into one that persists while the Empath and patient remain in the same room.
- Enables PERCEIVE HEALTH <patient> without touching them again.
- Explicitly required for some other link-based abilities.

Unity Link

- Requirement listed as 380 Empathy and 70th circle.
- Requires knowledge of basic Link.
- Intended for triage situations.
- Instantly transfers the patient's wounds to the Empath.
- Has a skill-based cooldown that starts around three minutes and can be reduced.
- Can instantly kill the Empath if used carelessly on lethal wounds.

Hand of Hodierna

- Requirement listed as 440 Empathy and 80th circle.
- Requires a Persistent Link first.
- Provides a slow pulsing healing mode that gradually draws hurts from multiple patients.
- Starts at two supported links and can expand to four with skill.

Manipulate

- Nonviolent creature control tool.
- MANIPULATE FRIENDSHIP <creature> causes many critters to regard the Empath as friend or non-threat.
- Success can remove the creature from combat engagement, make it leave, or make it attack another target.
- Evil or undead creatures can instead become enraged and focus the Empath.
- Shock reduces manipulation effectiveness, and at full shock manipulation fails entirely.
- The history section ties this ability to Trylaine and the First Empaths.

Shift

- Appearance-altering ability for other characters.
- Available after 30th circle by quest.
- Relies heavily on Empathy, with Scholarship and Appraisal also contributing.
- Requires a diagnostic link and target acceptance in normal play.
- Official guild stance in the source material is that shifting is dangerous and forbidden.
- The page states that shifting became illegal as of 34 Shorka 406 and can trigger justice consequences in justice zones.

Empathic Shock

Shock is not side flavor in the DB. It is one of the profession's central systems.

- Shock is caused primarily by directly harming living beings.
- The shock page also lists fishing and healing a Necromancer with sufficient Divine Outrage as shock-causing examples.
- Shock is granular rather than binary.
- Shock causes a brief stun when incurred.
- As shock rises, empathy-based abilities weaken and effective Empathy may be penalized.

Abilities lost at complete insensitivity

- healing others
- link
- perceive health
- manipulate
- shift
- teaching or listening to Empathy classes
- Fountain of Creation
- Guardian Spirit
- Heart Link
- Regenerate
- Circle of Sympathy
- Embrace of the Vela'Tohr

Abilities reduced but still functional while shocked

- Heal Wounds
- Heal Scars
- Vitality Healing
- Flush Poisons
- Cure Disease

Abilities listed as unaffected at full shock

- Aesandry Darlaeth
- Aggressive Stance
- Awaken
- Blood Staunching
- Compel
- Gift of Life
- Innocence
- Iron Constitution
- Lethargy
- Mental Focus
- Nissa's Binding
- Paralysis
- Perseverance of Peri'el
- Refresh
- Tranquility
- Vigor

Shock sharing and recovery

- At 10th circle, other Empaths can TAKE part of a guildmate's shock.
- Each share takes about half of the remaining shock, making shock circles efficient.
- The shock quest exists as a repeatable recovery path.
- The walkthrough page says null / fully shocked Empaths must complete it to begin recovering over time again, and partially shocked Empaths can also run it to reduce current shock.
- The quest begins with Nadigo in Vela'Tohr Edge, Secluded Grove.

Healing workflow and triage rules

The Empath healing page is one of the highest-value source pages in the database. It gives the actual practical loop the player experiences.

- Healing starts by establishing a link with TOUCH.
- The player then TAKES specific injuries.
- The page explicitly recommends not transferring poison, disease, or scars until the Empath can treat those conditions on themselves.
- Vitality transfer is possible, but the page warns that a patient's apparent loss may be much more dangerous to the healer than it looks.
- Multiple Empaths can distribute shock in a shock circle.
- Over-healing is a real failure state: the healer can die by taking lethal wounds, scars, or bleeding burden.
- The page calls out triage behavior, guild / infirmary healing, field healing, and etiquette such as asking before healing and taking turns with other Empaths.

This is the strongest evidence that the Empath player experience is about triage decision-making, not just casting recovery spells.

Empathy skill and progression identity

The Empathy skill page confirms that Empathy is exclusive to the Empath guild. It also documents how the class actually trains.

- Best training source is healing patients, except healing another Empath does not teach Empathy.
- Manipulating creatures teaches a meaningful amount of Empathy when there is challenge.
- Icutu Zaharenela can teach Empathy in battle, especially for shocked Empaths.
- Perceive Health teaches Empathy if a living being is successfully perceived.

Circle requirements

The profession page and Empath 3.0 page agree on the circle structure.

- Hard requirements are Empathy, First Aid, and Scholarship.
- Outdoorsmanship is a soft requirement.
- Sorcery and Thievery are restricted skills on the Empath 3.0 page.

The profession page provides a full per-band circle requirement table and cumulative totals through 200 circles. The most important class-defining detail is that Empathy, First Aid, and Scholarship are hard gates, which reinforces the profession as healer-scholar first.

Spellbooks and spell roster found in the DB

The profession page names five spellbooks:

- Healing
- Protection
- Body Purification
- Mental Preparation
- Life Force Manipulation

The page metadata in the DB also yields a concrete spell roster by spellbook.

Healing spellbook

- Heal Wounds
- Heal Scars
- Vitality Healing
- Heal
- Fountain of Creation
- Regenerate

Protection spellbook

- Aggressive Stance
- Innocence
- Iron Constitution
- Aesandry Darlaeth
- Guardian Spirit
- Perseverance of Peri'el

Body Purification spellbook

- Blood Staunching
- Cure Disease
- Flush Poisons
- Heart Link
- Absolution
- Adaptive Curing

Mental Preparation spellbook

- Mental Focus
- Awaken
- Compel
- Tranquility
- Circle of Sympathy
- Calculated Rage
- Embrace of the Vela'Tohr
- Nissa's Binding

Life Force Manipulation spellbook

- Refresh
- Gift of Life
- Lethargy
- Paralysis
- Raise Power
- Vigor
- Icutu Zaharenela

Spell tags that matter for implementation

- Several spells are marked Signature spells.
- Some are Cyclic spells: Aesandry Darlaeth, Guardian Spirit, Regenerate, Icutu Zaharenela.
- Some are Ritual spells: Absolution, Circle of Sympathy, Embrace of the Vela'Tohr, Perseverance of Peri'el.
- Some are Illegal spells: Nissa's Binding and Icutu Zaharenela.
- Adaptive Curing and Icutu Zaharenela are marked Scroll-only in the source metadata captured here.

First Empaths and guild lore

The First Empaths page provides the core mythic background. The summary preserved in the DB is that the first group who developed supernatural empathy became too sensitive to live normally among others. One of them was chosen and cast out so that the knowledge could be reduced, hidden, or channeled in later generations. The page frames modern Empathy as something deliberately channeled and lessened so later Empaths could survive.

That lore is directly useful for tone. The guild is not just compassionate. It is built on the danger of feeling too much.

What this means for recreating the player experience

The source-backed Dragonsire takeaways are:

- Empath should be built around link-first interaction, not fire-and-forget ally heals.
- Damage transfer and self-risk are the class identity.
- Shock must meaningfully interfere with core empathic actions.
- Perceive Health should make Empath a sensor and triage class, not just a healer.
- Manipulate provides a nonviolent survival and control path.
- Advanced links are major class progression milestones, not optional flavor.
- The guildhall should feel like a healer school and triage institution, not just a rank-up counter.

Recommended implementation order from the DB evidence

1. TOUCH and detailed diagnostic link.
2. TAKE / transfer for wounds, vitality, poison, disease, and shock.
3. Self-healing loop with over-heal risk.
4. Shock accumulation, penalties, sharing, and recovery path.
5. PERCEIVE HEALTH.
6. LINK, then Persistent Link.
7. Unity Link and Hand of Hodierna for group triage.
8. Manipulate.
9. Shift as a later social / justice-layer system.

Database confidence notes

- High confidence: profession identity, skillsets, mana type, guildhall locations, guild abilities, healing loop, shock behavior, perceive health behavior, link behavior, manipulate behavior, shift legality, spellbook membership, spell roster, circle requirement structure.
- Medium confidence: exact modern onboarding script, because the DB contains guides and books rather than a dedicated live join script page.
- Low confidence: any claim that there is a single formal modern "guild joining ritual" beyond guildleader onboarding and first-healing instruction. I did not find a canonical ritual page in the database.

EMPATH TRAINING 001–030

Patch-level implementation instructions

Phase goal

By EMPATH 030:

- Empath actions award XP through one progression path only
- XP goes into pools, not straight into ranks
- Pools pulse into ranks using the current EXP system
- Empathy, First Aid, and Scholarship all train from the correct actions
- First Aid uses timed pulses, not spam actions
- Legacy `use_skill` is removed from empath learning paths

EMPATH 001 - Confirm the authoritative progression path

Files to inspect

- `world/systems/skills.py`
- `world/systems/exp_pulse.py`
- `typeclasses/characters.py`

Patch intent
Make the transient EXP system authoritative for empath progression.

Do

- Identify the function currently used for real rank progression, such as `award_exp_skill`, `add_skill_xp`, or equivalent.
- Identify all empath-related places still calling legacy `use_skill(...)`.

Do not

- Leave both systems active for empath learning.
- Add a third path.

Done when

- You can name the single authoritative XP entry point.
- You have a list of all empath verbs still using legacy learning.

EMPATH 002 - Ensure empathy, first_aid, scholarship exist in transient EXP skills

Files

- `world/systems/skills.py`

Patch intent
Make sure these skills are real rankable skills in the EXP handler, not just legacy names.

Do

- Add or verify `empathy`, `first_aid`, and `scholarship` in the transient skill definitions or templates.
- If the handler auto-creates unknown skills, still add explicit metadata for these three so they have correct skillset placement.

Required mapping

- `empathy = primary`
- `first_aid = secondary`
- `scholarship = secondary`

Done when

- A new character can award XP into all three without errors.
- The EXP handler classifies them with the correct skillset tier.

EMPATH 003 - Seed missing EXP skill state on character init/repair

Files

- `typeclasses/characters.py`

Patch intent
Ensure characters always have valid transient EXP state for the three empath-relevant skills.

Do

- In character default/repair/init paths, ensure the transient EXP container can hold:
- `rank`
- `pool`
- `rank progress` or `bits`
- `mindstate`
- Do not rely on first use to silently create malformed state.

Done when

- Existing characters log in without missing-key errors.
- New characters start with valid transient state for `empathy`, `first_aid`, `scholarship`.

EMPATH 004 - Enforce rank-cost rule in the real EXP path

Files

- `world/systems/skills.py`

Patch intent
Use the confirmed DR-style next-rank cost rule in the authoritative rank system.

Do

- Ensure next rank cost is:
- `200 + current_rank`
- If the code already uses this, verify and leave it alone.
- If the code diverges, patch it here, not in empath commands.

Done when

- Rank-up cost for `empathy`, `first_aid`, `scholarship` matches `200 + rank`.

EMPATH 005 - Make pools authoritative, not direct rank gain

Files

- `world/systems/skills.py`

Patch intent
All empath XP goes into pools first.

Do

- Ensure the XP entry point adds to the skill pool or bits pool only.
- Do not directly add ranks from empath actions.

Done when

- `take`, `tend`, `perceive`, etc. increase pools/mindstate, not ranks immediately.

EMPATH 006 - Add or verify mindstate update from pool

Files

- `world/systems/skills.py`

Patch intent
Keep mindstate as a view of pool fullness.

Do

- Ensure each skill has a `0-34` mindstate ladder.
- Recompute mindstate whenever pool changes.
- Keep existing named mindstates if already present in code.

Do not

- Hardcode empath-specific mindstate names in command code.

Done when

- Awarding empathy XP visibly changes empathy mindstate through the normal EXP system.

EMPATH 007 - Remove legacy use_skill from empath TAKE paths

Files

- `typeclasses/characters.py`

Patch intent
Empath transfer must no longer train through legacy skill logic.

Do

- Find all empath transfer actions:
- wound transfer
- vitality transfer
- poison/disease transfer
- shock sharing if it teaches
- channel pulses if they teach
- Replace any `use_skill("empathy")` or equivalent with the authoritative EXP award function.

Do not

- Leave both old and new calls in place.

Done when

- Empath transfer actions only award via transient EXP/rank path.

EMPATH 008 - Add a real empathy XP calculator helper

Files

- `typeclasses/characters.py` or a nearby empath helper module

Patch intent
Centralize empathy XP math so all transfer actions are consistent.

Create helper

- `compute_empathy_xp(...)`

Inputs should include

- moved amount
- transfer type
- difficulty
- current empathy rank
- quick/advanced mode flag
- patient profession or empath/non-empath check
- current shock/load context

Do not

- Use flat `amount * 2`
- Scatter XP math inline across commands

Done when

- All empathy XP awards call one shared helper.

EMPATH 009 - Make empathy XP difficulty-based, not flat

Files

- same as EMPATH 008

Patch intent
XP must reflect challenge, not just quantity.

Do

- Include a difficulty-vs-rank factor.
- If action is trivial relative to current empathy rank, reduce XP.
- If action is appropriately challenging, grant full XP.
- If action is impossible or failed badly, no XP or reduced XP.

Use these sources

- Internal/external transfer unlock thresholds
- poison/disease thresholds
- manipulate difficulty
- perceive thresholds

Done when

- Easy transfers stop being optimal forever training.
- Harder transfer types naturally teach more.

EMPATH 010 - Add transfer-type modifiers to empathy XP

Files

- same helper as above

Patch intent
Different transfer families should not train identically.

Required relative ordering

- highest: risky patient-facing transfer families
- vitality
- poison/disease
- severe wound/scar transfer
- medium: ordinary wound transfer
- low: perceive health
- very low: passive link trickle

Do

- Add a transfer-type multiplier table in one place.

Done when

- `take vitality` teaches more than `perceive health`
- poison/disease are not lumped into ordinary wound XP

EMPATH 011 - Add non-empath patient bonus / empath patient penalty

Files

- empathy XP helper

Patch intent
Reflect the confirmed rule that healing another empath does not teach empathy normally.

Do

- If patient is an empath:
- give zero or sharply reduced empathy XP
- If patient is not an empath:
- full XP

Done when

- Healing a non-empath is the normal training case.
- Healing an empath is not a loophole trainer.

EMPATH 012 - Add QUICK transfer bonus to empathy XP

Files

- `typeclasses/characters.py`

Patch intent
Quick transfer is riskier and should teach more.

Do

- Detect quick/fast transfer mode if your command surface supports it.
- Increase empathy XP for quick transfer.
- Do not bypass normal risk systems to do this.

Done when

- QUICK or fast transfer teaches more but is still dangerous.

EMPATH 013 - Hook ordinary TAKE to empathy XP helper

Files

- `typeclasses/characters.py`

Patch intent
Standard wound transfer teaches empathy through the shared helper.

Do

- In `take_empath_wound(...)` or the authoritative choke point:
- calculate actual moved amount
- compute empathy XP from actual moved amount and difficulty
- award XP through transient EXP path

Do not

- Award off requested amount.
- Award before transfer math resolves.

Done when

- Standard TAKE teaches based on actual burden moved.

EMPATH 014 - Hook vitality transfer to empathy XP helper

Files

- `typeclasses/characters.py`

Patch intent
Vitality teaches empathy, but only through the explicit vitality branch.

Do

- After effective vitality amount is known, award empathy XP with vitality weighting.
- Keep the existing HP/shock/fatigue risk path authoritative.

Do not

- Let partial vitality route in.
- Add separate vitality XP systems.

Done when

- `take vitality` teaches empathy as a high-risk transfer.

EMPATH 015 - Hook poison and disease transfer to empathy XP helper

Files

- `typeclasses/characters.py`

Patch intent
Poison and disease transfer should teach empathy more than ordinary transfer when successfully handled.

Do

- Award via the same helper with poison/disease modifiers.
- Respect unlock thresholds and difficulty.

Done when

- difficult toxin transfer teaches more than basic wound transfer.

EMPATH 016 - Hook Manipulate to empathy XP

Files

- `typeclasses/characters.py` or manipulate command module

Patch intent
Manipulate is a combat empathy trainer.

Do

- On meaningful manipulate success or challenge-bearing attempt, award empathy XP.
- Scale by creature difficulty and challenge.

Do not

- Give free XP on trivial targets forever.

Done when

- Manipulate becomes a real alternate empathy training path.

EMPATH 017 - Hook Perceive Health to low-yield empathy XP

Files

- `typeclasses/characters.py` or perceive command

Patch intent
Perceive Health is a small solo trainer.

Do

- Award small empathy XP only on successful perception of a valid living target.
- Respect existing cooldown.

Done when

- Perceive teaches a little, not a lot.

EMPATH 018 - Hook Link to tiny empathy trickle

Files

- link maintenance path in `typeclasses/characters.py`

Patch intent
Link should teach a tiny amount while active, not compete with healing.

Do

- Add a very small periodic empathy award while maintaining active qualifying link state.
- Only award if the link is real and valid.

Done when

- Link gives a trickle, not a farm.

EMPATH 019 - Hook Unity and Channel/HoH-style systems to higher empathy yield

Files

- unity/channel logic in `typeclasses/characters.py`

Patch intent
Advanced group triage should be a better empathy trainer than plain healing.

Do

- Award empathy XP per successful unity/channel pulse.
- Make unity better than vanilla take.
- Make sustained channel or HoH-style healing teach in smaller but repeated bursts.

Done when

- Advanced empath group play is meaningfully rewarding.

EMPATH 020 - Remove legacy use_skill from perceive/manipulate/link/channel paths

Files

- all empath action paths in `typeclasses/characters.py`

Patch intent
Finish the unification.

Do

- Replace remaining empath `use_skill(...)` calls with transient EXP awards.

Done when

- No empath progression path depends on legacy mindstate-only updates.

EMPATH 021 - Hook TEND to First Aid using the authoritative EXP system

Files

- `typeclasses/characters.py`

Patch intent
First Aid training must run through the same real rank path.

Do

- Replace any legacy `use_skill("first_aid")` with transient EXP awarding.
- Award First Aid only from actual tending, bandaging, or lodged-item handling loops.

Done when

- Tending feeds real First Aid ranks.

EMPATH 022 - Implement 15-second First Aid training pulses for 5 minutes

Files

- tending logic in `typeclasses/characters.py`

Patch intent
Match the confirmed DB-backed First Aid behavior.

Do

- On a valid tend or bandage event, start a training window:
- pulse every 15 seconds
- for 5 minutes max
- Stop XP after 5 minutes unless the wound is re-tended properly.

Do not

- Reward spam tend every command.
- Let the same wound teach indefinitely.

Done when

- First Aid learns over time from a valid tended wound.

EMPATH 023 - Prevent First Aid spam abuse

Files

- tending logic

Patch intent
Honor the "wait for pulses" rule.

Do

- Track training-active tended wounds.
- Suppress repeated immediate XP if the same wound is just spammed.
- Reset only when the wound naturally needs retending or bandage state changes.

Done when

- Unwrap/retend spam is not the best XP route.

EMPATH 024 - Scale First Aid XP by bleed/wound severity

Files

- tending XP helper

Patch intent
Harder wound care should teach more.

Do

- Use severity bands or bleed levels to scale First Aid XP.
- Keep severe wounds more rewarding than slight bleeders.

Done when

- tending a hard bleed teaches more than a trivial one.

EMPATH 025 - Hook anatomy study to Scholarship and First Aid

Files

- study/anatomy chart handling

Patch intent
Charts are a safe dual-skill trainer.

Do

- Award Scholarship.
- Also award smaller First Aid.
- Use transient EXP path for both.

Done when

- anatomy work trains both correctly.

EMPATH 026 - Add optional tiny empathy gain from anatomy study

Files

- anatomy study handling

Patch intent
Reflect the documented small empathy relevance without making charts a main empathy trainer.

Do

- Award very small empathy XP on qualifying anatomy study.
- Keep it much lower than patient healing or manipulate.

Done when

- charts can help a little, but do not replace healing.

EMPATH 027 - Verify skillset-based pool formulas are applied to these three skills

Files

- `world/systems/skills.py`

Patch intent
Empathy, First Aid, and Scholarship must get the right pool size behavior.

Do

- Confirm primary vs secondary pool formulas are used.
- Ensure Intelligence and Discipline contribute to pool size.
- Ensure Wisdom affects drain into usable ranks.

Done when

- empathy uses primary pool behavior.
- first_aid and scholarship use secondary pool behavior.

EMPATH 028 - Align pulse groups for empathy and first_aid

Files

- `world/systems/exp_pulse.py`

Patch intent
Bring Dragonsire pulse timing closer to the extracted DR model.

Do

- Set or map:
- `first_aid` to the `120-second` group
- `empathy` to the `180-second` group
- If the system uses staggered offsets differently, align behavior as closely as practical without breaking the engine.

Done when

- empathy and first_aid pulse in the intended relative cadence.

EMPATH 029 - Make pulse the only source of rank gain

Files

- `world/systems/exp_pulse.py`
- `world/systems/skills.py`

Patch intent
Ranks must only advance via pulse drain, never directly from actions.

Do

- Verify actions only fill pools.
- Verify pulses consume pool and advance rank bits or progress.

Done when

- taking a wound raises pool or mindstate first.
- rank only rises when pulse runs.

EMPATH 030 - Add focused regression checks for learning unification

Files

- `diretest.py` or current training validation path

Patch intent
Lock the new learning behavior before circling work begins.

Add checks for

- wound transfer teaches empathy
- vitality transfer teaches empathy
- poison/disease transfer teaches empathy
- healing another empath does not meaningfully teach empathy
- manipulate teaches empathy
- perceive teaches a little empathy
- tend teaches first_aid on timed pulses
- anatomy study teaches scholarship and first_aid
- empath actions no longer rely on legacy `use_skill`

Done when

- these checks fail if someone reintroduces legacy learning paths.

Key implementation locks for Aedan

- Do not invent a second XP system.
- Do not leave empath actions split across `use_skill` and transient EXP.
- Do not make healing spells the primary empathy trainer.
- Do not flatten all empathy XP into one amount.
- Do not let First Aid be spam-trained by repeated instant tend actions.

What comes next after this batch

The next batch should be:

- circle requirements
- rank-based unlock gates
- ability/circle coupling
- late empathy thresholds
- training difficulty tuning

Historical note

- The earlier `EMPATH MICRO TASKS (001-040)` packet is superseded by this DireLore-backed learning rewrite wherever the two conflict.

🧱 EMPATH MICRO TASKS (041–060)
passively detect:
heavily injured characters nearby
🥇 EMPATH 036 — Sensitivity Messaging

You feel a nearby life force faltering.

🥇 EMPATH 037 — Add Transfer Overload Check
If empath takes too much at once:
chance of:
temporary stun (future hook)
penalty spike
🥇 EMPATH 038 — Add “Stabilize” Command

Command:

stabilize <target>

Effect:

reduces:
bleeding rate
does NOT heal

👉 pure triage tool

🥇 EMPATH 039 — Stabilize Messaging

You steady their condition, slowing the damage.

🥇 EMPATH 040 — Multi-Wound Triage Test

Test:

target has:
high bleeding
medium vitality loss
empath:
perceive
touch
stabilize
take bleeding
mend self

Verify:

correct prioritization matters
bleeding control feels important
empath must choose what to take
🧭 What You Now Have

After 40 tasks:

✅ Wounds are multi-dimensional
✅ Empath must make real decisions
✅ Perception system exists
✅ Remote sensing works
✅ Triage gameplay is real

🔥 What Comes Next (041–060)

Now we introduce:

Poison + disease systems
Advanced self-healing
Shock becoming a real limiter
First link expansion (beyond touch)
⚠️ Critical Design Insight

At this point, Empath is:

not healing damage
but managing damage flow

That distinction is everything.

We are now adding:

Poison + Disease (new problem types)
Shock as a real limiter (not just a number)
Deeper self-risk and recovery mechanics

This is where the class starts to feel tense.

🧱 EMPATH MICRO TASKS (041–060)

Phase: Poison, Disease, Shock Enforcement

🥇 EMPATH 041 — Add Poison System

Extend wounds:

wounds["poison"] = 0–100
🥇 EMPATH 042 — Add Disease System
wounds["disease"] = 0–100
🥇 EMPATH 043 — Poison Behavior
Poison:
increases over time (tick damage)
affects vitality slowly
🥇 EMPATH 044 — Disease Behavior
Disease:
reduces recovery rates
increases fatigue accumulation

👉 slower but persistent threat

🥇 EMPATH 045 — Diagnose Output Update

Add:

Poison: Moderate
Disease: Light

🥇 EMPATH 046 — Assess Precision Update

Empath sees exact:

Poison: 37%
Disease: 14%

🥇 EMPATH 047 — Transfer Poison
take poison <amount>
transfers poison to empath
🥇 EMPATH 048 — Transfer Disease
take disease <amount>
🥇 EMPATH 049 — Poison Transfer Risk
Taking poison:
increases:
ongoing self-damage rate

👉 immediate danger

🥇 EMPATH 050 — Disease Transfer Risk
Taking disease:
reduces:
healing effectiveness
recovery speed
🥇 EMPATH 051 — Add Command: “Purge”

Command:

purge <type>

Example:

purge poison
🥇 EMPATH 052 — Purge Effect
reduces:
poison OR disease on self
cost:
fatigue spike
🥇 EMPATH 053 — Purge Messaging

You force the corruption from your body.

🥇 EMPATH 054 — Shock Gain Hook (ENFORCEMENT START)
Any offensive action:
empath_shock += value

👉 hook into combat system

🥇 EMPATH 055 — Shock Threshold Effects
Shock	Effect
0–20	none
20–50	reduced transfer efficiency
50–80	perception degradation
80–100	major healing penalties
🥇 EMPATH 056 — Shock Messaging

Your connection dulls.
You feel disconnected from others.
You struggle to sense clearly.

🥇 EMPATH 057 — Shock Impacts Transfer
High shock:
increases:
damage taken during transfer
reduces:
amount successfully transferred
🥇 EMPATH 058 — Shock Impacts Perception
High shock:
vague perceive output
possible false readings
🥇 EMPATH 059 — Add Shock Decay System
Shock decreases:
slowly over time
faster when:
not in combat
actively healing

👉 encourages “proper behavior”

🥇 EMPATH 060 — Poison/Disease/ Shock Test Scenario

Test:

target has:
poison + bleeding
empath:
touch
take poison
take bleeding
empath:
accumulates damage + poison
empath:
purge
mend

Verify:

risk feels real
shock impacts performance
triage decisions matter
🧭 What You Now Have

After 60 tasks:

✅ Multiple damage types (complex triage)
✅ Poison & disease as real threats
✅ Shock actively constrains behavior
✅ Healing is no longer “safe”
✅ Empath gameplay has tension

⚖️ Identity Check (Now Fully Emerging)
Warrior
manages pressure
Ranger
manages positioning
Thief
manages opportunity
Empath
manages suffering

👉 That’s the class

🔥 What Comes Next (061–080)

Now we build the true Empath identity layer:

Advanced link system (beyond touch)
Persistent links
Early group healing mechanics
First nonviolent control (Manipulate-style)
⚠️ Critical Warning

Do NOT:

allow Empath to heal others directly without transfer
make purge too strong
let shock be ignorable

👉 These will break the class instantly

verything so far made Empath functional.
These next 20 make Empath:

indispensable in groups and unique in gameplay

We are now building:

True Link System (beyond touch)
Persistent connections
Group healing architecture
Nonviolent control (Manipulate-style)
🧱 EMPATH MICRO TASKS (061–080)

Phase: Link System + Group Support + Control

🥇 EMPATH 061 — Link System Refactor (CRITICAL)

Replace:

active_link = target

With:

links = {
    target_id: {
        "type": "touch",
        "strength": value,
        "duration": value
    }
}

👉 supports multiple link types later

🥇 EMPATH 062 — Link Types Enum

Define:

TOUCH
PERSISTENT
GROUP
🥇 EMPATH 063 — Link Strength System
Strength based on:
time connected
empath condition (shock, fatigue)

Higher strength:

better transfer efficiency
🥇 EMPATH 064 — Add Command: “Link” (Upgrade)

Command:

link <target>
creates stronger link than touch
requires:
proximity
🥇 EMPATH 065 — Link vs Touch Difference
Touch:
instant, weaker
Link:
slower to establish, stronger
🥇 EMPATH 066 — Link Duration System
Links persist for:
set duration
break on:
distance
severe shock
manual release
🥇 EMPATH 067 — Link Messaging

You deepen your connection, sensing their condition clearly.

🥇 EMPATH 068 — Transfer Scaling with Link Strength
Strong link:
more efficient transfer
less backlash
🥇 EMPATH 069 — Add “Persistent Link”

Command:

link persistent <target>
🥇 EMPATH 070 — Persistent Link Effect
lasts longer
allows:
remote perception (next phase hook)
costs:
fatigue over time
🥇 EMPATH 071 — Persistent Link Drain
while active:
small ongoing fatigue drain

👉 prevents always-on usage

🥇 EMPATH 072 — Add Command: “Unity”

Command:

unity <target1> <target2>
🥇 EMPATH 073 — Unity Effect (GROUP CORE)
links multiple targets
allows:
partial damage sharing between them

👉 This is HUGE for group play

🥇 EMPATH 074 — Unity Logic
incoming damage:
spreads across linked targets
reduces spike damage
🥇 EMPATH 075 — Unity Limitations
max targets: 2–3 (initial)
higher fatigue drain per target
🥇 EMPATH 076 — Unity Messaging

You weave a shared bond between your allies.

🥇 EMPATH 077 — Add Command: “Manipulate” (CONTROL CORE)

Command:

manipulate <target>
🥇 EMPATH 078 — Manipulate Effect
chance to:
calm target
reduce aggression
redirect target (future hook)
🥇 EMPATH 079 — Manipulate Behavior Rules
works better on:
animals
low-intelligence enemies
fails or backfires on:
undead
constructs

👉 DR-authentic behavior

🥇 EMPATH 080 — Full Link + Group Test

Test:

Link 2 players
Use:
unity
take damage from one
Verify:
damage spreads
empath can intervene
manipulate works situationally
🧭 What You Now Have

After 80 tasks:

✅ Link system (real, not placeholder)
✅ Persistent connections
✅ Group damage management
✅ Nonviolent control tool
✅ Empath is now group-critical

⚖️ Identity Check (Now Complete Core)
Warrior
controls battlefield
Ranger
controls engagement
Thief
controls opportunity
Empath
controls damage flow between players

👉 This is the missing pillar you needed

🔥 FINAL PHASE (081–100)

We finish Empath with:

advanced link interactions
wound redirection refinement
recovery loops
polish + identity feedback
⚠️ Critical Design Reminder

At this point:

👉 Empath is very powerful

You MUST ensure:

fatigue pressure remains real
shock matters
group systems don’t trivialize damage

We are now adding:

Advanced link behavior (true DR depth)
Wound redirection refinement
Long-term recovery loops
Identity polish + safeguards
🧱 EMPATH MICRO TASKS (081–100)

Phase: Advanced Link + Redirection + System Completion

🥇 EMPATH 081 — Link Priority System
When multiple links exist:
define priority:
persistent > standard > touch

👉 ensures predictable behavior

🥇 EMPATH 082 — Selective Transfer Targeting

Update:

take <type> <amount> from <target>
allows choosing among linked targets
🥇 EMPATH 083 — Multi-Link Awareness Display

Update assess:

Linked Targets:

Gary (Strong)
Corl (Weak)
🥇 EMPATH 084 — Add “Redirect” Command

Command:

redirect <type> <amount> from <target1> to <target2>
🥇 EMPATH 085 — Redirect Logic
moves wound:
between two linked targets
Empath acts as conduit:
takes partial strain

👉 This is high-skill gameplay

🥇 EMPATH 086 — Redirect Risk
chance to:
overload empath (fatigue spike)
higher risk with:
large transfers
🥇 EMPATH 087 — Redirect Messaging

You channel the injury through yourself, shifting its burden.

🥇 EMPATH 088 — Add “Wound Smoothing” Effect

Passive:

linked targets:
gradually equalize wound levels

👉 prevents spike damage

🥇 EMPATH 089 — Smoothing Limitations
capped per tick
does NOT eliminate need for transfer
🥇 EMPATH 090 — Add “Deep Link” Enhancement

Command:

link deepen <target>

Effect:

increases:
link strength cap
transfer efficiency

Cost:

fatigue spike
🥇 EMPATH 091 — Deep Link Messaging

Your connection deepens, their pain becoming clearer.

🥇 EMPATH 092 — Add “Overdraw” Mechanic
If empath takes too much:
temporary:
transfer lockout
perception penalty

👉 prevents infinite healing loops

🥇 EMPATH 093 — Overdraw Messaging

You have taken too much. Your senses falter.

🥇 EMPATH 094 — Add Recovery Loop: “Center”

Command:

center

Effect:

reduces:
fatigue
shock slightly
requires:
not in heavy combat
🥇 EMPATH 095 — Center Messaging

You steady yourself, regaining clarity.

🥇 EMPATH 096 — Link Decay Over Time
links weaken:
if not maintained
decay faster when:
empath stressed (high fatigue/shock)
🥇 EMPATH 097 — Link Break Feedback

Your connection slips away.

🥇 EMPATH 098 — Identity Feedback System

Dynamic feedback:

Low shock:

Your senses are clear.

High shock:

You feel disconnected from others.

Heavy load:

You are carrying too much pain.

🥇 EMPATH 099 — Full System Validation

Test full loop:

Link 2–3 targets
Apply:
unity
take
redirect
stabilize
Build:
fatigue
shock
Use:
center

Verify:

system remains stable
no infinite healing
empath must manage self
🥇 EMPATH 100 — Balance + Config Hooks

Centralize:

transfer efficiency
link strength scaling
smoothing rate
redirect cost
shock penalties

👉 critical for tuning

🧭 FINAL RESULT — EMPATH (COMPLETE)

You now have:

💚 Core Systems
Healing Engine
Multi-type wounds
Transfer-based healing
Poison + disease handling
Link System
Touch → Link → Persistent → Unity
Multi-target interaction
Redirection + smoothing
Risk Layer
Shock (behavior limiter)
Fatigue (resource pressure)
Overdraw (hard cap)
Control Layer
Manipulate (nonviolent control)
Perception Layer
Perceive health
Passive sensitivity

🧭 EMPATH SERVICE ECONOMY LOCK

Before the next implementation pass, preserve this DragonRealms-authentic rule set:

- player Empaths are not mandatory paid healers
- tipping is a social signal, not a hard transaction gate
- generous players can be remembered and preferred, but the Empath chooses
- an NPC healer exists as guaranteed fallback for blocked players
- that NPC must be slower, more clinical, and economically predictable than a player Empath

Core rule:

Empaths must have agency over who they help.

If the system auto-promotes highest payer first, the class stops being a social healer and becomes a service terminal.

If the system removes fallback healing, players get trapped when no Empath is around.

If the system makes the fallback healer too efficient, player Empaths lose relevance.

👉 Correct balance:

- player Empaths are socially driven
- NPC healers are economically driven

🔥 NEXT PHASE (131–150)

This tranche is intentionally appended out of numeric sequence. Earlier tasks already established the first Perceive Health implementation, so 131–137 refine and integrate that system into triage and social play rather than rebuilding it.

🧱 EMPATH MICRO TASKS (131–150)

Phase: Charity Economy + Triage Priority + NPC Fallback

PHASE NOTE:

These tasks MODIFY and EXTEND Perceive Health from EMPATH 029-034.
Do NOT reimplement base Perceive Health functionality here.

🥇 EMPATH 131 — Enforce Perceive Health Cooldown

Add a hard cooldown check to the existing perceive health command.

Requirement:

- 20 second reuse lock

Failure message:

- Your senses are still settling.

Purpose:

- keeps perception useful without becoming spammy room surveillance

🥇 EMPATH 132 — Add Perceive Target Mode Polish

Upgrade the existing targeted perceive path.

Support:

- perceive <target>

Rules:

- target must be in the room
- target mode bypasses broad room scan formatting
- target mode should produce the clearest available empathic read

Purpose:

- gives Empaths precise triage checks when multiple patients are present

🥇 EMPATH 133 — Add Roomwide Triage Scan Output

Upgrade non-targeted perceive into an actual triage sweep.

Without a target:

- scan all valid characters in the room
- summarize injury state per person
- include low vitality and later poison/disease hooks when present

Purpose:

- make perceive useful in crowded infirmary and field-healing situations

🥇 EMPATH 134 — Convert Perceive Output to Soft Severity Labels

Perceive output must avoid numeric HP-style presentation.

Use soft labels such as:

- light wounds
- moderate wounds
- badly injured
- faint vitality
- stable

Purpose:

- preserves DR-style qualitative triage instead of spreadsheet healing

🥇 EMPATH 135 — Add Hidden Suffering Detection Messaging

If a hidden or unseen target is present and detectable:

- do not fully reveal them
- emit a vague empathic cue instead

Example:

- Something unseen is suffering nearby.

Purpose:

- preserves the special sensor identity without breaking stealth too hard

🥇 EMPATH 136 — Add Perceive Overload Warning in Crowded Rooms

If the room contains many valid signals:

- show a minor overload warning
- optionally apply a future-facing strain hook, but no damage yet

Example:

- The flood of sensation is overwhelming.

Purpose:

- makes large triage scenes feel intense
- creates room for later stress tuning

🥇 EMPATH 137 — Hook Perceive Results into Empath Triage Context

After a successful perceive sweep:

- cache recent triage context for the Empath
- allow later queue output to reuse current room injury impressions

Purpose:

- connects sensing to service behavior instead of leaving it as a disconnected scan tool

🥇 EMPATH 138 — Create NPC House Healer

Add a baseline healer NPC in the infirmary or other designated medical room.

Behavior:

- always available
- not an Empath gameplay replacement
- exists to prevent total player blockage

Purpose:

- guaranteed fallback when no player Empath is available

🥇 EMPATH 139 — Add Command: Request Healing

Command:

- request healing

Rules:

- only works in the NPC healer's room or near the healer NPC
- rejects if the player has no treatable wounds

Purpose:

- creates the predictable fallback entry point

🥇 EMPATH 140 — Add NPC Per-Wound Cost Calculation

Implement a simple early pricing model.

Formula:

- cost = wound_count * base_rate

Rules:

- easy to tune later
- may scale by wound severity in a later pass, but keep first version simple

Purpose:

- make NPC healing economically driven and predictable

🥇 EMPATH 141 — Implement NPC Healing Resolution

When paid:

- remove or reduce wounds through NPC treatment
- do not use transfer mechanics
- do not simulate empathic burden gameplay

Purpose:

- clarify that fallback healing is service utility, not class fantasy

🥇 EMPATH 142 — Add NPC Healer Limitations and Tone

The NPC healer must not outclass players.

Requirements:

- slower messaging cadence
- no triage intelligence beyond simple treatment
- no social memory or preference layer
- clinical, detached tone

Purpose:

- preserve player Empaths as the richer and more desirable healing experience

🥇 EMPATH 143 — Add Command: Tip

Command:

- tip <target> <amount>

Validation:

- target must be a player
- target must be in the room
- caller must actually have the coins

Purpose:

- establishes the social economy signal without turning healing into a fee wall

🥇 EMPATH 144 — Store Last Tip, Recent Tip, and Lifetime Tips

On the Empath, track:

- last_tip_amount
- last_tip_time
- lifetime_tips

Optionally track per-patient memory keys for later flavor.

Purpose:

- store the signals needed for soft priority and recognition

🥇 EMPATH 145 — Add Tip Messaging Without Numeric Leakage

To the Empath:

- Jekar offers you a generous tip.

To the tipper:

- subtle confirmation that the offering was accepted

Rules:

- do not surface exact numbers to the Empath through the message layer

Purpose:

- keep the economy social and impressionistic, not transactional UI

🥇 EMPATH 146 — Define Recent Tip Decay Window

Add a recency rule for queue hints.

Initial value:

- recent = last 15 minutes

Purpose:

- reward recent generosity without creating permanent, rigid favoritism

🥇 EMPATH 147 — Add Empath-Only Queue Command

Command:

- queue

Access:

- Empath-only

Lists:

- injured players in room
- enough context for the Empath to make a service decision

Purpose:

- gives Empaths a triage tool instead of forcing them to manually track everything in chat scroll

🥇 EMPATH 148 — Add Soft Queue Sorting Heuristics

Sort by a weighted blend of:

- recent tip signal
- wound severity
- arrival time

Critical rule:

- this is only a suggestion layer
- the Empath can ignore it completely

Purpose:

- support player judgment without automating it away

🥇 EMPATH 149 — Add Queue Output with Social Memory Labels

Example output:

You take in the state of those around you...

Jekar - badly injured (generous)
Mira - moderate wounds (known)
Thorn - light wounds (no history)

Allowed label style:

- generous
- known
- no history
- desperate

Purpose:

- makes social memory visible without exposing exact reputation scores

🥇 EMPATH 150 — Add Empath Reputation Memory Hook

Add a lightweight memory structure such as:

empath_memory[target_id] = {
    "last_tip": value,
    "interaction_count": value,
    "last_seen_injured": timestamp,
}

Rules:

- use this for messaging flavor and future hooks
- do not make it a hard mechanical lockout system yet

Purpose:

- prepares future empath reputation, guild service memory, and social prioritization features without over-automating the class

🧭 RESULT AFTER 150

After this phase, Empath stops being just a burden-transfer profession and becomes a functioning social institution.

You now have:

- sensing that supports triage instead of existing in isolation
- a player-driven charity economy
- visible but non-numeric social memory
- an NPC healer fallback that prevents hard stalls
- a clear reason for players to seek out real Empaths instead of only using NPC services

👉 Most important design lock:

Money is not the point.

Relationship leverage is the point.

Tips are just the signal.

🔥 NEXT PHASE (151–180)

This is the point where Empath stops being a controlled profession demo and becomes part of the live game loop. Combat must create meaningful injuries, untreated wounds must matter, and Empaths must make visible triage decisions under pressure.

🧱 EMPATH MICRO TASKS (151–180)

Phase: Combat Integration + Pressure System

🥇 EMPATH 151 — Hook Combat Damage into Wound System

In the combat resolver, route incoming damage through wound generation instead of treating all harm as flat HP subtraction.

Replace the old shape of:

- hp -= damage

With:

- apply_wound(target, damage_type, severity)

Initial mapping:

- slice -> bleeding wound
- blunt -> trauma/internal burden
- puncture -> focused wound

Purpose:

- connect combat directly to the Empath healing loop

🥇 EMPATH 152 — Add Vitality vs Wound Split

Track separately:

- vitality
- wounds

Rules:

- vitality is immediate survivability pressure
- wounds are persistent medical burden

Purpose:

- stop the system from flattening all injury into one pool

🥇 EMPATH 153 — Make Wounds Persist Until Treated

Wounds should not disappear naturally in baseline play.

Rules:

- wounds remain until explicitly treated or otherwise resolved
- passive time passage alone should not erase the need for care

Purpose:

- ensure healing demand is real instead of optional

🥇 EMPATH 154 — Add Untreated Wound Penalties

Apply scalable penalties from untreated wounds.

Initial effects:

- accuracy penalty
- evasion penalty
- fatigue increase

Purpose:

- make untreated injuries a gameplay problem, not cosmetic state

🥇 EMPATH 155 — Add Bleeding Tick

Bleeding wounds should cause periodic vitality loss.

Rules:

- start light
- do not make the first pass instantly lethal

Purpose:

- create urgency without turning every small cut into nonsense death spirals

🥇 EMPATH 156 — Disable Passive Full Recovery

Remove the expectation that rest alone fully erases serious injury.

Allow:

- minor vitality recovery

Do not allow:

- full wound reset through passive downtime

Purpose:

- preserve the healer dependency loop

🥇 EMPATH 157 — Add Command: Rest

Command:

- rest

Effect:

- small vitality recovery
- no wound removal

Purpose:

- give injured players something useful to do without replacing actual treatment

🥇 EMPATH 158 — Add Injury-State Messaging

Add qualitative player feedback for meaningful injury burden.

Examples:

- You are in no shape to continue fighting.
- Your wounds are slowing you.

Purpose:

- make the pressure legible without dumping raw internals on the player

🥇 EMPATH 159 — Add Soft Combat Lock Threshold

If wound burden becomes too high:

- block voluntary combat engagement

Message:

- You need treatment.

Purpose:

- prevent absurd overextension while preserving some player freedom below the threshold

🥇 EMPATH 160 — Add Death Risk from Overextension

If the player is already near collapse:

- low vitality
- high wound burden

Then:

- the next serious hit should carry elevated death risk

Purpose:

- make fighting while untreated feel like an actual gamble

🥇 EMPATH 161 — Support Multi-Patient Triage Scenes

Allow multiple injured players in the same room with no special-case hard cap.

Purpose:

- support real infirmary and field-healing scenes instead of one-patient demos

🥇 EMPATH 162 — Add Triage Highlight Messaging

When an Empath uses perceive or queue in a stressed room:

- highlight the most urgent cases first

Purpose:

- support triage decisions without replacing player judgment

🥇 EMPATH 163 — Add Critical Condition State

If a target is at very low vitality or extreme wounds:

- mark them as critical

Purpose:

- create a clear top-end emergency state visible to healers

🥇 EMPATH 164 — Add Patient Degradation Over Time

If serious wounds remain untreated:

- allow slow worsening over time

Purpose:

- create pressure in crowded scenes where not everyone can be handled immediately

🥇 EMPATH 165 — Add Panic Messaging for Critical Patients

Examples:

- You are slipping away.

Purpose:

- make the crisis felt by patients, not just healers watching the room

🥇 EMPATH 166 — Increase Transfer Risk Under Load

If an Empath is already carrying wounds or heavy burden:

- taking more becomes meaningfully more dangerous

Purpose:

- preserve self-risk in live scenes

🥇 EMPATH 167 — Add Dangerous-Transfer Warnings

Before a risky TAKE:

- warn rather than hard-block

Example:

- This may overwhelm you.

Purpose:

- keep agency with the Empath while surfacing consequences clearly

🥇 EMPATH 168 — Add Overload Event

If the Empath exceeds a safe threshold:

- temporary stun or collapse
- forced link break

Purpose:

- make healer failure visible and real under pressure

🥇 EMPATH 169 — Add Recovery Delay After Overload

After overload:

- temporarily prevent further transfer actions

Purpose:

- stop immediate infinite re-entry into unsafe healing loops

🥇 EMPATH 170 — Add Visible Empath Degradation

To the room, surface burden-state feedback.

Example:

- The empath staggers under the weight of pain.

Purpose:

- make healer strain socially legible

🥇 EMPATH 171 — Hook Shock into Combat Aggression

If an Empath attacks a living target:

- apply shock immediately

Purpose:

- bring the profession restriction into actual play instead of keeping it theoretical

🥇 EMPATH 172 — Add Shock Feedback Messaging

Example:

- You feel something inside you recoil.

Purpose:

- make shock onset emotionally and mechanically visible

🥇 EMPATH 173 — Reduce Empath Effectiveness Under Shock

Apply penalties to:

- transfer efficiency
- perceive accuracy

Purpose:

- make shock damage the profession's core loop, not just a side number

🥇 EMPATH 174 — Block Advanced Abilities at High Shock

At high shock, disable advanced empath tools such as:

- unity
- redirect
- manipulate

Purpose:

- keep shock meaningful at the upper end

🥇 EMPATH 175 — Add Basic Shock Recovery Path

Allow recovery through:

- time decay
- basic guild rest hooks for future expansion

Purpose:

- ensure the system has a live recovery path before later quest or ritual layers deepen it

🥇 EMPATH 176 — Create Injured NPC Generator

Spawn lightly injured NPCs in town or nearby support spaces.

Purpose:

- create ambient healing demand beyond only player emergencies

🥇 EMPATH 177 — Add NPC Help Requests

Allow injured NPCs to visibly ask for aid.

Example:

- Please... can anyone help me?

Purpose:

- turn injury into public world texture

🥇 EMPATH 178 — Add Reward for NPC Healing

Add small rewards such as:

- coins
- reputation

Purpose:

- make ambient healing worth doing without overshadowing player service

🥇 EMPATH 179 — Add Multi-Injury Event Scenario

Create a controlled scenario with 3-5 injured targets at once.

Purpose:

- support both live tuning and deterministic test coverage for triage pressure

🥇 EMPATH 180 — Add DireTest: Triage Pressure

Add a DireTest scenario that validates:

- multiple patients in one scene
- prioritization remains under player control
- an Empath can fail under burden
- the system remains stable when triage goes badly

⚠️ DESIGN LOCKS (151–180)

- Do not reintroduce full passive healing.
- Do not remove empath self-risk.
- Do not auto-prioritize patients for the healer.
- Do not make combat wounds trivial to ignore.

🧭 RESULT AFTER 180

After this phase, Empath becomes a pillar of the game loop rather than a profession that only functions in controlled demos.

You now have:

- combat-generated wounds that matter after the fight ends
- persistent healing demand
- visible triage pressure
- healer failure states under load
- shock that changes live play behavior

🔥 NEXT PHASE (181–210)

This is the self-management layer: not how Empaths take pain, but how they survive what they take.

🧱 EMPATH MICRO TASKS (181–210)

Phase: Healing Spells + Purification Core

Goal by 210:

- Empaths can heal themselves through real profession tools instead of placeholder recovery
- wounds and vitality are handled by different abilities
- bleeding, poison, and disease become real gameplay burdens
- healing becomes resource-driven and weaker under load

### Heal Wounds foundation spell

🥇 EMPATH 181 — Create Empath Healing Module

Create a dedicated healing-system module.

File:

- world/systems/empath_healing.py

Purpose:

- centralize self-healing and purification logic instead of scattering it across commands

🥇 EMPATH 182 — Add Command: Heal Wounds

Create the baseline wound-healing command.

File:

- commands/cmd_heal_wounds.py

Restriction:

- Empath only

Purpose:

- replace the placeholder self-heal shortcut with a real profession tool

🥇 EMPATH 183 — Implement Heal Wounds Severity Reduction

Effect:

- reduce_wound_severity(target=self, amount=scaled)

Rules:

- does not instantly erase meaningful wounds
- heavy -> moderate
- moderate -> light
- light -> healed

Purpose:

- make healing about improving condition, not full resets on demand

🥇 EMPATH 184 — Scale Healing Efficiency by Burden

Scale healing output based on:

- future empathy/healing skill hooks
- current wound burden
- current transfer load

Rule:

- heavily burdened Empaths heal less efficiently

Purpose:

- preserve the profession's self-management tension

🥇 EMPATH 185 — Add Healing Cost System

Each healing action should cost something meaningful.

Initial model:

- increase fatigue or internal healing strain per cast

Example hook:

- healing_fatigue += value

Purpose:

- stop self-healing from becoming free throughput

🥇 EMPATH 186 — Add Healing Failure Condition

If the Empath is overloaded:

- partial heal or failure

Message:

- You cannot focus through the pain.

Purpose:

- keep healing fallible under pressure

🥇 EMPATH 187 — Add Heal Wounds Messaging

Messaging should feel physical and grounded.

Rules:

- subtle room echo
- no flashy spell spectacle

Purpose:

- keep Empath healing distinct from generic fantasy spellcasting

### Vitality healing as a separate tool

🥇 EMPATH 188 — Add Command: Heal Vitality

Add a distinct tool for vitality restoration.

Purpose:

- reinforce that vitality and wound burden are not the same thing

🥇 EMPATH 189 — Implement Vitality Healing Effect

Effect:

- vitality += scaled_amount

Rules:

- no wound interaction
- restores survivability, not structural injury state

Purpose:

- give Empaths a separate response to low vitality emergencies

🥇 EMPATH 190 — Enforce Vitality Cap

Rule:

- cannot exceed max_vitality

Purpose:

- keep vitality healing numerically sane and easy to reason about

🥇 EMPATH 191 — Add Vitality Healing Tradeoff

If wound burden is high:

- vitality healing becomes less effective

Purpose:

- prevent players from ignoring wounds by brute-forcing vitality back up

🥇 EMPATH 192 — Add Vitality Healing Messaging

Example tone:

- You steady your breath...

Purpose:

- keep vitality restoration feeling distinct from wound knitting

### Bleeding control

🥇 EMPATH 193 — Add Bleeding Flag to Wound Model

Extend wound representation with explicit bleeding state.

Example:

- is_bleeding = True / False

Purpose:

- separate open-bleeding control from general wound healing

🥇 EMPATH 194 — Add Command: Staunch

Effect:

- remove or reduce bleeding state

Rule:

- does not heal the wound itself

Purpose:

- let Empaths stop active deterioration without skipping the rest of treatment

🥇 EMPATH 195 — Add Staunch Validation

Fail if:

- there are no bleeding wounds to address

Purpose:

- avoid wasted actions and muddy feedback

🥇 EMPATH 196 — Scale Bleeding Control by Severity

Rule:

- heavier bleeding is harder to staunch

Purpose:

- make severe cases meaningfully more dangerous and time-sensitive

### Poison system full loop

🥇 EMPATH 197 — Add Poison State

On character, track:

- poison_level
- poison_type

Purpose:

- move poison from flavor to a real persistent condition

🥇 EMPATH 198 — Add Poison Tick System

Periodic effects:

- reduce vitality
- increase strain

Purpose:

- make poison a continuing threat, not a single check-box injury

🥇 EMPATH 199 — Add Command: Purge Poison

Effect:

- reduce poison_level

Purpose:

- add the core purification response to poison burden

🥇 EMPATH 200 — Add Purge Risk Under Strain

If the Empath is already under heavy strain:

- purge can fail or cause self-harm

Purpose:

- stop cleansing from becoming a free safety switch under overload

🥇 EMPATH 201 — Integrate Poison Transfer with TAKE

When poison is transferred:

- the Empath inherits the poison burden

Purpose:

- preserve the profession's transfer identity in purification cases too

🥇 EMPATH 202 — Add Poison Warning Messaging

Example:

- This poison feels dangerous.

Purpose:

- surface risk before players casually absorb conditions they cannot manage

### Disease system

🥇 EMPATH 203 — Add Disease State

On character, track:

- disease_type
- disease_severity

Purpose:

- treat disease as a real long-tail medical burden

🥇 EMPATH 204 — Add Disease Effects

Possible effects:

- stat penalties
- slower recovery
- other burden hooks

Purpose:

- make disease feel distinct from poison and wounds

🥇 EMPATH 205 — Add Command: Cure Disease

Effect:

- reduce disease severity

Purpose:

- add the core response tool for disease burden

🥇 EMPATH 206 — Scale Cure Difficulty by Disease Severity

Rule:

- harder diseases require repeated work or higher effectiveness

Purpose:

- prevent disease cleansing from collapsing into one-click cleanup

🥇 EMPATH 207 — Integrate Disease Transfer with TAKE

When disease is transferred:

- the Empath inherits the condition burden

Purpose:

- keep purification risks inside the same profession identity loop

### System integration

🥇 EMPATH 208 — Add Healing vs Burden Interaction

If an Empath is heavily wounded or strained:

- all healing and purification becomes less effective

Purpose:

- unify the self-management layer under one pressure model

🥇 EMPATH 209 — Add Recovery Feedback Messaging

Examples:

- You feel yourself stabilizing.
- Your condition worsens.

Purpose:

- make recovery state changes legible in live play

🥇 EMPATH 210 — Add DireTest: Empath Healing Core

Scenario must validate:

- heal wounds reduces severity instead of hard resetting
- vitality healing works separately
- poison transfer plus purge behaves correctly
- disease transfer plus cure behaves correctly
- the system remains stable under burden

⚠️ DESIGN LOCKS (181–210)

- Healing must never be an instant full reset.
- Poison and disease must feel dangerous.
- Healing must weaken under burden.
- Do not add free cleanse mechanics.

🧭 RESULT AFTER 210

After this phase, Empath no longer just takes damage correctly. It can survive accumulated damage through profession-specific tools.

You now have:

- real self-healing instead of placeholders
- wounds and vitality handled by different tools
- bleeding control
- poison lifecycle
- disease lifecycle
- risk-based healing that still respects burden

🔒 RESPONSIBILITY BOUNDARIES

Before moving into the next phase, keep these ownership lines explicit and non-overlapping:

- `TAKE` moves wounds and conditions onto the Empath.
- `heal wounds` reduces wound severity only.
- `heal vitality` restores survivability only.
- `staunch` stops bleeding only.
- `purge poison` and `cure disease` handle toxin states only.

If any one of these commands starts doing two jobs, players will find the exploit path and bypass the burden model.

🔥 NEXT PHASE (211–240)

This is the final identity layer for the core profession. It unlocks battle-Empath viability without damage creep, upgrades Perceive Health into a tactical sensing tool, and lets multiple Empaths cooperate without deleting total burden from the system.

🧱 EMPATH MICRO TASKS (211–240)

Phase: Control + Advanced Perception + Cooperation

Goal by 240:

- Empaths can influence combat without becoming damage casters
- Perceive Health becomes tactical rather than just informative
- multiple Empaths can share triage burden without erasing it
- stressed group healing scenes remain solvable but risky

### Manipulate as nonviolent combat control

🥇 EMPATH 211 — Add Command: Manipulate

Create:

- commands/cmd_manipulate.py

Usage:

- manipulate <target>

Target:

- creature/NPC only

Purpose:

- unlock the Battle Empath survival/control playstyle without turning the class into a damage dealer

🥇 EMPATH 212 — Add Manipulate Validation

Fail if:

- target is not living
- target is already controlled
- Empath is overloaded or otherwise unable to focus

Purpose:

- keep the command narrow, readable, and hard to abuse

🥇 EMPATH 213 — Implement Manipulate Core Effect

On success, choose one nonviolent outcome such as:

- remove target from combat
- reduce aggression
- redirect focus

Purpose:

- create real battlefield influence without raw damage output

🥇 EMPATH 214 — Add Manipulate vs Creature-Type Rules

Rules:

- ordinary living creatures: pacify/disengage possible
- aggressive creatures: partial success more common
- undead or corrupted/evil targets: fail or enrage

Purpose:

- preserve DR-authentic control limits and make target choice matter

🥇 EMPATH 215 — Add Manipulate Cost

Each use should increase:

- strain
- and optionally a light shock hook if later tuning needs it

Purpose:

- prevent manipulate spam from trivializing encounters

🥇 EMPATH 216 — Add Manipulate Failure Outcome

On failure:

- creature focuses the Empath
- danger increases immediately

Purpose:

- ensure control attempts carry real risk

🥇 EMPATH 217 — Add Manipulate Messaging

Tone:

- emotional and empathetic to the player
- subtle behavioral shifts to the room

Purpose:

- keep manipulate distinct from charm/domination magic fantasies

🥇 EMPATH 218 — Add Manipulate Cooldown System

Track:

- last_manipulate_time

Use:

- moderate cooldown to prevent spam loops

Purpose:

- make timing part of the decision instead of button-mashing

### Perceive Health as a tactical sensing tool

🥇 EMPATH 219 — Add Perceive Range Scaling

Extend perceive so it can weakly detect nearby suffering beyond the current room.

Initial scope:

- full same-room detail
- vague nearby signal for adjacent rooms or later expansion hooks

Purpose:

- grow perceive from a room-local utility command into a positioning tool

🥇 EMPATH 220 — Add Perceive Accuracy Scaling

If the Empath is strained:

- readings become less accurate

Purpose:

- make sense overload and burden affect information quality, not just healing output

🥇 EMPATH 221 — Add Deep Scan Mode

Command:

- perceive focus <target>

Effect:

- more detailed output
- longer cooldown

Purpose:

- create a deliberate tactical tradeoff between breadth and depth

🥇 EMPATH 222 — Add Deep Scan Risk

If the Empath is already overloaded:

- deep scans can add strain or minor self-harm

Purpose:

- keep high-fidelity sensing costly under pressure

🥇 EMPATH 223 — Add Emotional-State Detection

Perceive may reveal flavor states such as:

- fear
- panic
- calm

Rules:

- flavor only, no direct mechanics yet

Purpose:

- make perceive feel empathic, not purely medical

🥇 EMPATH 224 — Add Perceive Interference

If too many targets are present:

- output clarity degrades

Purpose:

- prevent perfect-room omniscience in crowded scenes

🥇 EMPATH 225 — Add Perceive Failure Case

If overwhelmed:

- return partial or even incorrect readings

Purpose:

- reinforce that sensing under pressure is powerful but not perfect

### Empath-to-Empath cooperation

🥇 EMPATH 226 — Add Shock Sharing Command

Command:

- take shock <target>

Purpose:

- begin the explicit multi-Empath cooperation layer

🥇 EMPATH 227 — Implement Shock Sharing Effect

Effect:

- reduce target shock
- increase self shock

Purpose:

- let Empaths carry one another through collapse states instead of only working alone

🥇 EMPATH 228 — Add Shock Sharing Limits

Rules:

- diminishing returns
- no instant full clear

Purpose:

- prevent one-command shock resets

🥇 EMPATH 229 — Add Shock Circle Behavior

Allow multiple Empaths to distribute shock across the group.

Purpose:

- support high-pressure group rescue scenes with real cooperation

🥇 EMPATH 230 — Add Shock Circle Messaging

Example tone:

- You share the burden...

Purpose:

- make cooperation legible and thematic

🥇 EMPATH 231 — Add Cooperative Triage Bonus

If multiple Empaths coordinate:

- add slight efficiency improvements

Hard rule:

- total burden does not decrease

Purpose:

- reward teamwork without erasing profession cost

🥇 EMPATH 232 — Prevent Cooperation Exploit Loops

Validate that:

- total system burden never disappears through sharing loops
- no infinite shock ping-pong or wound laundering emerges

Purpose:

- harden the cooperation layer before live players do it for you

### Group healing pressure

🥇 EMPATH 233 — Add Multi-Target Awareness UI

Enhance:

- queue

Show:

- group-level status summary

Purpose:

- help healers read crowded scenes without handing them perfect automation

🥇 EMPATH 234 — Add Priority Conflict Scenario

If multiple patients are critical:

- the Empath must choose

Purpose:

- preserve triage as a player judgment problem

🥇 EMPATH 235 — Add Group Failure State

If triage fails:

- one or more patients worsen or die

Purpose:

- keep group healing from becoming consequence-free throughput management

🥇 EMPATH 236 — Add Cooperative Recovery Flow

Allow multiple Empaths to split roles such as:

- one handles wounds
- one handles poison
- one stabilizes or shares shock

Purpose:

- support actual healer teamwork instead of parallel solo actions

### Stress and failure systems

🥇 EMPATH 237 — Add Cognitive Load System

If there are many targets and high strain:

- slow command response or reduce effectiveness

Purpose:

- represent healer overload without inventing a second fake profession resource bar

🥇 EMPATH 238 — Add Decision Pressure Messaging

Examples:

- You cannot help them all.
- Someone will die if you hesitate.

Purpose:

- make failure pressure emotionally legible in live scenes

🥇 EMPATH 239 — Add Collapse Cascade

If the Empath collapses:

- active links break
- patients degrade

Purpose:

- make healer failure propagate naturally through the scene

🥇 EMPATH 240 — Add DireTest: Empath Group Pressure

Scenario validates:

- multi-Empath cooperation
- shock sharing behaves correctly
- manipulate affects combat without trivializing it
- perceive degrades under load
- failure is possible while the system remains stable

⚠️ DESIGN LOCKS (211–240)

- Manipulate must not trivialize combat.
- Perceive must not become perfect information.
- Cooperation must not reduce total burden.
- Empaths must not become effectively invulnerable through coordination.

🧭 RESULT AFTER 240

After this phase, Empath does not just survive and heal. It can influence the battlefield and coordinate group survival while still paying the profession's cost.

You now have:

- nonviolent combat control
- advanced tactical sensing
- multi-Empath cooperation
- real group triage gameplay
- stress and failure loops that scale beyond solo play

🔥 NEXT PHASE (241–270)

We will treat the old Hand of Hodierna role as a Dragonsire-specific working name: `Resonant Channel`.

This phase adds three late-identity layers:

- passive empath sensing
- skill-based wound mitigation while taking burden
- sustained multi-target healing through Resonant Channel

🧱 EMPATH MICRO TASKS (241–270)

Phase: Resonant Channel + Mitigation + Passive Sensing

Goal by 270:

- Empaths feel nearby suffering even when not actively scanning
- advanced Empaths absorb a reduced version of incoming burden rather than always taking it one-for-one
- group healing gains a sustained, high-risk multi-target mode
- advanced empath play feels different from beginner play

### Passive empath sensing

🥇 EMPATH 241 — Add Passive Sensitivity Hook

In the character pulse/tick path:

- if character is an Empath
- and nearby injured targets exist

Then:

- emit low-frequency passive sensitivity checks

Purpose:

- give Empaths passive identity at idle, not only through explicit commands

🥇 EMPATH 242 — Add Passive Sensitivity Messaging

Examples:

- You feel a flicker of pain nearby.
- Someone close is suffering.

Rules:

- only trigger for meaningful injury states
- cooldown protected
- not spammy

Purpose:

- make Empath feel attuned to pain as a class trait, not just a button press

🥇 EMPATH 243 — Add Sensitivity Range

Initial scope:

- same room only

Future hook:

- adjacent rooms

Purpose:

- start small while leaving room for later growth

🥇 EMPATH 244 — Add Sensitivity Accuracy Scaling

If the Empath is strained:

- messages stay vague

If stable:

- messages become clearer

Purpose:

- tie passive perception quality to state, not just profession flag

🥇 EMPATH 245 — Add Critical Signal Override

If a nearby target is critical:

- bypass the normal passive-message cooldown

Example:

- A life hangs by a thread nearby.

Purpose:

- make true emergencies cut through normal ambient filtering

### Wound mitigation as mastery expression

🥇 EMPATH 246 — Add Mitigation Hook to TAKE

Modify transfer so the final burden applied can be reduced by a mitigation factor.

Shape:

- final_wound = original_wound * mitigation_factor

Purpose:

- add late-skill mastery expression to the core transfer loop

🥇 EMPATH 247 — Add Mitigation Factor

Base:

- mitigation = 0.0

Scale later with:

- empathy/healing skill
- current stability
- burden state

Purpose:

- create a progression hook instead of hard-coding perfect mitigation too early

🥇 EMPATH 248 — Add Mitigation Rules

Rules:

- cannot reduce burden to zero
- reduces severity tier rather than fully deleting harm

Examples:

- heavy -> moderate
- moderate -> light

Purpose:

- keep risk intact while making mastery feel earned

🥇 EMPATH 249 — Add Mitigation Messaging

Example:

- You absorb the worst of it.

Rules:

- no numbers
- subtle reinforcement of mastery

Purpose:

- surface improvement without turning mitigation into math UI

🥇 EMPATH 250 — Add Mitigation Penalty Under Strain

If the Empath is already wounded or overloaded:

- mitigation effectiveness drops

Purpose:

- stop mastery from overriding the burden model under stress

🥇 EMPATH 251 — Add Over-Mitigation Risk

If the Empath pushes too hard:

- strain spike
- or shock/backlash hook

Purpose:

- keep mitigation from becoming a free passive advantage with no edge-case danger

### Resonant Channel as sustained group healing

🥇 EMPATH 252 — Add Command: Channel

Usage:

- channel <target1> <target2> ...

Initial limit:

- 2 targets

Purpose:

- introduce sustained multi-target healing without direct-heal burst design

🥇 EMPATH 253 — Add Channel Requirements

Require:

- active link or touch state with each target

Fail if:

- invalid targets
- too many targets
- broken prerequisites

Purpose:

- keep the ability rooted in the existing link-first Empath identity

🥇 EMPATH 254 — Add Channel Activation State

Store a structured state such as:

- active_channel = {targets, duration, strain_rate}

Purpose:

- make channel a maintained state rather than a one-off action

🥇 EMPATH 255 — Add Channel Tick Effect

Each tick:

- take a small amount from each linked target
- apply it to the Empath

Purpose:

- create the slow pulsing group-heal identity layer

🥇 EMPATH 256 — Add Channel Throughput Rules

Rules:

- slower than manual TAKE
- burden distributed across multiple patients

Purpose:

- keep channel strong for coverage, not best-in-slot for burst response

🥇 EMPATH 257 — Add Channel Strain Scaling

Strain increases:

- per target
- per tick

Purpose:

- make sustained multi-target healing expensive in the intended way

🥇 EMPATH 258 — Add Channel Capacity Scaling

Initial:

- 2 targets

Future:

- expand toward 3-4 with progression

Purpose:

- create late-game growth without starting overpowered

🥇 EMPATH 259 — Add Channel Break Conditions

Break channel if:

- Empath overloads
- Empath moves
- target leaves room
- prerequisites fail

Purpose:

- keep the mode positional and fragile under pressure

🥇 EMPATH 260 — Add Channel Messaging

To Empath:

- You open yourself to their pain...

To room:

- subtle shared-effect messaging

Purpose:

- make the mode visible without turning it into spectacle spam

### Channel risk and failure

🥇 EMPATH 261 — Add Channel Overload

If total strain rises too high:

- force channel collapse

Purpose:

- ensure sustained healing carries real failure conditions

🥇 EMPATH 262 — Add Channel Collapse Effect

On collapse:

- links break
- Empath is stunned or otherwise compromised

Purpose:

- make channel failure costly and scene-visible

🥇 EMPATH 263 — Add Channel Warning Messaging

Before collapse:

- This is too much...

Purpose:

- give players a readable edge before failure instead of only post-failure punishment

🥇 EMPATH 264 — Add Channel Efficiency Drop

As strain rises:

- transfer efficiency falls

Purpose:

- make overextension self-limiting before full collapse

🥇 EMPATH 265 — Add Channel vs Mitigation Interaction

Mitigation applies to channel transfers too, but:

- at reduced efficiency under load

Purpose:

- unify mastery systems without letting them erase the cost of sustained healing

### Passive and active integration

🥇 EMPATH 266 — Add Passive Sensitivity to Channel Hinting

If the Empath passively detects a critical target:

- hint that channel may be appropriate

Rules:

- message hint only
- no auto-activation

Purpose:

- connect the passive identity layer to the advanced healing toolset

🥇 EMPATH 267 — Add Channel + Queue Integration

Queue should show:

- which patients are currently in channel

Purpose:

- keep triage readable when sustained healing is already in flight

🥇 EMPATH 268 — Add Multi-Empath Channel Interaction

If multiple Empaths channel the same target:

- share burden
- do not reduce total transferred harm

Purpose:

- support cooperation without introducing free efficiency from stacking

🥇 EMPATH 269 — Prevent Channel Exploits

Hard rule:

- total transferred burden must remain greater than or equal to original burden

Validate:

- no healing loops
- no burden deletion through timing tricks or multi-healer channel stacking

Purpose:

- harden the highest-risk advanced ability before live players stress it

### Validation

🥇 EMPATH 270 — Add DireTest: Empath Channel System

Scenario must validate:

- mitigation reduces severity correctly
- passive sensing triggers correctly
- channel transfers multiple targets
- channel overload works
- no exploit loops exist

⚠️ DESIGN LOCKS (241–270)

- Channel must not be safer than manual healing.
- Mitigation must not eliminate risk.
- Passive sensing must not become spam.
- Total burden must never decrease.

🧭 RESULT AFTER 270

After this phase, Empath does not only react to suffering. It anticipates, absorbs, and manages flows of pain in a way that marks clear mastery progression.

You now have:

- passive empath identity
- skill-based burden mitigation
- sustained multi-target healing
- advanced high-risk group play

🔒 PHASE LOCK

Do not proceed to long-term systems such as scars, trauma, identity, reputation, or endgame progression until EMPATH 271–290 is complete.

This next phase is mandatory. It closes the core empath ability surface rather than adding expansion systems.

🔥 NEXT PHASE (271–290)

This is the closure phase for the core toolkit.

No new expansion systems. No endgame layering.

The goal is precision, control, and completion of the existing empath action surface.

🧱 EMPATH MICRO TASKS (271–290)

Phase: Core Ability Completion Pass

Goal by 290:

- Empaths can control exactly what they take
- Empaths can buy time without healing through stabilize
- vitality becomes transferable and dangerous
- healing becomes precision-based instead of blunt
- no major gaps remain in the core empath command surface

### Stabilize as triage control

🥇 EMPATH 271 — Add Command: Stabilize

Create:

- commands/cmd_stabilize.py

Usage:

- stabilize <target>

Rules:

- Empath only

Purpose:

- let Empaths preserve a failing patient without directly healing them

🥇 EMPATH 272 — Add Stabilize Effect

Effect:

- halt wound worsening temporarily
- reduce bleeding progression rate
- do not heal

Purpose:

- create real triage control instead of forcing immediate transfer as the only answer

🥇 EMPATH 273 — Add Stabilize Duration

Add state such as:

- stabilized_until = timestamp

Rules:

- short duration
- refreshable

Purpose:

- make stabilize a timing tool rather than a permanent protection flag

🥇 EMPATH 274 — Add Stabilize Validation

Fail if:

- target has no wounds worth stabilizing
- target is already stabilized, unless refresh behavior is explicitly allowed

Purpose:

- keep the command readable and avoid meaningless spam use

🥇 EMPATH 275 — Add Stabilize Messaging

To Empath:

- You steady their condition.

To room:

- subtle relief tone

Purpose:

- distinguish stabilization from healing without making it invisible

🥇 EMPATH 276 — Add Stabilize Interaction Rules

Works with:

- bleeding
- wound worsening
- poison progression only partially, if at all

Does not:

- remove damage
- erase toxins

Purpose:

- preserve clear ownership boundaries across healing commands

### Vitality transfer as a dangerous tool

🥇 EMPATH 277 — Add Command: Take Vitality

Usage:

- take vitality <target>

Purpose:

- complete the missing vitality-side transfer surface explicitly rather than implying wounds cover everything

🥇 EMPATH 278 — Add Vitality Transfer Effect

Effect:

- target vitality is reduced or drawn out through the empathic transfer model
- the Empath pays for that through strain and self-risk

Rules:

- not a safe one-to-one conversion
- explicitly dangerous under pressure

Purpose:

- make vitality a real high-risk healing axis, not only a passive bar repaired later

🥇 EMPATH 279 — Add Vitality Transfer Risk

If the Empath has:

- low vitality
- high strain
- overload pressure

Then:

- self-harm spikes
- collapse risk rises

Purpose:

- ensure vitality transfer always feels dangerous and costly

🥇 EMPATH 280 — Add Vitality Transfer Messaging

Example tone:

- You draw out their life force...

Purpose:

- give the command a distinct, dangerous identity separate from ordinary wound transfer

### Selective transfer for precision healing

🥇 EMPATH 281 — Extend TAKE Syntax for Selective Transfer

Support forms such as:

- take arm <target>
- take chest <target>
- take head <target>
- take poison <target>

Purpose:

- give players control over what kind of burden they choose to accept first

🥇 EMPATH 282 — Add Body Part Mapping

Map categories such as:

- arm -> limb wounds
- chest -> internal wounds
- head -> critical wounds

Purpose:

- ground selective transfer in a consistent wound taxonomy

🥇 EMPATH 283 — Add Selective Validation

Fail if:

- the target does not have the requested wound type or condition

Purpose:

- prevent precision syntax from pretending to work when no valid subset exists

🥇 EMPATH 284 — Add Selective Transfer Effect

When selective TAKE succeeds:

- transfer only the matching subset
- leave unrelated wounds untouched

Purpose:

- convert TAKE from a broad instrument into a precision triage tool

🥇 EMPATH 285 — Add Selective Messaging

Example:

- You focus on the injury in their arm...

Purpose:

- reinforce intent and precision in the player experience

### Partial transfer control

🥇 EMPATH 286 — Extend TAKE Syntax for Partial Transfer

Support forms such as:

- take 25% <target>
- take 50% <target>
- take slow <target>

Purpose:

- let Empaths modulate risk instead of always committing to full extraction

🥇 EMPATH 287 — Add Percentage Transfer Logic

Model:

- transfer_amount = total_wound * percentage

Purpose:

- create readable partial triage that still respects total burden

🥇 EMPATH 288 — Add Rate-Based Transfer

Modes:

- slow -> lower strain, slower effect
- fast -> higher strain, faster effect

Purpose:

- add tempo choice without inventing a separate unrelated mechanic

🥇 EMPATH 289 — Add Partial Transfer Messaging

Example:

- You carefully draw only part of the pain...

Purpose:

- make partial transfer feel deliberate rather than underpowered

### Residual wound hook for future systems

🥇 EMPATH 290 — Add Residual Wound State

Extend the wound model with a future-facing state such as:

- residual_flag = True/False

Purpose:

- prepare scars and long-term consequences later without implementing them now

Rules:

- no gameplay effect yet
- hook only

⚠️ DESIGN LOCKS (271–290)

- Stabilize must not heal.
- Vitality transfer must always be dangerous.
- Selective take must not bypass difficulty.
- Partial transfer must not trivialize wounds.

🧭 RESULT AFTER 290

After this phase, Empath no longer relies on blunt tools. The profession can act with precision and intent across triage, transfer, and burden management.

You now have:

- full empath command surface
- precision wound control
- real stabilize gameplay
- dangerous vitality manipulation
- future-ready wound hooks without premature expansion

### Code-Facing Notes (271–290)

Implementation scaffolding only. Extend existing systems. Do not create a parallel empath subsystem.

#### Core touch points

- `commands/cmd_stabilize.py` — modify existing command, do not replace it with a new file plan
- `commands/cmd_take.py` — extend parser and routing
- `typeclasses/characters.py` — primary logic surface for empath transfer, stabilize, shock, and wound state
- `world/systems/wounds.py` — touch only if a shared wound helper is needed; do not move empath logic out of `Character` just to satisfy structure

#### 1. Stabilize

File:

- `commands/cmd_stabilize.py`

Current state:

- already exists
- already routes to `caller.stabilize_empath_target(target)` and `caller.stabilize_corpse(target)`

Implementation notes:

- keep this command thin
- validation should remain command-level only for target lookup and local presence
- all behavior belongs in `Character.stabilize_empath_target`

Character hooks:

- `typeclasses/characters.py:4753` `stabilize_empath_target`
- `typeclasses/characters.py:4782` `stabilize_corpse`

What to change:

- widen `stabilize_empath_target` from bleeding-only control into short-lived triage stabilization
- add a timestamp-style state such as `db.stabilized_until` in creation/default repair paths
- preserve the existing `apply_tend` and `sync_empath_wounds_from_resources()` flow for bleed handling
- allow stabilize to slow worsening and reduce bleed progression without removing wounds

Data hooks:

- initialize `db.stabilized_until` in `at_object_creation`
- repair missing `db.stabilized_until` in `ensure_core_defaults`

Do not:

- heal vitality
- remove wound buckets
- purge poison or disease here
- create a second stabilize path outside `Character`

#### 2. Selective take

File:

- `commands/cmd_take.py`

Current state:

- parser only supports `take <wound_type> [amount|all]`
- command forwards to `caller.take_empath_wound(wound_type, amount)`

Implementation notes:

- extend parsing instead of replacing the route
- support body-region and condition selectors while still ending in `take_empath_wound`
- pass parsed selector metadata rather than duplicating transfer logic in the command

Character hooks:

- `typeclasses/characters.py:4580` `take_empath_wound`
- `typeclasses/characters.py:3617` `normalize_empath_wound_key`

What to add in `Character`:

- a selector normalizer for inputs such as `arm`, `leg`, `chest`, `head`, `poison`
- a helper that maps selectors onto the existing wound model

Important constraint:

- the current empath wound model is scalar bucket-based (`vitality`, `bleeding`, `poison`, `disease`, `fatigue`, `trauma`), not a list of wound objects
- selective take therefore needs to use existing body-part bleed/internal state where available and fall back cleanly when only aggregate buckets exist

Do not:

- invent a new wound list model for this phase
- bypass `normalize_empath_wound_key`
- put transfer math into `cmd_take.py`

#### 3. Partial transfer

File:

- `commands/cmd_take.py`

Implementation notes:

- extend parser to recognize percentage and rate modifiers such as `25%`, `50%`, `slow`, and `fast`
- keep parser output simple: wound selector, amount mode, and transfer tempo
- forward those parsed values into `take_empath_wound`

Character hooks:

- `typeclasses/characters.py:4580` `take_empath_wound`
- `typeclasses/characters.py:4254` `get_empath_transfer_profile`
- existing shock, link-strength, and unity smoothing logic inside `take_empath_wound`

What to change:

- calculate requested amount from the current target bucket before existing efficiency math
- apply rate modifiers to strain/backlash hooks, not to wound identity
- keep total burden conservation intact

Do not:

- make partial transfer safer than normal take by default
- change mitigation rules here
- duplicate overload logic outside the current transfer path

#### 4. Vitality transfer

Files:

- `commands/cmd_take.py`
- `typeclasses/characters.py`

Current state:

- `take vitality 20` is already documented in the command help and already flows through `take_empath_wound`
- vitality is currently just one of the aggregate empath wound buckets

Implementation notes:

- treat this as a specialized branch inside `take_empath_wound`, not a separate command
- reuse `can_use_empath_ability`, link validation, shock penalties, and collapse/overdraw logic already present on `Character`
- if additional vitality-specific safety checks are needed, add them before the common transfer math branches commit state

What to change:

- make vitality transfer explicitly more dangerous than ordinary vitality bucket movement
- route consequences through existing `set_empath_wound`, `adjust_empath_shock`, overdraw checks, and roundtime hooks

Do not:

- create a new health system
- create custom collapse logic when existing empath overload/collapse hooks already exist
- make vitality transfer a safe one-to-one exchange

#### 5. Residual hook

Primary file:

- `typeclasses/characters.py`

Implementation notes:

- this phase should add data compatibility, not gameplay
- because empath wounds are currently stored as aggregate scalar buckets, the residual hook should attach to the detailed body-part or wound-resource structures that already exist, not replace `db.wounds` with a different schema
- if no shared detailed wound flag exists yet, add the lightest possible optional field where body-part wound state is already serialized

What to change:

- ensure future wound/resource entries can carry a `residual` or equivalent boolean flag
- normalize missing flags safely in any existing wound-state repair path

Do not:

- add messaging
- add mechanical penalties
- rewrite empath wound storage for this phase

#### 6. Engine rules

- reuse existing strain, shock, link stability, unity stability, and overdraw systems
- keep command files thin and `Character` methods authoritative
- all new parse branches must still end in the current empath transfer pipeline
- fail cleanly when selectors do not map to a valid current wound state

#### 7. Done criteria

- `stabilize <target>` uses the existing stabilize command path and adds timed triage control without healing
- `take` supports selective and partial inputs without duplicating transfer logic
- vitality transfer remains inside the current take pipeline and is more dangerous than baseline transfer
- residual data hooks exist without changing gameplay
- no new empath subsystem or alternate wound model is introduced
