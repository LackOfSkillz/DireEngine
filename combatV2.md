# Combat and Magic Combat Deep Dive

> Query date: 2026-04-08
> Database: local PostgreSQL `direlore` on port `5432`
> Project overlay: `direlore`
> Primary domains used: `mechanics`, `lore`, combat-related canon tables, weapon and armor tables, and spell metadata tables under the shared schema contract
> Contract packet source: `agent_active_instructions_v`, `agent_active_project_overlay_v`, `agent_query_playbooks_v`, `agent_schema_contract_v`

## Answer

The current DireLore snapshot supports a strong combat packet for core combat math, combat ranges, stance behavior, balance and position ladders, roundtime, armor and shield interactions, weapon-family behavior, stealth combat, damage messaging, and Magic 3.0 casting mechanics. The strongest sources are raw section text on the `Combat`, `Combat 3.0`, `Armor`, `Armor and shield player guide`, `Roundtime`, `Magic 3.0`, `Prepare command`, `Spell preparation`, `Targeted Magic skill`, `Stealth`, `Shield Usage skill`, and major weapon-skill pages.

The database does **not** currently preserve a full exact combat algorithm. The raw sources clearly describe the inputs, ladders, thresholds, and qualitative relationships, but they do not expose the engine's exact opposed-roll formulas for to-hit, armor contests, maneuver resolution, or most spell contests. The structured tables help confirm ladders and normalized categories, but they also preserve only a derived model in places.

In short:

- Combat is built around three ranges: `missile`, `pole`, and `melee`.
- Core physical resolution uses offensive skill, a random factor, Agility, weapon balance, the defender's combined defenses, then armor.
- At equal offensive force and defensive force, hit chance is explicitly stated as `66%`.
- Damage begins with weapon damage and maneuver weighting, is increased by Strength and weapon suitability, reduced by armor, then modified by hit quality, with better hits scaling damage up to double base damage.
- Balance and position are major hidden combat multipliers; higher values improve both offense and defense.
- Stance points determine what percentage of Evasion, Parry, Shield, and Attack you are actively using.
- Armor provides `protection` and `absorption`, while hindrance penalizes movement, stealth, and defenses.
- Armor experience is split by body coverage defended, not by individual piece hindrance.
- Shields and armor both interact strongly with range, hindrance, and weapon choices.
- Ranged weapons, thrown weapons, stealth, and targeted magic all have their own special handling.
- Magic 3.0 preserves more formulas than old combat in some places, especially spell stance ratios, spell difficulty bands, attack-style stat classes, and Targeted Magic stat inputs.

## Playbook Used

- `mechanics_lookup` for combat loops, balance, position, ranges, armor, shields, stealth, and spell resolution behavior.
- `lore_lookup` where combat pages were partly descriptive rather than strictly mechanical.
- Shared schema-contract reads for `canon_combat_rules`, `engine_combat_spec`, `canon_armor`, `canon_weapons`, `weapon_skills`, and `canon_spells` as corroboration only.

## Source Path Used

Primary source path used:

`sections -> raw_pages -> canon_combat_rules -> engine_combat_spec -> canon_armor/canon_weapons/weapon_skills/canon_spells`

Most important pages:

- `https://elanthipedia.play.net/Combat`
- `https://elanthipedia.play.net/Combat_3.0`
- `https://elanthipedia.play.net/Stance_command`
- `https://elanthipedia.play.net/Armor`
- `https://elanthipedia.play.net/Armor_and_shield_player_guide`
- `https://elanthipedia.play.net/Roundtime`
- `https://elanthipedia.play.net/Shield_Usage_skill`
- `https://elanthipedia.play.net/Stealth`
- `https://elanthipedia.play.net/Targeted_Magic_skill`
- `https://elanthipedia.play.net/Magic_3.0`
- `https://elanthipedia.play.net/Prepare_command`
- `https://elanthipedia.play.net/Cast_command`
- `https://elanthipedia.play.net/Spell_preparation`

## Source Quality

- High confidence, raw-backed: combat ranges, stance points, balance and position ladders, damage-message ladders, vitality/fatigue states, armor protection and absorption behavior, hindrance behavior, roundtime minima, shield size behavior, stealth contest notes, spell stance ratios, spell-type behavior, targeted magic stat notes.
- Medium confidence, raw-backed: weapon-family advice pages, weapon-category strengths and training use, hiding/stalking roundtime tables, crossbow load thresholds, pike combo advice, brawling stat pairings.
- Medium confidence, structured corroboration: normalized armor categories, damage-state ladders, combat range ladder, spell metadata, derived combat specs.
- Low confidence: exact engine formulas for contested melee, armor-factor rolls, maneuver success, debilitation success, and final spell damage rolls. The sources describe these qualitatively but do not publish the exact implementation math.

