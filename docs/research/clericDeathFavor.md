# Cleric / Death / Favor System Extraction

Data source: direct SQL queries against `direlore` on `localhost:5432` using `psycopg` with schema discovery, keyword search, and concept-pattern search across structured tables and text tables. Supplemental non-contradicted progression details were also preserved from public Elanthipedia pages where direlore lacked exact structured coverage.

Primary tables used:
- `public.canon_professions`
- `public.canon_spells`
- `public.canon_abilities`
- `public.facts`
- `public.entities`
- `public.relationships`
- `public.sections`
- `public.raw_pages`
- `knowledge.document_chunks`

## 1. Death System

### 1.1 Mechanics
- Death is explicitly non-permanent in the extracted data.
- Death can occur through `vitality loss` or `spirit death`.
- A dead character leaves behind a body/corpse and can remain bound to it for a limited time before decay.
- `DEPART` dissolves the mortal shell, leaves behind a grave, and sends the soul on the `starry road`.
- `DEPART` outcomes are favor-gated:
- `DEPART GRAVE` at 1 favor: lose coins, items go to grave, lose 1 favor if present.
- `DEPART COINS` at 2 favors: keep coins.
- `DEPART ITEMS` at 2 favors: keep items.
- `DEPART FULL` at 3 favors: keep both items and coins.
- Default `DEPART` behavior auto-selects by favor count: 3 favors uses full, 2 favors uses items, 1 or less uses grave.
- Death applies `Death's Sting`, a post-death stat penalty that depends on the ratio of pre-depart favors to circles.
- Best extracted `Death's Sting` ratio is `1 favor per 10 circles`.
- `Uncurse` can shorten the duration of `Death's Sting`, but does not reduce severity.
- Without favors, resurrection is blocked and altar healing is incomplete.
- `Resurrection` is a cleric spell-driven recovery flow, not a passive revive.
- `Resurrection` requires active mana infusion over time and a valid spirit in the Void.
- `Rejuvenation` is used to prepare the corpse and restore lost experience due to death.
- `Soul Bonding` prepares corpses for resurrection and restrains movement.
- `Vigil` is recommended on soon-to-expire bodies before resurrection.
- `Murrula's Flames` is a self-resurrection spell if cast before death.
- `Mass Rejuvenation` restores memories to dead bodies in an area.

### 1.2 States
- Alive.
- Dead body / corpse.
- Spirit death state: extracted as a distinct failure state for resurrection. If the target died from spirit loss, the depleted spirit cannot be found in the Void.
- Departed soul on the `starry road`.
- Grave state after depart.
- `Death's Sting` debuff state after depart.
- Corpse decay state, communicated by `PERCEIVE` as time-to-decay bands.
- `Dying` as a named intermediate state: `NOT FOUND` as a formal system state in the queried rows.

### 1.3 Constraints
- Resurrection requires at least 1 favor on the target.
- Carrying fewer than 15 favors is explicitly described as making resurrection more difficult for clerics.
- Zero favors causes three explicit penalties:
- cannot be resurrected
- maximum `Death's Sting`
- altar healing only restores enough to sustain life
- Corpse decay is time limited. `PERCEIVE` messaging bands include:
- `about a half hour`
- `less than a half hour`
- `several minutes`
- `a few minutes`
- `about a minute`
- Depart timer is tied to how long the soul remains attached to the body; the extracted text says this is based on spirit and improved by charisma.
- `Last Rites` must be performed on consecrated ground.
- `Last Rites` fails if the creature was skinned or looted first.
- `Last Rites` does not work on cursed creatures.
- `Resurrection` fails on spirit death.
- `Glyph of Warding` modifies depart cost by 1 favor and forces `DEPART ITEMS` behavior.
- New-character exceptions exist:
- first-circle characters get 5 favor-free deaths preserving items
- divine charm can grant unlimited favor-free simple depart while worn, with caveat text marked as possibly obsolete in source

### 1.4 Messaging
- Global death message system exists. Extracted examples include:
- `was just struck down`
- `was just struck down <at a location>` when the toggle is enabled
- `was just burned alive`
- `was just cremated`
- `was turned into an ice statue`
- `was smote by <Immortal>`
- `was purged by the Hounds of Rutilor`
- `was lost to the Plane of Exile`
- Room-visible corpse deterioration during resurrection window uses body-horror / fading-candle language:
- `body grows paler as the blood drains away from the skin`
- `body seems to shrivel slightly`
- `body appears to grow rigid`
- `body appears to dim, like a candle growing weaker`
- `body's appearance takes on a strikingly dark look`
- Death/favor explanatory tone is mechanical but mythic: `mortal shell`, `starry road`, `Immortal's attention`, `Death's Sting`.

