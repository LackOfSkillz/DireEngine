# Moon Mage Guild - Comprehensive Reference v2

> Primary source of truth: live DireLore PostgreSQL data verified on 2026-04-07 from `direlore` on port `5432`.
> Tables used directly in this pass: `canon_professions`, `profession_skills`, `raw_pages`, `sections`, `page_metadata`, `entities`, and `facts`.
> Important data-quality note: the normalized link tables `profession_spells` and `profession_abilities` currently contain no Moon Mage rows in this database snapshot, so the real implementation-grade payload lives in the raw page corpus and category metadata.

---

## 1. Scope and Source Priority

This file is an implementation packet, not a lore fan writeup.

It is intended to answer these build questions for Dragonsire:

- what a Moon Mage mechanically is
- how the guild teaches and advances
- what the command surface looks like
- how lunar mana, prediction, travel, and spell prep actually work
- which spells and subsystems are core enough to anchor a first Moon Mage vertical slice

Source priority for this document:

1. `raw_pages` and `sections` for concrete mechanics and page text
2. `page_metadata` for spellbook, category, and inventory grouping
3. `canon_professions` and `profession_skills` for the normalized profession shell

When the database does not preserve a clean answer, this document says so explicitly instead of inventing one.

---

## 2. Verified Profession Identity

### Canonical profession row

- `canon_professions` identifies `Moon Mage` as profession id `16` with source entity id `776`.
- Canonical description: Moon Mages are an esoteric collective of magicians, scholars, and soothsayers known for versatile lunar magic and foretelling the future.
- Guild field: `Moon Mage`
- Role field: `magic`

### Mechanical identity

The raw Moon Mage page is very clear about the profession's real identity:

- `Magic` is primary.
- `Lore` and `Survival` are secondary.
- `Weapon` and `Armor` are tertiary.
- Mana type is `Lunar`.
- Raw page special abilities are presented as `Lunar Magic`, `Prediction`, and `Enchanting`.

Moon Mage is not just “caster with teleport.” It is a profession built from four interacting systems:

- lunar mana and spellbook-specific attunement
- astrology and prediction pools
- alignment, fate manipulation, and divination tools
- moonbeam / teleport / moongate / astral travel mobility

### Race distribution preserved on the raw profession page

The raw page includes a race breakdown:

- Elothean: 38%
- Human: 20%
- Elven: 14%
- Prydaen: 8%

This is not mechanically binding for Dragonsire, but it does show the source identity profile of the guild.

---

## 3. Guild Structure and Social Identity

### Guild crest and public identity

- Guild crest: `six towers on a field of stars encircled by the three Elanthian moons`

### Guild halls and leaders preserved by the profession page

The current DireLore corpus explicitly preserves these guild locations and leader notes:

- Crossing: a massive observatory outside the city; Celestian `Kssarh T'Kinnirii` teaches new students “with a passion that most would dub abusive.”
- Taisgath: overseen by Fateweaver `Lomtaun Nedorath of the Gypsies`.
- Shard: led by Tezirite `Mortom Saist` in the Great Tower.
- Riverhaven: Guildleader `Gylwyn` teaches in the spire guildhall north of Riverhaven.
- Hibarnhvidar: Guildleader `Cherulisa D'Shari'sendal` resides in the Spire Guildhall on the Trabe Plateau.
- Lesser Fist: historically tied to Guildleader `Tiv` and the Monks of the Crystal Hand, but explicitly noted as destroyed/closed in the preserved page text.
- Another renowned guild leader named but not deeply described: `Prophet Estrille Ardwens`.

### Sects

The profession page preserves the sect model as a major part of Moon Mage identity. It explicitly says the guild was founded by six groups unified during the `Lunar Accord`, and that sect philosophy still matters even if many players never formally join one.

Preserved sects:

- Celestial Compact: astrologers and politicians who try to shape Kermoria through knowledge of the future.
- Followers of Fortune's Path: wandering fatalists / free spirits who try to follow fate rather than dominate it.
- Monks of the Crystal Hand: stoic ascetics seeking transcendence.
- Nomads of the Arid Steppe: star-guided tribal association tied to ancestry and the heavens.
- Progeny of Tezirah: shadow magic and backroom politics.
- Prophets of G'nar Peth: seekers of esoteric knowledge associated with madness.
- Heritage House: emergent unifying school trying to reconcile the guild's divergent perspectives.

### Conclaves

The `Moon Mage Conclaves` page gives useful guild-culture framing:

- conclaves are gatherings where Moon Mages explore major visions, discuss guild affairs, and renew personal and professional ties
- in quiet years they are informal; in unstable years they become grand events
- early conclaves were more public, but tended to lose outsiders once conversation turned deeply esoteric

This is useful implementation flavor. Moon Mage guild life is not just classroom training. It is scholarly, political, prophetic, and communal.

---

## 4. Guild Space and Atmosphere

### Crossing guild feel

The profession page's single strongest spatial cue is that the Crossing guild is a `massive observatory outside the city proper`.

That gives you the right visual direction immediately:

