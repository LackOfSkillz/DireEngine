Here's the complete v2 design goals doc:

---

# Zone Design Goals

**Date:** 2026-05-02
**Author:** MT-600-design (companion artifact)
**Status:** Draft v2 for review

## Purpose

This document captures the design principles that any DireEngine zone — AI-generated or human-authored — should satisfy. It exists alongside the AI zone generation orchestration design (`docs/design/ai_zone_generation.md`) and serves three purposes:

1. **Quality criteria for AI generation.** The MT-600 orchestrator's planner consumes these goals as the target each generated zone aims for. The critic uses them (via ZoneScore V1 today, ZoneScore V2 in the future) to evaluate whether output is shippable.
2. **Reference for human authors.** Whatever path the AI takes through the zone authoring pipeline, a human builder should be able to follow the same path. These goals describe what good looks like regardless of who or what is doing the authoring.
3. **Locked design language.** When a future dispatch asks "is this zone good enough," these goals are the vocabulary used to answer.

## Document structure

- **Zone topology and types** — six zone types, the doorway-room pattern, multi-zone composition
- **Tier 1 goals (G1-G3)** — immersion fundamentals
- **Tier 2 goals (G4-G6)** — engagement and exploration
- **Tier 3 goals (G7-G9)** — identity and memorability
- **Tier 4 goals (G10-G12)** — mechanical and systemic engagement
- **Tier 5 goals (G13-G15)** — variety and replayability
- **Structural goals (G16-G18)** — geographic persistence, zone-type appropriateness, doorway clarity
- **Demo zone goals (S1-S5)** — additional requirements for the starting/demo zone
- **Applicability matrix** — which goals apply to which zone types
- **AI generation guidance** — how the orchestrator consumes these goals
- **Demo zone composition (Path C scope)** — the locked v1 scope for what the demo zone produces

These goals are derived from a synthesis of MUD design (Bartle), MMORPG zone design (Blizzard's WoW level designers), classic level design principles (Dan Taylor's Ten Principles), environmental storytelling theory, and procedural generation lessons (Minecraft biomes), plus DireEngine-specific learnings about geographic structure and zone topology from the DragonRealms reference layouts.

---

## Zone topology and types

DireEngine zones are not all the same shape. The authoring approach, applicable goals, and AI generation strategy depend on what kind of zone is being authored. Six zone types are defined:

### Type 1: Outdoor city/town zones

Public outdoor spaces in a settlement: streets, alleys, plazas, parks, docks, market squares, gates, bridges. The Crossing-style map. These zones are the navigational backbone of urban areas.

Characteristics:
- Streets and alleys span multiple rooms and have persistent names
- Districts contain multiple streets
- Doorway rooms transition into Type 3-5 interior zones
- May have terrain variation within (paved street vs cobblestone alley vs muddy back lot)
- Maps are dense and player-legible

### Type 2: Wilderness zones

Forests, plains, mountains, coastlines, swamps, deserts, open dungeons. Geographic features (trails, rivers, ridges, named groves) span multiple rooms and persist.

