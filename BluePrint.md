# DRG-011 — Bundle Catalog Build

**Type:** Diagnostic, read-only (no code changes to DireLore)
**Output:** `docs/architecture/BUNDLE-CATALOG.md` (canonical reference document)
**Estimated touch:** 1 new markdown file, ~1500-2500 lines depending on metadata depth

---

## Background

DireLore is the source-of-truth knowledge platform feeding DireEngine (the Evennia-based MUD). The plan is to deliver DireEngine content via **bundles** — self-contained markdown dispatches with attached YAML payloads — that the DireEngine agent fetches by name and executes as roadmaps.

Bundles are **commercial software products**, not data exports. The free-tier release includes the base engine + 3 professions (Ranger, Empath, Cleric) + 2 races (Human, Elf) + 1 zone (The Crossing) + 1 trade system (Tailoring/clothing). Paid bundles include other professions, races, zones, trade systems, and a combined Mounts/Ships/Housing module. Each paid bundle is a standalone Python module that registers content via engine extension points — someone without the Moon Mage bundle should never see Moon Mage code on disk.

Before any bundle generator can ship, we need a **canonical catalog** enumerating every bundle, its tier, its dependencies, and its source-data references. This dispatch builds that catalog.

---

## Frozen design decisions

These are settled. Do not re-derive or alter.

### Tier structure

- **Tier 0** — Base Engine. Open-source giveaway. Internally modular (built as ~25-30 sub-bundles in dependency order) but released as one unified codebase. Contains all foundational systems plus shared mechanics that the free profession bundles depend on (combat, magic infrastructure, economy, crafting infrastructure, justice, weather, GM tools).
- **Tier 1** — Starter Content Bundles. Open-source, modular. Ships with the engine release. 6 bundles: Crossing, Ranger, Empath, Cleric, Human, Elf, plus Tailoring (the free trade system).
- **Tier 2** — Paid Bundles. Individually purchasable. 8 paid professions, 9 paid races, ~10-12 paid zones, 4 paid trade systems (Armor, Weapons, Alchemy, Fletching), 1 combined Mounts/Ships/Housing bundle.
- **Tier 3** — Premium add-ons. Festivals, CHE/society, auction, etc.

### Bundle inventory (canonical — populate metadata for exactly these entries)

**Tier 0 — Engine sub-bundles (each is its own future dispatch, listed in dependency order):**

*Foundation phase:*
1. T0-VERB-DISPATCH — verb dispatch + messaging primitives
2. T0-OBJECT-SYSTEM — room/item/exit template system
3. T0-VARFIELDS — variable system (player vars, room vars, world vars, B-variables)
4. T0-EFFECTS — effect/condition system (hidden, invisible, stunned, RT, addeffect/loseeffect)
5. T0-TIME — time, scheduling, tick handling, duration tracking
6. T0-COMMS — communication primitives (room broadcast, channels, ESP routing)
7. T0-UTIL — linked list utility + compass parser (S00057-S00059)

*Player state phase:*
8. T0-POSITION — position system (stand/sit/kneel/prone — S00003, S00005)
9. T0-STANCE — stance system (offensive/defensive proportions)
10. T0-ENGAGEMENT — engagement system (advance/retreat per S00028-S00029)
11. T0-VITALS — vitals system (health, fatigue, spirit, concentration)
12. T0-WOUNDS — wound system (body part wounds, severity, bleeding)
13. T0-ENCUMBRANCE — encumbrance and load tracking

*World interaction phase:*
14. T0-MOVEMENT — movement system (go/climb/swim/crawl)
15. T0-INVENTORY — inventory operations (get/put/drop/give — S00025)
16. T0-EQUIPMENT — equipment operations (wear/remove — S00023-S00024)
17. T0-CONTAINERS — open/close mechanics (S00026-S00027)
18. T0-PERCEPTION — look/perception system (S00006)

*Skill phase:*
19. T0-SKILLS — skill registration, rank tracking, training/advancement, skill checks

