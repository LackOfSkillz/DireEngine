# DireEngine Zone Engineering Guidelines

**Status:** Living document. Revisions expected.
**Version:** v0 (initial synthesis from external MUD design literature)
**Purpose:** Engineering ruleset for AI-assisted zone creation in DireEngine.

---

## How this document is used

This is a synthesis of established MUD design wisdom into rules an AI planner and AI critic can apply directly. Each rule is testable. Where a rule is judgment-based, the test is "would a thoughtful human reviewer flag this?" — which means the critic's answer should be flaggable for human review rather than auto-rejected.

The rules in this document feed three places in the AI-assisted zone creation pipeline:

1. **Planner pass** — the AI generating the zone outline reads Sections 1-3 as scaffolding for the plan it produces.
2. **Generator pass** — the AI generating per-room descriptions, NPC content, and quest content reads Sections 2-5 as constraints.
3. **Critic pass** — the AI critic reviewing generated content reads Sections 4, 5, and 7 as the validation checklist.

Section 8 (Process rules) governs how the pipeline is staged and how human review fits in. It is procedural, not content-related.

This document is **versioned alongside the codebase** and **expected to evolve**. The rules here are starting positions, not final answers. As trial zones get built and playtested, expect rules to be adjusted, removed, or added. Every revision should include a dated entry in the change log at the bottom.

---

## Sources

These rules synthesize wisdom from:

- **Andruid (writing-games.org)** — room descriptions, builder style guides, accessibility best practices
- **Morrn, "On Writing Areas"** (grimwheel.com/buildcraft/owa) — narrative-first vs structure-first zone planning, atmospheric mob pattern
- **moremoremuds.org Area Building Checklist** — 30-item production-readiness validation with severity tiers
- **Lysator/InfinityMUD "How to make good quests"** — Bill of Player's Rights, quest structure, plot/prologue/middle/end progression
- **Multiple puzzle design sources** — fairness, hint progression, dependency charts, puzzle types
- **Easter egg design literature** — confirmation that easter eggs are inherently human-authored and lose value when auto-generated

DireEngine-specific overrides (where they exist) take priority over these external sources. See Section 8.4.

---

## Section 1 — Zone-level planning rules (Planner pass)

These rules apply *before* any room or NPC content is generated. The planner pass produces a zone outline; these rules govern what a valid outline looks like.

### 1.1 Genesis order is determined by narrative content

**Rule:** The planner first decides what the zone is *for*. If the zone has a story (rescue the princess from the evil knight Scoundrel), generation starts with the cast (mobs) and key items (objects). If the zone has no story (a city slum, a wilderness path), generation starts with rooms.

**Why:** Story-first zones get incoherent if rooms come first — characters end up scattered without spatial logic. Atmosphere-first zones get sparse if mobs come first — the world feels like a stage set with actors but no setting.

**Critic check:** Does the planned zone have a stated narrative purpose? If yes, are key NPCs and objects named in the plan before room content begins? If no, are rooms anchored by terrain/atmosphere intent rather than left as "generic city space"?

### 1.2 Zone scale follows phase

**Rule:** Zones decompose into prologue / middle / end-game phases.

- **Prologue:** 8-10 rooms maximum. Simple map. Establishes mood, attracts the player to continue.
- **Middle game:** Bulk of rooms. Multiple puzzles or paths available simultaneously. Wide-but-not-shallow structure.
- **End game:** Narrow. Only a few rooms and objects accessible. Should not require items collected 500 turns ago.

**Why:** Prologues that are too large or too hard kill retention before players reach the meat of the zone. Players who never reach the middle game effectively never played the zone at all.

**Critic check:** Does the room manifest separate phases? Is the prologue under 10 rooms? Does the end game require only items obtainable within the end game itself, not from earlier phases?

### 1.3 Map continuity is mandatory

