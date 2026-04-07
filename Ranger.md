# Ranger Research Brief

This file is the canonical brief for Aedan's DireLore research pass on Rangers.

Goal: produce an implementation-grade Ranger guild packet for Dragonsire.

## Verification Status

Verified on 2026-04-06 against the live `direlore` PostgreSQL database on port `5432` using the supplied credentials.

Confirmed from current DireLore data:

- `canon_professions` contains a canonical `Ranger` profession row.
- `profession_skills` confirms Ranger profession buckets as `survival`, `weapon`, `armor`, `magic`, and `lore`.
- raw DireLore content confirms a Ranger command category with 17 Ranger-command pages.
- raw DireLore content confirms Ranger ability pages including beseeches, dual load, personal trail markers, pounce, ranger cache, ranger signs, ranger trail system, scout awareness, sign command, slip, snipe, wilderness bonus, and ranger companion content.
- raw DireLore content confirms Ranger spell coverage including `Animal Abilities` and `Nature Manipulation` spellbooks plus multiple named Ranger spells.

Not yet normalized enough in the current database to trust without targeted extraction:

- join and induction flow
- trainer and buyer mapping
- exact early-circle advancement steps
- exact implementation-ready command syntax for every Ranger mechanic

This means the brief is directionally correct as a research packet, but Aedan still needs to extract the raw-page details for the sections above instead of assuming the normalized canon tables are complete.

This is not a lore exercise.
This is not a flavor dump.
This is not a wiki summary.

The output must be usable to build a Ranger vertical slice that proves guild join, profession identity, skill loops, economy loops, and early progression.

## Why Ranger First

Ranger is the correct first profession slice because it proves:

- perception and track-style gating
- gathering and resource loops
- tool-gated interactions
- clean sell loops and profession-specific economy
- progression tied to action rather than abstract XP

It also avoids Empath-specific edge cases and recovery mechanics that would distort the first guild implementation.

## Research Constraints

The research must stay implementation-focused.

Do not return:

- lore dumps
- history summaries
- long fiction excerpts
- vague class fantasy language without mechanics
- unstructured lists of abilities or spells
- unsupported assumptions stated as fact

Every section must prioritize:

- commands
- mechanics
- requirements
- player-facing loops
- gating
- edge cases
- confidence level

If source material is incomplete, say so explicitly.
If a mechanic is uncertain, label it speculative.

## Required Output

Produce exactly this structure.

# RANGER GUILD PACKET v1

## 1. Guild Identity

Provide:

- guild name
- core philosophy in 1 to 2 paragraphs maximum
- role in world in mechanical terms, not lore fluff

## 2. Join / Induction Flow

Write the guild entry flow as a step-by-step sequence.

For each step include:

- where it happens
- required NPCs
- requirements such as skills, items, stats, or none
- commands used
- success conditions
- failure cases
- repeat-attempt rules

This section must use this format:

Step 1:
Step 2:
Step 3:

## 3. Circle Advancement Model

For each early circle, include:

- required skill ranks by category if applicable
- required actions if any
- required items or tasks
- trainer interaction
- titles unlocked

If the source material does not support a full circle table, state the strongest verified advancement model available.

## 4. Skill System

List all skills used by Rangers.

For each skill provide:

- name
- category: primary, secondary, or tertiary
- what actions train it
- what systems it affects

Use this format:

Skill: Foraging
Category: Primary
Trained by: forage, gather
Affects: resource discovery rate

## 5. Abilities / Verbs

List all Ranger-specific commands.

For each include:

- verb name
- syntax
- requirements
- effect
- cooldown or cost if known

Use this format:

Verb: TRACK
Syntax: track <target>
Requirements: if known
Effect: reveals direction or history
Cooldown/Cost: if known

## 6. Spell System

If Rangers have spells, provide:

- spell list
- prerequisites
- slot system or spellbook structure
- usage mechanics

If spells are not applicable or incomplete in the source, state that clearly.

## 7. Economy Loops

This section is mandatory.

Define how Rangers make money.

Cover at minimum:

- foraging and what items it yields
- hunting and what drops it creates
- skinning and what materials it yields
- tracking and whether it has indirect economic value

For each loop use this format:

Loop Name:
Discover:
Interact:
Transform:
Sell:
Skills Trained:

## 8. Perception Model