*Combat phase:*
20. T0-COMBAT-CORE — combat infrastructure (engagement state, RT integration, target validation)
21. T0-WEAPONS — weapon system (types, damage profiles, skill mapping)
22. T0-ARMOR — armor system (types, protection by hit area)
23. T0-HIT-AREA — hit area determination (S00047)
24. T0-DAMAGE — damage determination (S00048)
25. T0-ATTACK-VERBS — combined: thrust, lunge, slice, chop, sweep, feint, jab (S00031-S00037)
26. T0-DEFENSE — combined: parry, dodge, OF base, evasion, shield defense (S00039-S00043, S00046)

*Death and healing phase:*
27. T0-DEATH — death system, `$DIE` lifecycle, body creation, departure (S00001 death handling)
28. T0-WOUND-HEALING — natural recovery, scarring
29. T0-EMPATH-INFRA — empath restoration infrastructure (engine API; Empath profession plugs in)
30. T0-HERBS — herbal healing infrastructure (herb types, application, effects)
31. T0-RESURRECTION — deeds, soul/spirit recovery, body return

*Magic phase (parallel-developable to combat):*
32. T0-SPELL-CIRCLES — spell circle registration system (engine API)
33. T0-CASTING — casting infrastructure (prepare, cast, harness, mana pool)
34. T0-SPELL-DURATION — spell duration and effect application
35. T0-SPELL-CATEGORIES — targeted vs warding vs barrier categorization

*NPC infrastructure phase:*
36. T0-NPC-TEMPLATES — NPC typeclass hierarchy (NPCs, creatures, shopkeepers)
37. T0-DIALOG — NPC dialog tree system (script flags, branching)
38. T0-QUEST-FLAGS — quest/script flag system (per-player and global)
39. T0-CRITTER-AI — critter AI (spawning, aggression, fleeing — for hunting targets)
40. T0-LOOT — loot table system

