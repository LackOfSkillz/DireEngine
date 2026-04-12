# Fishing Research Packet

> Query date: 2026-04-08
> Database: local PostgreSQL `direlore` on port `5432`
> Project overlay: `direlore`
> Primary domains used: `mechanics`, `items`, `locations`, `experience`, raw fishing content tables, and supporting metadata tables under the shared schema contract
> Contract packet source: `agent_active_instructions_v`, `agent_active_project_overlay_v`, `agent_query_playbooks_v`, `agent_schema_contract_v`

## Query Path

- Domain: mechanics, items, locations, experience
- Contract path used: `agent_active_instructions_v` -> `agent_active_project_overlay_v` -> `agent_query_playbooks_v` -> `agent_schema_contract_v`
- Primary evidence tables: `sections`, `raw_pages`
- Corroboration tables: `page_metadata`, `entities`
- Primary source pages:
    - fishing system article
    - fishing training script page
    - fishing supply shop category page

## Source Quality

- The core fishing article is high-signal for commands, flow, fish groups, and location coverage.
- The same article also marks itself incomplete and notes that some skill-era details need revision.
- The dataset exposes named fish groups, fish species, and room lists, but it does not expose a clean numeric difficulty table or exact skill thresholds.
- Best interpretation: the named fish groups are the practical difficulty bands, while exact catch formulas remain unstated.

## What Fishing Trains

- Primary: Outdoorsmanship
- Secondary: some Mechanical Lore
- Secondary: Skinning
- Minor edge case: Engineering when untangling a line
- Side effect: fishing can cause empathic shock

## Required Items

- Fishing pole
- Bait

The source says a pole normally comes with line and hook already attached.

## Optional or Situational Items

- Hook and string
- Extra line
- Extra hook
- Hide scraper
- A light edged weapon for gutting fish
- Fish string from a fish buyer for carrying large numbers of fish

## How Fishing Works In Play

1. Move to a fishable body of water. Decorative water sources do not count.
2. Obtain or ready a pole.
3. Confirm line, hook, and bait state.
4. Cast the pole into the water.
5. Wait for line feedback.
6. React to bite states until the fish is either landed or lost.
7. Rebait and repeat.

The raw page and legacy script together imply a simple state machine:

- `idle`: player is holding a ready pole with valid gear
- `baited`: hook has bait attached
- `cast`: line is in water
- `nibble`: light tremor or test bite
- `hooked`: definite tug and active struggle
- `landed`: fish is pulled in successfully
- `junk`: seaweed or another non-fish snag
- `tangled`: line must be untangled before continuing
- `broken_or_lost`: pole, line, or hook failed and must be restored

## Core Mechanics

### 1. Fishable Location Check

- Fishing is only valid in rooms tagged as fishable water.
- If the room is not fishable, casting fails immediately.
- Fishable rooms are mapped to a fish group, and that group determines the catch table.

### 2. Gear Assembly

- Pole, line, hook, and bait are distinct stateful parts even if the starter pole comes pre-rigged.
- Some locations provide shared barrels with poles, line, hooks, and bait.
- Store-bought poles may need to be opened before use.

### 3. Baiting and Casting

- The player casts only after the pole is ready.
- Bait quality matters operationally because the source distinguishes easy bait from harder-to-use living or once-living bait.
- Easier bait is explicitly recommended for low Mechanical Lore characters.

### 4. Bite Signaling

- A slight tremor means a fish is testing bait but is not fully hooked.
- A hard or definite tug means either a hooked fish or junk on the line.
- A real fish is identified by line motion and struggle.
- Junk does not fight.

### 5. Fight Resolution

- Hooked fish can wear themselves out.
- They can also break the line, break the pole, pull the pole away, or slip the hook.
- Outcome depends on fish type, gear, and character qualities.

### 6. Landing the Fish

- Repeated pulls resolve the fight.
- On success, the fish is removed from the hook and the loop returns to rebaiting.

### 7. Failure and Recovery

- Moving while the line is in the water tangles the line.
- Failing to react to a bite can also tangle the line.
- A tangled pole must be untangled before further use.
- Pulling when there is no line in the water can break the pole.
- Free replacement poles are rate-limited by a ten-minute timer.

### 8. Post-Catch Processing

- Throw fish away
- Stow fish
- Put fish on a string for bulk carrying
- Skin fish for parts
- Scrape fish for skinning experience
- Sell fish by weight to a fish buyer
- Weigh fish on a leaderboard scale for possible bonus payout

## Difficulty Levels

The source does not provide numeric skill gates. The practical difficulty structure appears to be the catch-group taxonomy:

- `River 1`: likely novice or lower-difficulty inland group
- `River 2`: likely intermediate inland group
- `River 3`: likely harder inland group
- `Ocean`: separate saltwater catch table
- `Moonwake`: region-specific catch table
- `Stormcoil`: region-specific catch table
- `Coldspire Reach`: region-specific catch table
- `Sunfang Expanse`: region-specific catch table

Implementation-wise, these groups should be treated as the first-class difficulty or encounter bands unless a better numeric source is found later.

## Fish Types By Group

### River 1

- cross-eyed gudgeon
- starry trout
- swordspine snook
- three-striped bream
- whistling pickerel
- yellow-bellied chavener
- yellowtail grayling

### River 2

- blue-bellied chavener
- flathead pardfish
- freshwater eel
- largetooth carp
- longeared sunfish
- spiny-backed gar
- unicorn bream

### River 3

- crocodile gar
- fanged pike
- ghost-white frenadier
- hardscale carp
- humpbacked char
- humpbacked chub
- long-nosed viperfish
- razorbacked cobia
- river pardfish
- round hoodwinger
- roundmouth eel
- royal sturgeon
- silver samlet
- spiny loach

### Ocean

- blue muskalundge
- flat-eyed creppoo
- orange grek
- red nomlas
- small turtle

### Moonwake

- blue garamor
- blue gillie
- lough char
- pile perch
- starry flounder
- striped seaperch
- surlae trout
- wrymouth eel

### Stormcoil

- bigmouth monkfish
- black scorpionfish
- blue gillie
- Stormcoil salmon
- red-ringed octopus
- spottail bluefish
- striped needlefish
- wrymouth eel

### Coldspire Reach

- chelmor cod
- coldwater redfish
- pink salmon
- silver-gilled sculpin
- talan herring

### Sunfang Expanse

- butterfly fish
- dragon eel
- jester fish
- large alfarfish
- painted frogfish
- panther flounder
- pot-bellied snapper
- sharpnose shark
- spotted dogfish
- spotted knifejaw
- sting ray
- striped chub
- Sunfang grouper

## Fishable Areas

The source exposes explicit room lists. The major coverage is:

### Ambercrest Marches

- Duskmere Pier, Bay of Namaroth: Ocean
- Willowmarsh Brinebank: Ocean
- Willowmarsh Greensward: River 1
- Willowmarsh Deep Pool: Ocean
- Willowmarsh Lilypond Pier: River 1
- Bracken Rill Streambed: River 3
- Cinderwatch Blacksilt Beach: River 3
- Highford Docks, South End: Ocean
- Highford Landfall Dock: Ocean
- Highford Oxbridge Span: River 3
- Riverport Portage Dock: River 3
- Angler's Corner Eastwake Lane: Ocean
- Angler's Corner Wildmere Lane: Ocean
- Strand of Seredh Cove: Ocean
- Strand of Crystal Shoals: River 3
- Strand Old Pier: River 3
- Briarwood Brook: River 3
- Frostwall Trail, River's Edge: River 3
- Kestrel Hollow clear pool: River 2
- Lower Kestrel village pond: River 2
- Bladeclan river's edge: River 1
- Northroad Caravan Route bridge: River 3
- Northroad Caravan Route stream bank: River 1
- Northroad Trade Way river bank: River 1
- Silverglass Pool waterfall: River 2
- Selgareth ferries: River 3
- Selgareth south bank: River 1
- Mourning Reach foothills river: River 3
- Southroad Caravan Route Selgareth south bank: Ocean
- Emberclan manor waterfront: River 3

### Greyfen Reach

- Alder's Rest stream: River 1
- Forest stream near Alder's Rest: River 1
- Fallowdeep ferry: River 3
- Thorne's Star at Lake Glenhalon: River 3
- Langmere Falbar Seaward: River 3
- Langmere Daelwatch Seaward: River 1
- Langmere Jhalgev Ford: River 2
- Langmere lake edge: Ocean
- Langmere Lake Glenhalon: Ocean
- Langmere lake shore: River 2
- Langmere Seaward Tern: River 3
- Waldren's Landing: River 2 or River 3 by room
- Glenhalon Fens in the water: River 3
- Mosspire under-bridge river: River 3
- Lake Rathmyr, not shoreline or shallows: Ocean
- Northreach Road river's edge: River 3
- Northreach Road stone bridge: River 3
- Northreach Road plains: River 1
- Marshroad stone causeway: River 3
- Rivergate Lake Glenhalon east: Ocean
- Glenhalon Marina Lurassa Dock: River 2
- Sylvanmere Glade water rooms: Ocean
- Rivergate West Wilds lake shore: River 2
- Rivergate West Wilds north creek bank: River 1 or River 3 by room
- Rivergate West Wilds south creek bank: River 1, River 2, or River 3 by room
- Rivergate stone bridge: River 3
- Rivergate pier: River 3
- Roswyn Landing Coppernut Creek: River 1
- Roswyn Landing Jadepyre River: River 3
- Roswyn Landing dock on Lake Glenhalon: River 2
- Roswyn Landing river's edge: River 2

