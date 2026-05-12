# DireEngine Phase 4 Master Guidance

Type: Big-picture planning artifact

Canonical status: Standing reference for all DireEngine Phase 4 dispatches

Last validated: 2026-05-12

## What this document is

This is the agent's standing reference for DireEngine Phase 4 work. Every implementation dispatch below references it. When the agent is uncertain about ordering, modular boundaries, profession assignments, or architectural direction, this document is the source of truth.

The authoritative bundle catalog lives in DireLore at `docs/architecture/BUNDLE-CATALOG.md` (built by DRG-011). This DireEngine-side document references that catalog and translates it into engineering sequence.

## DireLore connection - primary data source

The agent extracts engineering guidance from the DireLore database. Connection details:

```python
DIRELORE_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "user": "user",
    "password": "pass",
    "dbname": "direlore",
}
```

This config already exists at `world/systems/canon_seed.py`. The agent uses it via `connect_direlore()` to query canon tables, GSL scripts, and bundle catalog data.

Tables that drive Phase 4 work:

- `gsl.scripts` (10,888 scripts) - canonical mechanics source. Read `raw_content` to extract GSL math, command grammar, message strings
- `canon_skills` (63 rows) - skill registry truth
- `canon_stats` (10 rows) - stat registry truth
- `canon_races` (11 rows) - race registry truth (covers Tier 1 Human/Elf + 9 paid Tier 2 races)
- `profession_spells` (396 rows) - guild spell roster
- `profession_abilities` (196 rows) - guild ability roster
- `canon_effects` (2,831 rows) - buff/debuff/status effects
- `canon_items` (35,195 rows) - item catalog
- `canon_recipes` family - crafting catalog (drives Tailoring + paid trade systems)
- `canon_shops` (3,145 rows) + inventory (9,091 rows) + operators (1,044 rows) - vendor catalog
- `canon_room_pois` - map POI canon (drives zone bundles)
- `map.rooms` + `map.exits` - zone-level geographic data
- `entities`, `facts` - cross-cutting reference layer

The DireLore-to-DireEngine bridge already exists in `server/systems/`:

- `direlore_item_import.py` - partial item import
- `direlore_npc_import.py` - partial NPC import
- `world/systems/canon_seed.py` - connection management

These get extended through Phase 4. No new connection layer is built.

## Canonical bundle structure (mirrors DRG-011)

Every Phase 4 dispatch ships into one of four tiers. Bundle IDs match DRG-011's catalog exactly.

### Tier 0 - Base Engine (open source, free, ships as one codebase)

Internally 55 sub-bundles built in strict dependency order; released as a unified codebase. The DRG-011 catalog enumerates all 55 and their dependency phases:

Foundation phase (1-7): verb dispatch, object system, varfields, effects, time, comms, util

Player state phase (8-13): position, stance, engagement, vitals, wounds, encumbrance

World interaction phase (14-18): movement, inventory, equipment, containers, perception

Skill phase (19): skill registration + rank tracking + training/advancement

Combat phase (20-26): combat core, weapons, armor, hit area determination, damage determination, attack verbs (thrust/lunge/slice/chop/sweep/feint/jab - S00031-S00037), defense (parry/dodge/OF base/evasion/shield - S00039-S00046)

Death and healing phase (27-31): death system + `$DIE` lifecycle, wound healing, empath restoration infrastructure, herbs, resurrection

Magic phase (32-35): spell circles, casting infrastructure, spell duration, spell categories (parallel-developable to combat)

NPC infrastructure phase (36-40): NPC templates, dialog trees, quest flags, critter AI, loot tables

Economy phase (41-46): currency (kronars/lirums/dokoras), banking, exchange, shopping, lockers, mail

Crafting infrastructure (47): crafting registration + recipe/pattern system + materials + tools/workstations

Outdoorsmanship (48): foraging, hunting prep, skinning, butchering, herbalism harvesting, fire-building, weather-reading, navigation

Governance and time (49-52): justice, climate/weather, planetary phase, GM tools

Familiars (53): combined templates + species + control + behavior

Social and lifecycle (54-55): social verbs, lifecycle (login/hangup/logoff - ships last in Tier 0)

### Tier 1 - Starter Content (open source, free, ships with engine)

Only 3 starter professions are free. Thief is not a starter profession - Thief is a paid Tier 2 bundle. Warrior is not a separate bundle - basic fighting is covered by Tier 0 combat infrastructure.