*Economy phase (free tier):*
41. T0-CURRENCY — currency system (kronars, lirums, dokoras + exchange rates)
42. T0-BANKING — banking (deposit, withdraw, money orders)
43. T0-EXCHANGE — currency exchange (province-to-province conversion)
44. T0-SHOPPING — shopping infrastructure (buy, sell, browse, haggle, appraise, repair)
45. T0-LOCKERS — lockers and safekeeping (persistent containers)
46. T0-MAIL — mail system (anchored in S00001's mail call)

*Crafting infrastructure (free tier):*
47. T0-CRAFTING-INFRA — crafting registration, recipe/pattern system, material/component system, tool/workstation requirements, crafting skill integration

*Outdoorsmanship (free tier):*
48. T0-OUTDOORSMANSHIP — combined: foraging, hunting prep, skinning, butchering, herbalism harvesting, fire-building, weather-reading, navigation

*Justice + weather + GM tools:*
49. T0-JUSTICE — crime tracking, arrest, jail, justice chamber, fines (S01000 references)
50. T0-CLIMATE — climate/weather (time of day, season, weather effects)
51. T0-PLANETARY — planetary phase system (lunar cycle — needed for Moon Mage, but engine infra)
52. T0-GM-TOOLS — `/onduty`, `/gmmode`, `/show`, `/move`, `/qfix`, `/info` (S00009-S00017, S03418, S00045)

*Familiars (free tier):*
53. T0-FAMILIARS — combined: template + species (S00052-S00053), control (S00050), movement (S00056), behavior (S00055), per-species hooks (cat S00049, wolf S00051)

*Social and lifecycle:*
54. T0-SOCIAL-VERBS — combined action/social verbs: action, nod, smile, knee, swear, wobble (S00002, S00007, S00008, S00015, etc.)
55. T0-LIFECYCLE — login, hangup, logoff (`$HELLO`, `$HANGUP`, `$LOGOFF` from S00001 — ships last in Tier 0 since it back-references nearly everything)

**Tier 1 — Starter content bundles:**

- T1-ZONE-CROSSING — The Crossing zone bundle
- T1-RACE-HUMAN — Human race bundle
- T1-RACE-ELF — Elf race bundle
- T1-PROF-RANGER — Ranger profession bundle
- T1-PROF-CLERIC — Cleric profession bundle
- T1-PROF-EMPATH — Empath profession bundle
- T1-TRADE-TAILORING — Tailoring/clothing crafting bundle (free trade)

**Tier 2 — Paid profession bundles:**

- T2-PROF-MOONMAGE — Moon Mage (first paid bundle; proves the paid-profession pattern)
- T2-PROF-PALADIN — Paladin
- T2-PROF-BARBARIAN — Barbarian
- T2-PROF-WARMAGE — Warrior Mage
- T2-PROF-BARD — Bard
- T2-PROF-THIEF — Thief
- T2-PROF-TRADER — Trader
- T2-PROF-NECROMANCER — Necromancer

**Tier 2 — Paid race bundles:**

- T2-RACE-HALFELF, T2-RACE-DWARF, T2-RACE-GNOME, T2-RACE-HALFLING, T2-RACE-SKRAMUR, T2-RACE-PRYDAEN, T2-RACE-RAKASH, T2-RACE-KALDAR, T2-RACE-GORTOG

**Tier 2 — Paid zone bundles** (final list to be expanded by agent against canonical zone enumeration; seed list):

- T2-ZONE-RIVERHAVEN
- T2-ZONE-THEREN
- T2-ZONE-SHARD
- T2-ZONE-HIBARNHVIDAR
- T2-ZONE-MUSPARI
- T2-ZONE-RATHA
- T2-ZONE-AESRY
- T2-ZONE-HARAJAAL
- T2-ZONE-BOAR-CLAN
- T2-ZONE-HORSE-CLAN
- T2-ZONE-STEELCLAW-CLAN
- Plus additional zones the agent identifies via DireLore's areas dataset

**Tier 2 — Paid trade systems:**

- T2-TRADE-ARMOR — armor crafting (leather, chain, plate)
- T2-TRADE-WEAPONS — weapon crafting (blades, hafted, etc.)
- T2-TRADE-ALCHEMY — alchemy
- T2-TRADE-FLETCHING — bow and arrow crafting

**Tier 2 — Combined transportation/dwelling bundle:**

- T2-MOUNTS-SHIPS-HOUSING — combined paid bundle (saddles/riding/sailing/dwelling ownership)

**Tier 3 — Premium add-ons:**

- T3-EVENT-HOLLOWEVE — Hollow Eve festival
- T3-EVENT-DROGOR — Drogor's Day
- T3-EVENT-FEAST — Feast of the Immortals
- T3-AUCTION — auction system (S03828)
- T3-PREMIUM — premium points, CHE/society systems
- Additional festivals/events the agent surfaces from the data

### Per-bundle metadata schema (every catalog entry must have these fields)

```text
Name: <human-readable name>
ID: <T0-XXX / T1-XXX / T2-XXX / T3-XXX>
Tier: <0 | 1 | 2 | 3>
Type: <engine-subbundle | starter-profession | starter-race | starter-zone | starter-trade |
       paid-profession | paid-race | paid-zone | paid-trade | combined-bundle | event | system>
Commercial: <free | paid>
Dependency phase: <foundation | player-state | world-interaction | skills | combat | death-healing |
                   magic | npc-infra | economy | crafting | outdoorsmanship | governance-time | familiars |
                   social-lifecycle | content | premium>
Dependencies: [list of bundle IDs that must exist first]
DireLore data refs: [list of DB tables/views and example queries]
GSL script refs: [list of S##### script numbers]
Map data refs: [for content bundles: list of rooms/areas/image files]
Elanthipedia refs: [list of wiki categories/article URLs]
Scope: {rooms, npcs, scripts, items, spells, abilities, ...} counts as applicable
Priority: <P0 | P1 | P2>
Complexity: <S | M | L | XL>
Status: planned
Notes: <agent's free-form observations — gotchas, gaps, ambiguities>
```

### Output file specification

- Path: `docs/architecture/BUNDLE-CATALOG.md`
- One top-level section per Tier (Tier 0, Tier 1, Tier 2, Tier 3)
- Within each Tier, group by Type (engine sub-bundle, profession, race, zone, etc.)
- Within each group, list bundles in dependency order (use the canonical ordering above for Tier 0; for Tier 1/2/3, agent picks a sensible order — typically alphabetical within group)
- Each bundle entry uses the metadata schema above, rendered as a markdown block
- Document header includes: purpose, conventions, how to read the catalog, footer credit
- Footer credit on every page: `© 2026 Gary Mix (Aetos). Provided to Justin Garret (Slippy).`

---

## Investigation queries

Run these queries against DireLore's DB, GSL tree (`origin/` source), map data, and Elanthipedia data to populate each bundle's metadata. Document query patterns and results in the catalog where they meaningfully shape an entry.

### Q1 — Tier 0 engine sub-bundles: GSL anchoring

For each Tier 0 entry that names a GSL script in its phase grouping (e.g., T0-POSITION cites S00003/S00005), verify the script exists in the GSL corpus and read its first 40 lines to confirm topical match. Where the catalog says "anchored in S#####", the script's purpose should align. Flag mismatches in the bundle's Notes field.

Expected outcome: per-bundle list of confirmed GSL script numbers, with any catalog corrections.

### Q2 — Tier 0 economy: currency, banking, shopping GSL evidence

The economy phase (T0-CURRENCY through T0-MAIL) needs GSL anchors. Search the GSL tree for scripts mentioning currency operations, banking, shopping, mail. Likely candidates: scripts containing tokens like "kronar", "lirum", "dokora", "deposit", "withdraw", "buy", "sell", "appraise", "haggle", "locker", "mail".

Expected outcome: per-bundle list of relevant scripts, populated into GSL script refs.

### Q3 — Tier 0 crafting + outdoorsmanship: GSL evidence

Search the GSL tree for crafting and gathering scripts. Foraging is anchored at S02612 ("continued foraging script"). Look for tokens: "forage", "skin", "butcher", "tailor", "sew", "weave", "spin", "tan", "harvest", "alchemy", "forge", "fletch".

Expected outcome: confirmed script ranges for T0-CRAFTING-INFRA and T0-OUTDOORSMANSHIP.

### Q4 — Tier 1 starter professions: data inventory

For each starter profession (Ranger, Empath, Cleric):
- Query DireLore for the profession's row in `professions` table — extract description, abilities, skills, guild references
- Query DireLore for spells linked to this profession (Cleric → Holy circle; Empath → Empathic Projection)
- Query DireLore for abilities linked to this profession via the abilities dataset
- Identify GSL scripts that reference the profession by name (search for "ranger", "empath", "cleric" tokens in script bodies)
- Identify Elanthipedia category/article URLs

Expected outcome: per-profession metadata block with concrete counts (abilities, spells, skills) and source refs.

### Q5 — Tier 1 starter races: data inventory

For each starter race (Human, Elf):
- Query DireLore for the race's row in `races` table — extract physical features, languages, cultural notes
- Identify GSL feature/description scripts (S5000-family for picture/locket rendering, S10070 for feature selection)
- Identify Elanthipedia race article URLs

Expected outcome: per-race metadata block.

### Q6 — T1-ZONE-CROSSING: data inventory

Already well-mapped from DRG-007 series. Pull current numbers:
- Rooms: 266 (combined slug group)
- Logical edges: 274 (post-merge)
- Source map files: 3
- Linked scripts: 11
- Mentioned NPCs: 38
- Shops in area
- Items found in area
- Notable rooms (guild entrances, government, landmarks)

Expected outcome: zone bundle metadata fully populated.

### Q7 — T1-TRADE-TAILORING: scope inventory

Identify all Tailoring-related scripts in GSL (tokens: "tailor", "sew", "stitch", "cloth", "wool", "linen", "silk"). Identify DireLore mechanics rows tagged tailoring/clothing. Identify clothing item types in DireLore's items dataset.

Expected outcome: scope counts (scripts, recipes, items), GSL refs, mechanics refs.

### Q8 — Tier 2 paid professions: data inventory

For each paid profession in the canonical list, run the Q4-equivalent query. Some professions have richer DireLore data than others — note gaps where they exist (e.g., "Necromancer abilities incomplete in DB, supplement from Elanthipedia").

Expected outcome: 8 profession metadata blocks. Moon Mage should be the most thoroughly populated since it's the first paid bundle and will be the reference implementation.

### Q9 — Tier 2 paid races: data inventory

For each paid race, run the Q5-equivalent query.

Expected outcome: 9 race metadata blocks.

### Q10 — Tier 2 paid zones: enumerate and inventory

Query DireLore's areas dataset for top-level area entries. Identify which qualify as "major zones" (>50 rooms, contains shops/guilds, has its own scripts). For each major zone, pull room count, image file count (per DRG-010 image partitioning), linked scripts, mentioned NPCs.

The seed list in this dispatch (Riverhaven, Theren, Shard, Hibarnhvidar, Muspari, Ratha, Aesry, Harajaal, Boar/Horse/Steelclaw Clan) is non-exhaustive. **Expand it.** Identify any major zones missing from the seed list and add T2-ZONE-XXX entries.

Expected outcome: complete paid-zone bundle inventory with per-zone metadata.

### Q11 — Tier 2 paid trade systems

For each paid trade (Armor, Weapons, Alchemy, Fletching):
- Identify GSL scripts (search tokens per trade)
- Identify DireLore mechanics rows
- Identify Elanthipedia recipe/material category URLs

Expected outcome: 4 trade bundle metadata blocks.

### Q12 — T2-MOUNTS-SHIPS-HOUSING

Identify scripts for horses (S09803 anchored), sailing, housing/dwelling. Identify DireLore mechanics rows.

Expected outcome: combined bundle metadata block, with a clear breakdown of the three sub-components.

### Q13 — Tier 3 premium add-ons

For festivals (Hollow Eve, Drogor, Feast), search GSL for event-named scripts. For auction, S03828 is anchored. For premium/CHE, search GSL and DireLore for relevant systems.

Expected outcome: Tier 3 entries with whatever evidence exists; mark gaps clearly.

### Q14 — Dependency graph verification

For each bundle's listed dependencies, verify that every dependency-target is itself a catalog entry (no dangling references). Build a forward-dependency view (X depends on Y) AND a reverse-dependency view (Y is depended on by [X, Z, W]). Surface any cycles — there should be none.

Expected outcome: clean dependency DAG; flag and resolve any issues in Notes fields.

### Q15 — Coverage check against existing DireEngine stubs

This question is **optional** for this dispatch — if access to DireEngine source is available to this agent, identify any DireEngine stubbed systems that don't map cleanly to a catalog entry. If not accessible, defer to DRG-012 (the DireEngine stub inventory dispatch).

---

## Verification checklist

- [ ] `docs/architecture/BUNDLE-CATALOG.md` exists at the specified path
- [ ] Document header includes purpose, conventions, footer credit
- [ ] All 55 Tier 0 sub-bundles listed in canonical dependency order
- [ ] All 7 Tier 1 bundles listed
- [ ] All 8 paid profession bundles listed
- [ ] All 9 paid race bundles listed
- [ ] Paid zone bundle list includes the 11 seed entries plus any additional zones agent identified from DireLore data
- [ ] All 4 paid trade bundles listed
- [ ] T2-MOUNTS-SHIPS-HOUSING listed as combined bundle
- [ ] Tier 3 entries present (at least Hollow Eve, Drogor, Feast, Auction, Premium)
- [ ] Every entry has all schema fields populated (Name, ID, Tier, Type, Commercial, Dependency phase, Dependencies, DireLore data refs, GSL script refs, Map data refs where applicable, Elanthipedia refs, Scope counts, Priority, Complexity, Status, Notes)
- [ ] Every Dependencies field references only valid bundle IDs (no dangling refs)
- [ ] Dependency DAG has no cycles
- [ ] Footer credit appears on the document
- [ ] Spot-check: pick 5 random bundles, verify their GSL refs against the actual script file contents in `origin/`
- [ ] Spot-check: pick 3 zone bundles, verify their room counts against `map.rooms` table queries
- [ ] Spot-check: pick 3 profession bundles, verify their spell/ability counts against DireLore datasets

---

## Out of scope

- No code changes to DireLore (this is documentation only)
- No bundle generator implementations (that's DRG-013)
- No DireEngine-side work (stub inventory is DRG-012; bundle consumption is later)
- No actual bundle MARKDOWN generation — the catalog describes what bundles WILL be, not the bundles themselves
- No commercial pricing, packaging, or licensing decisions — that's a separate non-engineering concern
- No reorganization of DireLore's existing data — work with what's already there; flag gaps in Notes

---

## Footer credit

Append to `docs/architecture/BUNDLE-CATALOG.md`:

```text
---

© 2026 Gary Mix (Aetos). Provided to Justin Garret (Slippy). All rights reserved. See LICENSE.md.
```