Characteristics:
- Named geographic features (the King's Road, the Whisperwood, the Ironback Hills) span rooms
- Terrain shifts within the zone (forest interior vs forest edge vs clearing)
- Foraging hooks dense throughout
- May have doorway rooms transitioning to Type 3-5 zones (caves, ruins, dungeons)
- Maps are sparser than city zones, with longer travel distances between features

### Type 3: Small/discrete interior zones

Single-purpose interiors: a shop with a back room, a small temple, a private cottage, an inn's common room. Typically 1-10 rooms.

Characteristics:
- Connected to a parent zone through one or more doorway rooms
- Single coherent purpose (commerce, worship, residence)
- Internal navigation is simple — usually no need for street-style geographic structure
- One or two NPCs typical
- Authored as a quick adjunct to the parent zone

### Type 4: Medium/structured interior zones

Larger interior environments with their own internal navigation: an academy, a guild hall, a manor house, a ship interior. Typically 10-50 rooms.

Characteristics:
- One or more entrances from a parent zone
- Internal geographic structure (floors, wings, halls, named rooms)
- Multiple NPCs with distinct roles
- May have its own emotional tone distinct from the parent zone
- Authored as its own zone with its own design pass

### Type 5: Large/dungeon-like interior zones

Sprawling underground or interior spaces: dungeons, large temple complexes, multi-level guild headquarters, the Underwater Mansion. May exceed parent zone size.

Characteristics:
- Internal structure resembles outdoor structure (named corridors function like streets)
- Multiple districts (the temple's outer halls, inner sanctum, crypts beneath)
- May have its own internal map and progression structure
- Multiple entrances or progression-gated zones common
- Authored as a major zone in its own right

### Type 6: Transit zones

Linear or sparse zones whose primary purpose is connecting two larger zones: the road between two cities, a ferry line, a mountain pass.

Characteristics:
- Few rooms, mostly linear
- Often serves as a "loading zone" between major content areas
- May have minimal content beyond traversal
- Sometimes hosts encounter content (bandit ambushes, travelers met on the road)

### The doorway-room pattern

Interior zones (Types 3-5) connect to parent zones (Types 1, 2) through doorway rooms. A doorway room is a single room on the parent zone that:

1. Exists on the parent zone's map (visible to players navigating the city or wilderness)
2. Has a normal description that includes the building/entrance from outside (the academy's tall stone facade, the shop's painted sign, the temple's columns)
3. Contains a transition exit using a verb appropriate to the entrance (`go arch`, `go gate`, `enter shop`, `climb stair`)
4. The transition exit moves the player into the interior zone, which is a separate authored zone

The doorway room belongs to the parent zone for navigation purposes but coordinates with the interior zone for narrative coherence — both should reference the same building name, the same architectural style, the same general identity. The interior's entry room often describes the doors leading back out (a "thanks for visiting" view from inside).

This pattern keeps maps clean (interiors don't clutter the city map) while preserving narrative coherence between exterior and interior.

### Cross-zone transitions vs doorway transitions

Two distinct kinds of transitions exist:

- **Doorway transitions:** Parent zone room → child interior zone (the academy, the shop). Interior is small or focused; player typically returns to the parent zone after their interaction.
- **Cross-zone transitions:** One major zone → another major zone (Crossing → Riverhaven, Crossing → the road north). Both zones are major; player often spends substantial time in either.

Both use exit verbs but have different authorial implications. Cross-zone transitions are world-level connections; doorway transitions are local-level connections.

---

## Tier 1: Immersion fundamentals

These are non-negotiable. A zone that fails Tier 1 isn't a zone — it's a checklist with words attached.

### G1. Physics-first consistency

Every room conforms to its terrain, climate, locality, and the broader world's rules unless there's a deliberate reason not to. A swamp room is wet. A mountain pass is cold. A coastal road has salt air. A city alley has the noise of the city around it.

Concretely:
- Room descriptions match `terrain.primary` and `terrain.secondary` tags
- Weather references are compatible with the zone's climate
- Foraging-eligible terrain produces foraging-appropriate prose hooks
- State-aware variants reflect actual atmospheric changes
- Adjacent rooms share atmospheric rules

This is Bartle's principle: "in the absence of a reason not to conform to reality, conform to reality."

### G2. Internal coherence within zones

Adjacent rooms feel like part of the same place. Same color palette, same atmospheric register, consistent landmark references.

A landmark visible from multiple rooms is referenced consistently. The zone's emotional tone is steady across rooms unless transition is deliberate. Faction control, civilization density, and danger level shift gradually. A river running through the zone is referenced wherever it's geographically present.

Two rooms in the same zone should never read like they're in different worlds.

### G3. Lived-in detail

Every room has at least one specific, throwaway, non-functional detail that makes the space feel inhabited. A child's chalk drawing on the wall. An empty cup forgotten on a barrel. Muddy footprints leading toward the door.

These details aren't quest hooks or lootable items — they're texture. They imply history without spelling it out. Even wilderness rooms have lived-in detail (a half-eaten carcass, trampled grass where deer recently bedded).

This is Blizzard's "wagon abandoned in the middle of a farm" principle.

---

## Tier 2: Engagement and exploration

### G4. Visual flow / Narrative flow

Room descriptions reference what's nearby. Exits hint at what comes next without spoiling it. Prose subtly directs attention.

A description ending with "the path continues north into deeper woods" tells the player there's more without forcing them. A description mentioning "smoke rises above the tree line to the east" draws attention to a feature in another room. Descriptions integrate exits into prose rather than listing them separately.

This is Dan Taylor's "fun to navigate" principle adapted for text.

### G5. Reward exploration

Every room has something to examine, look at, or interact with that isn't strictly required. Players who run through get the basic experience; players who linger get more.

Each room has at least one `details` entry. Some rooms have `read` targets. Some have hidden features that reward `search`. Combat-irrelevant interactions exist.

A bare-bones "you are in a forest" room with nothing to investigate fails this principle.

### G6. Surprise

Each zone has at least 2-3 rooms that defy player expectation: an unexpectedly beautiful vista, a moment of stillness in a hostile area, a strange detail hinting at deeper lore.

A dangerous zone has at least one peaceful room. A peaceful zone has at least one moment of unease. Some rooms break the zone's normal rhythm.

Dan Taylor: "surprise is a rapid surge in uncertainty, and uncertainty is the essence of fun."

---

## Tier 3: Identity and memorability

### G7. Emotional tone

Every zone has a definable feeling — melancholy, menace, wonder, urgency, peace, mystery, decay, hope. This tone is consistent across all rooms and is communicated through prose word choice, atmospheric detail, and pacing.

The zone's emotional tone is set in the `generation_context` (locked decision: human-authored, not AI-invented). Word choice in descriptions reflects the tone. A melancholy zone uses different vocabulary than a hopeful one.

A good zone has a feeling, not just a function.

### G8. Cultural signature

Settlements display the architecture, customs, and values of their inhabitants through environment alone. A dwarf hold reads as dwarvish without saying so. An elven grove reads as elvish without saying so.

Building materials, decorative motifs, and signage reflect cultural values. Even abandoned settlements still communicate the culture of their former inhabitants. Multi-cultural zones layer signatures rather than averaging them.

### G9. Memorable anchors

Each zone has at least one defining feature — a landmark, a vista, a recurring atmospheric note — that players will remember and use as a mental anchor.

A defining landmark visible from multiple rooms. A recurring atmospheric element (the sound of distant drums, the smell of woodsmoke). A signature room everyone passes through.

When a player thinks "that zone with the broken lighthouse," they're naming the anchor.

---

## Tier 4: Mechanical and systemic engagement

### G10. Show, don't tell

Lore and history are communicated through environmental detail (ruins, signage, abandoned camps, weathered statues), not exposition. Players who pay attention learn things.

A zone's history is implied through what remains: a battlefield with old armor, a temple ruin with broken iconography, a ghost town with abandoned tools. NPCs reference history in passing rather than delivering exposition.

Pardo's "play don't tell" rule.

### G11. Multi-skill engagement

Every zone supports multiple character types — foraging targets for survival, study items for scholarship, NPCs for social play, danger for combat, lockable containers for thieves, lore for scholars.

Wilderness zones offer foraging, hunting, tracking, combat. Settlement zones offer NPCs, shops, services. Mixed zones offer all of the above. Specialty zones lean heavily into one skill but still offer baseline engagement for others.

A zone serving only one character type is flat.

### G12. Mechanical hooks tied to atmosphere

The mechanical layer reflects the narrative layer.

Foraging in a swamp yields swamp-specific items. Foraging at night yields different items than during the day. Weather affects encounter tables. Time of day affects NPC presence. Recent zone events leave visible traces.

The mechanical layer should not feel bolted on. It should feel like a consequence of the zone's narrative reality.

---

## Tier 5: Variety and replayability

### G13. Biome-keyed variety

Two zones with similar terrain shouldn't read identically. Each has its own twist, focus, emotional tone. Same physics, different feeling.

Two coastal zones might both have salt air and gulls but feel different — one a bustling port, one an abandoned smuggler's cove. Variety comes from emotional tone (G7), cultural signature (G8), and memorable anchors (G9), not from breaking physics.

The Minecraft lesson: rules consistent, expression varied.

### G14. Transition richness

Boundaries between zones (and between micro-areas within zones) are deliberately constructed. Players should feel the transition.

Zone borders have transitional rooms. Within zones, micro-area transitions (city gate to outskirts, market square to back alleys) are marked by deliberate prose shifts. Sounds, smells, light quality, and population density shift gradually.

The boundary between things is often where worlds feel most magical.

### G15. Reasons to return

Every zone has at least one feature that pulls players back: time-gated content, weather-dependent events, NPCs whose state changes, regrowing resources, hidden things only some characters can find.

Foraging tables produce different yields based on weather, time, season. NPCs have schedules. Some content is gated by skill rank. Quest hooks rotate or refresh.

A zone you visit once and never return to is forgettable.

---

## Structural goals

These goals govern the geography and topology of zones. They are as important as Tier 1 goals — failing them produces zones that read as fake — but they operate at a structural rather than experiential level.

### G16. Geographic structure persistence

Named geographic features span multiple rooms and persist across them. A street is a long feature with rooms along it; the street name doesn't change at every intersection. A river referenced in one room is referenced consistently in every room it passes through. A trail named in the south end of a forest keeps that name in the north end.

For Type 1 (outdoor city) zones:
- Streets span multiple rooms; the same street name applies to all rooms along it
- Streets curve and continue (a street running N-S that bends NE/E and continues E is still the same street)
- Alleys branch off streets and have their own persistent names
- Plazas, squares, and intersections are named places where streets meet
- Districts contain multiple streets and have persistent names
- Bridges, gates, and major landmarks are named features

For Type 2 (wilderness) zones:
- Trails, paths, and roads have persistent names across all rooms they traverse
- Rivers, streams, and coastlines are named features referenced consistently
- Forest sections, glades, ranges, and ridges have persistent names
- Mountain passes, valley floors, and other named topographic features persist

For Type 4-5 (medium/large interior) zones:
- Halls, corridors, and named passageways span multiple rooms
- Floors, wings, and named sections persist
- Chambers and named rooms have stable names that are referenced from adjacent rooms

This goal solves the "every room has a different street name" failure mode. The geographic structure is authored at a higher layer than room prose; AI-generated descriptions consume the structure rather than inventing it.

### G17. Zone-type appropriateness

Each zone is authored according to its type. Outdoor city zones follow city rules. Wilderness zones follow wilderness rules. Interior zones follow interior rules. Transit zones follow transit rules.

The zone's type is set in the zone's metadata (a top-level field, e.g., `zone_type: outdoor_city`) and is consumed by the AI orchestrator as a constraint that shapes generation choices. A wilderness zone shouldn't have street structure. A small interior zone shouldn't have districts. A transit zone shouldn't have multi-skill engagement targets if its purpose is movement.

The applicability matrix below codifies which goals apply to which zone types.

### G18. Doorway clarity

Doorway rooms (parent-zone rooms that transition to child interior zones) clearly signal the transition.

Concretely:
- The exterior description references the building or entrance (the academy's tall stone facade, the shop's painted sign, the temple's columns)
- The exit verb is appropriate to the entrance (`go arch`, `go gate`, `enter shop`, `climb stair`, `go path`)
- The interior zone's entry room references the doors back out (the player can see how to leave)
- Both zones share landmark naming where relevant — if the doorway is "the iron gate of Asemath Academy" on the outside, the inside should know it's the iron gate
- Hidden or unmarked entrances are deliberate exceptions, used sparingly for specific narrative effects

Doorway rooms are the seams between zones. Done well, players don't notice them. Done poorly, the seams break immersion.

---

## Demo zone goals (S1-S5)

The starting zone has a special burden: it's how new players form their first impression of the entire system. Beyond the goals above:

### S1. Showcase the system's breadth

The starting zone must demonstrate every major subsystem at least once: foraging, state-aware descriptions, NPC interactions (idle dialogue, merchant trade, quest hooks, services), combat, skill checks across multiple skills, inventory mechanics, multi-terrain movement, doorway-to-interior transitions.

### S2. Density of inhabitation

The starting zone should feel populated. Multiple merchant NPCs with different specializations. Quest-giver NPCs scattered (not clustered in one quest hub). Patrolling guards or other moving NPCs. Service NPCs (healer, trainer, banker, innkeeper). Ambient NPCs (children playing, elders gossiping) for texture.

### S3. Approachable difficulty curve

Easy areas near entry points. Harder areas accessible but optional. Clear visual/prose signals for what's appropriate at what skill level.

### S4. Memorable first impressions

The zone has set-piece moments designed to be the player's "first time" experiences: the first vista showing the world's scope, the first NPC interaction with personality, the first foraging success, the first combat victory, the first time the player notices state-aware content. These aren't accidental. The starting zone choreographs them.

### S5. Replay value

Players will create new characters and revisit. Some content is character-class specific. Quest hooks vary by character background. Time-gated content provides reasons to return. Dynamic NPC schedules mean the zone reads differently at different times.

---

## Applicability matrix

| Goal | Type 1 Outdoor city | Type 2 Wilderness | Type 3 Small interior | Type 4 Medium interior | Type 5 Large interior | Type 6 Transit | Demo zone composition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G1 Physics consistency | Required | Required | Required | Required | Required | Required | Required |
| G2 Internal coherence | Required | Required | Required | Required | Required | Required | Required |
| G3 Lived-in detail | Required | Recommended | Recommended | Required | Required | Recommended | Required |
| G4 Visual flow | Required | Required | Recommended | Required | Required | Required | Required |
| G5 Reward exploration | Required | Required | Recommended | Required | Required | Recommended | Required |
| G6 Surprise | Recommended | Recommended | N/A | Required | Required | Recommended | Required |
| G7 Emotional tone | Required | Required | Required | Required | Required | Required | Required |
| G8 Cultural signature | Required | N/A (or ruins-only) | Required | Required | Required | Recommended | Required |
| G9 Memorable anchors | Required | Recommended | N/A | Required | Required | N/A | Required |
| G10 Show don't tell | Required | Recommended | Recommended | Required | Required | Recommended | Required |
| G11 Multi-skill engagement | Required | Required | Recommended (specialty) | Required | Required | Optional | Required |
| G12 Atmospheric mechanics | Recommended | Required | Recommended | Required | Required | Recommended | Required |
| G13 Biome-keyed variety | Required | Required | Recommended | Required | Required | Recommended | Required |
| G14 Transition richness | Required | Recommended | N/A (single point of entry) | Required | Required | Required | Required |
| G15 Reasons to return | Recommended | Recommended | Recommended | Recommended | Recommended | Optional | Required |
| G16 Geographic persistence | Required | Required | N/A (too small) | Required (internal halls) | Required | Recommended (route names) | Required |
| G17 Zone-type appropriateness | Required | Required | Required | Required | Required | Required | Required |
| G18 Doorway clarity | Required (parent side) | Required (parent side) | Required (child side) | Required (child side) | Required (child side) | N/A (cross-zone transitions handled separately) | Required |
| S1-S5 Demo zone goals | N/A | N/A | N/A | N/A | N/A | N/A | Required |

A demo zone composition (the outdoor demo zone plus its associated interior zones, treated as a unit) is required to satisfy every goal. That's why the demo composition is the hardest content to author and the right validation target for end-to-end AI generation.

---

## How AI generation should consume these goals

The MT-600 orchestrator's planner should treat these goals as the target each phase aims for:

- **Phase 1 (Zone-type setup):** G17. Human authors set the zone's type and emotional tone (G7) in `generation_context`. The orchestrator consumes this as the top-level constraint.
- **Phase 2 (Geographic structure):** G16, G14. Streets, alleys, districts, named landmarks, named geographic features for outdoor zones; halls, wings, named sections for medium/large interiors. Layer 2 authoring before any prose is generated.
- **Phase 3 (Room descriptions):** G1, G2, G3, G4, G5, G7, G10. Consume Layer 2 metadata; prose references geographic features by name rather than inventing them.
- **Phase 4 (Stateful descriptions):** G1, G2, G6, G12. Augment descriptions with state-aware variants for weather/time/invasion.
- **Phase 5 (Identity tags):** G1, G7, G8. Tag rooms with vocabulary that supports vocabulary-driven downstream generation.
- **Phase 6 (NPC roster):** G7, G8, G10, G11, S2. Generate NPCs (descriptions, idle dialogue, merchant flags, quest-giver flags) appropriate to the zone's identity. AI-authored.
- **Phase 7 (Item placements):** G3, G11, G12. Use the existing template service; AI selects from templates rather than authoring new items. Per Path C scope.
- **Phase 8 (Quest hook stubs):** G10, G11, S1. Generate stub hooks ("there's a rumor of bandits in the east"); actual quest mechanics are out of scope for MT-600 v1.
- **Phase 9 (Doorway coordination):** G18. Coordinate parent-zone doorway rooms with their child interior zones for shared landmarks and consistent naming.
- **Phase 10 (Critic and repair):** All applicable goals via ZoneScore V1 plus future ZoneScore V2.

ZoneScore V1 measures completeness, depth, and engagement — roughly mapping to G1-G5 and G11. ZoneScore V2 (future) should measure feel-quality goals: G6, G7, G8, G9, G10, G16, G18.

For v1, the orchestrator relies on ZoneScore V1 plus prompt engineering that explicitly cites relevant goals as the AI's authoring brief. Each generator's prompt includes the relevant goal text as the quality target.

---

## Demo zone composition (Path C scope, locked v1)

The demo zone is not one zone. It is a **zone composition**: one outdoor city zone plus a curated set of interior zones connected through doorway rooms.

### V1 scope

- **One Type 1 outdoor city zone:** Full quality. All goals satisfied. Streets named and persistent. Districts authored. NPCs scattered. Atmosphere set. Memorable anchors. Multi-skill engagement.
- **N Type 3 small interior zones connected via doorways:** Single-room per interior in v1. Each interior contains the right NPC for its purpose (innkeeper, merchant, healer, trainer, etc.) and just enough description to feel like a real place. NPCs are AI-authored; items inside are drawn from the existing template service.

The interior zone count for v1 is locked at the set required to demonstrate S1 (showcase breadth) and S2 (density of inhabitation). Recommended starting set:

1. **An inn** — innkeeper NPC, room description suggesting a hearth and tables
2. **A general store** — merchant NPC with general goods inventory
3. **A weaponsmith or armorer** — merchant NPC with weapon/armor inventory
4. **A healer's hut or temple healing shrine** — service NPC for healing
5. **A trainer's hall** — service NPC for skill training
6. **A bank or counting house** — service NPC for banking
7. **A scholar or library** — quest-giver/lore NPC for scholarship and quests
8. **A guard post or barracks** — quest-giver NPC for combat-flavor quests

Eight interior zones. Each is a single room in v1, expanded to multi-room versions in v2.

### V2 scope (future, not in MT-600 v1)

- Each interior zone expanded to its full multi-room structure (the academy as Asemath Academy with classrooms, library, courtyard, etc.)
- Additional Type 4-5 interior zones added (a major temple complex, the city's underground)
- Inter-zone references and shared lore
- Time-gated content and dynamic NPC schedules
- Quest mechanics tied to quest hook stubs

V2 is not in MT-600's first dispatch arc. It's named here to make clear what V1 is not committing to.

### Why Path C

Two alternatives were considered:

- **Path A (full v1):** Author all interiors at full Type 4-5 detail in MT-600 v1. This produces a complete demo but is multi-week work even at agent pace.
- **Path B (outdoor only):** v1 ships outdoor only with empty placeholder interiors. Demo isn't fully demo-ready until v2.
- **Path C (chosen):** v1 ships outdoor zone fully realized plus single-room interiors with proper NPCs. Demo is playable end-to-end. v2 expands interiors.

Path C ships a complete demo experience faster while preserving v2 work for interior richness. The demo zone is real, the merchants work, the trainer works, the quest givers work — but the academy's library doesn't exist yet, and the temple's inner sanctum is a v2 concern.

---

## Citations

- Bartle, Richard. *Designing Virtual Worlds.* Physics-first principle.
- Blizzard's WoW level designers (Sanders, Cannon). Cultural signature through architecture.
- Pardo, Rob. "GDC: Blizzard's Core Game Design Concepts." Play don't tell.
- Taylor, Dan. "Ten Principles of Good Level Design." GDC 2013. Fun-to-navigate, environmental storytelling, surprise.
- Koster, Raph. *A Theory of Fun.* Pattern-learning-as-fun.
- Bioshock's Rapture. Gold standard for environmental storytelling.
- Minecraft biome system. Rules consistent, expression varied.
- DragonRealms Crossing reference map. Zone topology and doorway-room pattern.

---

## Status and next steps

This document is the locked design language for what makes a DireEngine zone good, and how zones decompose into types and compositions. It should be referenced by:

- MT-600a and subsequent orchestration dispatches as quality criteria
- Future ZoneScore V2 design as the measurement target
- Human builder onboarding as the standard to author against
- Any future zone authoring tooling as the success bar

It is intentionally normative. Pushback is welcome — these goals should evolve as DireEngine evolves — but the goals as written represent the current intended quality bar.

---

That's the whole document. Let me know what you want to change before we lock it.