### Glassfire Coast

- Juleth Vale diving rock: River 1
- Juleth Vale stream: River 3
- Shadefall Reach stone basin: River 1
- Glassport northern lake shore east gate road: River 1
- Glassport eastern fields ash spring: River 1
- Glassport gates: River 2
- Glassport Greenmist River: River 3
- Under the Skyrail Wyrmspine river camp: River 1
- Under the Skyrail Bulenor Alcath: River 2

### Ironroot Holds

- Abandoned Mine underground lake: Ocean
- Ashen Ghazir ferry dock: Ocean
- Hawkrime Road Archer's Ford: River 3
- Hearthskog trench: River 1
- Ranger's Glade riverside: River 3
- Isola Taipan shore road: Ocean

### Starwater Isles

- Moonwake Harbor docks and shore: Moonwake
- Moonwake Surlan Reach: River 1
- Myriss wharf end: Ocean
- Stormcoil dock wards: Stormcoil
- Stormcoil rocky shore: River 2
- Stormcoil rocky shallows: River 2
- Stormcoil wreck of the Sea Warden: River 2
- Tidesgarde docks at Nightglass Landing: Ocean

### Blackreef Haven

- Blackreef Haven dock: Ocean
- Blackreef Haven shoreline: Ocean
- Blackreef Rise pool: River
- Note: Blackreef Haven is explicitly limited to estate holders

## Fishing Supply Shops

The category page lists these fishing-supply shops:

- Finwick's Fishing Supplies
- Wildmarch Outfitters (5)
- Wildmarch Outfitters (6)
- Isola Taipan Fishmonger's Stall
- Laughing Tidefin (3)
- Net and Bait
- Orin's Bait and Tackle
- Stormcoil Bait and Tackle
- Sunfang Bait 'n' Tackle
- Zevrin's Catchhouse

## Implementation Notes

### Recommended Data Model

- `FishingRoom`: room id, water type, fish group, restrictions
- `FishingPoleState`: line state, hook state, bait state, cast state, tangle state
- `FishTable`: fish group -> weighted species entries
- `FishProfile`: difficulty, weight range, struggle profile, sell-value modifier, salvage table
- `FishingAttempt`: actor, room, pole state, current phase, hooked fish, timestamps

### Suggested System Behavior

- Validate room eligibility before cast.
- Require a complete rig before entering the cast state.
- Use a timer or pulse loop to advance from `cast` to `nibble`, `hooked`, `junk`, or `nothing`.
- Resolve hook fights as repeated contests between fish profile, gear quality, and actor capability.
- Teach skill pulses on cast handling, hook resolution, untangling, scraping, and skinning.
- Treat bait families as modifiers on hookup chance and minimum lore friction.

## Suggested Code Snippets

These are intentionally partial snippets, not full implementations.

```python
def can_fish(room):
    return room.db.fish_group is not None and room.db.water_access == "fishable"
```

```python
def choose_catch(room, actor):
    fish_group = room.db.fish_group
    table = FISH_TABLES[fish_group]
    return weighted_choice(table, bonus=actor.skills.outdoorsmanship.rank)
```

```python
def advance_line_state(attempt):
    if attempt.line_tangled:
        return "tangled"
    if attempt.phase == "cast" and roll_nibble(attempt):
        return "nibble"
    if attempt.phase in {"cast", "nibble"} and roll_hookup(attempt):
        return "hooked"
    return attempt.phase
```

```python
def resolve_hooked_fish(attempt):
    fish = attempt.hooked_fish
    contest = fish.struggle_rating - attempt.actor.stats.reflex + attempt.pole.gear_bonus
    if contest >= BREAK_LINE:
        return "line_break"
    if contest >= SLIP_HOOK:
        return "lost_fish"
    if contest <= LAND_FISH:
        return "landed"
    return "still_fighting"
```

```python
def untangle_pole(actor, pole):
    pulse_skill(actor, "engineering", amount="minor")
    pulse_skill(actor, "mechanical lore", amount="minor")
    pole.db.line_tangled = False
```