- vertical sightlines
- instruments for observing the sky
- moonlight and star motifs
- a guild built around upward orientation, remote study, and controlled danger

### Riverhaven guildhall atmosphere preserved directly in room text

The `Moon Mage Guildhall (Riverhaven)` page is mechanically valuable because it preserves actual room descriptions.

Key atmosphere notes:

- Entrance: winding interior stairs, darkness overhead, cold blue-white `tzgaa` spheres in each riser, small paintings hidden beneath steps.
- Landing: narrow stair ascent, outdoor archway glimpse, vertical spire feel.
- Balcony: subtly-tinted glass dome, rain access to greenery beds, simple driftwood desk covered in books and parchments, Guild Leader Gylwyn present.
- Roof: open sky above, retaining wall with plant life, seating lip, a Grazhir shard `Taniendar`, and a stationary telescope.

### Implementation takeaway

Moon Mage guilds should feel like:

- observatories, towers, spires, domes, and vertical circulation
- telescopes, charts, shards, desks, books, and divination implements
- not martial barracks and not infirmaries
- dangerous scholarship rather than comfortable academia

### Atmosphere and messaging hooks worth reusing

Source-backed cues that are especially reusable for room flavor and NPC dialogue:

- Kssarh's harsh teaching reputation
- guild spaces built around telescopes and observation platforms
- books and parchments everywhere
- moon / shard / sky visibility as a daily concern
- prophecy treated as practical work, not theatrical mysticism

---

## 5. Joining, Guild Admission, and Sects

### Important gap: no clean modern guild-join ritual page is preserved

This database snapshot does **not** preserve a strong, modern, step-by-step “join Moon Mage” ritual page comparable to a clean onboarding walkthrough.

What it **does** preserve is:

- guildleader locations and starter guildhall presence
- the new player guide's guild welcome and profession-training framing
- sect representative routing and commands
- 100th circle quest structure later in progression

So the strongest honest conclusion is:

- DireLore preserves Moon Mage onboarding, philosophy, sect affiliation, and profession mechanics
- it does not preserve a single canonical dramatic first-join ritual in the same concrete way it preserves systems like prediction or astral travel

### Strongest source-backed join shape

The usable source-backed guild admission shape is:

1. Find a guildleader in a Moon Mage hall.
2. Join the profession through guild contact rather than a detached quest.
3. Begin with observations, prediction basics, spell choice, and lunar-magic training.
4. Choose a sect later, and only after understanding the social and philosophical implications.

### New player guide onboarding tone

The preserved new player guide opens with a direct welcome to the guild and immediately frames the profession around:

- training choices
- spell path decisions
- astrology and attunement
- combat vs non-combat leaning builds
- signature movement and prediction systems

That implies the class is taught as a toolkit, not as a cinematic induction trial.

### Sect joining is preserved clearly

The `Moon Mage sect representative locations` page preserves actual sect-join routing and syntax.

Critical preserved rules:

- sect representatives allow Moon Mages of appropriate skill to join a sect
- choosing based on cantrip or spell-affinity mechanics is explicitly discouraged
- the page repeatedly frames sect choice as roleplaying / identity first
- joining a sect is “more or less permanent and irreversible”
- Heritage House is the one exception: it can be joined after another sect, but doing so permanently replaces the earlier sect choice

### Preserved sect-join commands and locations

- Celestial Compact: inside the Crossing guild's sect hall; `ASK the stuffy junior officer about sect`
- Fortune's Path: Taisgath; `ASK the colorful gypsy about sect`
- Heritage House: Throne City; `GO building`, then `ASK cheerful representative about sect`
- Monks of the Crystal Hand: hidden Halls of Ith'Draknari; `PUSH crystal hand`, `GO stone wall`, `ASK hooded monk about sect`
- Nomads of the Arid Steppe: Trabe Plateau; `ASK the ancient shaman about sect`
- Progeny of Tezirah: base of the Great Tower in the Garden of Shadows; `PULL branch`, `GO bush`, `SOUTHEAST`, `ASK scarlet-robed mage about sect`
- Prophets of G'nar Peth: tent at Pathway's End of Kweld Andu; `GO tent`, `ASK blind prophet about sect`

### Dragonsire recommendation

For Dragonsire, do **not** invent a massive first-join rite unless you want to deliberately extend beyond the preserved material.

The source-backed minimum viable profession join is:

- guildleader-based profession acceptance
- immediate introduction to lunar mana, observation, and prediction
- sect affiliation delayed until after core profession identity is established

---

## 6. Circle Advancement and Requirements

### Core advancement rule

Moon Mage advancement is driven by category-based skill requirements, with two hard gates:

- `Scholarship`
- `Astrology`

The raw page and `Moon Mage 3.0` both explicitly say these are hard requirements and cannot count toward Nth-skill substitutions.

The raw pages also explicitly note:

- `Thievery` is restricted for Moon Mages and does not count toward Nth skill requirements.
- general mastery skills do not count toward Nth requirements, including `Defending`, `Parry Ability`, `Offhand Weapon`, `Melee Mastery`, `Missile Mastery`, and `Lunar Magic`.

### Circle requirement table