- `T1-ZONE-CROSSING` - The Crossing zone
- `T1-RACE-HUMAN`, `T1-RACE-ELF` - only two starter races; other 9 races are paid
- `T1-PROF-RANGER`, `T1-PROF-CLERIC`, `T1-PROF-EMPATH` - only three starter professions
- `T1-TRADE-TAILORING` - only free trade system; Armor/Weapons/Alchemy/Fletching are paid

### Tier 2 - Paid Bundles (standalone Python modules)

8 paid professions (Moon Mage ships first as reference implementation):

- `T2-PROF-MOONMAGE`, `T2-PROF-PALADIN`, `T2-PROF-BARBARIAN`, `T2-PROF-WARMAGE`, `T2-PROF-BARD`, `T2-PROF-THIEF`, `T2-PROF-TRADER`, `T2-PROF-NECROMANCER`

9 paid races:

- `T2-RACE-HALFELF`, `T2-RACE-DWARF`, `T2-RACE-GNOME`, `T2-RACE-HALFLING`, `T2-RACE-SKRAMUR`, `T2-RACE-PRYDAEN`, `T2-RACE-RAKASH`, `T2-RACE-KALDAR`, `T2-RACE-GORTOG`

11+ paid zones (final list expanded via DireLore areas dataset):

- `T2-ZONE-RIVERHAVEN`, `THEREN`, `SHARD`, `HIBARNHVIDAR`, `MUSPARI`, `RATHA`, `AESRY`, `HARAJAAL`, `BOAR-CLAN`, `HORSE-CLAN`, `STEELCLAW-CLAN` + others

4 paid trade systems:

- `T2-TRADE-ARMOR`, `T2-TRADE-WEAPONS`, `T2-TRADE-ALCHEMY`, `T2-TRADE-FLETCHING`

1 combined bundle:

- `T2-MOUNTS-SHIPS-HOUSING` (saddles/riding/sailing/dwelling ownership all in one)

### Tier 3 - Premium Add-ons

- `T3-EVENT-HOLLOWEVE`, `T3-EVENT-DROGOR`, `T3-EVENT-FEAST` - festivals
- `T3-AUCTION` - auction system (S03828)
- `T3-PREMIUM` - premium points, CHE/society systems

## Architectural prime directive - bundle extension points

This is a non-negotiable architectural constraint from DRG-011:

> Each paid bundle is a standalone Python module that registers content via engine extension points. Someone without the Moon Mage bundle should never see Moon Mage code on disk.

Implications for every Phase 4 dispatch:

1. Profession code does not live in the engine. Even free Tier 1 professions (Ranger, Cleric, Empath) must register through the same extension API that paid bundles will use. The engine has no hardcoded knowledge of "ranger" or "cleric" - it has a profession registration API, and the Ranger bundle calls it.
2. Race code does not live in the engine. Same pattern - race bundles register racial data, stat modifiers, language sets, descriptions through an API.
3. Zone code does not live in the engine. The Crossing bundle (free) registers its rooms, NPCs, shops, scripts through the same API that Riverhaven and Theren will use when they're sold.
4. Trade systems register through crafting infrastructure. Tailoring (free) and Armor/Weapons/Alchemy/Fletching (paid) all use the same registration surface in `T0-CRAFTING-INFRA`.
5. Bundles never cross-import. Empath module cannot import from Cleric module. They communicate through engine APIs only. This is what enables independent purchase/installation.
6. Engine APIs must be stable, versioned, and documented. Bundles consume the API; engine doesn't reach into bundle code. The contract is one-directional.
7. Graceful degradation. When a paid bundle is absent, the engine still works. A map referencing "Riverhaven" when that zone isn't installed shows "Riverhaven zone not installed" - it doesn't crash.

**API contract:** `docs/architecture/bundle-extension-api.md` documents the registry interfaces, manifest format, loader behavior, boot sequence, and graceful-degradation rules for all downstream bundle work.

This means DRG-022.5 - Bundle Extension Point Architecture - must ship before any profession or zone overhauls. Otherwise overhauled code can't cleanly extract into Tier 2 modules later. Designing the extension points first lets every per-system dispatch register correctly from day one.

## Modernization principle — behavior fidelity, not implementation fidelity

**GSL is the source of truth for WHAT the code does, not for HOW the code is structured.**