### 1.5 Observed Gaps
- No single normalized structured `death_states` table was found.
- No structured table for exact resurrection mana formulas was found.
- Exact corpse decay timing curve was `NOT FOUND`.
- The strongest current DB-backed decay data is only banded messaging:
- `about a half hour`
- `less than a half hour`
- `several minutes`
- `a few minutes`
- `about a minute`
- Exact resurrection success / recovery formula was `NOT FOUND` in current normalized data.
- A legacy / obsolete raw page in direlore claims resurrection math was based on `circle of the Cleric vs. circle of the corpse` and capped raised targets at `49% Vitality`, `49% Fatigue`, and `89% Spirit Health`, but that page is explicitly marked obsolete and should not be treated as current math without confirmation.
- `Character Death Messaging` exists only as a sparse raw page/stub, not a well-normalized message table.
- Formal distinction between `dead`, `dying`, `spirit`, and `corpse` as engine enums was `NOT FOUND`.

---

## 2. Favor System

### 2.1 Resource Model
- Favors are a death-protection resource tied to the Immortals.
- The extracted definition: favors are gained through sacrifice of experience to protect against death penalties.
- Favor acquisition commonly uses `favor orbs`.
- Cleric orb color is `yellow`.
- Favor orbs have fill stages described by glow intensity:
- `glows faintly and wavers slightly`
- `glows faintly`
- `glows a pale (color), wavering slightly`
- `glows a steady pale (color)`
- `glows strong (color), wavering slightly`
- `glows a strong and steady (color)`
- overfilled orb: `no response when overfilled`
- Only two favor orbs should be carried for filling at once; additional filled orbs waste fed experience.
- Favor orbs kept off-person will eventually shatter.
- Prydaen favors use symbols rather than standard orb handling and auto-convert when full.
- Rakash favors do not require experience sacrifice and are capped at six.

### 2.2 Gain Mechanics
- General altars in Zoluren, Therengia, and Ilithi grant neutral-aspect favor orbs.
- Extracted general-altar process is consistent across the three province hubs:
- travel to the favor altar area, often with `DIR FAVOR`
- `KNEEL`
- `PRAY` three times
- `SAY` the name of one of the Thirteen neutral aspects
- `STAND`
- `GET ORB ON ALTAR`
- After receiving a general favor orb, the player must complete exit puzzles before leaving the favor area successfully.
- Puzzle count scales upward with current favor count.
- The extracted failure/abort path is `DROP MY ORB`, which destroys the orb and teleports the player back to the entrance.
- General altar locations explicitly extracted:
- Zoluren: Siergelde stone grotto west of Crossing
- Therengia: Alcove of the Font in the Blackthorn Grove mausoleum east of Riverhaven
- Ilithi: World Dragon shrine in the temple west of Shard
- Immortal-specific altars grant Immortal-specific favor orbs and require an offering item rather than the generic neutral-aspect prayer flow.
- Extracted immortal-specific altar process:
- go to the correct Immortal altar/shrine
- if needed, clean the altar with holy water first
- place the proper sacrifice item on the altar
- `PRAY`
- wait about a minute for the sacrifice to be replaced with a favor orb
- Immortal-specific altars only accept that Immortal's orbs when turning favors in.
- Resurrection altars accept favors from any Immortal.
- Cleric `Truffenyi's commune` is a direct favor-generation path, not just a devotion mechanic.
- Extracted commune syntax:
- `COMMUNE TRUFFENYI` while holding a proper favor offering or a filled favor orb
- `COMMUNE TRUFFENYI <PERSON>` while the target is kneeling and holding a proper favor offering
- The extracted note explicitly says the target-assisted version requires a bead/primer/Immortal-specific offering and not an orb.
- Favor orb fill methods:
- `RUB` the orb to drain a small amount of active experience
- `HUG` the orb to give all undrained experience
- Prydaen favor process is materially different from favor-orb use:
- acquire the appropriate symbol from the Three
- hold and `INVOKE` the symbol to drain field experience
- once full, the symbol vanishes and grants a favor automatically
- no return trip to an altar is required after filling
- Prydaen symbols split drain by source:
- `faiyka` symbol drains experience from all skillsets
- `shariza` symbol drains Magic and Lore
- `iladza` symbol drains Weapon and Survival
- Rakash favor process is also separate from normal orb filling.
- Extracted data only states that Rakash gain favors in the Awksa Dzilvawta Ala outside Siksraja, require no experience sacrifice, and cap at six.
- Cleric rituals/devotions are adjacent to favor economy because communes strain favor/devotional standing and rituals restore devotion used to support commune usage.
- Most cleric rituals found in the data grant `devotion` or `theurgy`, not direct favor. The main direct favor exceptions found are favor-orb generation and `Truffenyi's commune`.