| Requirement | 1-10 | 11-30 | 31-70 | 71-100 | 101-150 | 151-200 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Scholarship | 3 | 3 | 3 | 4 | 4 | 10 |
| Astrology | 3 | 4 | 4 | 5 | 6 | 15 |
| 1st Magic | 4 | 4 | 5 | 6 | 7 | 18 |
| 2nd Magic | 4 | 4 | 4 | 5 | 6 | 15 |
| 3rd Magic | 3 | 4 | 4 | 5 | 5 | 13 |
| 4th Magic | 2 | 3 | 4 | 5 | 5 | 13 |
| 5th Magic | 0 | 3 | 3 | 4 | 5 | 13 |
| 6th Magic | 0 | 3 | 3 | 4 | 5 | 13 |
| 7th Magic | 0 | 0 | 3 | 3 | 4 | 10 |
| 1st Survival | 2 | 3 | 3 | 4 | 5 | 13 |
| 2nd Survival | 2 | 3 | 3 | 4 | 4 | 10 |
| 3rd Survival | 2 | 2 | 3 | 3 | 4 | 10 |
| 4th Survival | 2 | 2 | 2 | 3 | 3 | 8 |
| 5th Survival | 0 | 2 | 2 | 3 | 3 | 8 |
| 1st Lore | 2 | 3 | 3 | 4 | 5 | 13 |
| 2nd Lore | 2 | 2 | 3 | 3 | 4 | 10 |
| 3rd Lore | 1 | 2 | 2 | 3 | 3 | 8 |

### Eligible Nth-skill pools preserved in the raw page

- Armor: Shield Usage, Light Armor, Chain Armor, Brigandine, Plate Armor
- Weapon: Small Edged, Large Edged, Twohanded Edged, Small Blunt, Large Blunt, Twohanded Blunt, Slings, Bow, Crossbow, Staves, Polearms, Light Thrown, Heavy Thrown, Brawling
- Lore: Forging, Engineering, Outfitting, Alchemy, Enchanting, Mechanical Lore, Appraisal, Performance, Tactics
- Magic: Attunement, Arcana, Targeted Magic, Augmentation, Debilitation, Utility, Warding, Sorcery
- Survival: Athletics, Perception, Stealth, Locksmithing, First Aid, Outdoorsmanship, Skinning, Evasion

### 100th circle gate

The profession page preserves a hard late progression gate:

- upon promotion to 99th circle, the guildleaders task the mage with a quest for deeper cosmic understanding
- the quest must be completed before advancing to 100th circle and beyond
- completion unlocks the ability to tap the Astral Plane from anywhere by teleporting or moongating to Grazhir rather than only the three visible moons
- it also makes moon-not-up teleport failure safer by shunting the mage to the nearest Grazhir shard / conduit rather than producing the usual disastrous outcome

This is one of the profession's clearest proof points that high circle progression is tied to world traversal mastery, not just bigger spell numbers.

---

## 7. Core Skills and Training Loops

### Moon Mage training identity from the guide

The new player guide's training philosophy is explicit:

- the profession is expected to train broadly, not just rush circles
- circling grants TDPs, spell slots, and access to stronger spells, but does not itself improve execution quality
- seven magic skills, five survival skills, three lore skills, plus `Astrology` and `Scholarship`, are the minimum circling baseline presented by the guide

### Recommended long-form skill package preserved by the guide

Magic:

- Astrology
- Attunement
- Arcana
- Utility
- Augmentation
- Warding
- Targeted Magic
- Debilitation

Survival:

- Evasion
- Stealth
- Perception
- Skinning
- Locksmithing
- Athletics
- Outdoorsmanship
- First Aid

Lore:

- Scholarship
- Appraisal
- Tactics

Weapons:

- Parry
- Missile Mastery
- Melee Mastery
- Small Edged
- Small Blunt
- Light Thrown
- Bow
- Crossbow
- Sling

Armor:

- Defending
- Shields
- Light Armor
- Chain Armor
- Brigandine
- Plate Armor

### Combat identity from the guide

The guide explicitly pushes back on the idea that Moon Mages should avoid combat entirely.

It points to real combat enablers:

- `Seer's Sense` for Evasion
- `Cage of Light` for damage absorption
- `Shadows` for Stealth
- `Whole Displacement` for pulsing range control
- `Calm`, `Dazzle`, and `Sleep` for early control
- targeted spells like `Burn` and `Dinazen Olkar`

Implementation implication:

Moon Mage is a real hunting profession, but one that survives through layered control, evasion, space manipulation, and setup rather than brute armor/weapon dominance.

---

## 8. Lunar Mana, Attunement, and Spell Preparation

### Moon Mage-specific attunement model

Moon Mage attunement is fundamentally different from room-based mana professions.

Preserved rules:

- lunar mana is not primarily room-dependent
- available mana differs by spellbook and celestial conditions instead
- moons, stars, and later planets determine how much mana each lunar spellbook can access
- novices are far more at the mercy of moon phase and moon position than advanced Moon Mages

### Moon Mage power perception surface

The `Moon Mage Attunement` page preserves a much larger `PERCEIVE` surface than normal casters get.