## Structure Gaps

- `canon_combat_rules` preserves ladders and message tiers, but not exact roll equations.
- `engine_combat_spec` is useful, but is clearly a derived layer and explicitly notes where timing or exact formulas are unspecified.
- `canon_weapons` and `weapon_skills` are incomplete and inconsistent for some weapon families, so raw skill pages are more trustworthy than the normalized tables for family descriptions.
- `canon_spells` exposes spell metadata, but not a normalized cast-message table.
- Spell-preparation messaging exists only as prose blocks on `Spell_preparation`; it is not normalized into a structured message catalog.
- Some wiki pages conflict slightly with later combat-era summaries, especially around arm-worn shield penalties.

## Storage Recommendation

- Promote a normalized `combat_resolution_rules` layer with explicit formulas where known and `unknown` markers where not known.
- Normalize spell-preparation messages into `spell_preparation_messages` with source, feat requirements, self-message, and observer-message fields.
- Normalize ranged-weapon speed thresholds and crossbow load-reduction breakpoints.
- Normalize stance rules, including attack-to-defense tradeoff, into explicit rows rather than prose.
- Clean and reconcile `canon_weapons` to better align weapon families with player-facing skill categories.

## 1. Combat Architecture

### 1.1 Core loop

The derived combat spec summarizes the system as:

- choose action
- resolve maneuver
- apply damage
- update states
- repeat

That is only a high-level contract, but it lines up with the raw pages.

### 1.2 Primary combat states

The strongest preserved state ladders are:

- Balance: `incredibly balanced` down to `completely imbalanced`
- Position: `overwhelming` down to `opponent overwhelming you`
- Vitality: `invigorated` down to `in death's grasp`
- Fatigue: `energetic` down to `bone-tired`

These ladders are preserved both in `Combat` and in `canon_combat_rules`.

### 1.3 What matters most in every exchange

The raw pages repeatedly point to these inputs:

- offensive skill
- defender combined defenses
- Agility and weapon balance for hit chance
- Strength and weapon suitability for damage
- armor skill and armor stats for mitigation
- balance and position for both offense and defense
- fatigue and hindrance as performance constraints

## 2. Stance and Defensive Allocation

### 2.1 How stance works

`Stance command` is the best direct source for stance behavior.

Confirmed stance rules:

- Stance sets what percentage of your actual Evasion, Parry, and Shield skill you are actively using.
- Example: `STANCE PARRY 80` uses `80%` of your parry skill for defense.
- Characters begin with `180` defensive stance points.
- The common baseline allocation is `100/80` across primary and secondary defenses.
- Additional stance points come from `Defending`.
- One defensive stance point is granted every `50`, `60`, or `70` ranks for armor-primary, armor-secondary, and armor-tertiary guilds respectively.

### 2.2 Attack versus defense tradeoff

There is also an `ATTACK` stance value.

Explicit rule:

- For every `5` points you reduce `ATTACK`, you gain `1` defensive stance point to reassign.

This is one of the clearest hard ratios preserved in the DB.

### 2.3 Shield fallback behavior

`Stance command` also confirms an important projectile rule:

- Parry stance points are automatically used as Shield stance when an incoming attack cannot be parried but can be blocked.
- This includes ranged projectiles from thrown weapons, bows, and crossbows.
- It also includes projectile-like spells, with `Death From Above`-style spells called out as shield-ignoring exceptions.

### 2.4 Defensive partnership in Combat 3.0

`Combat 3.0` states:

- Evasion, Parry, and Shield form a first line of defense.
- They are intended to be equal partners.
- Any `180%` stance variation is intended to be equally effective, all else equal.

That means the system is not supposed to be purely evasion-dominant anymore.

## 3. Balance, Position, and Movement

### 3.1 Balance ladder

The preserved balance ladder is:

- incredibly balanced
- adeptly balanced
- nimbly balanced
- solidly balanced
- slightly off balance
- off balance
- somewhat off balance
- badly balanced
- very badly balanced
- extremely imbalanced
- hopelessly unbalanced
- completely imbalanced

`solidly balanced` is the stated baseline.

### 3.2 Position ladder

The preserved position ladder runs from:

- overwhelming
- in dominating position
- in excellent position
- in superior position
- in very strong position
- in strong position
- in good position
- in better position
- have slight advantage
- no advantage

...down through the mirrored opponent-advantage states to:

- opponent overwhelming you

### 3.3 Mechanical effect

The raw page and derived notes agree on the important parts:

- higher balance improves defense
- higher position improves both offense and defense
- stuns drop balance sharply
- a stun automatically drops balance to `very badly balanced`, with stronger stuns pushing it even lower

