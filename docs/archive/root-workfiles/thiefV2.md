# Thief Profession and Guild Deep Dive

> Query date: 2026-04-08
> Database: local PostgreSQL `direlore` on port `5432`
> Project overlay: `direlore`
> Primary domains used: `mechanics`, `experience`, `lore`, plus profession tables under the shared schema contract
> Contract packet source: `agent_active_instructions_v`, `agent_active_project_overlay_v`, `agent_query_playbooks_v`, `agent_schema_contract_v`

## Answer

The current DireLore snapshot supports a strong Thief packet for profession identity, circle requirements, khri mechanics, ambush progression, stealth and thievery training, urban bonus and confidence behavior, and the global experience math that governs how skill ranks are earned. The strongest sources are raw section text on the `Thief`, `Thief new player guide`, `Khri`, `Thief ambushes`, `Mark`, `Slip`, `Snipe`, `Urban bonus`, and `Experience` pages.

The database does **not** currently preserve a clean, fully normalized thief ability model. `profession_abilities` is empty for Thief, the Thief entity has no useful fact rows, and `canon_abilities` only covers part of the khri tree. Because of that, the most trustworthy answer for thief mechanics comes from `sections` first, with `raw_pages`, `entities`, `canon_professions`, and partial `canon_abilities` used only as corroboration.

In short:

- Thieves are Survival-primary, with Weapon and Lore secondary, and Magic and Armor tertiary.
- Circling is heavily Survival-driven, with Stealth and Thievery as soft requirements.
- Guild joining is intentionally secretive; the preserved text treats admission itself as the first test, not a public ritual.
- Khri is the core supernatural system, fueled by concentration, gated by circle, skill, confidence, and urban context.
- Ambushes, Mark, Blindside, Slip, Snipe, Contacts, Passages, Sign Language, and urban/confidence systems define the non-khri thief toolkit.
- Skill ranks and pool sizes follow the global Experience 3.0 formulas, so thief learning speed depends on skillset placement, ranks, Intelligence, Wisdom, and Discipline.

## Playbook Used

- `mechanics_lookup` for thief abilities, khri, ambushes, urban bonus, confidence, and contested-action behavior.
- `experience_lookup` for skill rank math, experience pool formulas, pulses, mindstates, and stat scaling.
- `lore_lookup` for guild secrecy, leadership, passages, and institutional guild behavior.
- No `profession` playbook exists in the current contract views, so profession identity was assembled under the shared schema contract and project overlay rules.

## Source Path Used

Primary source path used:

`sections -> raw_pages -> entities -> canon_professions -> canon_abilities`

Most important pages:

- `https://elanthipedia.play.net/Thief`
- `https://elanthipedia.play.net/Thief_new_player_guide`
- `https://elanthipedia.play.net/Khri`
- `https://elanthipedia.play.net/Thief_ambushes`
- `https://elanthipedia.play.net/Mark`
- `https://elanthipedia.play.net/Slip`
- `https://elanthipedia.play.net/Snipe`
- `https://elanthipedia.play.net/Urban_bonus`
- `https://elanthipedia.play.net/Experience`

## Source Quality

- High confidence, raw-backed: skillset identity, circle requirements, khri costs and prerequisites, ambush progression, stealth/thievery training, experience rank math, pool formulas, pulse timing.
- Medium confidence, raw-backed: Contacts, Slip progression, Sign Language, Voice Throw, Snipe learning flavor, confidence details, province-level guild leadership.
- Low to medium confidence: a fully exhaustive normalized list of all thief abilities, because the structured ability layer is incomplete.

## Structure Gaps

- `profession_abilities` has no thief rows.
- The promoted Thief entity currently has no useful fact rows for abilities, join flow, or progression rules.
- `canon_abilities` includes only part of the khri set and does not cover the full thief toolkit.
- Join ritual data is intentionally sparse in raw text and not normalized at all.
- Several thief features exist only as prose fragments in section text instead of clean rows: Contacts, Sign Language, Voice Throw, confidence, urban bonus, reputation punishments.
- The experience page preserves most formulas, but a few wiki-rendered math expressions are lost in section export and have to be reconstructed from the prose and tables.

## Storage Recommendation

- Add a normalized `profession_abilities` population pass for thief abilities, ambushes, and non-khri profession verbs.
- Add a `guild_join_flows` or equivalent structured raw model for hidden-guild induction logic and province-specific join gating.
- Promote khri rows uniformly, including tree, tier, slot cost, startup cost, pulse cost, prerequisites, learned-at circle, and effect summary.
- Promote urban bonus, confidence, and reputation into explicit mechanic-rule rows rather than leaving them as prose.
- Promote training links such as `ability -> trains skill` and `skill -> common training verbs` into fact or mechanic tables.