**Rule:** Adjacent rooms must make geographic sense. A "Glacier" cannot directly connect to a "Fire Station" cannot directly connect to a "Cheese Room." Geographic features should extend across multiple rooms (the mountainside continues, the stream flows through several rooms with consistent direction).

**Why:** Geographic incoherence breaks immersion harder than any prose problem. A player who sees a forest connecting directly to an underwater cave loses faith in the world's reality, and that loss is hard to recover.

**Critic check:** For every pair of adjacent rooms, does the transition make terrain/architectural sense? Does any geographic feature mentioned in one room appear consistently in adjacent rooms when relevant?

### 1.4 Map shape avoids square-grid feel

**Rule:** Include diagonal exits (NE, NW, SE, SW) where natural. Include a few long loops players can walk to avoid endless backtracking. For zones over ~30 rooms, include some rapid-travel mechanism (named landmarks, magic words, conduits).

**Why:** Pure orthogonal grids feel mechanical and signal "made by code" rather than "made by a person who walked through it imagining the space."

**Critic check:** What percentage of exits are cardinal-only? Are there any loops? Is there a fast-travel mechanism for long zones?

### 1.5 Density target: meaningful content per room

**Rule:** As a rule of thumb, aim for ~4 interactable items per room (lookable details + objects + NPCs combined), not 4 portable items. Junctions and corridors can be sparse; named rooms should not be.

**Why:** Rooms are precious; empty rooms train players to skim. Once a player learns that descriptions don't reward attention, they stop reading them, and all the careful prose work in the zone becomes invisible.

**Critic check:** What percentage of rooms have zero interactables beyond exits? Any room flagged as "named" (not a corridor) with under 2 interactables is suspect.

---

## Section 2 — Per-room content rules (Generation pass)

These apply during description and content generation per room.

### 2.1 Description length follows audience

**Rule:** RP-focused zones: 5-8 lines / 25-50 words / 2-4 sentences. Hack-and-slash zones: shorter, focused on functional details. The choice is per-zone, not per-room. Once chosen, all rooms in the zone follow the same length range.

**Why:** Description length is a zone-level style decision. Inconsistency feels sloppy.

**Critic check:** What is the variance in word count across the zone? High variance suggests inconsistency. Are length norms set in the zone plan?

### 2.2 Five senses, not just sight

**Rule:** Generated descriptions should include non-visual sensory information. Not all five senses in every room, but the zone overall should distribute sound, smell, touch, taste — not just sight.

**Why:** Critical for accessibility (aphantasia affects ~4% of players; screen reader users rely on non-visual content) and for immersion generally.

**Critic check:** Sample 20% of rooms. What percentage mention sound? Smell? Touch? If under 30% of rooms mention any non-sight sense, flag for revision.

### 2.3 Show, don't tell

**Rule:** "The forest is dark and gloomy" is a violation. "Hardly any light filters through the dense forest canopy" is correct. Descriptions show conditions through specifics rather than naming them.

**Why:** Universal writing principle. AI generation in particular tends toward abstract feeling-words because they're cheap to produce; specific sensory details require more effort and are more memorable.

**Critic check:** Does the description use abstract feeling-words ("gloomy," "creepy," "majestic," "beautiful") without grounding them in specific sensory details?

### 2.4 Don't force player reactions

**Rule:** "The waterfall takes your breath away" is a violation. "The sight of the waterfall is enough to take one's breath away" is correct. The text describes what the room can do, not what the player feels.

**Why:** Roleplaying players need the freedom to roleplay their own reactions. A stoic warrior character should not have their stoicism overridden by description prose forcing emotional reactions.

**Critic check:** Search for second-person directives ("you feel", "you see", "you hear", "your heart"). Flag for revision in RP-focused zones.

### 2.5 No system-handled content in prose

**Rule:** If the engine handles weather, descriptions don't bake in weather conditions. If the engine handles time-of-day, descriptions don't say "the sun is high overhead." Use the engine's state markup (`$state(...)`) for variable content.