Moon Mage perception options include:

- `PERCEIVE`
- `PERCEIVE <Katamba|Yavash|Xibar>`
- `PERCEIVE MOONS`
- `PERCEIVE <Moonlight Manipulation|Psychic Projection|Perception|Enlightened Geometry>`
- `PERCEIVE MANA`
- `PERCEIVE TELEOLOGIC SORCERY`
- `PERCEIVE PLANETS`
- `PERCEIVE <person|creature>`
- `PERCEIVE MOONBEAM`
- `PERCEIVE WATCHERS`

Special preserved benefits:

- can eventually perceive precise moon degree above or below horizon
- can identify whether a target is a magic user and what mana they use
- can see held mana, prepared spells, and active spells on targets
- can detect magical watching / clairvoyance
- can support `Backtrace`

### Attunement training loop

The guide and attunement page both preserve the practical loop:

- use `PERCEIVE MANA` on a roughly 2-minute timer
- also perceive moons, spellbooks, planets, moonbeams, area, and watchers
- Moon Mage / Trader lunar attunement training comes from perceiving a large menu of celestial states, not from “power walking” across rooms

### General spell prep rules from `Prepare_command`

The preserved general preparation layer matters because Moon Mages rely heavily on harness / cambrinth / cyclic management.

Key rules:

- `PREPARE <spell> <amount>` sets mana devoted to the spell
- that prep amount is augmented by harnessed mana and focused cambrinth mana at cast time
- omitting an amount defaults to the spell's minimum prep
- prep-hiding costs an extra 3 seconds unless the caster has the `Silent Preparation` feat

### General cast rules from `Cast_command`

Preserved cast surface includes:

- `CAST`
- `CAST <target>`
- `CAST AREA`
- `CAST ENGAGED`
- `CAST CREATURES`
- `CAST GROUP`
- `CAST SELF`

### Harness rules from `Harness_command`

- `HARNESS <amount>` stores mana for later use
- `HARNESS QUIET`, `WARN`, and `VERBOSE` control prep messaging behavior
- `MANA` can be used to inspect harness information while in RT

### Magic 3.0 prep / training rules that matter to Moon Mage implementation

The `Magic 3.0` page preserves several critical casting assumptions:

- larger casts are rewarded with better training than multiple smaller casts
- the intended best training behavior is casting at the highest amount the caster can manage
- spell difficulty depends on spell base difficulty plus mana added
- cyclic spells drain held mana per pulse and only one cyclic spell can be active at a time
- ritual spells can begin around 150 mana and reach 600 mana caps
- cambrinth is linked with `INVOKE`, and partial discharge is possible

### Moon Mage-specific spellbook and slot model

The raw profession page preserves:

- free feats at second circle: `Basic Preparation Recognition` and `Utility Mastery`
- spell slot growth for a magic-prime guild:

| Circle Range | Slot Gain |
| --- | --- |
| 1-50 | every circle |
| 51-100 | every 2 circles |
| 101-150 | every 3 circles |
| 151-200 | none |

---

## 9. Astrology, Observation, and Prediction Mechanics

### What Astrology does

The `Astrology skill` page is explicit:

- Astrology is the guild skill
- it drives study of heavenly bodies for future insight
- it supports predictions on people's abilities, event prediction, and weather prediction
- nearly 70 heavenly bodies become study targets as standing in the guild rises

### Observation loop

Preserved observation rules:

- `OBSERVE SKY` shows celestial objects currently available
- `OBSERVE <target>` makes a specific observation
- the easiest novice observation is `OBSERVE SUN`
- observations are learned gradually as circle / guild standing improve
- observation timer is approximately 2 minutes in the new player guide and 2-4 minutes random on the deeper prediction page
- telescopes make observations easier and fill pools faster
- the best telescopes are stationary in guildhalls

Observation is influenced by:

- Astrology
- Scholarship
- Perception
- Clear Vision
- Aura Sight
- telescope quality
- cloud cover

### Prediction pools

The prediction page preserves a real pool model:

- each celestial body contributes to a skillset pool
- skillset pools include `Defense`, `Event`, `Lore`, `Magic`, `Offense`, `Survival`, and `All`
- `PREDICT STATE <skillset>` shows accumulated insight for that pool
- skillset prediction pools do **not** decay over time
- the separate event pool **does** decay over time
- pool size is the largest determinant of prediction power and duration

### Prediction math

The prediction page preserves several hard numbers and constraints:

- predictions apply a bonus or penalty to one skill
- they are capped at `20% of the base skill`
- they have a `minimum effect floor of 10 ranks`
- durations run from `a few minutes` to `upwards of two hours`
- a character may have unlimited predictions active overall, but only one prediction per skill
- multiple predictions on the same skill average together
- predictions do not stack with stronger spell or buff effects; only the stronger current effect applies

### Factors that influence prediction outcome

- Astrology skill
- Wisdom
- Charisma
- prediction method
- prediction pool size
- prediction tool quality

### Divination tools and sect associations preserved by the raw page