DragonRealms's GSL is a proprietary scripting language from the early 1990s. It encodes the math, mechanics, and behavioral spec of a deep MUD in patterns that were idiomatic at the time: numeric variable slots (`$v0`, `$a0`), goto-style control flow, event-token string dispatch (`$DIE`, `$TARGET`), tightly coupled global state, and file-by-script-number organization.

DireEngine is a modern Python/Evennia codebase. The architecture follows current idioms: typed services, named variables, clear control flow, object-oriented domain models, explicit interfaces, tests as first-class artifacts.

These two facts are not in conflict. GSL gives us the FORMULA, the THRESHOLDS, the STATE MACHINE, and the EVENT ORDERING. Modern Python expresses all of it cleanly. The numerical output should match GSL exactly. The code structure should look nothing like GSL.

### What carries forward from GSL (extracted faithfully)

- Math formulas (damage, mana cost, prep time, skill check curves, contest resolution)
- Threshold values (critical endroll, fumble endroll, RT modifiers, skill ranks for ability gates)
- State machine transitions (stance progression, combat engagement, spell prep stages)
- Event ordering (when `$DIE` fires relative to combat cleanup; when `$TARGET` evaluates vs `$ATTACK`)
- RT values, cooldown durations, mana costs, prep times
- Specific magic numbers that ARE the spec (e.g., `$TREASURE` seg 701006 → that exact treasure segment)

### What does NOT carry forward from GSL

| GSL pattern | DireEngine pattern |
|---|---|
| `$v0`, `$v9`, `$a0` numeric slots | Named typed variables |
| `GOTO :label` flow | Function calls, method invocations, structured control flow |
| `$DIE` / `$TARGET` / `$ATTACK` event token strings | Typed event dispatchers, signal/slot patterns, or method hooks |
| Global mutable script vars | Service-owned state with explicit getters/setters |
| File-by-script-number organization (`S00031.txt`) | Module/class organization by concern |
| No type information | Type hints on every function signature |
| String-keyed effect lookups (`$EFFECT,kissme`) | Enum-keyed or strongly-typed effect registries |
| Linear procedural scripts | Object-oriented services + dataclass domain models |
| Hardcoded constants buried in math | Named constants at module scope, docstring citing GSL source |
| Embedded message strings in math logic | Math returns structured results; presentation layer formats |
| No tests | Pytest with focused per-behavior tests verifying GSL parity |

### Documentation pattern

Every system that translates GSL math/mechanics carries a docstring citing the GSL source:

```python
def resolve_attack(attacker_score: int, defense_score: int, *, rng=random) -> CombatRoll:
    """Resolve an attack via AS/DS endroll contest.

    Math from GSL S00088 (CPDF combat hit). Critical threshold endroll >=101,
    normal hit >=60, miss otherwise. Damage rolls and modifiers follow GSL
    exactly; see tests/combat/test_resolve_attack.py for verified parity.

    Related GSL: S00047 (hit area), S00048 (damage tier),
    S00031-S00037 (attack verbs that call into this).
    """
```

Provenance is part of the deliverable. Future readers can verify behavior against the cited script.

### Test discipline reinforces this

GSL parity is tested via numerical assertions. A typical combat math test:

```python
def test_endroll_101_yields_critical():
    """GSL S00088 specifies endroll >=101 as critical threshold."""
    rng = FixedRng([50])  # roll = 50, AS=100, DS=49 → endroll = 101
    result = resolve_attack(attacker_score=100, defense_score=49, rng=rng)
    assert result.result == HitResult.CRITICAL
    assert result.endroll == 101
```

Test names cite GSL behavior. Assertions verify the numerical contract. The implementation can be refactored freely as long as tests pass.

### Per-dispatch enforcement

Every Phase 4 dispatch operates under this principle:

1. Pull math/mechanics from GSL via DireLore. Read the script's `raw_content`. Extract formulas, thresholds, state transitions.
2. Express them in modern Python — typed dataclasses, named constants, clean control flow, OO domain models, services for mutation.
3. Cite the GSL source in docstrings.
4. Test numerical parity — tests verify the math matches GSL; tests do NOT verify implementation structure.

**The architecture is ours. The behavior is GSL's. Both matter; neither is negotiable.**

## Authority architecture (unchanged from DireEngine's current state)

The May 6 `engine-contract.md` defines:

- Dependency direction: `commands -> services -> domain`
- `commands -> typeclasses -> services`
- `services -> domain + infrastructure`
- `domain -> nothing`
- Mutation authority: `CombatService`, `SkillService`, `StateService`, `InjuryService` (plus future services as surface grows)
- `typeclasses/characters.py` is a state container and compatibility surface, not a math home