### 3.4 Tactical maneuvers

The `Combat` maneuver chart shows that non-attack maneuvers trade off:

- fatigue
- balance
- speed
- accuracy
- defense weighting

Examples from the raw chart:

- `bob` helps fatigue and balance, but is weak for parry and shield
- `circle` helps balance and offense setup
- `weave` helps evasion-style play
- `parry` and `block` are direct defensive maneuvers
- `retreat` and `flee` are movement-driven rather than damage-driven

`Combat 3.0` further says:

- combo chains were removed
- maneuvers now have independent benefits and penalties
- penalties fade after a few seconds instead of lasting until your next maneuver
- `BOB`, `WEAVE`, and `CIRCLE` train `Tactics` instead of `Brawling`

## 4. Ranges and Range Control

### 4.1 Range ladder

All combat is divided into three ranges:

- `missile`
- `pole`
- `melee`

The derived combat spec confirms that range transitions are `adjacent only`, meaning you move missile <-> pole <-> melee rather than skipping directly.

### 4.2 Starting range behavior

`Combat` states:

- outdoors, targets usually begin at `missile`
- indoors, targets usually begin at `pole`

That alone shapes the opening value of ranged weapons versus melee weapons.

### 4.3 What works at each range

- Missile: bows, crossbows, slings, thrown weapons
- Pole: ranged weapons plus long pole-range weapons like halberds and longer spears
- Melee: all weapons can be used

The page explicitly notes that you no longer automatically charge to melee when out of range.

### 4.4 Range commands

The important range-control verbs are:

- `ADVANCE`
- `RETREAT`
- `HANGBACK`
- `FLEE`
- `ASSESS`

Key behavior:

- `ADVANCE` closes distance
- `RETREAT` either stops advancing or moves back one range
- `HANGBACK` automatically counters advance with retreat
- `FLEE` attempts to fully disengage, but defenses are reduced while the flee resolves
- `ASSESS` shows ranges, facing, and balance states

### 4.5 Retreat penalties

`Combat` and `Combat 3.0` preserve two anti-kiting rules:

- repeated retreats within a short time add increasing attack penalties
- after a ranged attack or offensive spell, the attacker cannot leave for about `4` seconds after attack RT ends

`Combat 3.0` also states that repeated retreating penalizes ranged attacks and that `ASSESS` will show the penalty level.

## 5. To-Hit and Damage Math

### 5.1 To-hit math

`Combat` preserves the clearest high-level formula:

- an Offensive Force or Factor is generated from skill plus a random number
- that number is bonused by the attacker's `Agility`, modified by weapon `balance`
- it is compared against the defender's effective combined `Evasion`, `Parry`, and `Shield`

The clearest hard number:

- when offensive force equals defense, hit chance is `66%`

The page also explicitly says:

- there is always some chance to hit
- there is always some chance to miss

### 5.2 Damage pipeline

The raw `Combat -> Damage` section lays damage out in order:

1. Start with base physical damage from the weapon.
2. Modify by attack type or maneuver weighting.
3. Use different percentages of the weapon's puncture, slice, and impact values depending on the maneuver.
4. Add Strength-based damage, modified by weapon suitability.
5. Reduce by target armor, modified by the defender's skill in that armor.
6. Increase damage by hit quality depending on how far the hit exceeded the minimum needed to connect.
7. Cap body-part damage based on the target's remaining vitality.

One critical upper bound is explicit:

- hit quality can scale damage up to `double` base damage

### 5.3 Offense split in Combat 3.0

`Combat 3.0` reinforces the offense split:

- hit chance is bonused by Agility and weapon balance
- damage is bonused by Strength and weapon suitability
- to-hit and damage were intentionally separated to reduce one-hit kills

### 5.4 Damage messaging ladder

The damage-message tiers preserved in both raw text and `canon_combat_rules` are:

- light hit
- good hit
- good strike
- solid hit
- hard hit
- strong hit
- heavy strike
- very heavy hit
- extremely heavy hit
- powerful strike
- massive strike
- awesome strike
- vicious strike
- earth-shaking strike
- demolishing hit
- spine-rattling strike
- devastating hit
- overwhelming strike
- obliterating hit
- annihilating strike
- cataclysmic strike
- apocalyptic strike

No-damage hit messages are:

- benign
- brushing
- gentle
- glancing
- grazing
- harmless
- ineffective
- skimming

### 5.5 Maneuver damage typing

`Combat -> Weapon` preserves broad maneuver affinities:

- puncture-heavy maneuvers: `JAB`, `THRUST`, `LUNGE`
- slice-heavy maneuvers: `FEINT`, `SLICE`, `CHOP`
- impact-heavy maneuvers: `SWING`, `SLAM`, `BASH`, sometimes `JAB/FEINT`