**Why:** Engine state authority. Hard-coded prose conflicts with system-driven variation. DireEngine has weather, calendar, and invasion state systems; descriptions must integrate with them, not duplicate them.

**Critic check:** Search for hardcoded weather words ("rain," "sun," "snow," "fog") or time words ("morning," "noon," "evening") outside `$state(...)` blocks.

### 2.6 Include something unique per room

**Rule:** Every named room has at least one specific detail that distinguishes it from other rooms in the zone. Generic prose ("a busy street with shops and people") is a fallback, not a target.

**Why:** Players read descriptions only if there's a reason to. Once they learn the zone is full of generic prose, they stop reading anywhere.

**Critic check:** For each room, can the critic identify one specific feature mentioned nowhere else in the zone? If no, flag.

### 2.7 No pop culture, no contemporary references

**Rule:** No references to real-world current events, brands, internet culture, or modern technology in fantasy/historical zones. No medieval guards using smartphones. No taverns called "Starbucks."

**Why:** Breaks tone within seconds. AI generation is particularly prone to this because training data is saturated with modern references.

**Critic check:** Check description text against a denylist of obvious modern terms (varies by zone genre). For fantasy zones, this is straightforward.

### 2.8 Accessibility floor

**Rule:** No ASCII art in descriptions. No color used as the *only* indicator of important information. No reliance on visual layout for meaning.

**Why:** Screen reader users hear ASCII art as garbled noise. Color-only cues are invisible to visually impaired players. Aphantasic players (~4% of population) cannot visualize what they read; they need straightforward concrete language.

**Critic check:** Search for ASCII characters (`/\|_-+*`) used as decoration. Search for color-only semantic markers.

---

## Section 3 — Population rules (Population pass)

### 3.1 Density gradient by zone type

**Rule:**

- **City zones:** 1 merchant per 8-12 rooms; 1 quest giver per 25-40 rooms; 1 atmospheric NPC per 5-8 rooms; hostiles only in designated unsafe zones.
- **Wilderness zones:** Hostiles in 10-20% of rooms, scaling with depth from safe zones; 1 quest giver at zone entry or critical landmark; foraging available based on terrain.
- **Dungeon zones:** Hostiles in 40-60% of rooms; loot-bearing hostiles average 1-2 per 10 rooms; a boss/landmark at zone end.
- **Guild/institutional zones:** 2-3 NPCs per major room (functional roles); minimal hostiles; quest hooks tied to guild progression.

**Why:** Population density is the difference between zones that feel inhabited and zones that feel like sets.

**Critic check:** Compute the ratio per zone type. Flag deviations beyond 30%.

### 3.2 Hostile placement respects safety conventions

**Rule:**

- No `AGGRESSIVE` mob in the entry room or rooms adjacent to designated `SAFE` rooms.
- No mob more than 1.5× above the zone's intended level bracket.
- Hostiles in wilderness should match terrain (field goblins in plains, sewer rats in tunnels, predatory cats in forests).

**Why:** Aggressive mobs at zone entry kill new players before they understand the zone. Mismatched terrain hostiles break immersion.

**Critic check:** For every aggressive mob, what's the distance from the nearest safe room? For every hostile, does its species match the room's terrain category?

### 3.3 Atmospheric NPCs as ambient layer

**Rule:** Cities and active zones include invisible/non-interactive "atmospheric mobs" that emit periodic ambient messages (a child's laugh, a hawker's call, the clang of a distant smithy). These are immune to attack and don't interact with players.

**Why:** Ambient atmosphere through NPCs is more dynamic than static room prose. The same room feels different at different moments without requiring state-markup variation.

**Critic check:** Does the zone manifest list atmospheric NPCs? Are their messages varied (5+ unique messages per atmospheric NPC)?

### 3.4 NPC equipment matches role

**Rule:** A blacksmith carries hammers and metal goods, not fish. A fisher carries nets and bait. Equipment lists must be semantically consistent with the NPC's role.

**Why:** Edge cases are exactly what make zones feel AI-generated. Players notice the blacksmith with fish.