Phase 4 preserves this. Bundle extension points fit inside this architecture - they're a registration layer on top of services, not a parallel path. No dispatch creates parallel mutation paths. New GSL math goes into existing services. Domain modules stay pure.

## Phase 4 dispatch sequence

### Bootstrap phase

**DRG-022 - Stub inventory walk**

- Audit existing DireEngine code against the DRG-011 bundle catalog
- Per existing system: locate code, identify which bundle it eventually belongs to, flag pre-GSL math, note canon mappings
- Output: `docs/roadmap/stub-inventory.md` per-system breakdown with bundle assignments
- Authority preserved; no code changes

**DRG-022.5 - Bundle extension point architecture**

- Design and implement the extension API surface that bundles use to register content
- Profession registration API, race registration API, zone registration API, trade registration API, content registration API (spells, abilities, items, NPCs, etc.)
- Verify graceful degradation: engine runs with zero bundles installed
- Verify isolation: a registered profession's code can be removed cleanly
- Output: working extension API + tests demonstrating registration + tests demonstrating graceful absence

**DRG-023 - Foundational data wiring**

- Wire `canon_skills` (63), `canon_stats` (10) into engine via DireLore bridge
- Skills registered through the extension API even though they're free engine concepts (proves the API)
- Pre-GSL math left in place; this dispatch wires data only

Status: complete for stats and skills. `stat_registry` and `skill_registry` now boot from DireLore through the extension API, with explicit fallback paths so Evennia still boots when DireLore is unavailable.

### Tier 0 overhaul phase

Tier 0 sub-bundles follow DRG-011's strict dependency order. Group dispatches naturally:

**DRG-024 - Tier 0 Combat overhaul (sub-bundles 20-26)**

- Combat core, weapons, armor, hit area (S00047), damage (S00048), attack verbs (S00031-S00037), defense (S00039-S00046)
- Canon-correct core model is the OF minus EDF subtractive contest from S00041, S00042, S00043, S00046, S00091, S00092, with S00265 combat RNG applied inside OF
- DRG-024 completed the combat-core rewrite in place under `domain/combat/resolution.py` and added `domain/combat/rng.py`
- DRG-024 preserved the existing `AttackResolution.details` payload contract so `combat_service`, combat XP, and presenters could keep working while the math changed underneath
- Follow-up work remains split as:
    - DRG-024a: hit area, damage tier, armor reduction, and wound-depth parity from S00047/S00048/S00066/S00072
    - DRG-024b: attack verb routing and per-verb GSL parity for S00031-S00037
    - DRG-024c: broader defense and equipment parity around richer parry/shield/weapon-force inputs

Status: combat core complete and validated. Evennia restarted cleanly after the rewrite; focused combat tests and broader regression slices are green.

**DRG-024.5 - Tier 0 Magic overhaul (sub-bundles 32-35)**

- Spell circle registration, casting infrastructure, spell duration, spell categories
- Mana math from GSL (existing `domain/mana/`)
- Backlash from GSL
- Cast contest mechanics
- All circles register via extension API; specific spell content ships in profession bundles

**DRG-024.6 - Tier 0 Economy + Crafting + Outdoorsmanship overhauls (sub-bundles 41-48)**

- Currency, banking, exchange, shopping, lockers, mail
- Crafting infrastructure (registration + recipes + materials + tools)
- Outdoorsmanship (foraging anchored at S02612, hunting prep, skinning, etc.)
- All extension points proven via free bundles in Tier 1 phase