Define what Rangers can perceive that others cannot.

Include at minimum:

- tracks
- animals
- environmental cues
- hidden resources

Also include:

- tool requirements if any
- skill thresholds if any

## 9. Tools and Equipment

List required or typical tools.

Examples include:

- bow
- skinning knife
- traps
- nets
- profession-specific tools if any

For each tool include what systems depend on it.

## 10. NPC Ecosystem

Identify:

- guild leader or leaders
- trainers
- buyers and relevant merchants
- special NPC interactions

Buyers matter. Do not omit where Ranger outputs are converted into money or advancement.

## 11. Restrictions / Identity Rules

Document profession-specific penalties, expectations, or mechanical constraints.

If none are supported by the source, explicitly write:

none

## 12. Edge Cases / Gotchas

Document failure and friction points such as:

- tracking failure conditions
- skinning failure
- resource depletion
- environmental gating
- conflicting systems
- repeat-attempt restrictions

## 13. Source Confidence

For each section, rate confidence as one of:

- high confidence
- partial
- speculative

If possible, attach the reason for the rating.

## Source Requirements

Use DireLore and closely related DragonRealms source material to support the packet.

For each section:

- separate verified facts from inference
- prefer command syntax, trainer flow, gating rules, and system descriptions over flavor
- identify where the source is thin or contradictory

If exact syntax differs by era or source, note that instead of collapsing variants into fake certainty.

## Implementation Warning

Do not recommend building profession-specific one-off systems as the long-term architecture.

Do not frame the result as:

- build a Ranger tracking system
- build a Ranger foraging system
- build a Ranger hunting system

Instead, the packet must support a later conversion into generic systems with Ranger configuration layered on top.

The research should help us build:

- a generic perception gating system
- a generic resource discovery system
- a generic tool-gated interaction system
- a generic profession progression model
- a generic sell and buyer loop

Ranger should prove the systems. Ranger should not hardcode the systems.

## What Ranger Must Prove

The packet must support an implementation that proves:

- only Rangers or Ranger-gated perception can see certain tracks or cues
- forage to bundle to sell works as a coherent loop
- tool gating works, such as knife enabling skinning
- Ranger income feels different from other professions
- progression is tied to action, not abstract XP grinding

## Success Criteria

Ranger is considered done when a new player can:

- join the guild
- forage
- hunt or skip hunting if the loop allows it
- sell gathered goods
- gain relevant skills
- advance from circle 1 to circle 2

Without:

- admin help
- debug commands
- manual intervention

## Deliverable Rules For Aedan

- Keep each section compact and structured.
- Prefer tables or repeated field blocks where useful.
- Do not bury commands inside prose.
- Do not hide missing information.
- If a section lacks evidence, mark it partial or speculative instead of improvising.
- If a mechanic seems iconic but dangerous to implement early, call that out.

## Appendix: Prior Hypotheses To Verify, Not Assume

These are useful starting ideas from prior notes, but they must be verified against source material rather than copied straight into implementation.

- Rangers appear to be a survival-forward profession rather than simply an archery guild.
- Tracking, scouting, trails, and wilderness perception are likely core identity systems.
- Foraging, gathering, skinning, and related economy loops are likely central to early implementation value.
- Wilderness attunement or environment-linked bonuses may be a profession identity hook.
- Ranger magic may exist, but it should not displace the survival and economy core of the first slice.
- Companions, advanced traversal, and deeper supernatural features may be important long-term but are likely poor first-slice targets.

Treat every item in this appendix as a hypothesis to confirm, constrain, or reject.

## Appendix: Partially Populated Ranger Guild Packet

This section is a partial Ranger guild packet populated directly from the current DireLore database contents on 2026-04-06.

It is intended to support implementation planning for guild joining and early training.

It is not complete.

### 1. Guild Identity

Guild name:
Ranger Guild

Core identity:
DireLore consistently presents Rangers as survival-first protectors of the wild. Their profession identity centers on tracking, hiding, foraging, ranged hunting, nature-oriented magic, and maintaining a meaningful relationship with wilderness rather than city life.

Mechanical role in world:
Rangers are expected to advance primarily through Survival skills, while also maintaining enough Weapon, Armor, Magic, and Lore to satisfy guild progression. DireLore repeatedly frames them as a broad-spectrum profession with especially strong ties to scouting, outdoorsmanship, perception, stealth, bows, and wilderness-dependent advantages.