- Celestial Charts: Celestial Compact
- Divination Bones: Nomads of the Arid Steppe
- Ornate Mirror: Progeny of Tezirah
- Sandstone Bowl: Prophets of G'nar Peth
- Sapphire Prism: Monks of the Crystal Hand
- Tokka Cards: Followers of Fortune's Path

### Align and prediction targeting

To use a prediction pool, the Moon Mage must first align.

Preserved behavior:

- `ALIGN <OFFENSE|DEFENSE|MAGIC|SURVIVAL|LORE>` aligns to a skillset pool
- `ALIGN <SKILL>` aligns to a specific skill, weighted within that skillset
- `ALIGN <...> CURSE` attempts to force a negative prediction instead of a boon
- the profession page also says `ALIGN` controls which skillset / skill is used by `Tangled Fate`

### Predict analyze

`PREDICT ANALYZE` is a real mechanical inspection tool, not fluff.

Preserved rules:

- contests Astrology and Power Perception against the target's circle and active prediction complexity
- useful with `Aura Sight`
- teaches moderate Astrology and minor Power Perception
- only teaches if at least one prediction is active
- timer is about `100 seconds`
- up to `10` active predictions are viewable

Preserved power-read scale from analyze messaging:

| Visual read | Approximate strength |
| --- | --- |
| Translucent | 1-3% |
| Flickering | 4-6% |
| Quivering | 7-9% |
| Solid | 10-12% |
| Undulating | 13-15% |
| Vivid | 16-18% |
| Luminous | 19-20% |

### Weather prediction

Preserved rules:

- syntax: `PREDICT WEATHER`
- 10-minute experience cooldown
- usable indoors or outdoors, though indoors is harder
- can be used in the Astral Plane to get a read on Grazhir stream behavior
- each returned line represents roughly 10 minutes into the future

### Event prediction

Preserved rules:

- requires `10th circle`
- learned from another Moon Mage who already has the ability
- requires at least one observation in the event pool
- event pool is filled with `STUDY SKY`
- fills faster at night and with more skill
- checked with `PREDICT STATE EVENT`
- failed attempts have no roundtime, so attempts can be spammed until one lands
- predicting on other players can reveal guild/event-specific visions

### Core implementation lesson

Prediction is not cosmetic prophecy text. It is a real buff/debuff subsystem with:

- fillable resource pools
- targeting state (`ALIGN`)
- tool loadouts
- power/duration randomness constrained by skill and pool depth
- inspection tooling (`PREDICT ANALYZE`)

This is one of the most profession-defining systems in the corpus and should be treated as such.

---

## 10. Astral Travel, Teleport, Moongate, and Mobility Stack

### Profession identity

The new player guide says the most famous Moon Mage attribute is fast long-distance movement.

The preserved movement stack is layered:

- `Focus Moonbeam`
- `Shift Moonbeam`
- `Teleport`
- `Moongate`
- Astral travel / Walking the Ways
- late-game Grazhir-anywhere transit
- `Riftal Summons` for pulling others through space

### Astral travel overview

The `Astral travel` page preserves the core loop:

1. Focus on a named Grazhir shard whose name pattern you have memorized.
2. Enter the Astral Plane via `Moongate` or `Teleport` cast on that shard.
3. Harness mana to survive the raw lunar streams.
4. `PERCEIVE` in each Astral room to navigate toward the center of the microcosm.
5. Move to the pillar associated with the destination conduit.
6. Focus the destination shard name.
7. Navigate to the end of that conduit.
8. Exit through the target shard with Teleport or Moongate again.

### Astral travel difficulty and death model

Preserved rules:

- travel is dangerous and often fatal
- not all shard names are equally easy to memorize
- Scholarship, Astrology, and Arcana all help memorization and travel
- navigation errors can strand the Moon Mage in the `Grey Expanse`
- one mistake does not instantly kill you; the page explicitly says players effectively get one mulligan per trip before real consequence rolls begin

### Astral travel survival math

The page is explicit that survival inside the plane is driven mainly by:

- concentration
- held / harnessed mana

Preserved behavior:

- raw lunar mana in the plane is deadly
- bottoming out concentration causes a gruesome death
- holding more mana reduces concentration loss and extends survival
- concentration hits grow exponentially over time
- held mana currently caps at `999`
- higher mana also changes perceive times / travel safety

### Conditions and random events

Preserved rules:

- Astral conditions vary and can worsen perceive times by several seconds each step
- conduit paths can ripple and change
- strong mana streams increase random concentration threats
- `PREDICT WEATHER` in the Astral Plane gives a read on whether conditions are improving or worsening
- denizens and random events in the plane can help, hinder, or kill

### Travel-support spells and abilities preserved directly

- `Invocation of the Spheres`: improves concentration through Discipline and Intelligence boosts
- `Aura Sight`: improves Attunement and Astrology

### Astral guide enchantment

The `Astral guide` page preserves an advanced shortcut system:

- bypasses the microcosm and takes a direct route shard-to-shard
- used by `RAISE`ing the guide at the appropriate shard
- requires Arcana and enough guide quality / power
- has charge counts and cooldown-style crafting limitations

