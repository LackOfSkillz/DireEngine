# DireEngine

DireEngine is the game and engine workspace behind Dragons Ire, a modern browser-first MUD project built to recreate the feel of DragonRealms while making it faster to access, easier to extend, and free to play.

The goal is not to clone old friction. The goal is to keep the tension, pace, depth, and skill-driven identity that made classic text worlds compelling, then rebuild that experience with a cleaner architecture, a modern web client, stronger tooling, and an open development workflow.

## Vision

DireEngine is aiming for:

- the dangerous, skill-based, verb-driven feel of classic DragonRealms-style play
- modern browser accessibility instead of requiring a dedicated legacy client
- a free and openly developed codebase that can keep growing without proprietary lock-in
- an engine foundation that supports handcrafted content and map-assisted world building

In practical terms, that means a game where combat pacing matters, injuries matter, movement and positioning matter, skill training matters, and the interface does not fight the player.

## Current State

DireEngine is already well past a stock Evennia scaffold.

The project currently includes:

- a custom browser-native web client for moment-to-moment play
- DragonRealms-inspired combat pacing with roundtime, targeting, weapon profiles, and NPC retaliation
- a body-part injury model with bleeding, tending, recovery pressure, and condition reporting
- survival, lore, combat, armor, and early magic/guild scaffolding
- inventory, equipment, wearable containers, sheaths, and weapon handling flows
- stealth and survival verbs such as hide, sneak, stalk, forage, harvest, skin, and search
- trading and appraisal-oriented systems including vendors, buying, selling, haggle support, and item evaluation flows
- spell preparation and casting scaffolding with targeted, warding, augmentation, debilitation, utility, and cyclic-ready support
- a browser map system with fullscreen mode, drag/pan, fit/center controls, pathfinding, click-to-walk, and generic fallback layouts for non-forged rooms
- AreaForge, a map-driven world-building pipeline that can turn processed source maps into playable area graphs and Evennia content

## What Makes It Different

### DragonRealms feel, modernized

The design target is the feel of an older premium text game without the old access barriers. DireEngine keeps the deliberate tempo, the layered character state, and the verb-heavy world interaction, but presents it in a modern browser shell with visible map context, cleaner UI state, and a codebase that is easier to iterate on.

### Browser-first play

The current client is a custom Evennia webclient override, not just a recolored default terminal pane. It includes:

- a live feed panel for world output
- character, status, inventory, and equipment rails
- hotbar and quick action support
- structured client updates for map, character, combat, and chat state
- an interactive local and zone map renderer

### AreaForge world pipeline

AreaForge is a custom content pipeline for turning map sources into playable spaces. It supports:

- manifest-driven area intake
- OCR-assisted extraction and review
- graph-based area serialization
- rebuilding and validating large map spaces
- full-zone map payloads for the browser client

This lets the project mix traditional hand-authored game logic with faster world bootstrapping from map assets.

## Implemented Systems

### Core character and combat systems

- persistent character state with combat, target, balance, fatigue, attunement, stance, and injury tracking
- roundtime as a global action pacing system
- weapon profiles that drive damage, fatigue cost, balance pressure, and timing
- NPC combat participation with retaliation and combat loop support
- disengage, retreat, targeting, and combat-state cleanup

### Injury, bleeding, and first-aid loop

- body-part injuries for head, chest, abdomen, back, arms, hands, and legs
- separate external, internal, bruise, and bleed values
- bleed-state escalation and player-facing injury reporting
- first-aid tending with temporary bleed suppression rather than trivial instant reset
- reopen behavior for wounds after tending expires
- empath-style injury transfer foundations

### Skills, abilities, and progression foundations

- shared skill registry with starter baselines
- skill categories across combat, armor, survival, lore, and magic
- guild-locked visibility hooks for future profession identity
- ability visibility, cooldown, and execution scaffolding
- mindstate and learning-oriented support paths

### World interaction and item systems

- inventory inspection and action routing
- wearing, removing, wielding, unwielding, stowing, and drawing
- wearable containers and sheaths
- traps, lockpicks, locksmithing-oriented interactions, and survival tools
- vendors, spawning helpers, and test-world utility commands

### Magic and guild-facing foundations

- spell preparation and release flow
- category-driven spell handling
- targeted, augmentation, debilitation, warding, and utility support layers
- cyclic spell scaffolding
- guild-aware access hooks for future spellbook identity

### Browser map and navigation systems

- structured server-side map payloads
- zone maps for AreaForge-tagged areas
- deterministic local-map fallback for rooms without authored coordinates
- fullscreen map mode
- pan, fit, and center controls
- click-to-route and auto-walk from exit graph pathfinding
- stable fallback layout anchoring so compact areas do not shift while moving