Source confidence:
High.
Supported by `canon_professions`, `profession_skills`, `Ranger new player guide`, `Ranger introduction speech`, and `Category:Ranger abilities`.

### 2. Join / Induction Flow

What DireLore currently supports:

Step 1:
Find a Ranger guildleader or guildhall.
Crossing support is explicit: the Crossing guild hall is in a small glade just outside the walls, and Guild Leader Kalika tends young Rangers there. DireLore also lists multiple Ranger guild leaders in other regions.

Step 2:
Satisfy join eligibility.
The `Attributes` page states that Rangers have joining stat requirements of: Strength 8, Stamina 8, Agility 8, Reflex 7, Intelligence 7, Charisma 6, Wisdom 6. It also states that a guildleader may refuse entry if any stat is below 8.

Step 3:
Use `JOIN`.
The Ranger new player guide says players who have found the guild should use the `JOIN` command to become Rangers.

Step 4:
Induction speech and profession application.
Kalika's introduction speech says: "To join us, you merely need to do just that. Just JOIN to become part of our ranks." The same speech then describes the player being appointed a Journeyman Ranger, tutored in Ranger lore and craft, returned to Kalika, and prepared for induction into the guild.

Step 5:
Post-induction orientation.
DireLore implies that induction immediately grants guild membership and tutorial-style orientation. The new player guide assumes the player has already joined and begins explaining how to train as a Ranger from there.

Best current implementation reading:
The DireLore-backed join path is simpler than a quest-gated induction. The player appears to join by meeting minimum stat requirements, reaching a guildleader, and using `JOIN`. The narrative induction sequence happens as part of that acceptance, not as a separate multi-room quest.

Failure cases currently supported:

- insufficient joining stats
- possibly being warned to be certain before choosing the path

Failure cases not yet fully confirmed from current extraction:

- exact rejection text for an ineligible commoner
- whether joining requires a second confirmation `JOIN`
- whether region-specific guildleaders alter the flow

How the profession is applied to a commoner player:
DireLore does not expose a normalized backend state transition, but the player-facing text is explicit that `JOIN` makes the player "become part of our ranks." For Dragonsire, the faithful implementation is: a Commoner meets Ranger join requirements, uses `JOIN` with the guildleader, then their profession changes to Ranger and their onboarding/tutorial state is updated to the Ranger training track.

Source confidence:
Partial.
The command and induction speech are well-supported, but exact failure/retry behavior is not fully extracted yet.

### 3. Guild Leader and Training NPCs

Confirmed Ranger guild leaders and locations from DireLore:

- Kalika: Crossing. Tends young Rangers in a small glade outside the walls.
- Ievia: Riverhaven. Supports young Rangers under 20th circle.
- Tolle: Langenfirth. Explicitly associated with Snipe and hunter's bows.
- Tomma: Shard / western Ilithi border.
- Marion: Aesry.
- Paglar: Boar Clan.
- Roopardua: Forfedhdar wanderer, no fixed guildhall listed.

Confirmed training and register responsibilities from the `Ranger` page:

- Kalika checks 7 different specific Survival skills plus Primary Magic.
- Tolle checks a combination of all bow skills.
- Tomma checks `AL` and foraging.
- Marion checks 3 Stealth skills and Scouting.
- Paglar checks Circle.

Implementation value:
This is enough to design a multi-mentor progression model instead of a single all-purpose trainer. Even if Dragonsire compresses the live DR structure, these registers give a canon-backed reason to split early Ranger progression across survival, stealth, ranged combat, and circle advancement.

Source confidence:
High.

### 4. Circle Progression Model

What DireLore currently confirms for advancement pressure:

- Rangers are required to actively train at least 8 Survival skills to advance within the guild.
- Scouting is explicitly required as the guild-specific skill.
- Rangers must learn at least 2 weapon classes in addition to Parry.
- For circles 1 through 10, Rangers can advance with a single armor skill plus their defending skill.
- After that, Rangers must train 2 armor skills.
- Rangers must move at least 2 Lore skills, though lore requirements are described as light.
- Rangers have access to beseeches starting at 10th circle.
- Snipe becomes learnable at 40th circle from Tolle.
- Slip grows by circle with milestones at 30, 40, 50, 60, and 90.
- Companions have circle gates at 13 for raccoon and 35 for wolf.