(Other Tier 0 sub-bundles - foundation, player state, world interaction, skills, death/healing, NPC infra, familiars, governance/time, social/lifecycle - may already be sufficiently in place in DireEngine. DRG-022's audit determines which need overhauls and bundles them appropriately.)

### Tier 1 free content phase

The three free starter professions, two free starter races, free zone, and free trade - all built as bundles using the extension API.

**DRG-025 - T1-PROF-RANGER**

- Spell list from `profession_spells` where `profession='ranger'`
- Ability list from `profession_abilities` where `profession='ranger'`
- Wilderness bond, terrain bonuses, trail/tracking, companion, foraging skills
- Registers through profession extension API

**DRG-026 - T1-PROF-CLERIC**

- Spell list from `profession_spells` where `profession='cleric'`
- Ability list from `profession_abilities` where `profession='cleric'`
- Devotion subsystem, commune mechanics, resurrection, favor system

**DRG-027 - T1-PROF-EMPATH**

- Spell list from `profession_spells` where `profession='empath'`
- Ability list from `profession_abilities` where `profession='empath'`
- Healing math from GSL (transfer mechanics, shock, strain, body-part wound transfer)
- Link/unity mechanics

**DRG-028 - T1-RACE-HUMAN + T1-RACE-ELF**

- Race profiles from `canon_races` (Human, Elf rows)
- Stat modifiers, language sets, physical features, cultural notes
- Registers through race extension API

**DRG-029 - T1-ZONE-CROSSING**

- 266 rooms via `map.rooms` + `map.exits` + `canon_room_pois`
- 38 mentioned NPCs, shops via `canon_shops`, scripts via `gsl.scripts`
- Registers through zone extension API
- This is the headline free zone

**DRG-030 - T1-TRADE-TAILORING**

- Recipes via `canon_recipes` filtered to tailoring/clothing
- Materials, patterns, tools
- Registers through trade extension API

### Tier 2 paid content phase

Moon Mage ships first as reference implementation - first paid profession through the bundle pipeline. Everything after follows the proven pattern.

**DRG-031 - T2-PROF-MOONMAGE (reference paid profession)**

- Full extension-API-based bundle
- Spell list from `profession_spells` where `profession='moon_mage'` (celestial circle + lunar mechanics)
- Ability list from `profession_abilities` where `profession='moon_mage'`
- Prediction, planetary tracking (T0-PLANETARY consumes), divination
- Establishes the pattern for all subsequent paid bundles

**DRG-032 through DRG-038 - Remaining paid professions**

- Paladin, Barbarian, Warrior Mage, Bard, Thief, Trader, Necromancer
- Each follows the Moon Mage pattern via extension API
- Order can be adjusted based on player demand once Moon Mage ships
- Trader is the most complex (caravan/contract/supply system) - budget more time
- Necromancer last because of faction-pressure crosscutting

**DRG-039 - Paid races (batch dispatch)**

- 9 races registered via race extension API
- Half-Elf, Dwarf, Gnome, Halfling, S'Kra Mur, Prydaen, Rakash, Kaldar, Gor'Tog
- Each is small; ship as one batch dispatch unless complexity surfaces

**DRG-040 through DRG-045 - Paid zones**

- Riverhaven first (largest, most-referenced cultural city)
- Then Theren, Shard, Hibarnhvidar, Muspar'i, Ratha, Aesry, Harajaal, three clan cities
- Final list from DRG-022 audit + DireLore areas dataset
- Each registers via zone extension API

**DRG-046 - Paid trade systems**

- Armor, Weapons, Alchemy, Fletching
- All register via trade extension API
- Can ship together or sequentially based on complexity

**DRG-047 - T2-MOUNTS-SHIPS-HOUSING combined**

- Saddles, riding, sailing, dwelling ownership all in one combined bundle
- Horses (S09803), sailing scripts, housing/dwelling
- Most complex single bundle

### Tier 3 premium phase

**DRG-048 - Tier 3 premium add-ons**

- Festivals (Hollow Eve, Drogor, Feast of the Immortals)
- Auction system (S03828)
- Premium points, CHE/society systems
- Each registers through event/system extension APIs

## Per-system overhaul pattern (DRG-024 onward)

Every system-level dispatch follows seven steps:

1. Audit existing implementation. Read current code in relevant locations. Document factually.
2. Cross-reference DRG-011 + DireLore canon. Identify which bundle the system belongs to, which canon tables drive it, which GSL scripts are the truth source.
3. Flag GSL deltas. For each behavior: `gsl_aligned`, `gsl_canon_data_missing`, `pre_gsl_math_overhaul`, `scaffolding_only`. DireLore canon is authority.
4. Overhaul in place. Modify existing code. No parallel modules. No duplicate registries. No forked services. Authority direction preserved.
5. Register through extension API. Even Tier 0 substrate registers through APIs where appropriate, so the API is exercised before paid bundles arrive. Tier 1+ content always registers via the API.
6. Test against GSL spec. Diretest scenarios per system. Migrate pre-GSL tests to GSL-aligned assertions; don't delete unless redundant.
7. Record bundle membership. In `docs/architecture/modular-boundaries.md`, document which bundle ID this code belongs to (for example, "this file -> T2-PROF-MOONMAGE") and what extension API surface it consumes.

## DireLore engineering guide extraction pattern

For each system dispatch, the agent extracts engineering guidance from DireLore using the connection above. Typical extraction queries:

**GSL scripts as primary spec:**

```python
from world.systems.canon_seed import connect_direlore
with connect_direlore() as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT script_number, raw_content
        FROM gsl.scripts
        WHERE script_number IN ('S00031','S00032','S00033','S00034','S00035','S00036','S00037')
        ORDER BY script_number
    """)
    attack_verb_scripts = cur.fetchall()
```

**Profession content from canon:**

```python
cur.execute("""
    SELECT s.name, s.circle, s.tier, s.mana_cost, s.prep_time, s.description
    FROM profession_spells s
    WHERE s.profession = %s
    ORDER BY s.circle, s.tier
""", ('ranger',))
```

**Items by category for bundle scope:**

```python
cur.execute("""
    SELECT i.id, i.name, i.category, i.subcategory, i.properties
    FROM canon_items i
    WHERE i.category = %s
""", ('weapon',))
```

**Zone content for zone bundles:**

```python
cur.execute("""
    SELECT r.id, r.title, r.description, r.tags, r.image, r.image_coords
    FROM map.rooms r
    WHERE r.area = %s
""", ('The Crossing',))
```

The agent's job in each system dispatch: pull canonical engineering data from DireLore, translate to extension-API-compliant DireEngine code.

## Validation snapshot - 2026-05-12

This roadmap was filed with the following validation results:

- Q1 passed: DireLore connection works through `world/systems/canon_seed.py`; `gsl.scripts` count is 10,888.
- Q2 passed: minimum canon table thresholds were met for `canon_skills` (63), `canon_stats` (10), `canon_races` (11), `canon_effects` (2,831), `canon_items` (35,195), `profession_spells` (396), `profession_abilities` (196), and `canon_shops` (3,145).
- Q3 not confirmed from the current workspace: `docs/architecture/BUNDLE-CATALOG.md` is not present in this repository, and no adjacent local DireLore checkout was found at `c:\Users\gary\direlore`, `c:\Users\gary\source\repos\direlore`, or `c:\Users\gary\source\direlore`. Treat DRG-011's bundle catalog as canonical, but its filesystem copy was not accessible during this filing.
- Q4 passed: `commands/`, `engine/services/`, `domain/`, and `typeclasses/` all exist, and a scan of `domain/**/*.py` found no obvious imports from `commands`, `typeclasses`, or `engine.services`.
- Q5 passed: `world.professions.professions.PROFESSION_PROFILES` currently contains 13 entries.

## Current discrepancies to preserve explicitly

- `docs/architecture/modular-boundaries.md` does not currently exist in this repository. Phase 4 dispatches that reach step 7 of the per-system overhaul pattern will need to create it or establish an approved equivalent architecture registry.
- `DATA-GAP-AUDIT.md` did not exist in this repository at filing time. It was created by this dispatch so the requested Phase 4 audit note has a canonical home.
- The current profession registry includes `thief` and `warrior` as present runtime profiles even though this roadmap defines Tier 1 free professions as Ranger, Cleric, and Empath only. That is not a filing blocker, but it is a migration constraint for later bundle extraction work.

## Scope guardrails for follow-on dispatches

- No Phase 4 implementation dispatch should bypass the extension-point requirement.
- No follow-on dispatch should silently reinterpret Tier 1 starter scope.
- No per-system overhaul should introduce parallel mutation authority outside the documented services path.

## Expectations set honestly

- DRG-022, DRG-022.5, and DRG-023 are foundation dispatches with no immediate gameplay payoff.
- DRG-024 (combat overhaul) is the first visible GSL-aligned moment.
- DRG-031 (Moon Mage) is the first marketplace-visible moment.
- Full path from here to a playable Crossing-and-3-foundation-guilds package is roughly 15-20 dispatches.
- Full path to the first paid bundle (Moon Mage) is roughly 17-22 dispatches.
- Full path to a complete DR-equivalent catalog is 30+ dispatches across months of work.

This is a bucket-list passion project per Gary's framing. Pace is sustainable; revenue is gravy. The roadmap exists to keep momentum and prevent tech debt accumulation, not to drive deadlines.

© 2026 Gary Mix (Aetos). Provided to Justin Garret (Slippy). All rights reserved. See LICENSE.md.