```python
def process_catch(actor, fish, action):
    if action == "sell":
        return calc_buyer_price(weight=fish.weight, champion=fish.is_champion)
    if action == "skin":
        return roll_fish_parts(fish)
    if action == "scrape":
        pulse_skill(actor, "skinning", amount="light")
```

## Structure Gaps

- The source does not publish numeric fishing formulas, so the model below is an inferred implementation guess rather than a confirmed extraction.
- Fang's Rise is labeled only as `River`, not `River 1/2/3`, so it likely needs a fallback inland-band assignment.
- The underlying article is incomplete, so fish lists and room coverage should still be treated as provisional content data.

## Inferred Mechanics Model

The cleanest inferred model is a four-layer loop:

1. Room selects a fish group and environment modifiers.
2. Bait and gear quality shape nibble and hookup rates.
3. Player skill and stats oppose fish difficulty during the struggle.
4. Post-catch actions generate rewards, parts, and training pulses.

### Suggested Numeric Bands

Use fish groups as default difficulty tiers until better data exists:

- `River 1`: difficulty 20 to 40
- `River 2`: difficulty 40 to 60
- `River 3`: difficulty 60 to 85
- `Ocean`: difficulty 45 to 75
- `Moonwake`: difficulty 50 to 80
- `Stormcoil`: difficulty 55 to 85
- `Coldspire Reach`: difficulty 60 to 90
- `Sunfang Expanse`: difficulty 70 to 100

For Fang's Rise, the safest default guess is `River 2` until room-level catch data proves otherwise.

### Suggested Derived Ratings

- `fishing_rating = outdoorsmanship * 0.65 + reflex * 0.20 + discipline * 0.15`
- `bait_rating = bait_quality + bait_match_bonus + lore_handling_bonus`
- `gear_rating = line_rating + hook_rating + pole_rating`
- `fish_pressure = fish_difficulty + random_swing(0, 20)`
- `junk_rating = room_junk_density - bait_cleanliness`

This produces a system where Outdoorsmanship drives the core loop, Mechanical Lore helps with bait handling and rig quality, and reflex-like stats help with landing harder fish.

### Suggested Event Timing

- Check for a nibble every 6 to 10 seconds while the line is in the water.
- Convert nibble to a definite hookup after 1 to 3 successful response windows.
- Resolve active struggle every 2 to 4 seconds until the fish is landed, lost, or breaks gear.
- Apply a tangle check immediately on movement and on missed bite windows.

### Suggested Probability Guesses

These are reasonable starting values for a first playable implementation:

- `nibble_chance = clamp(0.18 + bait_rating * 0.003 + room_density * 0.05 - fish_difficulty * 0.0015, 0.05, 0.65)`
- `hookup_chance = clamp(0.30 + fishing_rating * 0.004 + hook_rating * 0.02 - fish_difficulty * 0.003, 0.10, 0.85)`
- `junk_chance = clamp(0.08 + junk_rating * 0.03 - bait_quality * 0.01, 0.02, 0.35)`
- `tangle_chance_on_miss = clamp(0.10 + fish_difficulty * 0.002 - reflex * 0.001, 0.05, 0.40)`
- `line_break_chance = clamp(0.04 + (fish_pressure - gear_rating) * 0.01, 0.01, 0.50)`
- `slip_hook_chance = clamp(0.06 + (fish_difficulty - hook_rating - fishing_rating * 0.2) * 0.008, 0.02, 0.45)`

These formulas create the expected shape:

- weak bait still gets occasional nibbles but fewer hookups
- better hooks improve conversion from nibble to catch
- strong line and pole quality reduce catastrophic failures
- hard fish remain catchable but materially riskier

### Suggested Bait Families

Normalize bait mechanically even if surface item names differ:

- `artificial_simple`: beginner-safe, low lore requirement, moderate nibble rate
- `worm_cutbait`: baseline universal bait
- `live_bait`: higher nibble and hookup potential, higher lore friction
- `specialty_lure`: better fish-group matching but more expensive

Suggested bait modifiers:

- `artificial_simple`: `bait_quality=10`, `lore_requirement=0`, `match_bonus=0`
- `worm_cutbait`: `bait_quality=14`, `lore_requirement=10`, `match_bonus=2`
- `live_bait`: `bait_quality=18`, `lore_requirement=25`, `match_bonus=4`
- `specialty_lure`: `bait_quality=16`, `lore_requirement=20`, `match_bonus=6 when matched else -2`

## Storage Recommendations