Early advancement model Dragonsire can safely infer:

- Circle 1 to 10: strong Survival focus, required Scouting growth, at least 2 weapon classes plus Parry, 1 armor skill, minimal Lore, starter Ranger magic.
- Post-10: second armor requirement becomes relevant, more advanced ability gates start to appear, and Ranger-specific perks begin unlocking by circle and quest.

Important limitation:
The current extraction does not yet provide a clean circle-by-circle full requirement table from 1 upward. It provides advancement rules and circle-gated abilities, which is enough for a first-pass training model but not enough for a full canonical promotion matrix.

Source confidence:
Partial to high.
High for the specific training rules above. Partial for a full circle table.

### 5. Guild Titles

DireLore contains a large Ranger title list with explicit requirement examples.

Confirmed titles and requirements currently extracted:

- `Tenderfoot`: at least 15 Evasion, 15 Skinning, 10 Scouting.
- `Leaf Chaser`: at least 15 Scouting, 15 Outdoorsmanship, 15 Perception.
- `Sojourner`: at least 20 Scouting, 20 Perception.
- `Composter`: must know the Compost spell.
- `Native`: must be at least circle 5.
- `Wildling`: at least 25 Scouting and 25 Outdoorsmanship.
- `Scout`: at least 25 Scouting, 25 Stealth, 25 Perception.
- `Wayfarer`: at least 30 Scouting.
- `Wanderer`: at least 30 Scouting and 30 Athletics.
- `Awakener`: must know `Awaken Forest`.
- `Sun Beseecher`: must know `Beseech the Sun to Dry`.
- `Animal Caller`: at least 150 Outdoorsmanship and must have a companion.
- `Feral`: at least 50 Scouting, 50 Outdoorsmanship, and `Wolf Scent`.
- `Pathfinder`: at least 50 Scouting and 50 Perception.
- `Wildflower`: at least circle 25 and 50 Outdoorsmanship.

Implementation value:
Titles are a useful secondary progression layer and can be added after join and promotion are working. The extracted titles are already strong enough to build a first Ranger title subsystem tied to skill and ability milestones.

Source confidence:
High for listed sample titles. Partial for the full title catalog until a dedicated extraction pass captures the rest cleanly.

### 6. Circle-Gated Ranger Abilities

DireLore-backed ability gates currently extracted:

- 10th circle: `Beseech the Sun to Dry`
- 15th circle: `Beseech Elanthia to Imbue`
- 20th circle: `Beseech the Wind to Clean`
- 25th circle: `Beseech Elanthia to Cradle`
- 30th circle: `Beseech the Wind to Preserve` quest, Slip tier 1
- 35th circle: wolf companion, `Beseech Elanthia to Petrify` quest
- 40th circle: `Snipe`, `Beseech the Dark to Sing`, several horse-training milestones
- 50th circle: `Beseech Elanthia to Seal`, advanced horse-training milestones, Slip tier 3
- 55th circle: `Beseech the Water to Solidify`
- 60th circle: `Beseech the Wind to Refresh`, Slip tier 4
- 65th circle: `Beseech the Wind to Echo`
- 90th circle: `Beseech Elanthia to Transfer`, Slip tier 5

Other extracted thresholds:

- `Scout Awareness`: 16 Scouting
- `Scout Area`: 101 Scouting
- `Personal Trail Markers`: 175 Scouting
- `Cover my Trail`: 200 Scouting
- `Dual Load`: 201 Bows plus Reflex + Agility = 60
- `Snipe`: 40th circle

Source confidence:
High.
This is strongly supported by `Category:Ranger_abilities`, `Ranger_Abilities_Chart`, and `Ranger quest walkthroughs`.

### 7. Immediate Implementation Guidance For Dragonsire

If the near-term goal is to accurately implement Ranger joining and early training, the DireLore-supported minimum viable guild flow is:

1. A Commoner finds Kalika at the Crossing Ranger guild site.
2. The game checks minimum Ranger join stats.
3. The player uses `join`.
4. The player is converted from Commoner to Ranger.
5. The player receives Ranger induction text and a short guided tutorial pass.
6. Early progression requires active training in Survival with mandatory Scouting, plus the minimal Weapon, Armor, Lore, and starter Magic expectations described above.
7. Promotions can initially be routed through a simplified register model while keeping Kalika, Tolle, Tomma, Marion, and Paglar as distinct canon anchors.