### 2.3 Acquisition Process And Locations
- Standard neutral favor-orb loop:
- go to one of the three general altar sites
- perform the altar prayer sequence
- collect the orb
- solve the exit puzzles
- fill the orb with experience using `RUB` or `HUG`
- return/turn in the orb at an altar to convert it into an actual favor
- Immortal-specific favor-orb loop:
- travel to a dedicated Immortal altar
- if required, clean the altar with holy water
- place the approved sacrifice item on the altar
- `PRAY`
- wait for the orb to replace the offering
- fill the orb with experience
- turn it in at the proper altar; Resurrection altars accept any Immortal's favor
- Cleric-assisted loop:
- the cleric uses `Truffenyi's commune`
- either self-target while holding the proper offering/orb, or target another kneeling player holding the proper offering
- the result is a favor orb rather than an immediate completed favor
- Prydaen loop:
- obtain the correct symbol
- invoke it repeatedly or as needed to drain field experience
- when full, it disappears and grants the favor automatically
- Rakash loop:
- go to Awksa Dzilvawta Ala outside Siksraja
- no experience sacrifice required
- exact room-by-room rite/puzzle flow was `NOT FOUND`

### 2.4 Spend Mechanics
- A favor is consumed when an adventurer departs.
- A favor is consumed when a cleric is resurrected using `Murrula's Flames`.
- Sufficient favor unlocks safer depart modes (`COINS`, `ITEMS`, `FULL`).
- `Being sacrificed by a cleric` drains all favors immediately and blocks resurrection.
- Favor count affects the severity/duration of `Death's Sting`.
- Favor count affects how easy resurrection is and how much field experience can be retained.

### 2.5 Constraints
- Absolute mechanical minimum for cleric resurrection is 1 favor.
- Recommended minimum is 15 favors.
- Favor orbs cannot be safely stored off-person for long periods.
- General favor-orb acquisition areas are not fire-and-forget pickups; the player must clear puzzles to exit successfully.
- Only two favor orbs should be carried for filling at once; extra concurrent orbs waste experience.
- Immortal-specific altars only accept their own Immortal's orbs.
- Resurrection altars accept favors from any Immortal.
- Favors do not `leak`; the source explicitly marks orb leakage as a myth.
- Overfilling behavior can appear to change because orb size is recalculated from current favors/circles after redeeming or losing favors.

### 2.6 Messaging
- Core favor description uses reverent transactional language: `gaining the Immortal's attention through sacrifice of your experience`.
- Dark ritual gain message:
- `You feel that the dark gods have cracked a bleak smile of good favor at your attempts to please them.`
- Light ritual gain message:
- `You feel that the light gods have cast their benevolent gaze favorably upon you at your attempts to please them.`
- Neutral/non-aligned gain message:
- `You feel that your gods have smiled upon you for your attempts to please them.`
- Off-person orb warning messaging is sensory and escalating:
- emits glow
- pulses light
- rapid pulse is final warning before shattering
- container-carried orb may emit a faint glow or a low whine
- Prydaen symbol filling has explicit messaging:
- invoking the symbol causes part of the self to flow into it and is described as `curiously painless`
- completion messaging says the symbol vanishes and the player feels `more complete`
- `Truffenyi's commune` first-person orb creation messaging is highly Immortal-specific and ceremonial, with the offering transforming into a glowing orb through a deity-themed vision.

### 2.7 Observed Gaps
- No normalized `favor_cap` table was found for standard races.
- Exact formula for how many favors can be held by non-Rakash/Prydaen was `NOT FOUND`.
- No dedicated structured table for favor orb fill thresholds was found.
- Exact `XP -> favor orb fill` formula was `NOT FOUND`.
- The strongest DB-backed statements are qualitative only:
- all non-Rakash orbs consume `unabsorbed experience pool`
- `the more favors or circles you have, the more experience is needed to fill them`
- `one circle is the same as having one extra favor`
- favor boosters `reduce the amount of experience your favor orbs require`
- Exact altar turn-in / redemption syntax for converting a fully filled generic orb into a completed favor was only indirectly implied by the source pages and was not extracted as a clean standalone command sequence.
- Exact Rakash favor rite steps were `NOT FOUND` in the queried rows.

---