**Critic check:** For each NPC with inventory, does every item plausibly belong to the NPC's role?

### 3.5 Shopkeeper economy must close

**Rule:** Buy/sell prices cannot allow infinite arbitrage. Sell-back prices are always less than buy prices. Currency types must match the zone's economic context.

**Why:** Economic exploits are zone-killers. One discovered exploit ruins the zone's reputation and forces emergency content patches.

**Critic check:** For every shop, validate buy_price > sell_price for every item. Validate currency is consistent with zone.

---

## Section 4 — Quest design rules (Quest pass)

These rules come from Lysator's "Bill of Player's Rights." Each is testable and each is critic-checkable.

### 4.1 No death without warning

**Rule:** No room exit leads to death without a prior textual hint. Hidden traps must have at least one hint within the surrounding rooms.

**Critic check:** For every death-trap room, search the descriptions of rooms within 2 exits for any hint that signals danger.

### 4.2 No game-state lockout without warning

**Rule:** If an action permanently closes off a path, the description warns that the action is consequential. ("This door looks heavy and would be difficult to open again.")

**Critic check:** For every irreversible state change in quest scripts, is there a warning in the preceding text?

### 4.3 Solvable from current information only

**Rule:** Every quest must be solvable using only information available within the current playthrough — no "you should know from a previous game/life that the bomb is buried under floor 3." No knowledge required from outside the zone unless the zone explicitly bridges from another.

**Critic check:** For every quest step, can the critic identify the in-zone source of information needed to solve it?

### 4.4 Reasonable synonyms

**Rule:** Every interactable object has at least 3 keyword synonyms (e.g., "longsword", "sword", "blade"). NPC dialogue triggers accept multiple natural phrasings.

**Critic check:** Count keywords per object. Flag objects with fewer than 3.

### 4.5 No required items missable later

**Rule:** Items required for late-game puzzles must either be reset on a frequent cycle, or be marked `nodrop`/`noshrop`, or be obtainable from multiple sources.

**Critic check:** For every quest item, is it flagged correctly? If droppable, is it reset frequently enough that a player who drops it can recover?

### 4.6 Good reasons for impossibility

**Rule:** When the player attempts something that won't work, the response either explains why or is genuinely funny. Generic "you can't do that" failures are a violation. ("Down seems more likely" when trying to walk east while falling is the gold standard.)

**Critic check:** Sample 10% of obvious impossible-action attempts in the zone. Are responses specific to the attempt, or generic?

### 4.7 Multi-solution puzzles where reasonable

**Rule:** When a puzzle has an obvious alternate solution, that alternate either works, or generates a thoughtful "good guess but..." response, never silent failure.

**Critic check:** For each puzzle, does the design contemplate at least one obvious alternate approach? Is there an in-game response when that approach is tried?

### 4.8 No required boring tasks

**Rule:** No fetch quests across the entire zone for items that have no narrative reason to be where they are. No mazes that require mapping just to map them. No 10-minute waits at uninteresting junctions.

**Critic check:** For each quest, what's the minimum traversal time? What percentage of that time is *interesting* (encounters, decisions, discoveries) vs *transit*? Flag if transit is over 50%.

### 4.9 Quest reward includes new content

**Rule:** Quest completion grants either narrative advancement (new rooms, new NPCs to talk to, new lore) or interesting items (not just gold). Pure gold rewards are a fallback for trivial quests.

**Critic check:** For each quest, what new content unlocks on completion? Is it more than just stats?

### 4.10 Quest reward proportional to effort

**Rule:** Time-to-complete vs reward ratio is tracked across the zone. Outliers (10-minute quest with epic reward; 3-hour quest with 50 gold) are flagged.

**Critic check:** Compute reward-per-minute. Flag outliers.

---

## Section 5 — Puzzle design rules

### 5.1 Puzzles teach themselves