## 1. Profession Identity

The Thief page describes the profession as more than shoplifting. The profession identity is built around stealth, thievery, locksmithing, traps, hidden movement, concentration-based khri, and city-focused opportunism.

Confirmed identity points:

- Thieves are `Survival` prime.
- `Weapon` and `Lore` are secondary.
- `Magic` and `Armor` are tertiary.
- The guild treats most of its own abilities as in-game secrets.
- The guild operates through hidden halls, passages, dens, and criminal infrastructure rather than public-facing institutions.

Directly confirmed profession summary from `canon_professions`:

> Beyond skulking in shadows and relieving the careless of their burden of coin, Thieves' superior stealth, hyper-aware senses, and familiarity with locks and traps make them valuable additions to any adventuring party.

## 2. Guild Structure and Culture

### 2.1 Core guild tone

The strongest guild-level statement in the raw corpus is the guild-hall access line:

> "That is a secret -- think of gaining entry to the guild as your first test."

That matters because it frames the Thief guild as:

- hidden by design
- selective by design
- culturally suspicious of outsiders
- more interested in proving discretion than delivering a public initiation speech

### 2.2 Province leadership currently preserved

The `Thief` page preserves these guild leadership anchors:

- Zoluren: Kalag the Sly
- Therengia: Crow and Swan
- Muspar'i: Kingpin Wulras
- Ilithi: Saishla
- Qi'Reshalia: Dwillig
- Forfedhdar: Ivitha

### 2.3 Council and infrastructure

The database also preserves:

- `Thief Council`: the governing body of the Five Provinces guilds, though "little is known"
- `Passages`: thief-only shortcuts and hideouts across cities
- `Contacts`: city-based underworld operatives who perform errands for thieves
- `Pretend Guild`: a concealment and roleplay system to obscure real guild affiliation

## 3. Joining Rituals and Admission

This is one of the places where the DB is explicit about tone but sparse on implementation detail.

What the current snapshot **does** confirm:

- admission is intentionally secret
- the player is not told how to join in public-facing newbie help
- secrecy itself is treated as the first test
- once inside, the guild begins normal training immediately

Evidence:

- `Thief -> Guild Hall Locations`: "think of gaining entry to the guild as your first test"
- `Thief new player guide -> Getting Started`: "If you don't know how to join the guild, you won't be learning how to do it here."

What the current snapshot does **not** confirm cleanly:

- a full normalized join ritual
- a public step-by-step induction command chain
- specific stat gates for joining
- whether the hidden-entry test differs by province in a codified way

Best-supported conclusion:

- The thief guild does not present joining as a public ceremonial ritual.
- The preserved onboarding behavior is secrecy-first, local-knowledge-first, and anti-spoiler by design.
- The hidden entrance and the act of finding it are part of the initiation fantasy.

## 4. Skillsets and Circle Requirements

### 4.1 Skillset placement

Confirmed from `Thief -> Skillset`:

- Primary: Survival
- Secondary: Weapon, Lore
- Tertiary: Magic, Armor

This matters mechanically because Experience 3.0 gives larger pools and faster pulse behavior to prime skills than tertiary ones.

### 4.2 Circle requirement table

Confirmed from `Thief -> Circle Requirements`:

| Skillset | Requirement | 1-10 | 11-30 | 31-70 | 71-100 | 101-150 | 150+ |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Survival | Thievery | 2 | 3 | 3 | 4 | 4 | 10 |
| Survival | Stealth | 2 | 2 | 3 | 3 | 4 | 10 |
| Survival | 1st Survival | 4 | 4 | 5 | 5 | 6 | 15 |
| Survival | 2nd Survival | 4 | 4 | 4 | 5 | 6 | 15 |
| Survival | 3rd Survival | 3 | 4 | 4 | 5 | 6 | 15 |
| Survival | 4th Survival | 3 | 4 | 4 | 5 | 6 | 15 |
| Survival | 5th Survival | 3 | 4 | 4 | 4 | 5 | 13 |
| Survival | 6th Survival | 2 | 3 | 4 | 4 | 5 | 13 |
| Survival | 7th Survival | 2 | 3 | 3 | 4 | 5 | 13 |
| Survival | 8th Survival | 1 | 2 | 2 | 3 | 3 | 8 |
| Weapon | Parry Ability | 1 | 2 | 2 | 3 | 3 | 8 |
| Weapon | 1st Weapon | 3 | 3 | 4 | 4 | 5 | 13 |
| Weapon | 2nd Weapon | 1 | 2 | 3 | 3 | 4 | 10 |
| Lore | 1st Lore | 1 | 2 | 3 | 3 | 4 | 10 |
| Lore | 2nd Lore | 1 | 2 | 2 | 3 | 3 | 8 |
| Lore | 3rd Lore | 1 | 1 | 2 | 2 | 3 | 8 |
| Armor | 1st Armor | 2 | 2 | 2 | 3 | 3 | 8 |
| Magic | Inner Magic | 1 | 2 | 3 | 3 | 4 | 10 |
| Magic | 1st Magic | 1 | 2 | 2 | 3 | 3 | 10 |
| Magic | 2nd Magic | 0 | 0 | 2 | 2 | 4 | 8 |