This is probably not first-slice Dragonsire content, but it is valuable future-roadmap material.

### Teleport mechanics

Preserved Teleport rules:

- valid normal targets: `Katamba`, `Xibar`, and `Yavash`
- with `Ripplegate Theory`, predetermined locations become valid through that metaspell path
- cannot teleport another person with this spell
- arrival causes stun, sometimes knockdown
- longer teleports cause longer stun
- cross-ocean and boat teleports are harsher
- if cast on a moon that is not out, the caster is disintegrated unless they have the 100th circle ability
- can also be used to enter or leave the Astral Plane through Grazhir shards

Approximate preserved Teleport mana distances:

| Distance | Mainland | Islands | Island to Mainland |
| --- | ---: | ---: | ---: |
| 0 zones | 5 | 10 | - |
| 1 zone | 5 | 10 | - |
| 2 zones | 7 | 15 | ? |
| 3 zones | 8 | 19 | 32 |
| 4 zones | 10 | ? | 37 |
| 5 zones | 13 | - | 43? |
| 6 zones | 15 | - | 51 |
| 7 zones | 19 | - | ? |
| 8 zones | 23 | - | 79 |
| 9 zones | 27 | - | 83 |
| 10 zones | 32 | - | ? |
| 11 zones | 37 | - | ? |
| 12 zones | 43 | - | - |

### Moongate mechanics

Preserved Moongate rules:

- cyclic spell
- cast by targeting a moon or, with the 100th circle ability, `Grazhir`
- minimum `5` mana streams, maximum `45`
- post-prep harnessing increases duration, not initial strength
- around `250 Utility` is cited as the point where casting begins to become realistic
- caster can `GUARD` the gate and `NOD` people through
- cannot open to or from a boat
- maintaining the gate gets easier if the caster stands at an endpoint
- ongoing cost rises the longer the gate remains open

Approximate preserved Moongate mana distances:

| Distance | Mainland | Islands | Island to Mainland |
| --- | ---: | ---: | ---: |
| 0 zones | 5 | 6 | - |
| 1 zone | 5 | 6 | - |
| 2 zones | 6 | 8 | 10? |
| 3 zones | 6 | 8 | 12 |
| 4 zones | 6 | ? | 13? |
| 5 zones | 7 | - | 15 |
| 6 zones | 7 | - | 16 |
| 7 zones | 8 | - | ? |
| 8 zones | 9 | - | 23 |
| 9 zones | 10 | - | 24? |
| 10 zones | 11 | - | 25? |
| 11 zones | 12 | - | ? |
| 12 zones | 13 | - | - |

### Braun's Conjecture interaction

The preserved Moongate page explicitly says Braun's Conjecture can reduce mana costs by up to `20%`, down to `80%` of normal travel cost.

### Moongate atmosphere and failure messaging

This page preserves some of the best player-facing Moon Mage messaging in the corpus.

Rogue failure:

- reality tears wide open into a rogue gate tinged with screaming, razor-edged shadows
- a voidspawn may emerge and kill the caster
- or violent teleportational backlash may tear the caster apart

Gate color / mood variants:

- black gate: rippling ink with star-like points
- red gate: blazing ring of fire
- blue gate: glare and blue-white brilliance

This is useful directly for Dragonsire content writing.

---

## 11. Moonblade and Moonweapon Mechanics

`Moonblade` is one of the profession's clearest combat signatures and has unusually implementation-rich source text.

### Preserved syntax

- `CAST <moon> <refresh> <hand>`
- `SHAPE <moonblade/moonstaff>`
- `SHAPE <moonblade/moonstaff> TO <warded/unwarded>`
- `SHAPE <moonblade/moonstaff> TO <normal/small/narrow/curved/heavy/huge/blunt>`
- `SHAPE <moonblade/moonstaff> TO <primary/secondary/tertiary>`
- `SHAPE <moonblade/moonstaff> TO CAMBRINTH`
- `STUDY <moonblade/moonstaff>`
- `WEAR <moonblade/moonstaff>` to suspend it on telekinetic currents

### Preserved shape identity

The guide explicitly says Moonblade can cover these training shapes:

- small edged
- large edged
- two-handed edged
- quarterstaff / blunt form

### Tier system preserved directly

The page preserves a 3-tier quality ladder:

- Tier 3: base weapon
- Tier 4: either correct weaponsmithing technique or very strong moon influence
- Tier 5: strong moon influence **and** correct weaponsmithing technique

Comparison language preserved:

- tier 3: best storebought baseline
- tier 4: player-crafted steel equivalency
- tier 5: player-crafted rare metal equivalency

### Sliver mechanics preserved directly

Moonblade can be broken into orbiting slivers for `Telekinetic Throw` and `Telekinetic Storm`.

Hard mechanical notes preserved:

- roughly `104` Arcana begins successful sliver creation
- roughly `115-116` Arcana creates slivers consistently
- max `100` orbiting slivers
- only one moon's sliver set can orbit at once
- creating a different moon's slivers cancels matching amounts of the current set

Damage type variation on slivers:

- Katamba: piercing + impact
- Xibar: piercing + cold
- Yavash: piercing + fire