## 6. Roundtime and Speed Math

### 6.1 Effective Strength formula

`Roundtime` preserves the clearest explicit equation in the combat corpus:

`Effective Strength = ((Strength x Suitedness) + (Agility x Balance)) / (Suitedness + Balance)`

Variables explicitly called out as RT inputs:

- weapon class
- weapon balance
- weapon suitedness
- Strength
- Agility

### 6.2 Minimum melee RTs

The page gives these minimum RT families for melee weapons:

| Weapon class | Jab | Draw | Slice group | Chop group |
| --- | ---: | ---: | ---: | ---: |
| Light | 1 | 2 | 2-3 | 2-3 |
| Medium | 1 | 2 | 3 | 3 |
| Heavy | 2 | 3 | 4 | 4 |
| Twohanders | 2 | 3 | 4 | 5 |

Grouping rules preserved on the page:

- `JAB` and `FEINT` share RT
- `DRAW` has its own RT
- `SLICE`, `SWING`, `THRUST`, `SLAM`, and `PUMMEL` share RT
- `CHOP`, `BASH`, `LUNGE`, and `SWEEP` share RT

### 6.3 Minimum thrown and brawling RTs

Thrown weapons:

| Type | Lob | Throw | Hurl |
| --- | ---: | ---: | ---: |
| Heavy Thrown | 2 | 3 | 4 |
| Light Thrown | 1 | 2 | 3 |

Non-grappled brawling minima:

- Claw: 2
- Elbow: 2
- Gouge: 1
- Kick: 3
- Punch: 2
- Slap: 2

Grappled brawling minima:

- Tackle: 3
- Grab: 3
- Bite: 2
- Knee: 2
- Claw: 2
- Elbow: 2
- Gouge: 1
- Punch: 2

### 6.4 Combat 3.0 speed notes

`Combat 3.0` adds these system-level speed notes:

- combat was intentionally slowed down
- many maneuver RTs increased by `1` second
- higher stats are needed for RT reduction
- overall time-to-kill was intended to be roughly four times longer than older combat

## 7. Armor, Shields, and Defense Layers

### 7.1 Defense order

The clearest raw statement is:

- `Evasion`, `Shield Usage`, and `Parry Ability` are checked together
- armor follows after those defenses

That makes armor a mitigation layer, not the first avoidance layer.

### 7.2 Armor stats

`Armor` and the player guide agree that armor has:

- coverage area
- weight
- protection
- absorption
- maneuvering hindrance
- stealth hindrance
- construction
- durability

### 7.3 Protection versus absorption

This is one of the clearest armor mechanics blocks preserved.

Protection:

- flat damage reduction
- best against light hits
- more likely to reduce damage to zero
- heavily modified by an armor-factor versus offensive-factor contest
- with low armor skill versus attacker offense, armor can lose all of its protection

Absorption:

- percentage damage reduction
- best against large hits
- usually will not reduce damage to zero
- only slightly modified by the armor-factor versus offense contest

### 7.4 Armor scales

Protection scale runs from:

- `no` to `unbelievable`

Absorption scale runs from:

- `no` to `unbelievable`

Construction scale runs from:

- `extremely weak and easily damaged` to `practically invulnerable`

Condition scale runs from:

- `in pristine condition` down to `battered and practically destroyed`

Performance degradation begins below `80%` condition.

### 7.5 Hindrance

Hindrance comes in two types:

- maneuvering hindrance
- stealth hindrance

Explicit effects:

- maneuvering hindrance penalizes all defenses
- evasion is affected the most
- shield is affected the least
- stealth hindrance penalizes actions like hiding

### 7.6 Armor skill and skillset placement

The player guide preserves several key rules:

- any guild can wear any armor
- guild skillset placement mainly controls learning speed and ability to work down hindrance
- Paladins are best at working off hindrance
- armor-secondary guilds are average
- armor-tertiary guilds are worst

The 3.0 page also says:

- armor skill is used as a passive defense against attacker offense
- armor protection progressively reduces as attacker offense outstrips defender armor skill

### 7.7 Training armor and mixed armor

The strongest armor-training rule is:

- armor experience from defended attacks is split solely by percent body coverage

It is **not** based on the piece's own hindrance.

The guide also explicitly confirms:

- clownsuiting is wearing multiple armor types to train multiple armor skills
- mixed armor adds an extra hindrance penalty per additional armor type
- Paladins can negate the mixing penalty gradually every 10 circles

### 7.8 Coverage and experience split

The guide preserves example coverage math:

- if full plate covers `79%` and brigandine accessories cover `21%`, then `79%` of armor experience goes to plate and `21%` goes to brigandine
- the same split also applies to hindrance attribution