Critical rule:

- `Stealth` and `Thievery` are soft requirements and may count toward the Nth Survival requirements.

### 4.3 Practical interpretation

The guild is strongly biased toward broad Survival development first, then enough Weapon, Lore, Armor, and Supernatural development to keep thief tools online.

The practical minimum circle plan is therefore:

- keep `Stealth` and `Thievery` moving at all times
- maintain eight viable Survival skills
- keep two weapon skills plus Parry active
- keep three Lore skills active
- keep at least one armor and the core supernatural skills active

## 5. What Skills the Guild Expects You to Train

### 5.1 Survival skills

The raw pages repeatedly point to these as core thief training skills:

- `Stealth`
- `Thievery`
- `Athletics`
- `Backstab`
- `Evasion`
- `Locksmithing`
- `Perception`
- `Outdoorsmanship`
- `First Aid`
- `Skinning`

The guild states that thieves need to train a minimum of eight Survival skills consistently.

### 5.2 Weapon skills

The recommended weapon package is:

- one melee weapon for general combat and Parry support
- `Small Edged` for backstabbing
- `Bow` or `Crossbow` for later ranged stealth play
- `Brawling` for thief maneuvers and support skills
- `Light Thrown` for dirt-based ambush support

### 5.3 Lore skills

Best-supported lore package from the guide:

- `Appraisal`
- `Tactics`
- `Scholarship` or a craft

Why these matter:

- `Appraisal` improves `MARK`
- `Tactics` supports non-damaging attack play and target analysis
- `Scholarship` supports teaching, listening, charts, and general utility

### 5.4 Supernatural skills

Thieves use only part of the magic skill family:

- `Inner Magic`
- `Augmentation`
- `Utility`
- `Debilitation`
- `Warding`

Thieves do **not** learn `Targeted Magic` or `Attunement` in normal thief play.

## 6. How Thieves Train Their Skills

This section answers the practical "what trains ranks" part of the request.

### 6.1 Stealth

Confirmed training methods:

- `HIDE`
- `STALK`
- `SNEAK`
- hiding during combat
- attacking from stealth
- `POACH`
- `SNIPE`

Best-supported guidance:

- stealth trains best around valid observers or creatures
- combat hiding is one of the strongest training methods
- the classic close-range loop is hide -> approach -> backstab or ambush

### 6.2 Thievery

Confirmed training methods:

- `STEAL` from shops, NPCs, players, and the Throne City Museum
- shoplifting is the recommended standard training route

Important mechanics:

- lighter and cheaper items are easier to steal
- repeated steals from the same target get harder
- the target's guard resets after one hour
- marking items helps gauge theft difficulty before acting

### 6.3 Backstab

Confirmed behavior:

- Backstab is both a skill and a thief-only attack style
- it does **not** have a hard circle requirement
- it is still strongly recommended because it is central to thief combat

Confirmed training routes:

- normal `BACKSTAB` on valid targets
- thief ambushes also train `Backstab` to a minor degree
- ordinary attacks from hiding do **not** train Backstab by themselves

Backstab constraints:

- weapon must be under 30 stones
- weapon must be small edge and thrusting in the older newbie-guide description
- the guide treats two-legged targets as the default easy case

### 6.4 Debilitation

Confirmed training routes:

- thief ambushes train `Debilitation`
- some khri also use `Debilitation`
- Debilitation learning is contest-based against similarly capable creatures

Important note from the guide:

- Debilitation learning is based on stat comparison, not just the raw skill number.

### 6.5 Inner Magic and other supernatural skills

Confirmed training behavior:

- khri uses the supernatural skillset
- `Inner Magic` trains while training the other supernatural skills
- augmentation khri train augmentation-style learning
- utility khri train utility-style learning
- debilitation khri or ambushes train debilitation

### 6.6 Perception