## 3. Cleric Profession

### 3.1 Role Definition
- `canon_professions` contains one structured Cleric row:
- name: `Cleric`
- guild: `Cleric`
- description: diverse worshipers of Light, Dark, and Balance Immortals
- Clerics are described as the primary conduit between mortals and the gods.
- Guide text describes clerics as `helper to those who seek protection in and from death`.
- Clerics are strongly positioned as undead specialists.

### 3.2 Core Abilities
- `COMMUNE` with gods using earned favor.
- Ritual/devotion systems to regain or strengthen standing with the gods.
- `ALIGN` to a deity/aspect for magic skill bonuses and penalties.
- `Resurrection`, `Rejuvenation`, `Mass Rejuvenation`, `Murrula's Flames`, `Soul Bonding`, `Uncurse`, `Vigil`.
- `Bless` to hit incorporeal enemies and support holy-water ritual usage.
- `Truffenyi's commune` to create or return favor orbs.
- `Meraud's commune` can consecrate a room, enabling rituals including `last rites`.

### 3.3 Skill System
- Structured skill families in `profession_skills` for Cleric are only broad buckets:
- armor
- lore
- magic
- survival
- weapon
- More specific progression data comes from section text, not from `profession_skills`.
- Primary skillset: `Magic`.
- Secondary skillsets: `Lore`, `Weapon`.
- Tertiary skillsets: `Survival`, `Armor`.
- Guild-specific skill: `Theurgy`.
- `Holy Magic` trains indirectly through casting and directly by teaching from another Holy Magic user.
- Guide text explicitly treats rituals as early `devotion/theurgy tools`.
- Clerics receive free magical feats at 2nd circle: `Augmentation Mastery` and `Efficient Channeling`.
- Exact current circle requirement tables were `NOT FOUND` in direlore-normalized data.
- Supplemental web-derived progression details preserved because they are not contradicted by direlore:
- the live Cleric page lists `Theurgy`, `Parry Ability`, and `Shield Usage` as hard circle requirements and `Attunement` as a soft requirement
- hard requirements cannot satisfy `Nth` bucket requirements; soft requirements can
- eligible `Nth` bucket pools are listed as:
- Armor: Shield Usage, Light Armor, Chain Armor, Brigandine, Plate Armor
- Weapon: Small Edged, Large Edged, Twohanded Edged, Small Blunt, Large Blunt, Twohanded Blunt, Slings, Bow, Crossbow, Staves, Polearms, Light Thrown, Heavy Thrown, Brawling
- Lore: Forging, Engineering, Outfitting, Alchemy, Enchanting, Scholarship, Mechanical Lore, Appraisal, Performance, Tactics
- Magic: Attunement, Arcana, Targeted Magic, Augmentation, Debilitation, Utility, Warding
- Survival: Evasion, Athletics, Perception, Stealth, Locksmithing, First Aid, Outdoorsmanship, Skinning
- live page exclusions from `Nth` counting: Defending, Parry Ability, Offhand Weapon, Melee Mastery, Missile Mastery, Holy Magic, plus Cleric-specific exclusions `Sorcery` and `Thievery`
- live cumulative totals include:
- total at 10th: `310`
- total at 30th: `1,110`
- total at 70th: `3,190`
- total at 100th: `5,110`
- total at 150th: `9,010`
- total at 200th: `19,010`
- live cumulative magic totals include:
- total magic at 10th: `140`
- total magic at 30th: `500`
- total magic at 70th: `1,380`
- total magic at 100th: `2,190`
- total magic at 150th: `3,840`
- total magic at 200th: `8,040`
- preserved web crafting-affiliation detail:
- one free technique slot in Artificing
- one free technique slot in Binding
- one free technique slot in Invoking
- all within Enchanting disciplines