### 7.9 Armor families

Raw page categories:

- Light armor: cloth, leather, bone
- Chain armor: ring, chain, mail
- Brigandine: scale, brigandine, lamellar
- Plate armor: light plate, plate, heavy plate

Structured corroboration in `canon_armor` is consistent with four main armor skills, though the table contains one capitalization duplicate.

### 7.10 Shields

Shield stats preserve two concepts:

- fortuitous block chance
- protection

Fortuitous block chance:

- is a chance-based bonus that can happen regardless of skill
- does not change between held and worn states

Protection:

- scales with shield skill
- is reduced when worn on the arm instead of held

### 7.11 Shield size behavior

Two raw sources preserve shield-size behavior.

Detailed percentages from `Shield Usage skill`:

- Small shield: `100%` melee, `80%` missile
- Medium shield: `98%` melee, `90%` missile
- Large shield: `96%` melee, `100%` missile

Coarser summary from `Combat 3.0`:

- Small: good versus melee, bad versus ranged
- Medium: moderately good versus both
- Large: good versus ranged, poor versus melee

### 7.12 Arm-worn shield penalties

There is mild source drift here.

`Armor and shield player guide` says:

- arm-worn shields lose `20%` protection compared to holding

`Combat 3.0` says:

- arm-worn shields were changed to a flat `25%` reduction to shield stats

Best-supported interpretation:

- holding is better than wearing
- wearing a shield is mechanically convenient, but comes with a measurable protection loss
- the exact numeric penalty appears to differ across source eras

### 7.13 Twohanders and shields

The DB preserves these rules:

- using a twohanded weapon with a shield hinders both attack and shield defense
- some guilds can ignore the bow-and-arm-worn-shield penalty under specific limits
- Paladins can ignore it with medium or small shields
- Barbarians and Rangers can ignore it with small shields

## 8. Weapon Families and What They Train

### 8.1 General rule

The raw combat pages treat each weapon family as training its matching weapon skill. The structured weapon tables are too inconsistent to replace the raw skill pages, but they do support the existence of normalized weapon families and skill mappings.

### 8.2 Small edged

`Small Edged skill` covers:

- light edged weapons such as daggers, knives, katars
- medium edged weapons that are still below the larger one-handed classes

Mechanical notes:

- very high balance
- strong for parrying
- common offhand choice
- thrusting variants are strong for backstab and ambush

### 8.3 Large edged

`Large Edged skill` covers larger one-handed axes and swords.

Mechanical notes:

- one-handed
- high slice and impact
- works well with shields or dual wielding
- popular because it balances damage and flexibility

### 8.4 Twohanded edged

`Twohanded Edged skill` covers large two-handed swords and axes.

Mechanical notes:

- high slice and impact
- sometimes pole-ranged
- can be paired with arm-worn shields, but with penalties to both shield and weapon use

### 8.5 Large blunt

`Large Blunt skill` covers morning stars, clubs, hammers, ball and chains, and heavy maces.

Mechanical notes:

- heavy impact damage
- good at stunning and disabling
- low balance makes hitting and parrying harder against skilled foes

### 8.6 Twohanded blunt

`Twohanded Blunt skill` is an extreme Strength-scaling class.

Mechanical notes:

- rewards high Strength strongly
- many weapons can hit from pole range
- severe impact is common
- often stuns and knocks down
- weak for parrying and against high natural armor due to low puncture and slice

### 8.7 Staves

`Staves skill` splits mainly into short staff and quarter staff behavior.

Short staff:

- one-handed
- low damage
- can be used while grappling

Quarter staff:

- usually two-handed
- moderate to severe impact, plus some puncture
- some quarterstaves can strike from pole range
- can be used while grappling

### 8.8 Polearms

`Polearms skill` includes pikes and halberd-like nonstandard polearms.

Pike notes:

- extremely heavy
- puncture-oriented
- many can be thrown with `Heavy Thrown`
- many are one-handed despite being heavy
- many can strike from pole range
- Barbarians and Paladins can parry ranged attacks with them at pole range

Preserved pike combo advice:

- puncture pikes: `Jab -> Thrust -> Lunge -> Repeat`
- slash pikes: `Jab -> Sweep -> Slam -> Repeat`

### 8.9 Bows

`Bows skill` is split into short bows, longbows, and composite bows.

Short bows:

- default load time around `2` seconds
- highest balance of the standard bow classes
- best for high-Agility, lower-Strength users

Longbows:

- higher strength suitability than short bows
- load slower than short bows, faster than composite bows
- very popular for maximizing attack power

Composite bows:

- slowest-loading bow class
- hits hard
- relies more heavily on Strength than Agility for load RT and damage