What is still missing before calling the packet complete:

- exact rejection and retry messaging for failed joins
- exact full circle requirement tables
- a full normalized guild-title extraction
- a raw-page pass over the Ranger quest pages for each quest-gated beseech and companion milestone

### 8. Source Confidence Summary For This Partial Packet

- Guild leader identity and locations: high confidence
- Join command and basic induction flow: high confidence
- Commoner-to-Ranger profession application: partial, but strongly implied by induction text
- Early training and circle progression rules: high confidence for broad rules, partial for a full table
- Guild titles: partial to high depending on title
- Quest-gated Ranger abilities: high confidence

## Appendix: Ranger 001-030 Microtasks (Locked)

Goal:

By task 030, a player can:

- join Ranger guild
- interact with renamed NPCs
- forage and sell
- perform a basic hunting loop
- pass a simplified advancement check from Circle 1 to Circle 2

### Phase R1 - Profession + Join System

R-001 - Define Profession Enum / Registry

Create:

```python
PROFESSIONS = {
	"ranger": {
		"name": "Ranger",
		"perception_flags": ["tracks", "wild_resources"],
	}
}
```

R-002 - Add Profession Field to Character

```python
character.db.profession = None
```

Default = `commoner`

R-003 - Helper: `get_profession()`

```python
def get_profession(character):
	return character.db.profession or "commoner"
```

R-004 - Ranger Stat Gate Validator

```python
def can_join_ranger(character):
	return (
		character.db.str >= 8 and
		character.db.sta >= 8 and
		character.db.agi >= 8 and
		character.db.ref >= 7 and
		character.db.int >= 7 and
		character.db.cha >= 6 and
		character.db.wis >= 6
	)
```

R-005 - Create Guild Location Tag

Rooms:

```python
room.tags.add("ranger_guild")
```

R-006 - Create Guildmaster NPC (`Elarion`)

Typeclass:

```python
class RangerGuildmaster(NPC):
	key = "Elarion"
```

R-007 - Guildmaster Dialogue Hook

Supports:

- `join`
- `advance`
- fallback dialogue

R-008 - Implement `JOIN` Command

Syntax:

```text
join ranger
```

Flow:

- check location via guild tag
- check stats
- assign profession
- send onboarding text

R-009 - Assign Profession on Join

```python
character.db.profession = "ranger"
character.msg("You are now recognized as a Ranger.")
```

R-010 - Add Join Failure Messaging

Cases:

- wrong location
- insufficient stats

### Phase R2 - Domain NPC System (Renamed)

R-011 - Create Domain NPC Base

```python
class RangerMentor(NPC):
	domain = None
```

R-012 - Create NPC: `Bram Thornhand`

- domain: `survival`
- handles: forage and skin validation

R-013 - Create NPC: `Serik Vale`

- domain: `hunt`
- handles: ranged weapon validation

R-014 - Create NPC: `Lysa Windstep`

- domain: `stealth`
- handles: scouting validation

R-015 - Create NPC: `Orren Mossbinder`

- domain: `lore`
- handles: magic and lore validation

R-016 - Dialogue Routing by Domain

Each NPC responds differently to:

```text
ask <npc> about training
```

R-017 - Add Flavor Differentiation

Each NPC must:

- have unique tone
- use different phrasing
- avoid reused DragonRealms text

### Phase R3 - Resource + Foraging Loop

R-018 - Resource Node Framework (Generic)

```python
{
	"type": "grass",
	"visible_to": ["ranger"],
}
```

R-019 - Render Resource in Room

On `look`:

- show resource if profession matches

R-020 - Implement `FORAGE` Command

```text
forage
```

Flow:

- check for resource
- generate item
- remove node or start cooldown

R-021 - Create Resource Items

Examples:

- `grass tuft`
- `stick bundle`

R-022 - Implement `BUNDLE` Command

```text
bundle grass
```

Converts:

- raw to processed

R-023 - Add Skill Gain Hook

```python
gain_skill(character, "foraging")
```

### Phase R4 - Economy Loop

R-024 - Create Buyer NPC

Example:

```python
class FieldBuyer(NPC):
	accepts = ["grass", "bundle", "hide"]
```

R-025 - `SELL` Command