## Tech Stack

- Python 3.11
- Evennia
- Django via Evennia's web stack
- custom JavaScript/CSS browser client under [web/static/webclient](web/static/webclient)
- game logic in [typeclasses](typeclasses), [commands](commands), and [world](world)

## Project Layout

- [typeclasses](typeclasses): characters, rooms, objects, NPCs, weapons, armor, spells, and gameplay rules
- [commands](commands): player verbs, admin/debug commands, and system actions
- [world/area_forge](world/area_forge): AreaForge extraction, review, serialization, and map APIs
- [web/templates/webclient](web/templates/webclient): custom browser client template
- [web/static/webclient](web/static/webclient): browser client JS and CSS
- [server/conf](server/conf): Evennia configuration and startup hooks
- [maps](maps): source map assets used for AreaForge intake

## Running Locally

From the project root:

```powershell
evennia migrate
evennia start
```

Then open the browser client:

```text
http://localhost:4005/webclient/
```

If your local ports differ, check [server/conf/settings.py](server/conf/settings.py).

## Useful Test Commands

Some helpful flows already present in the repo:

- `attack training dummy` for combat loop testing
- `stats`, `injuries`, and `mindstate` for state inspection
- `renew`, `renew room`, and `renew all` for test resets
- `spawnweapon`, `spawnwearable`, `spawnsheath`, `spawnvendor`, and related debug spawners
- `maptest local` and `maptest zone` for structured map payload checks

DireTest currently has these live scenario entrypoints:

```powershell
c:/Users/gary/dragonsire/.venv/Scripts/python.exe diretest.py list
c:/Users/gary/dragonsire/.venv/Scripts/python.exe diretest.py balance-baseline --seed 1234
c:/Users/gary/dragonsire/.venv/Scripts/python.exe diretest.py scenario race-balance
c:/Users/gary/dragonsire/.venv/Scripts/python.exe diretest.py scenario movement --seed 1234
c:/Users/gary/dragonsire/.venv/Scripts/python.exe diretest.py scenario inventory --seed 1234
c:/Users/gary/dragonsire/.venv/Scripts/python.exe diretest.py scenario combat-basic --seed 1234
c:/Users/gary/dragonsire/.venv/Scripts/python.exe diretest.py scenario death-loop --seed 1234
c:/Users/gary/dragonsire/.venv/Scripts/python.exe diretest.py scenario grave-recovery --seed 1234
c:/Users/gary/dragonsire/.venv/Scripts/python.exe diretest.py scenario economy --seed 1234
c:/Users/gary/dragonsire/.venv/Scripts/python.exe diretest.py scenario bank --seed 1234
c:/Users/gary/dragonsire/.venv/Scripts/python.exe diretest.py repro artifacts/bank_direct_1234
c:/Users/gary/dragonsire/.venv/Scripts/python.exe diretest.py diff artifacts/bank_direct_1234/snapshots.json::initial artifacts/bank_direct_1234/snapshots.json::deposited
```

Optional flags:

- `--profession commoner`
- `--sample-weight 80`
- `--base-xp 100`
- `--json`

The direct gameplay scenarios now cover movement, inventory, basic combat, death and depart loops, grave recovery, vendor trading, and banking. Artifact bundles under `artifacts/` now include `diffs.json`, `failure_summary.json`, timing and delta metrics, and replayable scenario metadata.

`diretest.py balance-baseline --seed <n>` is the first descriptive balance pass. It rolls up combat outcomes, economy flow, and onboarding progression pacing into a single artifact-backed report without adding hard balance gates yet.

## Development Notes

- The repository includes implementation reports and task-range reports documenting major system work.
- The browser client is the active player-facing target.
- AreaForge build artifacts are intentionally kept out of git by the current ignore rules.
- The codebase is under active development and still contains placeholder and future-facing hooks where deeper guild, spell, economy, and content systems will expand.

## License

DireEngine is licensed under the BSD 3-Clause License in [LICENSE.txt](LICENSE.txt).

This repository also includes Evennia-derived and Evennia-dependent work. Evennia's license is included separately in [LICENSE.evennia.txt](LICENSE.evennia.txt).

## Direction

DireEngine is building toward a full modern text-world platform that preserves the identity of classic skill-based fantasy MUDs while removing the cost and friction that kept those experiences niche.

If the old goal was "make a deep text world players can disappear into," the new goal is:

Build that world again, make it sharper, make it easier to enter, and keep it open.