Extra ranged mechanics:

- AIM gives large damage and accuracy bonuses
- Barbarians, Rangers, and Thieves can dual-load arrows under conditions
- the second arrow of dual load uses `70%` of the user's attack power as a snap shot
- Rangers and Thieves can `SNIPE` while hidden

### 8.10 Crossbows

`Crossbows skill` splits into light crossbow, heavy crossbow, and arbalest.

Light crossbow:

- quicker than heavy crossbow
- does not require both hands while aiming
- relies primarily on Agility for load reduction
- first guaranteed load-time reduction threshold preserved as `36 Agility`, `Strength + Agility = 60`, `251 ranks`

Heavy crossbow:

- harder-hitting, slower-loading than light crossbow
- requires an open hand to load and aim
- relies more on Strength for load reduction
- first guaranteed reduction preserved as `31 Strength`, `Strength + Agility = 60`, `201 ranks`

Arbalest:

- slowest class
- preserved load times start at `18` seconds unhidden and `21` seconds while hidden
- can be loaded and fired while the off hand is full
- cannot be worn

### 8.11 Light thrown and heavy thrown

Both thrown classes preserve a special rule:

- they use melee calculations rather than standard ranged calculations

That makes them:

- more vulnerable to shield and armor than normal ranged weapons
- still distinct from ordinary melee because they attack across range without aim

Light thrown:

- rocks, throwing daggers, darts, knives, clubs, mallets, axes, dirt, naphtha, and similar small throwables
- non-weapon small items can still use the skill
- weights under `25 stones` can use light thrown even if they do not appraise as throwing weapons

Heavy thrown:

- weights `25 stones` or more can use heavy thrown even if they do not appraise as throwing weapons
- `HURL` guarantees lodging for all types
- `LOB` is a fast, light attack with `0%` chance to lodge

### 8.12 Brawling

`Brawling` is both a damage skill and a grappling ecosystem.

Preserved notes:

- `BOB`, `WEAVE`, and `CIRCLE` no longer train Brawling; they train `Tactics`
- grappling likely imposes a defensive-factor penalty on both parties
- some actions are restricted during grapples, including loading, shooting, hiding, thrusting, lunging, and kick

Brawling stat pairings preserved on the page:

- Strength + Stamina: `PUNCH`, `GOUGE`, `KICK`, `ELBOW`, `KNEE`, `BUTT`
- Strength + Agility: `SLAP`
- Strength + Reflex: `BITE`
- Agility + Reflex: `CLAW`

## 9. Stealth Combat

### 9.1 General stealth contest

`Stealth` defines the skill as:

- ability to hide without being noticed
- ability to stay hidden
- ability to move while hidden

It is affected by:

- wounds
- armor type
- combat status
- Discipline

And it is contested against `Perception`.

### 9.2 Combat hiding rules

The stealth training page confirms:

- hiding is easier when creatures are not facing you
- hiding gets harder the closer enemies get while engaged
- hiding at melee is no longer restricted as harshly by guild type as it once was

### 9.3 Hide and stalk roundtimes

Hide roundtimes preserved:

| Effective ranks | Roundtime |
| ---: | --- |
| 60 | 5 seconds |
| 120 | 4 seconds |
| 180 | 3 seconds |
| 240 | 2 seconds for Survival-primary |

Stalk roundtimes preserved:

| Effective ranks | Roundtime |
| ---: | --- |
| 0 | 6 |
| 40 | 5 |
| 80 | 4 |
| 120 | 3 |
| 160 | 2 |

### 9.4 Combat stealth actions

The DB preserves these stealth-combat interactions:

- `Backstab` ignores shield and parry
- `Ambush` uses stealth-combat positioning
- `Snipe` lets some ranged users fire from hiding
- advancing while hidden trains stealth via stalking-like behavior
- creatures gain significant bonuses to spot you as you get closer during combat

### 9.5 Stealth, armor, and hindrance

This interaction is explicit across multiple pages:

- armor type matters to hiding success
- stealth hindrance makes hiding harder
- light armor is favored by stealth-heavy builds because it is least hindering

## 10. Combat Messaging

### 10.1 Vitality states

`Combat Messaging` preserves this ladder:

- above 100%: `invigorated`
- 100%: no message
- 99%-90%: `bruised`
- 89%-80%: `hurt`
- 79%-70%: `battered`
- 69%-60%: `beat up`
- 59%-50%: `very beat up`
- 49%-40%: `badly hurt`
- 39%-30%: `very badly hurt`
- 29%-20%: `smashed up`
- 10%-9%: `terribly wounded`
- 9%-1%: `near death`
- below 1%: `in death's grasp`

### 10.2 Spirit states