Confirmed training routes:

- `MARK` teaches `Perception`
- `COLLECT`
- `HUNT`
- identifying traps and locks on boxes
- juggling some items

### 6.7 Appraisal

Confirmed training routes:

- `MARK` teaches `Appraisal`
- normal appraisal of gear and creatures also supports it

### 6.8 Outdoorsmanship

Confirmed training routes:

- `FORAGE`
- `COLLECT`
- herb gathering

### 6.9 First Aid

Confirmed training routes:

- stopping bleeding
- removing arrows and bolts
- removing parasites
- studying anatomy charts

### 6.10 Locksmithing

Confirmed or strongly implied routes:

- box trap and lock work
- lockpick carving support mechanics
- `GLANCE` becomes available at 100 `Lockpicking` to preview box traps and locks

### 6.11 Athletics and Evasion

Confirmed routes:

- `Athletics`: climbing and swimming obstacles
- `Evasion`: direct combat use

### 6.12 Skinning

Confirmed route:

- `SKIN` creature corpses

Important thief-specific limitation:

- many creatures ideal for backstabbing are poor skinning targets, so the guide explicitly recommends varying hunting targets.

## 7. Core Thief Ability Systems

## 7.1 Urban bonus, reputation, and confidence

These are not cosmetic. They are core thief mechanics.

### Urban bonus

Confirmed behavior:

- applies to non-combat survival skill performance
- depends on the room's urban level
- checked with `SMIRK SELF`
- can be `very urban`, `urban`, `neutral`, or `wilderness`
- directly raises effective ranks for contested actions
- cannot be negative by itself
- does not affect `Evasion` or `Perception`

### Reputation

Confirmed behavior:

- province-specific guild standing exists
- being caught committing crimes lowers reputation
- low enough reputation can deny guild support
- lowest reputation can cause the guild to kill the thief on entry
- reputation can be improved with stolen-good donations, guild tasks, and staying clear of local law trouble

### Confidence

Confirmed behavior:

- confidence reflects how the thief feels about their own skill
- high confidence improves performance
- low confidence hinders base ranks by 5%
- low confidence can negate urban bonus
- current confirmed modifiers are `Stealth`, `Blindside`, and `Thievery`
- starting khri checks confidence, so low confidence can lock a thief out of some khri starts

### Combined interpretation

Thief effective performance in many actions is not just raw ranks. It is:

- raw skill ranks
- plus or minus confidence effects
- plus urban bonus in city-friendly rooms
- plus any khri or other effective-rank modifiers

That means two thieves with the same sheet ranks can perform very differently in practice.

## 7.2 Mark

Confirmed mechanics:

- thief-only command
- gauges difficulty for stealing, stalking, hiding, and backstabbing
- uses effective ranks, not raw ranks
- teaches both `Appraisal` and `Perception`
- gives better information the more skilled the thief is relative to the target

Confirmed training details:

- creature mark timer: 1 minute per creature for repeat experience
- shop marks do not appear to have the same training timer, but repeated marking can trigger shopkeeper attention
- harder items teach more than easier items

Confirmed practical uses:

- shoplifting difficulty preview
- player theft difficulty preview
- fight matchup preview
- wealth and coin read on marked characters

## 7.3 Blindside and Backstab

The raw snapshot splits older Backstab guidance and newer Blindside guidance.

Confirmed Blindside mechanics:

- surprise melee attack from hiding
- successful blindside adds major damage
- the first successful damaging blindside gets an "alpha strike" boost for roughly 30 seconds
- successful blindside uses shield-ignoring behavior and imposes roughly a 15% defensive penalty on average
- target may still evade even on a technically successful blindside
- damage increases as the Stealth vs Perception success margin increases
- urban bonus influences blindside via stealth support
- successful blindsides can raise confidence

Confirmed targeting rules:

- success is based on attacker `Backstab` vs target `Perception`
- target area depends on success margin
- no extra setup beyond hiding and using blindside

Confirmed weapon notes:

- allows light and medium edged and blunt weapons
- medium weapons use the smaller of `30 stones` or `Strength` as the weight cap
- blindside damage weighting depends on weapon profile, with puncture-heavy edged setups favored in the old explanation

## 7.4 Ambushes

Global ambush behavior:

- must be hidden or invisible and engaged
- stealth contest is attacker `Hiding/Stealth` vs defender `Perception`
- success adds a hit bonus to the attack
- for thieves, ambush-related actions can teach `Backstab`

Thief-specific ambush rules:

- special thief ambushes use `Stealth`, `Backstab`, `Debilitation`, a weapon skill, and a stat contest
- they are part combat and part magic
- they train `Debilitation` and minor `Backstab`