- Promote fishing rooms into a normalized table keyed by room id and fish group.
- Promote fish species into a canonical fishing-species table with region tags, weight bands, and reward data.
- Store bait families separately from cosmetic bait items so mechanics are stable even when item names vary.
- Store struggle outcomes as explicit weights instead of burying them in ad hoc command handlers.
- Capture training pulses per action so future balance passes can tune learning without rewriting the interaction loop.

Suggested normalized fields:

- `fish_group`: canonical room difficulty band
- `room_density`: how often bite checks should succeed
- `junk_density`: chance of seaweed or trash results
- `bait_family`: normalized mechanical bait category
- `fish_difficulty`: primary contest input for that species
- `fight_profile`: favors slipping, thrashing, diving, or exhausting
- `weight_band`: small, medium, large, trophy

## Suggested Gap-Fill Code Snippets

```python
FISH_GROUP_DEFAULTS = {
    "River 1": {"difficulty": (20, 40), "room_density": 0.55, "junk_density": 0.08},
    "River 2": {"difficulty": (40, 60), "room_density": 0.48, "junk_density": 0.10},
    "River 3": {"difficulty": (60, 85), "room_density": 0.42, "junk_density": 0.12},
    "Ocean": {"difficulty": (45, 75), "room_density": 0.46, "junk_density": 0.14},
    "Moonwake": {"difficulty": (50, 80), "room_density": 0.44, "junk_density": 0.10},
    "Stormcoil": {"difficulty": (55, 85), "room_density": 0.43, "junk_density": 0.11},
    "Coldspire Reach": {"difficulty": (60, 90), "room_density": 0.40, "junk_density": 0.09},
    "Sunfang Expanse": {"difficulty": (70, 100), "room_density": 0.38, "junk_density": 0.13},
}
```

```python
def infer_room_group(room):
    if room.db.fish_group:
        return room.db.fish_group
    if room.key == "Blackreef Rise pool":
        return "River 2"
    return "River 1"
```

```python
def calc_fishing_rating(actor):
    outdoors = actor.skills.outdoorsmanship.rank
    reflex = actor.stats.reflex
    discipline = actor.stats.discipline
    return outdoors * 0.65 + reflex * 0.20 + discipline * 0.15
```

```python
def calc_nibble_chance(actor, room, bait, fish):
    fishing_rating = calc_fishing_rating(actor)
    bait_rating = bait.quality + bait.match_bonus + bait.lore_bonus(actor)
    room_density = room.db.room_density or 0.45
    chance = 0.18 + bait_rating * 0.003 + room_density * 0.05 - fish.difficulty * 0.0015
    return clamp(chance, 0.05, 0.65)
```

```python
def calc_hookup_chance(actor, pole, fish):
    fishing_rating = calc_fishing_rating(actor)
    hook_rating = pole.hook.rating
    chance = 0.30 + fishing_rating * 0.004 + hook_rating * 0.02 - fish.difficulty * 0.003
    return clamp(chance, 0.10, 0.85)
```

```python
def roll_junk_result(room, bait):
    junk_density = room.db.junk_density or 0.10
    chance = 0.08 + junk_density * 0.03 - bait.quality * 0.01
    return random() < clamp(chance, 0.02, 0.35)
```

```python
def resolve_struggle_round(actor, pole, fish):
    fishing_rating = calc_fishing_rating(actor)
    gear_rating = pole.line.rating + pole.hook.rating + pole.rating
    fish_pressure = fish.difficulty + randint(0, 20)
    if fish_pressure - gear_rating > 25:
        return "line_break"
    if fish_pressure - (gear_rating + fishing_rating * 0.2) > 15:
        return "lost_fish"
    if fishing_rating + gear_rating > fish_pressure + 10:
        return "landed"
    return "still_fighting"
```

```python
def award_fishing_xp(actor, event, fish=None):
    if event == "hookup":
        pulse_skill(actor, "outdoorsmanship", amount="moderate")
    elif event == "landed":
        pulse_skill(actor, "outdoorsmanship", amount="heavy")
    elif event == "untangle":
        pulse_skill(actor, "engineering", amount="minor")
        pulse_skill(actor, "mechanical lore", amount="minor")
    elif event == "scrape":
        pulse_skill(actor, "skinning", amount="light")
```

## Bottom Line

Fishing is best modeled as a room-gated, pole-state interaction loop that trains Outdoorsmanship first and branches into lore and harvesting side actions. The strongest inferred implementation is a room fish-group tag plus normalized bait families, a derived fishing rating, periodic nibble and hookup checks, and repeated struggle rounds where fish difficulty pushes against player rating and gear strength. That gives a tunable system with predictable progression, meaningful equipment upgrades, and straightforward hooks for tangles, breakage, junk results, and post-catch processing.