The same section preserves spirit messaging:

- mighty
- no message
- shaky
- very shaky
- weak
- very weak
- drained
- very drained
- cold
- very cold
- empty
- desolate
- nonexistant

### 10.3 Fatigue states

- above 100%: `energetic`
- 100%-90%: no message
- 89%-80%: `winded`
- 79%-60%: `tired`
- 59%-40%: `fatigued`
- 39%-30%: `worn-out`
- 29%-20%: `beat`
- 19%-10%: `exhausted`
- 9% to near zero: `bone-tired`

### 10.4 Damage strings

The damage tier strings are covered in Section 5.4 and remain the primary outward message for hit severity.

## 11. Magic Combat and Casting Math

### 11.1 Targeted magic in combat

`Targeted Magic skill` preserves several important combat rules:

- opponent balance is a key factor in targeted spell success
- opponents with compromised balance are easier to hit with TM
- compromised balance also tends to increase spell damage dealt
- body-part targeting can partially disable or disarm opponents
- body-part targeting does **not** increase learning

### 11.2 Targeted magic stats

Explicit TM stat effects:

- Discipline increases TM accuracy
- Intelligence and Wisdom increase TM damage

### 11.3 Spell attack classes

`Magic 3.0` preserves attack classes and stat bundles.

Offense classes:

- Mind: Intelligence, Discipline, Wisdom
- Magic: Wisdom, Intelligence, Discipline
- Spirit: Wisdom, Charisma, Intelligence
- Charm: Charisma, Discipline, Intelligence
- Fear: Charisma, Strength, Discipline
- Power: Strength, Stamina, Discipline
- Finesse: Agility, Reflex, Intelligence

Defense classes:

- Reflexes: Reflex, Agility, Intelligence; also affected by incapacitating conditions
- Fortitude: Stamina, Discipline, Strength; also affected by vitality, spirit, and fatigue
- Willpower: Discipline, Wisdom, Intelligence; also affected by nerve damage, stuns, unconsciousness, `Khri Serenity`, and `Cunning`

### 11.4 Spell stance ratios

One of the most explicit Magic 3.0 mechanics blocks is `SPELL STANCE`.

Each spell distributes power across:

- Potency
- Duration
- Integrity

Explicit ratio limits:

- any one facet can be raised as high as `130%`
- any one facet can be reduced as low as `70%`

Important rule for spells without one facet:

- if a facet does not apply, only the ratio of the remaining facets is used

Example preserved on the page:

- a TM spell with Duration `130%`, Integrity `85%`, and Potency `85%` uses the Integrity:Potency ratio of `1:1`

### 11.5 Spell difficulty and mana scaling

`Magic 3.0` and `Experience` together preserve:

- experience depends on spell difficulty relative to your base ranks
- difficulty depends on spell base difficulty, the difficulty of adding mana, and how much mana you add
- larger casts are generally better for training than several smaller casts
- handicapping yourself no longer improves training; base ranks are used

Preserved difficulty bands from GM Socharis:

- `Intro`: castable from about `1` rank
- `Basic`: around `10` ranks before casting at minimum mana
- `Advanced`: around `100` ranks
- `Esoteric`: roughly `200+` ranks to cast

### 11.6 Harness and mana behavior

`Magic 3.0 -> Casting` preserves these rules:

- harness regeneration is inverse to old behavior: the more you have used, the faster it returns
- large casts are less problematic to harness level than before
- amount prepared is augmented by mana from harness and focused cambrinth

### 11.7 Spell types relevant to combat

The DB preserves several type rules:

- Battle spells: quicker to cast, shorter duration, meant for combat
- Cyclic spells: drain mana each pulse, only one can be active at once
- Ritual spells: huge mana costs, starting around `150` mana and capping as high as `600`
- Targeted spells: can skip manual prep using `TARGET {SPELL} {MANA} AT {TARGET}`
- Metaspells: modify already learned spells

### 11.8 Magical versus non-magical attack styles

Magical attack styles:

- Mind attacks
- Magic attacks
- Spirit attacks
- Charm attacks

Non-magical attack styles:

- Fear attacks
- Power attacks
- Finesse attacks

This matters because the contest class determines which stat trio the attack and defense use.

### 11.9 Sorcery in combat casting

Sorcery is used when casting spells outside your mana type.

Important limiter rule:

- if a foreign spell uses a magical skill higher than Sorcery, that skill is effectively lowered to the Sorcery level for that cast

## 12. Casting Commands and Preparation Messaging

### 12.1 Core commands

`Prepare command` preserves:

- `PREPARE <spell name> <amount>`
- `/LIST`
- `/SHIFT`
- `/DEFAULT`
- `/CLEAR`
- `/HIDE`
- `/HELP`