### Thief ambush progression

| Ability | Type | Slots | Prereqs | Effect |
| --- | --- | ---: | --- | --- |
| Ambush Choke | debilitation | 1 | 3rd circle | `-Stamina`; fatigue damage |
| Ambush Stun | debilitation | 2 | 25th circle | head damage and variable-duration stun |
| Ambush Screen | debilitation | 2 | 30th circle, Ambush Choke | `-Perception`; random roundtime to all engaged targets on success |
| Ambush Slash | debilitation | 2 | 39th circle | prevents retreat/movement briefly and can drop target to knees on high success |
| Ambush Clout | debilitation | 2 | 50th circle, Ambush Stun | concentration damage, pulsing drain, can strip a prepared spell |
| Ambush Ignite | ambush | 2 | Ambush Slash | lowers armor value by damaging armor, or deals physical damage to unarmored areas |

Where to learn them:

- Kalag the Sly: Choke
- Dwillig: Screen, Slash, Stun
- Saishla: Ignite
- Ivitha: Clout

## 7.5 Khri

Khri is the largest and most mechanically detailed thief subsystem in the current snapshot.

### Core khri rules

Confirmed from `Thief` and `Khri` pages:

- thief-only concentration abilities
- all guild leaders teach the full khri list
- concentration has an upfront startup cost and usually a pulse cost
- khri pulse every 12 seconds
- khri can be stacked without an extra stacking surcharge
- starting multiple khri at once has a skill check
- start difficulty is modified by urban status and confidence
- kneeling, sitting, or lying down can make difficult khri easier to start
- delayed start can enhance power in many cases
- khri duration depends on skill and difficulty
- stopped khri go on cooldown, usually from 5 seconds to 3 minutes depending on skill and difficulty

### Khri slots

Confirmed slot progression:

- 1 slot at 1st circle
- 1 slot at 2nd circle
- then 1 slot every 2 circles through 102nd circle
- then 1 slot every 3 levels starting at 105th circle
- total from circling: 68 slots
- Premium gets an extra slot at 1st circle
- Standard gets an extra slot at 50th circle or 500 Inner Magic ranks, whichever comes first
- current total cost for all khri and ambushes is given as 74 slots, so a thief cannot learn literally everything

### Khri startup thresholds

Confirmed approximate standing thresholds from `Khri -> General information`:

- Tier 1 while standing: about 50 magic ranks
- Tier 2 while standing: about 100 magic ranks
- Tier 3 while standing: about 150 magic ranks
- Tier 4 while standing: about 250 magic ranks
- special note: with neutral confidence, Tier 3 can reportedly be started outside town at about 80 ranks

### Khri cost math

Confirmed costs:

- Tier 1: startup 8, pulse 2
- Tier 2: startup 12, pulse 3
- Tier 3: startup 16, pulse 4
- Tier 4: startup 20, pulse 5
- Tier 5: startup 25, pulse 6
- Special one-time costs: Calm 25, Eliminate 35, Vanish 30

Concentration per minute is:

$$CPM = pulse\ cost \times 5$$

Because khri pulse every 12 seconds, there are 5 pulses per minute.

Examples:

- Tier 1 khri: `2 x 5 = 10 CPM`
- Tier 2 khri: `3 x 5 = 15 CPM`
- Tier 3 khri: `4 x 5 = 20 CPM`
- Tier 4 khri: `5 x 5 = 25 CPM`
- Tier 5 khri: `6 x 5 = 30 CPM`

### Khri command set

- `KHRI START <name>`
- `KHRI <name> <name> ...`
- `KHRI DELAY <name> <name> ...`
- `KHRI STOP`
- `KHRI STOP <name>`
- `KHRI CHECK`
- `KHRI MEDITATE`
- `KHRI HELP`
- `ASK <leader> ABOUT <khri> UNLEARN` once every 30 real-life days
- `TEACH KHRI <khri> TO <person>`

### Khri catalog