### 3.4 Spell System
- Profession-linked spell rows in `profession_spells` for Cleric were `NOT FOUND`.
- Cleric spell data exists indirectly in `canon_spells`, `facts`, and section summaries.
- Extracted cleric-relevant examples:
- `Auspice`: augmentation; boosts charisma, spirit health, spirit regen
- `Bless`: utility; guide text says it enables holy water and incorporeal/undead interaction
- `Rejuvenation`: restores lost experience due to death
- `Mass Rejuvenation`: creates a cloud restoring memories to dead bodies in the area
- `Resurrection`: cyclic utility revive spell
- `Soul Bonding`: prepares corpses for resurrection and restrains movement
- `Uncurse`: dispels curses, offensive spells, or `Death's Sting`
- `Vigil`: equalizes spirit health of two linked players
- `Murrula's Flames`: self-resurrection if cast before death
- `Osrel Meraud`: stores cleric buff spells in an orb
- `Persistence of Mana`: attunement / pool regeneration support
- Guide text recommends early spell choices:
- `Bless`
- `Centering`
- `Minor Physical Protection`
- early combat options include `Horn of the Black Unicorn`, `Fists of Faenella`, `Soul Sickness`
- Extracted spellbook/category names from text:
- Holy Evocations
- Metamagic
- Spirit Manipulation
- Holy Defense
- Exact mana-cost / timing data that is present in direlore raw pages:
- `Resurrection`: `Prep (min/max) 5 / 50`, `Pulse Timing 18 seconds`, `Skill Range (min/max) 80 / 800`
- `Resurrection`: harnessed mana must be `<=` the mana cast into Resurrection
- `Resurrection`: `541 Attunement` with `Persistence of Mana` active or `600 Attunement` without it lets the cleric skip the harness step
- `Rejuvenation`: `Prep (min/max) 5 / 100`, `Skill Range (min/max) 10 / 600`
- `Soul Bonding`: `Prep (min/max) 1 / 33`, `Skill Range (min/max) 10 / 600`
- `Vigil`: `Prep (min/max) 5 / 100`, `Skill Range (min/max) 10 / 600`
- `Murrula's Flames`: `Prep (min/max) 300 / 800`, `Duration (min/max) 30 minutes / 90 minutes`, `Skill Range (min/max) 250 / 1000`
- Exact spell-cost curves beyond those prep ranges were `NOT FOUND`.
- Exact `Rejuvenation` decay-protection duration curve was `NOT FOUND`; the DB only states it lasts `for a time based on the amount of mana used`.
- Exact `Vigil` spirit-transfer-per-pulse curve was `NOT FOUND`; the DB only states that more mana increases the possible transfer per pulse.
- Exact `Murrula's Flames` field-experience retention curve was `NOT FOUND`; the DB only states that retention chance and amount depend on spell potency.
- Exact current resurrection recovery math was `NOT FOUND` in non-obsolete entries.
- Legacy / obsolete resurrection numbers that still exist in direlore raw pages:
- recovery cap after raising: `49% Vitality`, `49% Fatigue`, `89% Spirit Health`
- extra favor for the caster every `10 resurrections` if the caster has fewer than `15 favors`
- legacy note that outcome was based on `circle of the Cleric vs. circle of the corpse`
- Supplemental web-derived spell progression preserved because it is not contradicted by direlore:
- Clerics are listed as using `Holy mana`
- preserved spell-slot progression cadence for a primary-magic guild:
- circles `1-50`: one slot every level
- circles `51-100`: one slot every 2 levels
- circles `101-150`: one slot every 3 levels
- circles `151-200`: no additional base slots
- preserved base total by 150th circle: `92 slots`
- preserved account-based bonus-slot note:
- subscribers: `+1` immediately and `+1` at 500 ranks of Primary Magic
- premium accounts: `+2` immediately

### 3.5 Ritual System
- Rituals are a core cleric progression and devotion loop.
- Important distinction from favor acquisition: the extracted cleric ritual corpus primarily grants `devotion` / `theurgy`, not direct favors.
- Ritual categories extracted from sections:
- dark rituals
- light rituals
- non-aligned rituals
- local rituals
- miscellaneous rituals
- consecrated-ground rituals
- Some rituals require consecrated ground or a room blessed by `Meraud's commune`.
- Some rituals can use a devotional prayer mat in unconsecrated rooms.
- Beginning rituals / early devotion tools include:
- acts of humility
- dance and poetry
- preaching
- prayer
- menial humility
- planting of sirese
- incense
- offerings of sacred wine
- Examples of ritual requirements:
- holy water
- incense/wine
- altar, statue, or prayer mat
- kneeling / kissing objects
- `Bless` to sanctify wine or fill temple bath
- Some rituals are quest-gated or knowledge-gated:
- rites in guild halls cannot be deciphered until earned through holy quests
- local ritual text references knowledge of `Resurrection` and `Murrula's Flames`
- Ritual timers are explicitly mentioned:
- most non-aligned rituals: 10 minutes for devotion gain
- praying on a pilgrim's badge: 80 minutes
- tithing: 10 minutes