Important hard rule:

- hiding your preparation message normally adds a `3 second` penalty unless you have `Silent Preparation`

`Cast command` preserves:

- `CAST`
- `CAST <target>`
- `CAST AREA`
- `CAST ENGAGED`
- `CAST CREATURES`
- `CAST GROUP`
- `CAST SELF`

### 12.2 Basic preparation messages

`Spell preparation` preserves the default guild preparation families.

Guild message families preserved:

- Cleric / Paladin: chanting catechisms, mantra, prayer, or psalm
- Empath / Ranger: calm, meditative, rigid, or tense bodily preparation stances
- Moon Mage / Trader: raising arm, arms, head, or palms skyward while chanting the equation of the spell
- Necromancer: muttering foul phrases, blasphemies, or incoherent phrases
- Warrior Mage / Bard: tracing angular, careful, curving, geometric, or hasty sigils in the air

### 12.3 Alternate preparation messages

Requires `Alternate Preparations` feat.

The page preserves many cosmetic families, including:

- Followers of Fortune's Path
- Nomads of the Arid Steppe
- Prophets of G'nar Peth
- Progeny of Tezirah
- many Premium LTB patterns
- Spell Library patterns
- Festival patterns
- Su Helmas event patterns
- Hollow Eve event patterns

Common preserved templates include:

- careless gesturing while chanting
- soft whispering into the air
- chanting an obscure mantra while focusing on ambient energies
- sly murmuring of tenebrous phrases
- syncopated gestures and giggling
- arcane runes, geometric shapes, motes of light, frost, fire, lightning, mist, darkness, or soul-wailing visuals

### 12.4 Silent preparation messages

Requires both:

- `Alternate Preparations`
- `Silent Preparation`

These are mechanically easier to hide.

Preserved families include:

- Celestial Compact
- Monks of the Crystal Hand
- Heritage House
- Premium LTB patterns
- Spell Library patterns
- Festival patterns
- Su Helmas and Hollow Eve event patterns

Common silent themes include:

- tracing sigils with almost no sound
- studied one-hand gestures
- finger-waggling or knuckle work
- internal concentration with minimal movement
- faint skin patterns, iridescent breath clouds, crystalline sparks, planetary alignments, or shadow-light collisions

### 12.5 Legacy preparation messaging

The DB preserves one older legacy pattern as incompatible with the current system:

- clapping on a mote of energy and drawing apart a crackling sphere to shape the spell

## 13. Direct Formula and Threshold Cheat Sheet

### 13.1 Hard numbers preserved directly

- Hit chance at equal offense and defense: `66%`
- Maximum documented hit-quality bonus: up to `2x` base damage
- Starting defensive stance pool: `180`
- Defensive stance gain: `1 point` every `50/60/70` Defending ranks by armor placement
- Attack-to-defense trade: `5 attack` -> `1 defensive stance point`
- Spell stance bounds: `70%` to `130%`
- Hidden prep penalty without feat: `3 seconds`
- Post-ranged-attack or offensive-spell movement lock: about `4 seconds` after RT ends
- Minimum melee RT bands: see Section 6.2
- Minimum thrown RT bands: see Section 6.3
- Hide RT milestones: `60/120/180/240` ranks -> `5/4/3/2` seconds
- Stalk RT milestones: `0/40/80/120/160` ranks -> `6/5/4/3/2`

### 13.2 Explicit equations preserved directly

- Effective Strength for melee RT:

  `((Strength x Suitedness) + (Agility x Balance)) / (Suitedness + Balance)`

### 13.3 Inputs preserved, but exact formulas not published

- offensive force generation
- defender combined-defense calculation
- armor-factor versus offensive-factor contest
- maneuver contested rolls
- exact TM hit and damage rolls
- exact debilitation contest math
- exact shield-weight contest formula

## 14. Best-Supported Conclusions

If you need the most actionable mechanical summary from the current DireLore DB, it is this:

- Balance and position are central multipliers in both weapon combat and targeted magic.
- Stance is not flavor; it is a direct percentage allocation of real defensive skill.
- Armor works best when you have the skill to support its protection, but absorption remains valuable even with weaker skill support.
- Hindrance is one of the biggest hidden taxes in combat, especially for evasion and stealth-heavy builds.
- Thrown weapons are a hybrid system that behave like ranged attacks using melee-style math.
- Roundtime reduction is a stat-and-weapon problem, not just a skill-rank problem.
- Magic 3.0 strongly rewards larger, harder casts and preserves explicit stance-ratio tuning for potency, duration, and integrity.
- The DB preserves many ladders and thresholds, but not the engine's exact closed-form combat formulas, so any precise simulator would still need live-game testing or engine code.