| Khri | Tree | Tier | Slots | Cost | Prereqs | Effect |
| --- | --- | --- | ---: | --- | --- | --- |
| Hasten | Finesse | 1 | 1 | 8 + 2/pulse | none listed | chance for `-1/-2 sec` roundtime on melee/thrown attacks, trap disarm, box picking, armor wear/remove in combat |
| Adaptation | Finesse | 2 | 1 | 12 + 3/pulse | Hasten | reduces damage from repeated strikes in a short window |
| Avoidance | Finesse | 2 | 1 | 12 + 3/pulse | Hasten | `+Reflex` |
| Safe | Finesse | 2 | 2 | 12 + 3/pulse | Hasten, 14th circle | `+Locksmithing`; chance to dodge a blown trap |
| Plunder | Finesse | 2 | 2 | 12 + 3/pulse | Hasten | `+Thievery`, `+Discipline` |
| Elusion | Finesse | 2 | 2 | 12 + 3/pulse | Avoidance | `+Brawling`, `+Evasion` |
| Muse | Finesse | 3 | 2 | 16 + 4/pulse | none listed | `+Alchemy`, `+Engineering` |
| Cunning | Finesse | 3 | 3 | 16 + 4/pulse | Elusion | `+Tactics`, `+Charisma`, pulsing anti-web/immobilization |
| Flight | Finesse | 3 | 3 | 16 + 4/pulse | Elusion | `+Athletics`, balance healing, chance to catch/return thrown weapon |
| Slight | Finesse | 4 | 2 | 20 + 5/pulse | Plunder | reduces chance of getting caught shoplifting |
| Guile | Finesse | 4 | 2 | 20 + 5/pulse | Plunder | `-Evasion` to all engaged targets |
| Credence | Finesse | 4 | 2 | 20 + 5/pulse | Cunning | calms all engaged targets |
| Focus | Potency | 1 | 1 | 8 + 2/pulse | none listed | `+Agility` |
| Sight | Potency | 2 | 1 | 12 + 3/pulse | Focus, 14th circle | `+Perception`, darkvision |
| Terrify | Potency | 2 | 2 | 12 + 3/pulse | Focus | single-target immobilize |
| Insight | Potency | 2 | 2 | 12 + 3/pulse | Sight | `+First Aid`, `+Outdoorsmanship` |
| Calm | Potency | 2 | 2 | 25 one-time | Focus, 14th | indiscriminate self-dispel |
| Intimidate | Potency | 3 | 1 | 16 + 4/pulse | Terrify | prevents engagement |
| Fright | Potency | 3 | 2 | 16 + 4/pulse | Intimidate | `+Debilitation`, `+Intelligence` |
| Steady | Potency | 3 | 2 | 16 + 4/pulse | Prowess | `+Bows`, `+Crossbows`, `+Heavy Thrown`, `+Light Thrown`, faster aim |
| Endure | Potency | 3 | 2 | 16 + 4/pulse | Calm | `+Stamina`, slows bleeding |
| Serenity | Potency | 3 | 2 | 16 + 4/pulse | Calm, 30th | SvS barrier vs Will |
| Eliminate | Potency | 3 | 2 | 35 one-time | Prowess, 60th | Small Edged attacks ignore armor and shield for about 10 seconds |
| Prowess | Potency | 3 | 2 | 16 + 4/pulse | Focus, Circle 14 | `-Tactics`, `-Reflex`, `-Offensive Factor`; Tactics note is PvP-only, OF note is PvE-only |
| Sagacity | Potency | 4 | 1 | 20 + 5/pulse | Serenity, Level 40 | non-ablative percentage barrier to physical damage |
| Unburn | Potency | 4 | 2 | 20 + 5/pulse | Endure, Level 50, quest | grants `UNBURN`, undoing recent elemental damage with cooldown |
| Darken | Subtlety | 1 | 1 | 8 + 2/pulse | none listed | `+Stealth` |
| Harrier | Subtlety | 2 | 1 | 12 + 3/pulse | Darken | `+Strength` |
| Dampen | Subtlety | 2 | 2 | 12 + 3/pulse | Darken | reduces stealth hindrance, anti-locate barrier, blocks `HUNT` |
| Silence | Subtlety | 2 | 2 | 12 + 3/pulse | Darken | pulsing invisibility |
| Strike | Subtlety | 2 | 3 | 12 + 3/pulse | Darken, Circle 13 | boosts held-weapon offensive skill package including Backstab and many melee weapon skills |
| Shadowstep | Subtlety | 3 | 2 | 16 + 4/pulse | Dampen | lowers advance time while hidden, `0 RT` sneaking in town |
| Sensing | Subtlety | 3 | 3 | 16 + 4/pulse | Dampen | remote view of neighboring room, passive hidden detection |
| Vanish | Subtlety | Special | 2 | 30 one-time | Silence, 40th | instant invisibility and retreat |
| Evanescence | Subtlety | 5 | 2 | 24 + 6/pulse | none listed | invisibility on receiving a sufficiently damaging strike |

## 7.6 Slip

Slip is shared with Bards, Rangers, and Necromancers, but the raw page states that thieves learn the broadest set and get them earlier.