### Implementation takeaway

Moonblade is not just “summon sword.” It is:

- weapon conjuration
- weapon-form customization
- quality scaling from moon state and crafting knowledge
- future metamagic support
- ammo generation for telekinetic offense

It is a major subsystem, not a single spell.

---

## 12. Moon Mage Ability Surface

### Abilities / systems explicitly surfaced through page metadata

- Align
- Astral guide
- Astral travel
- Backtrace
- Coordinate Chart
- Divination bones
- Divination bowl
- Divination charts
- Divination deck
- Divination mirror
- Divination prism
- Moon Mage attunement
- Prediction
- Shaderald
- Star chart
- Time Sense
- Zone map

### Moon Mage command pages explicitly categorized

- `Align command`
- `Chant command`
- `Intone command`

This is a smaller command-category list than the real practical verb surface, because much of the actual Moon Mage gameplay is preserved under spell and ability pages instead.

### Real player verb surface preserved by the corpus

These are the verbs and actions the packet repeatedly references and that matter for implementation:

- `OBSERVE SKY`
- `OBSERVE <target>`
- `STUDY SKY`
- `PREDICT STATE <pool>`
- `PREDICT FUTURE <person>`
- `PREDICT FUTURE EVENT`
- `PREDICT WEATHER`
- `PREDICT ANALYZE`
- `ALIGN <skillset|skill>`
- `ALIGN <...> CURSE`
- `RECALL HEAVENS`
- `RECALL HEAVENS GRAZHIR`
- `PERCEIVE MANA`
- `PERCEIVE MOONS`
- `PERCEIVE WATCHERS`
- `PERCEIVE MOONBEAM`
- `FOCUS <shard>`
- `CAST <moon|shard>` for travel spells
- `GUARD MOONGATE`
- `NOD` to permit passage
- `ASK <representative> ABOUT SECT`

---

## 13. Spell Inventory by Spellbook

The page metadata cleanly preserves a Moon Mage spell list of `56` spells across six spellbooks.

### Perception spellbook

- Artificer's Eye
- Aura Sight
- Clear Vision
- Destiny Cipher
- Distant Gaze
- Locate
- Machinist's Touch
- Piercing Gaze
- Read the Ripples
- Seer's Sense
- Unleash

Notes:

- strongly weighted toward augmentation, utility, and divination support
- includes signature prediction / perception anchors like `Destiny Cipher`, `Read the Ripples`, and `Seer's Sense`

### Moonlight Manipulation spellbook

- Burn
- Cage of Light
- Dazzle
- Dinazen Olkar
- Focus Moonbeam
- Iyqaromos Fire-Lens
- Moonblade
- Refractive Field
- Shadow Web
- Shadows
- Shape Moonblade
- Shift Moonbeam
- Steps of Vuan

Notes:

- heavy identity concentration around moonbeams, stealth/light, and moonweapons
- contains multiple signature movement/combat-building blocks

### Psychic Projection spellbook

- Calm
- Empower Moonblade
- Hypnotize
- Mental Blast
- Mind Shout
- Psychic Shield
- Rend
- Shear
- Sleep
- Sorrow
- Telekinetic Shield
- Telekinetic Storm
- Telekinetic Throw
- Thoughtcast

Notes:

- this is the pressure / mind-control / telekinetic offense book
- supports both ranged combat and social-control flavor

### Enlightened Geometry spellbook

- Braun's Conjecture
- Contingency
- Moongate
- Partial Displacement
- Riftal Summons
- Ripplegate Theory
- Shadow Servant
- Shadowling
- Teleport
- Whole Displacement

Notes:

- this is the core travel / displacement / planar-manipulation book
- if Dragonsire wants the Moon Mage to feel correct, this book matters enormously

### Stellar Magic spellbook

- Invocation of the Spheres
- Shadewatch Mirror
- Starlight Sphere

Notes:

- small but high-impact set
- strongly tied to quest / signature status in this snapshot

### Teleologic Sorcery spellbook

- Saesordian Compass
- Sever Thread
- Sovereign Destiny
- Tangled Fate
- Tezirah's Veil

Notes:

- explicitly illegal / corrupting in the preserved material
- scroll-oriented rather than normal guild teaching

### Signature, illegal, cyclic, and ritual flags worth preserving

The metadata is unusually helpful here.

Examples:

- Cyclic: `Moongate`, `Steps of Vuan`, `Shadow Web`, `Starlight Sphere`
- Ritual: `Braun's Conjecture`, `Destiny Cipher`, `Read the Ripples`, `Invocation of the Spheres`
- Illegal: `Shadow Web`, `Mind Shout`, `Telekinetic Storm`, the Teleologic Sorcery book, and several teleologic spells
- Scroll-only in this snapshot: `Iyqaromos Fire-Lens`, `Shadow Web`, `Saesordian Compass`, `Sever Thread`, `Sovereign Destiny`, `Tangled Fate`, `Tezirah's Veil`

---

## 14. Titles and Long-Term Progression Signals

The `Moon Mage Titles` page is one of the best long-range progression sources in the corpus because it shows what the profession values.