```text
sell <item>
```

Flow:

- validate item
- remove item
- add currency

R-026 - Add Value Mapping

```python
VALUES = {
	"grass": 1,
	"bundle": 3,
}
```

R-027 - Add Skill Gain on Sell

Optional but recommended:

```python
gain_skill(character, "trading")
```

### Phase R5 - Basic Hunt Loop

R-028 - Create Animal NPC

Examples:

- `deer`
- `rabbit`

R-029 - Skinning Command

```text
skin <corpse>
```

Requires:

- knife check on equipped gear

Returns:

- `hide`

R-030 - Circle Advancement (1 -> 2)

Via `Elarion`:

```text
ask elarion about advancement
```

Check:

- foraging used
- scouting >= minimal threshold
- weapon used, or optional per design toggle

If pass:

```python
character.db.circle = 2
```

### Required DireTest Coverage

Create scenarios:

- `ranger-join`: success and failure
- `ranger-forage`: resource visibility and item creation
- `ranger-economy`: sell loop works
- `ranger-hunt`: kill to skin to item
- `ranger-advance`: Circle 1 to 2

### Design Checkpoint

After R-030, verify:

- nothing is hardcoded to Ranger only beyond configuration and profession flags
- resource system is generic
- NPC domains are reusable for other guilds
- advancement is data-driven, not hand-scripted per profession

### End State

By R-030, Dragonsire should have:

- a real profession system
- a real guild join path
- an original renamed NPC ecosystem
- a functional Ranger economy loop
- a validated early progression path

## Appendix: Ranger 031-050 Patch-Level Implementation (Locked)

This section defines the next controlled expansion after the initial Ranger vertical slice.

Goal:

Turn Ranger from:

- can join

Into:

- can live as a Ranger

### Rules For Aedan

- Do not create new systems.
- Do not duplicate logic.
- Only extend existing code in `typeclasses/npcs.py`, `commands/cmd_ask.py`, `typeclasses/characters.py`, and existing forage, hunt, and skin logic.
- Keep patches small and localized.

### Phase R6 - Domain Mentors

R-031 - Add Bram Thornhand (Survival)

File:

- `typeclasses/npcs.py`

Add:

```python
class RangerMentor(NPC):
	domain = None

	def handle_inquiry(self, speaker, topic):
		topic = topic.lower()

		if topic in ("training", self.domain):
			return self.training_response(speaker)

		return None

	def training_response(self, speaker):
		return "You should not see this."
```

Add Bram:

```python
class BramThornhand(RangerMentor):
	key = "Bram Thornhand"
	domain = "survival"

	def training_response(self, speaker):
		return (
			"The wild provides, if you know how to listen. "
			"Start with forage. Learn what grows beneath your feet."
		)
```

R-032 - Add Serik Vale (Hunt)

```python
class SerikVale(RangerMentor):
	key = "Serik Vale"
	domain = "hunting"

	def training_response(self, speaker):
		return (
			"A clean shot ends suffering quickly. "
			"Practice your aim. Respect your prey."
		)
```

R-033 - Add Lysa Windstep (Stealth)

```python
class LysaWindstep(RangerMentor):
	key = "Lysa Windstep"
	domain = "scouting"

	def training_response(self, speaker):
		return (
			"You are loud. The forest hears you coming. "
			"Learn to move without being noticed."
		)
```

R-034 - Add Orren Mossbinder (Lore)

```python
class OrrenMossbinder(RangerMentor):
	key = "Orren Mossbinder"
	domain = "lore"

	def training_response(self, speaker):
		return (
			"There is power in the old ways. "
			"Understanding comes before control."
		)
```

R-035 - Hook Them Into `ask`

File:

- `commands/cmd_ask.py`

Find where NPC inquiry is handled.

Modify:

```python
response = target.handle_inquiry(caller, topic)
if response:
	caller.msg(f'{target.key} says, "{response}"')
	return
```

No new system. Only ensure mentors respond through the existing inquiry path.

### Phase R7 - Circle System

R-036 - Add Circle Field

File:

- `typeclasses/characters.py`

Inside character creation or initialization:

```python
if not self.db.circle:
	self.db.circle = 1
```

R-037 - Add Advancement Check

File:

- `typeclasses/characters.py`

Add:

```python
def can_advance_ranger(self):
	if self.db.profession != "ranger":
		return False, "You are not a Ranger."

	forage_used = self.db.get("forage_uses", 0)
	scouting = self.get_skill("scouting")

	if forage_used < 1:
		return False, "You have not yet learned to gather from the wild."

	if scouting < 5:
		return False, "Your awareness of the wild is still too shallow."

	return True, None
```

R-038 - Hook Advancement Into Elarion

File:

- `typeclasses/npcs.py`

Inside `RangerGuildmaster.handle_inquiry`:

```python
if topic == "advancement":
	can, reason = speaker.can_advance_ranger()

	if not can:
		return reason

	speaker.db.circle = 2
	return "You have taken your first true step into the wilds."
```

R-039 - Sync State (Optional but Recommended)

File:

- `typeclasses/characters.py`

After circle change:

```python
self.sync_client_state()
```

Only do this if client sync is already used elsewhere for equivalent character state updates.

R-040 - Improve Failure Messaging

Ensure `can_advance_ranger()` returns specific requirement failures instead of generic rejection.

### Phase R8 - Forage Loop Upgrade

R-041 - Add Profession Bonus

File:

- `commands/cmd_forage.py`

Find yield logic.

Modify:

```python
if caller.db.profession == "ranger":
	yield_amount += 1
```

R-042 - Add Skill Influence

```python
foraging = caller.get_skill("foraging")
yield_amount += foraging // 10
```

R-043 - Add Resource Variation

Replace static output with:

```python
import random

roll = random.random()

if roll < 0.7:
	item = "grass"
elif roll < 0.95:
	item = "stick"
else:
	item = "wild herb"
```

R-043.1 - Track Forage Usage

Still in `commands/cmd_forage.py`:

```python
caller.db.forage_uses = caller.db.get("forage_uses", 0) + 1
```

### Phase R9 - Skinning Validation

R-044 - Enforce Tool Requirement

File:

- `commands/cmd_skin.py`

Add:

```python
if not caller.is_wielding("skinning knife"):
	caller.msg("You need a skinning knife to do that.")
	return
```

R-045 - Add Quality Outcome

Replace static hide creation with:

```python
import random

roll = random.random()

if roll < 0.2:
	quality = "poor"
elif roll < 0.8:
	quality = "normal"
else:
	quality = "fine"

hide_name = f"{quality} hide"
```

### Phase R10 - DireTest Patches

R-046 - `ranger-advance-success`

File:

- `diretest.py`

Add scenario:

```python
@scenario(name="ranger-advance-success", tags=["ranger"])
def ranger_advance_success(ctx):
	p = ctx.player()

	ctx.cmd("join ranger")

	ctx.cmd("forage")
	p.set_skill("scouting", 10)

	ctx.cmd("ask elarion about advancement")

	assert p.db.circle == 2
```

R-047 - `ranger-advance-fail`

```python
@scenario(name="ranger-advance-fail", tags=["ranger"])
def ranger_advance_fail(ctx):
	p = ctx.player()

	ctx.cmd("join ranger")
	ctx.cmd("ask elarion about advancement")

	assert p.db.circle == 1
```

R-048 - `ranger-npc-inquiry`

```python
@scenario(name="ranger-npc-inquiry", tags=["ranger"])
def ranger_npc_inquiry(ctx):
	ctx.cmd("ask bram about training")
	ctx.cmd("ask serik about hunting")
	ctx.cmd("ask lysa about scouting")
```

R-049 - `ranger-forage-scaling`

```python
@scenario(name="ranger-forage-scaling", tags=["ranger"])
def ranger_forage_scaling(ctx):
	p = ctx.player()
	ctx.cmd("join ranger")

	before = p.inventory_count()

	ctx.cmd("forage")

	after = p.inventory_count()

	assert after > before
```

R-050 - `ranger-skinning-tool`

```python
@scenario(name="ranger-skinning-tool", tags=["ranger"])
def ranger_skinning_tool(ctx):
	p = ctx.player()
	ctx.cmd("join ranger")

	ctx.cmd("skin deer")

	ctx.give_item("skinning knife")
	ctx.cmd("wield skinning knife")

	ctx.cmd("skin deer")
```

### End State After This Patch Set

You now have:

- multi-NPC guild structure
- advancement system
- skill-based gating
- economy loop scaling
- tool-gated interaction
- DireTest validation