Confirmed general rules:

- slip is taught virally by players, not NPCs
- uses a combination of `Thievery` and `Stealth`
- overall progression is circle-based
- teachers need 100 `Scholarship` to teach Slip

### Thief Slip progression

| Level | Ability |
| ---: | --- |
| 10 | Sleight of hand with coins |
| 15 | Slip coins to people |
| 20 | Slip personal objects to/from personal containers |
| 30 | Slip personal objects to another person's containers or hands |
| 40 | Slip worn items on and off |
| 50 | Slip into hiding and stalk at the same time |
| 60 | Slip into hiding and sneak a direction at the same time |
| 70 | Slip items from the ground to your possession |

## 7.7 Snipe

Confirmed requirements:

- Survival-prime guild only
- minimum `40th circle`
- available to Thief, Ranger, and Necromancer in guild-specific forms

For thieves:

- learned from Kalag the Sly
- supports `Bow`, `Crossbow`, and `Sling`
- can combine with dual load for a single target with two projectiles

Confirmed mechanics:

- uses `Stealth`, the appropriate weapon skill, and the guild-only skill (`Blindside` for thieves) as a modifier
- opposed by target `Perception` and defenses
- success keeps the thief hidden and grants an accuracy bonus
- failure becomes a normal attack and breaks hiding
- with invisibility only, the thief is revealed regardless of success

## 7.8 Contacts

Confirmed rules:

- contacts exist in each major city and some smaller cities
- first searches are local to the city walls
- more distant searches come later
- contact fees rise with law "heat"
- thieves gain one additional contact use per 20 circles
- maximum simultaneous contacts: 5

## 7.9 Sign Language and Voice Throw

Confirmed Sign Language details:

- secret thief-only language
- uses sleight of hand
- non-thieves may notice with enough `Perception`
- taught by Crow's assistant
- no direct skill/stat bonus; mainly identity and communication value

Confirmed Voice Throw detail:

- ventriloquism-style ability shared with Bards
- must be learned from a Bard player, not an NPC thief teacher

## 7.10 Lockpick Carving and Glance

Confirmed thief-specific utilities:

- `Lockpick Carving` and lockpick repair start at `12th circle`
- lockpick quality scales with `Lockpicking` skill and `Agility`
- `GLANCE` on loot boxes unlocks at `100 Lockpicking`, showing remaining traps and locks and some preview detail

## 8. Experience Math and How Skill Ranks Work

The `Experience` page gives the global learning math that applies to thieves.

## 8.1 Bits, ranks, and the next-rank rule

Confirmed rule:

- the next rank after current rank `n` costs `200 + n` bits

So:

$$bits\ for\ next\ rank = 200 + n$$

Summing from `0` to `r-1`, the total bits needed to reach rank `r` from zero is:

$$B(r) = \sum_{n=0}^{r-1}(200+n) = 200r + \frac{r(r-1)}{2} = \frac{r(r+399)}{2}$$

Useful inverse form for estimating rank from total bits:

$$r \approx \left\lfloor \frac{-399 + \sqrt{399^2 + 8B}}{2} \right\rfloor$$

Confirmed examples from the page:

- Rank 100: 24,950 bits
- Rank 200: 59,900 bits
- Rank 500: 224,750 bits
- Rank 1,000: 699,500 bits
- Rank 1,750: 1,880,375 bits

## 8.2 Pool-size math

Each skill has its own experience pool. Pool size depends on:

- skillset placement
- current ranks
- Intelligence
- Discipline

### Step 1: base pool by skillset and ranks

Let `X` be total ranks in the skill.

Primary skill base pool:

$$y = \frac{15000X}{X+900} + 1000$$

Secondary skill base pool:

$$y = \frac{12750X}{X+900} + 850$$

Tertiary skill base pool:

$$y = \frac{10500X}{X+900} + 700$$

For thieves this means:

- Survival skills get the largest base pools
- Weapon and Lore get medium pools
- Magic and Armor get the smallest pools

### Step 2: Intelligence bonus

Let `x` be Intelligence.

If `x < 30`:

$$y = \frac{(x-10)\times 60}{10}$$

If `30 <= x <= 60`:

$$y = \frac{((x-30)\times 30)+1200}{10}$$

If `x > 60`:

$$y = \frac{((x-60)\times 15)+2100}{10}$$

### Step 3: Discipline bonus

Let `x` be Discipline.

If `x < 30`:

$$y = \frac{(x-10)\times 20}{10}$$

If `30 <= x <= 60`:

$$y = \frac{((x-30)\times 10)+400}{10}$$

If `x > 60`:

$$y = \frac{((x-60)\times 5)+700}{10}$$

### Step 4: stat-modified pool

Let:

- `i` = Intelligence bonus from step 2
- `d` = Discipline bonus from step 3
- `x` = base pool from step 1

Then the stat-modified pool is:

$$y = \left(\frac{1000 + i + d}{1000}\right) x$$

## 8.3 Pulse behavior

Experience in pools drains into permanent ranks in pulses.

Confirmed drain bands from mind lock to clear:

- Primary: 40-60 minutes
- Secondary: 50-80 minutes
- Tertiary: 70-100 minutes

Important exceptions:

- secondary skills under 50 ranks drain like primaries
- tertiary skills under 25 ranks drain like secondaries

For thieves, that means early tertiary supernatural and armor skills are less painful than they become later.

## 8.4 Wisdom, Intelligence, and Discipline in practice

Confirmed summary from `Stats and learning`:

- `Intelligence`: increases maximum pool size
- `Wisdom`: increases pulse size
- `Discipline`: increases both pool size and pulse size, but at about 10% efficiency relative to the main mental stats

Confirmed effect examples relative to stat 10 baseline:

- 30 Int/Wis: about 112%
- 60 Int/Wis: about 121%
- 90 Int/Wis: about 125%
- 120 Int/Wis: about 130%

## 8.5 Mindstates

Mindstate runs from `0/34 clear` to `34/34 mind lock`.

Important late bands:

- 30/34: rapt
- 31/34: very rapt
- 32/34: enthralled
- 33/34: nearly locked
- 34/34: mind lock

## 8.6 Maximum rank

Confirmed cap:

- hard rank cap is `1750`
- effective ranks may exceed that through buffs
- self-cast skill buffs cap at 20%
- third-party support using a different bonusing ability can extend to 30%

## 8.7 Offline drain and rested experience

Confirmed offline drain:

- starts after 30 minutes logged out
- drains a percentage based on logout time divided by 360 minutes, or 480 minutes if warned within six months

Confirmed rested experience points:

- Standard: 4 hours bank
- Premium: 6 hours bank
- Platinum: 8 hours in Platinum instance
- accumulates at 2:1 while not draining experience
- usage cap refreshes on a roughly 23:30 personal cycle

## 9. What This Means Specifically for Thieves

The interaction between thief progression and global experience math is straightforward but important:

1. Survival skills learn faster and hold more because they are prime.
2. Weapon and Lore are manageable because they are secondary.
3. Armor and Supernatural learning are the long-term pain points because they are tertiary.
4. Thieves must still keep tertiary supernatural skills moving because khri, ambushes, and Inner Magic are part of circling.
5. Confidence and urban bonus can make effective performance look better or worse than sheet ranks alone would suggest.
6. Mark, ambushes, and khri create strong cross-training loops among Appraisal, Perception, Backstab, Debilitation, and Supernatural skills.

In practice, the guild wants a thief to feel like a city predator with wide Survival coverage, adequate combat support, and carefully maintained concentration-driven utility.

## 10. Best-Supported Thief Training Package

If the goal is to build a faithful thief progression path from the current DB, the safest package is:

- Survival core: `Stealth`, `Thievery`, `Evasion`, `Athletics`, `Perception`, `Locksmithing`, `Outdoorsmanship`, `First Aid` or `Skinning`
- Weapon core: `Small Edged`, one general combat weapon, `Parry`
- Recommended extras: `Bow` or `Crossbow`, `Brawling`, `Light Thrown`
- Lore core: `Appraisal`, `Tactics`, `Scholarship` or a craft
- Supernatural core: `Inner Magic`, `Augmentation`, `Utility`, `Debilitation`, `Warding`

Then layer on:

- `Khri Focus` at circle 1
- `Mark` in the first few circles
- early ambushes for Debilitation and control
- `Slip` as circle milestones unlock
- `Snipe` at 40th circle
- higher-tier khri once concentration and supernatural ranks permit

## 11. Final Assessment

The thief profession is one of the clearer professions in DireLore when the answer is allowed to stay raw-backed. The guild's identity, circle structure, khri math, and stealth/thievery training all come through strongly.

The weak part is structured storage, not source material. The raw corpus knows what a thief is. The normalized tables just do not yet reflect that breadth.

The most faithful implementation reading from this snapshot is:

- hidden-entry guild culture
- Survival-first circling
- concentration-based khri progression
- effective-rank play driven by confidence and urban bonus
- cross-training loops between stealth, theft, appraisal, perception, backstab, debilitation, and Inner Magic

That is the thief profession the database currently supports.