### Early guild titles

- `Initiate Moon Mage`: at least circle 1
- `Apprentice Moon Mage`: at least circle 10
- `Journeyman Moon Mage` / `Journeywoman Moon Mage`: at least circle 20

### Early prediction ladder

- `Lucky`: 1 prediction
- `Soothsayer`, `Chiromancer`, `Palm Reader`, `Austromancer`: Astrology 10 and 5 predictions
- `Luckbringer`: Astrology 15 and 10 predictions
- `Augur` / `Daydreamer`: Astrology 20 and 25 predictions
- `Fortuneteller`: Astrology 30 and 50 predictions
- `Visionist`: Astrology 40 and 75 predictions

### Long prediction ladder highlights

- `Doomsayer`: Astrology 60 and 100 predictions
- `Dowser`: Astrology 80 and 150 predictions
- `Prophet`: Astrology 250 and 1000 predictions
- `Forecaster`: Astrology 300 and 2000 predictions
- `Harbinger`: Astrology 600 and 10000 predictions
- `Fateshaper` / `Fateshackled`: Astrology 800 and 15000 predictions
- `Alda Pelan`: Attunement 1400, Astrology 1000, 20000 predictions, plus Aura Sight and Seer's Sense

### Magic ladder highlights

- `Mentalist`: highest magic 60, Astrology 50, Calm known
- `Mesmerist`: highest magic 80, Astrology 70, Calm known
- `Ascendant`: highest magic 120, Astrology 110, Teleport known
- `Psychic`: highest magic 145, Astrology 130, Thoughtcast known
- `Occultist`: highest magic 220, Astrology 190, at least one Stellar spell known
- `Astrologist`: highest magic 780, Astrology 660, Arcana 425
- `Lightcrafter`: highest magic 850, Astrology 720, plus Dazzle, Burn, Moonblade, Cage of Light

### Travel / spell knowledge titles

- `Traveler`: Teleport known
- `Telepath`: Thoughtcast known
- `Hypnotist`: Hypnotize known
- `Astral Traveler`: knows how to use The Ways
- `Untethered`: Whole Displacement, Moongate, Contingency, Shift Moonbeam, and The Ways
- `Planeswalker`: Attunement 1500, Astrology 1000, and The Ways

### Why titles matter for Dragonsire

The title ladders prove that Moon Mage progression is not centered on raw damage alone. It values:

- astrology repetition
- prediction volume
- perception/divination
- travel mastery
- specific spell-knowledge packages
- sect identity

That is extremely useful when deciding what your advancement system should reward.

---

## 15. What the Database Does Not Cleanly Preserve

These are the major gaps in the current DireLore snapshot:

- a clean modern profession-join ritual or admission walkthrough
- a normalized spell table linked directly to Moon Mage through `profession_spells`
- a normalized ability table linked directly to Moon Mage through `profession_abilities`
- a single canonical Moon Mage guildhall map page for Crossing comparable to the rich Empath guildhall packet
- exact current production formulas for every prediction roll, travel roll, and spell difficulty calculation

That means Dragonsire should treat the following as source-backed **shape**, not exact numerical clone targets:

- prediction RNG weighting beyond the preserved caps and factors
- shard memorization difficulty curves
- full travel survival math
- exact prep-to-distance conversion on travel spells in modern live DR beyond the preserved tables

---

## 16. Implementation Takeaways for Dragonsire

If you want a source-faithful Moon Mage vertical slice, the profession should be built in this order:

### Phase 1: Profession shell

- Magic primary, Lore/Survival secondary, Weapon/Armor tertiary
- Lunar mana type
- Astrology and Scholarship as hard advancement gates

### Phase 2: First real profession loop

- `OBSERVE SKY`
- `OBSERVE <body>`
- prediction pools by skillset
- `ALIGN`
- `PREDICT FUTURE`
- readable positive/negative outcome messaging

This alone already makes the profession unique.

### Phase 3: Lunar attunement identity

- spellbook-based lunar mana rather than room-only mana
- `PERCEIVE MANA`, `PERCEIVE MOONS`, `PERCEIVE WATCHERS`, `PERCEIVE MOONBEAM`
- moon phase / horizon dependence

### Phase 4: First mobility slice

- `Focus Moonbeam`
- `Shift Moonbeam`
- short-range `Teleport`

This gives the class its signature spatial identity early.

### Phase 5: Group-defining signature spell slice

- `Moonblade`
- `Moongate`
- one divination buff like `Seer's Sense`
- one control spell such as `Calm` or `Dazzle`

### Phase 6: Long-term expansion

- Astral travel and shard memorization
- sect selection
- teleologic sorcery and corruption
- advanced prediction tools and analysis
- metaspells and moonblade shaping depth

### Minimum design truths to preserve

Do not flatten Moon Mage into “wizard with teleport.”

The database says the profession is really:

- a lunar mana specialist
- a future-reading support / curse engine
- a precision mobility profession
- a guild of sects, observatories, and dangerous scholarship

If Dragonsire preserves those four truths, the profession will feel recognizably Moon Mage even before the full 56-spell catalog exists.