**Rule:** The first puzzle of a type uses easily-available resources (key in plain sight). Subsequent puzzles of the same type extend the mechanic. The zone never introduces a new puzzle type without first teaching it.

**Why:** Universal puzzle design wisdom (Portal, Baba Is You, Witness). Players must learn the rules through play; explanation in text is a poor substitute.

**Critic check:** For each puzzle type appearing in the zone, where does it first appear? Is the first instance trivially solvable?

### 5.2 Hints are layered

**Rule:** Difficult puzzles have at least 2 layers of hints — an environmental hint (visible in room descriptions) and a more direct hint (NPC dialogue, found note, journal). Players who explore should never be permanently stuck.

**Critic check:** For each puzzle of difficulty > trivial, identify the hint layers. Flag puzzles with only 0-1 hints.

### 5.3 Solved puzzles are explicable

**Rule:** When a puzzle is solved, the player should be able to articulate *why* the solution worked. Solutions found by trial-and-error without comprehension are a violation.

**Critic check:** For each puzzle solution, does the in-game text after solving explain the logic? Is the connection between hint and solution traceable?

### 5.4 Puzzle dependency chart is acyclic and reasonable

**Rule:** The dependency graph between puzzles in the zone has no circular dependencies. No bottleneck puzzle gates more than 30% of zone content unless intentional.

**Why:** Ron Gilbert's Puzzle Dependency Chart concept. A single failed puzzle should not lock players out of large portions of the zone.

**Critic check:** Build the dependency graph. Validate it's acyclic. Check max-bottleneck-impact.

### 5.5 Mazes need a twist

**Rule:** Plain "maze of twisty little passages" mazes are forbidden. If a zone contains a maze, it must offer one of: a non-mapping solution (a guide who can be bribed, fluorescent arrows visible only in dark, a clue that bypasses the maze entirely), or a thematic twist that justifies the maze's existence.

**Why:** Pure mapping mazes signal author laziness. Players who recognize a "standard maze" often abandon zones rather than work through them.

**Critic check:** For each maze room cluster (>5 rooms with low information distinguishability), is there an alternate-solution path?

---

## Section 6 — Easter eggs and game-to-game nods

### 6.1 Easter eggs are human-authored, not AI-generated

**Rule:** The AI generation pipeline does *not* generate easter eggs. Easter eggs are added by humans during the polish phase. The reason: easter eggs derive their value from being intentional acts of authorship, and AI generation systematically produces patterns that read as inauthentic.

**Why:** The easter egg literature consistently identifies "intimacy between creator and player" as the core value. Auto-generation removes the creator. A discovered easter egg is the player saying "someone put this here for me to find" — and the someone has to be a person.

**Critic check:** N/A. This is a process rule, not a content rule.

### 6.2 References to other games are author-curated

**Rule:** When a zone references another game (DragonRealms quotes, Zork nods, fantasy-genre staples), the reference is added by a human reviewer. The AI may suggest *places* where a reference could go (a tavern with a clearly-establishing tone, an NPC archetype that maps to a famous character), but the actual reference text is human-written.

**Why:** Same as 6.1.

### 6.3 Reference obscurity matches audience

**Rule:** When humans add references, they should match the obscurity level to the target audience. A flagship zone designed for new players gets pop-culture-recognizable nods; a deep endgame zone designed for veterans gets niche references.

---

## Section 7 — Production-readiness rules (Critic + ZoneScore pass)

These map directly to the moremoremuds.org area-building checklist with severity tiers preserved.

### 7.1 Critical (block production)

- All standard exits have a return exit unless designed as one-way.
- VNUM ranges don't overlap between zones.
- Sector types match descriptions (Forest sector with forest description).
- No room is a dead-end trap without recall capability unless designed.
- All mob levels are within zone bracket.
- No infinite triggering loops in scripts.
- Shopkeeper economy doesn't permit infinite gold.
- All armor/weapons within stat caps.
- All wear-flags valid.
- Quest variable parsing works for all pronoun gender combinations.
- Players cannot bypass quest stages.
- Area syntax validates against codebase parser.
- No memory leaks on zone reload.
- Zone connects correctly to world map at all expected boundaries.