### 3.6 Guild Structure
- Cleric guild halls are listed in:
- Crossing
- Riverhaven
- Shard
- Ratha
- Aesry Surlaenis'a
- Mer'Kresh
- Vela'tohr Valley / Forfedhdar
- Muspar'i
- Named guild leaders extracted from profession page:
- Esuin (Crossing)
- Jelna Sarik (Riverhaven)
- Sothavi (Shard)
- Kor'yvyn (Ratha)
- Innu (Aesry)
- Eydtha (Mer'Kresh)
- Vecuto (Vela'tohr Valley)
- Anctarcarim (Muspar'i)
- `Cleric Guild` page itself contains no useful structured content in the extracted sections.

### 3.7 Guild Joining Process
- No structured join flow was found in `canon_professions`, `profession_abilities`, or `profession_spells`.
- A join flow does exist in guide/lore text from `Approaching_Acolyte`:
- find the guild with `DIR CLERIC`
- speak to guild master `Tallis`
- `ASK TALLIS ABOUT GUILD`
- `JOIN`
- after basics, `ASK TALLIS ABOUT MAGIC`
- choose an initial spell
- The same guide states Tallis continues education and controls study progression.
- Joining prerequisites beyond talking to Tallis were `NOT FOUND`.
- Current/legacy consistency issue:
- `Approaching_Acolyte` names Tallis as guild master for joining
- the Cleric page lists Esuin as Crossing guild leader
- this likely means the database preserves mixed-era sources

### 3.8 Messaging / Flavor Tone
- Cleric text uses reverent, devotional, and duty-heavy language.
- Supplemental web-derived guild flavor preserved because it is not contradicted by direlore:
- the monk outside the Crossing Cleric Guild changes greeting text by circle band at non-cleric, 1st, 10th, 20th, 30th, 50th, 70th, 90th, and `106th+`
- this implies visible social rank progression messaging in addition to mechanical progression
- Favored recurring tone elements:
- divine attention
- service to gods
- duty and devotion
- spiritual consequence
- mythic death imagery (`starry road`, soul, void)
- ritual messaging often blends liturgy with bodily sensation:
- `bleak smile of good favor`
- `benevolent gaze favorably upon you`
- `warm feeling of serenity and approval washes over you`
- dark rituals use harsher body-horror imagery, including blood loss, smoke, sizzling, and opened wounds.

### 3.9 Observed Gaps
- Structured `profession_spells` and `profession_abilities` links for Cleric are empty.
- No normalized cleric join/tutorial table was found.
- No explicit structured cleric rank ladder or per-circle unlock table was found beyond page text.
- Exact spell-slot progression for the profession as a whole was `NOT FOUND` in a normalized table.

---

## 4. Cross-System Relationships

- Death and clerics are tightly coupled through corpse prep, spirit handling, memory restoration, and resurrection.
- Favor is the main gate between death and recovery:
- no favor blocks resurrection
- low favor worsens `Death's Sting`
- higher favor improves resurrection outcomes and depart preservation
- Cleric abilities are themselves favor/devotion gated:
- communes consume or strain favor/devotional standing
- rituals rebuild devotion and support commune frequency/usefulness
- Rituals tie directly into both systems:
- `Last Rites` acts on corpses on consecrated ground
- `Bless` supports ritual materials
- `Meraud's commune` can create consecrated conditions needed for rituals
- `Truffenyi's commune` ties clerics directly into favor creation and transfer
- Resurrection workflow crosses all three systems:
- death leaves corpse and decay timer
- favor determines whether resurrection is possible/easier
- cleric spell sequence performs the recovery

---

## 5. Engineering Implications

- Implement death as a multi-state system, not a single boolean:
- vitality death
- spirit death
- corpse present with decay timer
- departed/grave state
- post-death sting state
- Favor must be a real consumable resource with at least four responsibilities:
- resurrect eligibility gate
- depart option gate
- death-penalty mitigation
- resurrection quality modifier
- Cleric recovery should be modeled as a procedure, not one instant button:
- perceive corpse timer
- optionally stabilize with `Vigil`
- prep with `Rejuvenation`
- maintain `Resurrection` infusion over time
- apply `Soul Bonding`
- complete gesture/raise
- Corpse state must preserve constraints:
- looting/skinning can invalidate rites
- cursed status blocks some rites
- spirit death blocks resurrection path entirely
- Ritual system needs environmental predicates:
- consecrated ground
- altar/statue/prayer-mat presence
- blessed items/holy water/wine/incense
- quest/unlock gating
- timer throttles for devotion gain
- Cleric progression likely needs two parallel loops:
- ordinary skill/circle advancement
- cleric-specific devotion/theurgy progression through rituals, communes, and holy quests
- Source inconsistency risk is real:
- join flow text references Tallis while location page references Esuin
- structured canon tables are sparser than section prose
- implementation work should distinguish `stable mechanic` from `legacy / guide-era flavor` before encoding NPC names or exact tutorial steps
- Messaging should preserve tonal split:
- death messaging is blunt, public, and physical
- favor messaging is devotional and transactional
- cleric ritual messaging ranges from serene approval to dark sacrificial horror

---

## 6. Raw Data Appendix

### 6.1 Tables and Columns Used
- `canon_professions(name, guild, role, description, confidence)`
- `profession_skills(profession_id, skill_name, progression_hint)`
- `canon_spells(name, spell_type, cyclic, mana_type, difficulty, prerequisites, effect, skill_range_min_max)`
- `canon_abilities(name, ability_type, tree, requirements, ability_skill, effect, messaging)`
- `facts(entity_id, key, value, source_url, confidence, provenance)`
- `entities(id, name, entity_type, entity_subtype, source_url, confidence)`
- `relationships(source_entity_id, target_entity_name, relation_type, source_url)`
- `sections(url, heading, content, section_tag)`
- `raw_pages(url, title, raw_text)`
- `knowledge.document_chunks(source_url, content, chunk_index)`

### 6.2 Structured Rows

#### `canon_professions`
- `(14, 'Cleric', 'Cleric', NULL, 0.9, 'The Clerics of Elanthia are a vastly diverse group...')`

#### `profession_skills` for profession `14`
- `armor`
- `lore`
- `magic`
- `survival`
- `weapon`

#### `canon_spells`
- `Auspice` -> `standard / augmentation`; `+Charisma, +Spirit health, +Spirit health regeneration`; prereq `Centering`; range `10 / 600`
- `Bless` -> `standard / utility`; sparse structured row, richer behavior comes from guide text
- `Mass Rejuvenation` -> `standard / utility, area of effect`; `Creates cloud that gradually restores memories to dead bodies in the area`; prereq `Circle 10`; range `80 / 800`
- `Osrel Meraud` -> `standard / utility`; `Creates an orb to store cleric buff spells`; prereq `Circle 30`; range `250 / 1000`
- `Persistence of Mana` -> `ritual / augmentation`; `+Attunement skill, +Attunement pool regeneration`; prereq `Circle 20`; range `80 / 800`
- `Rejuvenation` -> `standard / utility`; `Restores the lost experience due to death`; prereq `Centering`; range `10 / 600`
- `Resurrection` -> `cyclic / utility`; structured effect field empty in `canon_spells`, but mechanics present in `sections`
- `Soul Bonding` -> `battle / debilitation`; `Prevents advancing, retreating, and leaving the room. Prepares corpses for Resurrection`; prereq `Vigil`; range `10 / 600`
- `Soul Sickness` -> `battle / debilitation`; `Immobilizes and forces kneeling`; prereq `Centering`; range `10 / 600`
- `Uncurse` -> `battle / utility`; `Dispels offensive spell, curse, or Death's Sting on target`; prereq `Circle 5`; range `10 / 600`
- `Vigil` -> `standard / utility`; `Spirit damage, Spirit heal, Equalizes the spirit health of two linked players`; prereq `Rejuvenation`; range `10 / 600`
- `Murrula's Flames` -> found in `facts`/`entities`; effect `Self-resurrection provided it's cast before death.`

#### `facts`
- `Murrula's Flames.effect` -> `Self-resurrection provided it's cast before death.`
- `Rejuvenation.effect` -> `Restores the lost experience due to death.`
- `Soul Bonding.effect` -> `Prepares corpses for Resurrection.`
- `Vigil.effect` -> `Equalizes the spirit health of two linked players.`
- `Uncurse.effect` -> `Dispels offensive spell, curse, or Death's Sting on target.`
- `Truffenyi's commune.ability_skill` -> `commune / theurgy`
- `Truffenyi's commune.effect` -> `Convert offering into a favor orb (self or others) or return favor orb (self only).`

### 6.3 Key Text Excerpts

#### `sections` / `Death`
- `Favors`: `Obtaining favors is gaining the Immortal's attention through sacrifice of your experience in order to protect against the penalties of death.`
- `Death without Favors`: `You cannot be Resurrected.` and altar healing is only enough to sustain life.
- `DEPART ing`: soul takes a trip on the `starry road`; body attachment time is based on spirit; first-circle favor-free death protection is documented.

#### `sections` / `Favor`
- `Zoluren`, `Therengia`, `Ilithi`: all three general altar hubs use the same base sequence: `KNEEL`, `PRAY` three times, `SAY` a neutral aspect, `GET ORB ON ALTAR`, then clear exit puzzles.
- `Gaining Favors from Immortal-Specific Altars`: use a proper offering item, `PRAY`, wait about a minute, and receive a favor orb; some neutral/dark aspect altars must first be cleaned with holy water.
- `How to Fill Favor Orbs`: `RUB` drains a small amount of active experience; `HUG` gives all undrained experience.
- `Favor orb sources`: direct sources are general altars, Immortal-specific altars, and player-character clerics using `Truffenyi's commune`.

#### `sections` / `Prydaen_Favors`
- `Invoking`: hold and invoke the symbol to drain field experience; when full it vanishes and grants a favor automatically.
- `Symbols`: different symbols drain different skillset groupings.

#### `sections` / `Truffenyi's commune`
- `Usage`: `COMMUNE TRUFFENYI` while holding a proper favor offering or a filled favor orb; `COMMUNE TRUFFENYI <PERSON>` while they are kneeling and holding a proper favor offering.
- `First Person Messaging`: orb creation is represented as deity-specific transformation imagery around the offering.

#### `sections` / `Resurrection`
- `Usage`: `PERCEIVE <BODY>` -> verify favor -> `Vigil` if needed -> `Rejuvenation` until silver nimbus -> `PREPARE REZZ`/`CAST` -> `HARNESS` -> `INFUSE REZZ` -> `Soul Bonding` -> final `GESTURE <BODY>`.
- `Notes`: spirit death prevents finding the spirit in the Void; devotion threshold required; retained field experience depends on favors.
- `Visible to room`: body grows paler, shrivels, grows rigid, dims like a candle.

#### `sections` / `Cleric`
- `Communes`: clerics call upon favor earned through devotion; rites are guild-hall references; some rites require holy quests to decipher.
- `Devotion`: clerics in high favor have enhanced magic; neglected devotion causes fading ability.

#### `sections` / `Cleric_3.0`
- `Rituals`: `Last Rites` must be on consecrated ground and fails after skinning/looting or on cursed creatures.
- `Infusion`: clerics with both infusion and `Rejuvenation` may restore their own memories while dead.
- `Theurgy`: guild-specific skill powering god-related abilities.

#### `web` / `Cleric`
- preserved web `Crafting Affiliation`: guilded clerics receive one free Enchanting technique slot each in Artificing, Binding, and Invoking.
- preserved web `Circle Requirements`: live page includes the full per-band table for armor, weapon, lore, magic, and survival requirements through 200th circle.
- preserved web `Cumulative`: live page includes cumulative totals through 200th circle, including `all.Total = 19,010` and `magic.Total Magic = 8,040` at 200th.
- preserved web `Miscellaneous`: Crossing guild monk greeting changes at 1st, 10th, 20th, 30th, 50th, 70th, 90th, and `106th+` circles.

#### `web` / `Spell_slot_progressions`
- preserved web note: Clerics use the `Primary` spell-slot track because Cleric is a primary-magic guild.
- preserved web total base slots by 150th circle: `92`.
- preserved web cadence: every level to 50, every 2 levels to 100, every 3 levels to 150, none after 150.

#### `sections` / `Cleric_guide`
- `Beginning rituals:` explicitly identifies early devotion/theurgy training tools.
- `Hunting the Undead`: clerics are the strongest undead hunters and need blessed weapons to hit incorporeal foes.
- `Spell Paths and Choices`: recommends `Bless`, `Centering`, and `Minor Physical Protection` as early spells.

#### `sections` / `Cleric_rituals`
- dark gain message: `the dark gods have cracked a bleak smile of good favor`
- light gain message: `the light gods have cast their benevolent gaze favorably upon you`
- neutral gain message: `your gods have smiled upon you`
- `Consecrated ground` section describes altar/statue/prayer-mat ritual execution model.

#### `sections` / `Approaching_Acolyte`
- joining flow: `ASK TALLIS ABOUT GUILD`, `JOIN`, `ASK TALLIS ABOUT MAGIC`
- role framing: cleric as one who protects others `in and from death`

#### `raw_pages` / `Character_Death_Messaging`
- page exists but is a stub
- contains global death message examples like `was just struck down`, `was just struck down <at a location>`, `was just burned alive`, `was turned into an ice statue`, `was smote by <Immortal>`

### 6.4 Notable Missing or Sparse Records
- `profession_spells` rows for Cleric: `NOT FOUND`
- `profession_abilities` rows for Cleric: `NOT FOUND`
- normalized cleric join table: `NOT FOUND`
- normalized death-state enum table: `NOT FOUND`
- normalized favor-cap/scaling formula table: `NOT FOUND`