### 7.2 Recommended (flag for review)

- Hidden exits have keyword test passing (you can `look <keyword>` to find them).
- No `AGGRESSIVE` mobs adjacent to safe rooms.
- Loot drops are actually carried by mobs.
- Object keywords have at least 3 synonyms.
- Quest items flagged correctly (`nodrop`/`noshrop` where appropriate).
- Quest rewards proportional to effort.
- Quest mobs/objects reset frequently enough for parallel players.
- Spelling/grammar pass.
- Keyword consistency between description nouns and lookable items.
- Light flags correct (indoor/dark vs outdoor/sun).
- Reset table size within engine limits.
- Version control commit with changelog.

### 7.3 Optional (ZoneScore bonus)

- Five-senses coverage above 30% of rooms.
- Item weight/bulk realistic.
- Extra descriptions for non-takeable mentioned objects.

---

## Section 8 — Process rules

### 8.1 Pipeline phases are explicit

The AI-assisted zone creation pipeline is:

1. **Plan** (zone outline, narrative arc, room manifest, NPC manifest, quest list) — AI generates, human reviews.
2. **Generate** (per-room descriptions, per-NPC content, per-quest content) — AI generates against the plan.
3. **Audit** (critic pass against rules in this document, ZoneScore measurement) — AI critic flags issues; human triages.
4. **Polish** (specific room rewrites, easter eggs, named-NPC characterization, nods to other games) — Human edits.
5. **Playtest** — Real players or human admin walks through. Issues feed back to revisions.

### 8.2 ZoneScore is necessary, not sufficient

**Rule:** A zone passing ZoneScore 70+ is *eligible* for production. A zone is *ready* for production only after Phase 4 (human polish) and at least one Phase 5 (playtest) cycle.

**Why:** ZoneScore measures schema completeness and density. It does not measure fun.

### 8.3 The 5% problem is the killer

**Rule:** Reviewers focus their attention on detecting the 5% of rooms/NPCs/quests that are *visibly wrong* (semantic contradictions, broken hooks, hallucinated references). The 80% of correct content does not need close review; the 15% of unmemorable-but-correct content does not block release; the 5% wrong content does.

**Why:** One broken room makes the whole zone feel unreliable. Players don't say "20 out of 21 rooms were great" — they say "the zone has bugs."

**Critic check:** The AI critic prioritizes flagging *contradictions* over flagging style nits. A merchant whose description doesn't match their inventory is a critical flag; a description that's slightly bland is not.

### 8.4 Style guide per project

**Rule:** Each project has its own style guide that overrides defaults in this document. DireEngine's style guide is enforced as a higher-priority source than any rule here.

**Why:** Different games have different audiences and tones. A guideline appropriate for a roleplay-focused fantasy game may be wrong for a hack-and-slash sci-fi game.

---

## Open questions / known gaps

This v0 document does not yet address:

- **Cross-zone coherence.** How do adjacent zones share theme, NPCs, lore, and difficulty curves? Currently each zone is treated in isolation.
- **DragonRealms-specific design wisdom.** The DR engine lineage has its own builder traditions; those are not yet captured here.
- **Gemstone IV builder docs.** Same as above; relevant given the engine inspiration.
- **Player-driven content.** Rules for zones that include player-housing, player-shops, or other player-modifiable content.
- **Seasonal and event-based content.** How holiday or seasonal events overlay onto zones.
- **Multi-language considerations.** The Lysator paper specifically notes localization; not yet addressed here.

These gaps will be filled as needed when specific dispatches surface them.

---

## Change log

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-05-01 | v0 | Initial synthesis from external MUD design literature | Claude (research synthesis) |

---

*This document is part of the DireEngine project documentation and is expected to evolve alongside the codebase. Pull requests and revisions are welcome.*
